extends RefCounted

# Real imported assets are required. These checks cover skin/clock/socket
# integration; deformation appearance, gameplay contact and GPU cost still
# require the separate rendered art review.
const PROFILES: Array[String] = ["hero", "sentinel_melee"]
const GRIP_TO_TIP_M := 1.19
const TOTAL_SWORD_M := 1.35

static func _meshes(root: Node) -> Array[MeshInstance3D]:
	var result: Array[MeshInstance3D] = []
	if root is MeshInstance3D:
		result.append(root)
	for child in root.get_children():
		result.append_array(_meshes(child))
	return result

static func _rest_bounds(visual: ActorVisual) -> Dictionary:
	var lower := Vector3(INF, INF, INF)
	var upper := Vector3(-INF, -INF, -INF)
	var count := 0
	var weighted_meshes := 0
	for mesh in _meshes(visual.skeletal_bridge.rig):
		if mesh.skin == null:
			continue
		if mesh.skin.get_bind_count() != 53:
			return {"ok":false}
		var skeleton := mesh.get_node_or_null(mesh.skeleton) as Skeleton3D
		if skeleton == null or mesh.mesh == null:
			return {"ok":false}
		var skin_transforms: Array[Transform3D] = []
		for bind in range(mesh.skin.get_bind_count()):
			var bone := mesh.skin.get_bind_bone(bind)
			if bone < 0:
				bone = skeleton.find_bone(mesh.skin.get_bind_name(bind))
			if bone < 0 or bone >= skeleton.get_bone_count():
				return {"ok":false}
			skin_transforms.append(skeleton.get_bone_global_rest(bone) * mesh.skin.get_bind_pose(bind))
		var into_actor := visual.global_transform.affine_inverse() * skeleton.global_transform
		for surface in range(mesh.mesh.get_surface_count()):
			var arrays := mesh.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var bone_ids: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
			var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
			if vertices.is_empty() or bone_ids.size() != weights.size() or weights.size() % vertices.size() != 0:
				return {"ok":false}
			var influences: int = weights.size() / vertices.size()
			for vertex in range(vertices.size()):
				var point := Vector3.ZERO
				for influence in range(influences):
					var offset := vertex * influences + influence
					var bind := bone_ids[offset]
					if bind < 0 or bind >= skin_transforms.size():
						return {"ok":false}
					point += (skin_transforms[bind] * vertices[vertex]) * weights[offset]
				point = into_actor * point
				if not point.is_finite():
					return {"ok":false}
				lower = lower.min(point)
				upper = upper.max(point)
				count += 1
		weighted_meshes += 1
	return {"ok":count > 0, "lower":lower, "upper":upper, "vertices":count, "meshes":weighted_meshes}

static func _weapon_span(visual: ActorVisual) -> float:
	if not is_instance_valid(visual.rig_weapon):
		return -1.0
	var grip := visual.rig_weapon.find_child("GripOrigin", true, false) as Node3D
	var tip := visual.rig_weapon.find_child("BladeTip", true, false) as Node3D
	return grip.global_position.distance_to(tip.global_position) if grip != null and tip != null else -1.0

static func _weapon_direction(visual: ActorVisual) -> Vector3:
	var grip := visual.rig_weapon.find_child("GripOrigin", true, false) as Node3D
	var tip := visual.rig_weapon.find_child("BladeTip", true, false) as Node3D
	if grip == null or tip == null:
		return Vector3.ZERO
	return (visual.global_basis.inverse() * (tip.global_position-grip.global_position)).normalized()

static func _weapon_axial_length(visual: ActorVisual) -> float:
	var grip := visual.rig_weapon.find_child("GripOrigin", true, false) as Node3D
	var tip := visual.rig_weapon.find_child("BladeTip", true, false) as Node3D
	if grip == null or tip == null:
		return -1.0
	var axis := grip.global_position.direction_to(tip.global_position)
	var lower := INF
	var upper := -INF
	for mesh in _meshes(visual.rig_weapon):
		var box := mesh.get_aabb()
		for corner in range(8):
			var projection := (mesh.global_transform * box.get_endpoint(corner)).dot(axis)
			lower = minf(lower, projection)
			upper = maxf(upper, projection)
	return upper-lower

static func _socket_matches_current_pose(visual: ActorVisual) -> bool:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var hand := skeleton.find_bone("RightHand")
	if hand < 0 or not is_instance_valid(visual.weapon_socket):
		return false
	var expected := skeleton.global_transform * skeleton.get_bone_global_pose(hand)
	return visual.weapon_socket.global_transform.is_equal_approx(expected)

static func _textured(mesh: MeshInstance3D, has_eyelid_wall: bool = false) -> bool:
	if mesh.mesh == null or mesh.material_override != null:
		return false
	for surface in range(mesh.mesh.get_surface_count()):
		if mesh.get_surface_override_material(surface) != null:
			return false
		var material := mesh.get_active_material(surface) as BaseMaterial3D
		# The eye-opening derivative adds exactly one opaque, nonmetallic inner
		# lid wall. Only that named second body surface is intentionally plain.
		if has_eyelid_wall and surface == 1:
			if material == null or material.resource_name != "NewEyelidInnerDepth" or material.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED or material.metallic != 0.0 or absf(material.roughness-0.57) > 0.0001 or material.albedo_texture != null:
				return false
			continue
		if material == null or material.albedo_texture == null or material.normal_texture == null:
			return false
	return mesh.mesh.get_surface_count() == 2 if has_eyelid_wall else mesh.mesh.get_surface_count() > 0

static func _pose(visual: ActorVisual, snapshot: Dictionary, delta: float = 0.0) -> void:
	visual.pose(delta, float(snapshot.get("speed", 0.0)), -1.0, false, false, false, snapshot)

static func _supported(visual: ActorVisual, state: StringName, snapshot: Dictionary) -> bool:
	_pose(visual, snapshot)
	return visual.skeletal_bridge.visible and not visual.model.visible and visual.skeletal_bridge.selected_state == state and _socket_matches_current_pose(visual) and absf(_weapon_span(visual) - GRIP_TO_TIP_M) < 0.002

static func _gait_moves_feet(visual: ActorVisual, state: StringName, snapshot: Dictionary) -> bool:
	var bridge := visual.skeletal_bridge
	bridge.reset_presentation()
	_pose(visual, snapshot)
	var skeleton := bridge.get_skeleton()
	var left := skeleton.find_bone("LeftFoot")
	var right := skeleton.find_bone("RightFoot")
	if left < 0 or right < 0:
		return false
	var first_left := skeleton.get_bone_global_pose(left).origin
	var first_right := skeleton.get_bone_global_pose(right).origin
	var length := bridge.animation_player.get_animation(bridge.clips[state]).length
	_pose(visual, snapshot, length*0.25)
	var distance := maxf(first_left.distance_to(skeleton.get_bone_global_pose(left).origin), first_right.distance_to(skeleton.get_bone_global_pose(right).origin))
	return distance > 0.03 and bridge.selected_state == state and _socket_matches_current_pose(visual)

static func _action(profile: String, state: StringName, elapsed: float, duration: float) -> Dictionary:
	var snapshot := {"speed":0.0, "locomotion_reference_speed":3.6 if profile == "sentinel_melee" else 6.4}
	match state:
		&"dodge":
			snapshot.merge({"dodge_remaining":maxf(0.0001, duration-elapsed), "dodge_elapsed":elapsed, "dodge_duration":duration, "dodge_local_x":0.0, "dodge_local_z":-1.0})
		&"hit", &"heavy_hit":
			snapshot.merge({"stagger":maxf(0.0001, duration-elapsed), "hit_elapsed":elapsed, "hit_duration":duration, "hit_reaction":String(state)})
		&"parry":
			snapshot.merge({"parry_remaining":maxf(0.0001, duration-elapsed), "parry_elapsed":elapsed, "parry_duration":duration})
		&"charge":
			snapshot.merge({"charge_active":true, "charge_elapsed":elapsed, "charge_duration":duration})
		&"heal":
			snapshot.merge({"heal_remaining":maxf(0.0001, duration-elapsed), "heal_elapsed":elapsed, "heal_duration":duration})
		&"death":
			snapshot.merge({"dead":true, "death_elapsed":elapsed, "death_duration":duration})
		_:
			snapshot.merge({"attack_id":String(state), "attack_elapsed":elapsed, "attack_duration":duration})
	return snapshot

static func _charge_checks(visual: ActorVisual, check: Callable) -> void:
	var bridge := visual.skeletal_bridge
	var skeleton := bridge.get_skeleton()
	var hips := skeleton.find_bone("Hips")
	var grip := visual.rig_weapon.find_child("GripOrigin", true, false) as Node3D
	if hips < 0 or grip == null:
		check.call(false, "Hero charge resolves its actual hips and weapon grip")
		return
	# A new idle sample is the anatomical baseline. Finger rotations cannot
	# move either of these markers, so a fist-only end key cannot pass.
	bridge.reset_presentation(70001)
	_pose(visual, {"speed":0.0, "presentation_epoch":70001})
	var idle_hips_y := (skeleton.global_transform*skeleton.get_bone_global_pose(hips)).origin.y
	var idle_grip := grip.global_position
	var charged := _action("hero", &"charge", 0.65, 0.65)
	charged["presentation_epoch"] = 70001
	_pose(visual, charged)
	var charged_hips_y := (skeleton.global_transform*skeleton.get_bone_global_pose(hips)).origin.y
	var charged_grip := grip.global_position
	var hip_drop := idle_hips_y-charged_hips_y
	var grip_travel := idle_grip.distance_to(charged_grip)
	check.call(bridge.selected_state == &"charge" and (hip_drop >= 0.02 or grip_travel >= 0.02), "Hero full charge remains a prepared body/weapon pose instead of returning to idle with finger-only changes")
	var charged_bones: Array[Transform3D] = []
	for index in range(skeleton.get_bone_count()):
		charged_bones.append(skeleton.get_bone_pose(index))
	charged["charge_elapsed"] = 1.3
	_pose(visual, charged)
	var held := absf((skeleton.global_transform*skeleton.get_bone_global_pose(hips)).origin.y-charged_hips_y) < 0.00001 and grip.global_position.distance_to(charged_grip) < 0.00001
	for index in range(charged_bones.size()):
		held = held and skeleton.get_bone_pose(index).is_equal_approx(charged_bones[index])
	check.call(held and bridge.selected_state == &"charge", "Holding charge beyond .65s retains the full prepared skeleton and weapon pose without cycling back")
	print("RUNEFALL_CHARGE_PREPARATION: ", JSON.stringify({"hip_drop_m":hip_drop, "grip_travel_m":grip_travel, "held":held}))

static func _profile_checks(world: Node3D, check: Callable, profile: String) -> bool:
	var prepared := ProductionCharacterArt.prepare(profile)
	check.call(prepared.ok, "%s real production asset is installed with every required authored clip" % profile)
	if not prepared.ok:
		return false
	var visual := ActorVisual.new()
	world.add_child(visual)
	visual.position = Vector3(3, 0, 4)
	visual.rotation.y = 0.37
	visual.setup("hero" if profile == "hero" else "sentinel")
	var result := visual.use_production_profile(profile)
	check.call(result.ok, "%s mounts its actual weighted character and reviewed weapon socket" % profile)
	if not result.ok:
		visual.free()
		return false
	var bridge := visual.skeletal_bridge
	var skeleton := bridge.get_skeleton()
	var hand := skeleton.find_bone("RightHand")
	check.call(skeleton.get_bone_count() == 53 and hand >= 0 and visual.weapon_socket.get_parent() == skeleton and visual.weapon_grip.get_parent() == visual.weapon_socket, "%s uses the actual 53-bone hand and a separate grip-offset child" % profile)
	var map := skeleton.get_meta("humanoid_bone_map", null) as BoneMap
	check.call(map != null and map.get_skeleton_bone_name(&"RightHand") == &"RightHand" and map.get_skeleton_bone_name(&"Hips") == &"Hips", "%s carries explicit humanoid hand and hips mappings" % profile)
	check.call(absf(bridge.rig.rotation.y-PI) < 0.00001 and absf(visual.model.rotation.y-PI) < 0.00001, "%s corrects imported forward once, independently of the hidden pivot model" % profile)
	var bounds := _rest_bounds(visual)
	var expected_height: float = prepared.config.height
	check.call(bounds.ok and absf(bounds.upper.y-bounds.lower.y-expected_height) < 0.001 and absf(bounds.lower.y) < 0.001, "%s CPU-skinned REST height and soles match its meter-scale capsule contract" % profile)
	check.call(absf(_weapon_span(visual)-GRIP_TO_TIP_M) < 0.002 and absf(_weapon_axial_length(visual)-TOTAL_SWORD_M) < 0.003, "%s keeps the real 1.19m grip-to-tip and 1.35m total sword instead of inheriting the body normalization scale" % profile)
	var materials_ok := true
	var body_count := 0
	for mesh in _meshes(bridge.rig):
		if is_instance_valid(visual.eye_model) and visual.eye_model.is_ancestor_of(mesh):
			continue # Procedural eye parts have their own explicit material audit.
		var body := mesh.skin != null
		body_count += int(body)
		materials_ok = materials_ok and _textured(mesh, profile == "hero" and body)
	check.call(materials_ok and body_count == 1, "%s preserves textured body/sword PBR; only the explicit inner eyelid surface is plain" % profile)
	var actor_transform := visual.transform
	var actions: Dictionary = {&"death":bridge.animation_player.get_animation(&"death").length, &"hit":0.15 if profile == "hero" else 0.28}
	if profile == "hero":
		for index in range(3):
			actions[StringName("light_%d" % (index+1))] = RunePlayer.LIGHTS[index].duration()
		actions.merge({&"heavy":RunePlayer.HEAVY.duration(), &"charged_heavy":RunePlayer.CHARGED_HEAVY.duration(), &"skill_1":0.79, &"skill_2":0.79, &"skill_3":0.79, &"dodge":0.32, &"parry":0.22, &"charge":0.65, &"heal":0.35})
	else:
		actions[&"enemy_attack"] = RuneEnemy.BASE_ATTACK.duration()
		actions[&"heavy_hit"] = 0.48
	var actions_ok := true
	var clocks_ok := true
	var root_motion_ok := true
	var root_bone := skeleton.find_bone("Root")
	var root_origin := skeleton.get_bone_global_pose(root_bone).origin
	var max_hand_travel := 0.0
	var first_hand := (skeleton.global_transform * skeleton.get_bone_global_pose(hand)).origin
	for state: StringName in actions:
		var duration: float = actions[state]
		clocks_ok = clocks_ok and absf(bridge.animation_player.get_animation(state).length-duration) < 0.001
		for fraction in [0.0, 0.25, 0.5, 0.9, 1.0]:
			actions_ok = _supported(visual, state, _action(profile, state, duration*float(fraction), duration)) and actions_ok
			var root_position := skeleton.get_bone_global_pose(root_bone).origin
			root_motion_ok = root_motion_ok and Vector2(root_position.x-root_origin.x,root_position.z-root_origin.z).length() < 0.001
			max_hand_travel = maxf(max_hand_travel, first_hand.distance_to((skeleton.global_transform * skeleton.get_bone_global_pose(hand)).origin))
	check.call(clocks_ok, "%s authored action lengths agree with actual gameplay windows rather than long stock aliases" % profile)
	check.call(actions_ok and max_hand_travel > 0.02, "%s real action tracks deform the hand and update its weapon in the same manual sample without pivot fallback" % profile)
	check.call(root_motion_ok, "%s action clips do not introduce horizontal skeletal root motion beside the gameplay controller" % profile)
	if profile == "hero":
		var arcs_ok := true
		for index in range(3):
			var attack: AttackData = RunePlayer.LIGHTS[index]
			for fraction in [0.01, 0.25, 0.5, 0.75, 0.99]:
				_pose(visual, _action(profile, StringName("light_%d" % (index+1)), attack.startup+attack.active*float(fraction), attack.duration()))
				var direction := _weapon_direction(visual)
				var horizontal := Vector3(direction.x,0,direction.z)
				var target := Vector3.FORWARD.rotated(Vector3.UP, deg_to_rad(lerpf(-attack.arc*0.5,attack.arc*0.5,float(fraction))))
				arcs_ok = arcs_ok and horizontal.length() > 0.9 and horizontal.normalized().dot(target) >= cos(deg_to_rad(5.0))
		check.call(arcs_ok, "All three real light-attack blades follow the gameplay sweep direction during their active windows")
		_charge_checks(visual, check)
	var move_speed := 3.6 if profile == "sentinel_melee" else 6.4
	var movement_ok := _supported(visual, &"idle", {"speed":0.0})
	var feet_move := true
	for state: StringName in [&"walk", &"walk_back", &"walk_left", &"walk_right", &"run"]:
		var direction := Vector2(0, -1)
		if state == &"walk_back":
			direction = Vector2(0, 1)
		elif state == &"walk_left":
			direction = Vector2(-1, 0)
		elif state == &"walk_right":
			direction = Vector2(1, 0)
		var speed := 8.5 if state == &"run" else move_speed
		var snapshot := {"speed":speed, "move_local_x":direction.x, "move_local_z":direction.y, "locomotion_reference_speed":speed}
		movement_ok = _supported(visual, state, snapshot) and movement_ok
		feet_move = _gait_moves_feet(visual, state, snapshot) and feet_move
	check.call(movement_ok, "%s actual forward, backward and side cycles remain skeletal for gameplay movement and separation" % profile)
	check.call(feet_move, "%s imported gait cycles actually move weighted foot bones instead of reusing a static pose" % profile)
	if profile == "hero":
		var dodges_ok := true
		for direction in [Vector2(0,-1), Vector2(0,1), Vector2(-1,0), Vector2(1,0)]:
			for time in [0.0, 0.16, 0.30]:
				var snapshot := {"speed":0.0, "dodge_remaining":0.32-time, "dodge_elapsed":time, "dodge_duration":0.32, "dodge_local_x":direction.x, "dodge_local_z":direction.y}
				dodges_ok = _supported(visual, &"dodge", snapshot) and dodges_ok
		check.call(dodges_ok, "Hero directional dodges retain the real skin and same-frame hand attachment in all four directions")
	_pose(visual, {"speed":0.0})
	check.call(visual.transform.is_equal_approx(actor_transform) and absf(bridge.rig.rotation.y-PI) < 0.00001, "%s action/dodge sampling leaves actor movement and facing authoritative and restores visual yaw" % profile)
	var freeze_state: StringName = &"light_1" if profile == "hero" else &"enemy_attack"
	var freeze_duration: float = RunePlayer.LIGHTS[0].duration() if profile == "hero" else RuneEnemy.BASE_ATTACK.duration()
	_pose(visual, _action(profile, freeze_state, freeze_duration*0.5, freeze_duration))
	var frozen_hand := skeleton.global_transform * skeleton.get_bone_global_pose(hand)
	var frozen_socket := visual.weapon_socket.global_transform
	await world.get_tree().process_frame
	await world.get_tree().process_frame
	check.call((skeleton.global_transform*skeleton.get_bone_global_pose(hand)).is_equal_approx(frozen_hand) and visual.weapon_socket.global_transform.is_equal_approx(frozen_socket), "%s real rig and weapon hold a hit-paused sample without independent animation playback" % profile)
	visual.scale = Vector3.ONE * 1.25
	_pose(visual, _action(profile, &"light_1" if profile == "hero" else &"enemy_attack", 0.1, 0.52 if profile == "hero" else 1.5))
	check.call(absf(_weapon_span(visual)-GRIP_TO_TIP_M*1.25) < 0.002 and absf(_weapon_axial_length(visual)-TOTAL_SWORD_M*1.25) < 0.003 and _socket_matches_current_pose(visual), "%s weapon cancels only internal rig scale while retaining the external actor scale" % profile)
	visual.free()
	return true

static func _capsule_checks(world: Node3D, check: Callable) -> void:
	for profile: String in PROFILES:
		var actor = RunePlayer.new() if profile == "hero" else RuneEnemy.new()
		world.add_child(actor)
		actor.set_physics_process(false)
		var shape: CollisionShape3D
		for child in actor.get_children():
			if child is CollisionShape3D and child.shape is CapsuleShape3D:
				shape = child
		var radius := 0.36 if profile == "hero" else 0.4
		var height := 1.85 if profile == "hero" else 1.95
		var centre := 0.95 if profile == "hero" else 0.975
		var capsule := shape.shape as CapsuleShape3D if shape != null else null
		var expected_layer := 2 if profile == "hero" else 4
		var expected_mask := 5 if profile == "hero" else 7
		check.call(capsule != null and absf(capsule.radius-radius) < 0.00001 and absf(capsule.height-height) < 0.00001 and absf(shape.position.y-centre) < 0.00001 and actor.collision_layer == expected_layer and actor.collision_mask == expected_mask, "%s production body preserves the existing gameplay capsule dimensions, height and collision layers" % profile)
		var visual: ActorVisual = actor.visual
		var before_transform: Transform3D = actor.transform
		var before_layer: int = actor.collision_layer
		var before_mask: int = actor.collision_mask
		var before_health: float = actor.health
		var before_shape: Shape3D = shape.shape if shape != null else null
		visual.clear_rig()
		var result := visual.use_production_profile(profile)
		check.call(result.ok and actor.transform.is_equal_approx(before_transform) and actor.collision_layer == before_layer and actor.collision_mask == before_mask and actor.health == before_health and shape != null and shape.shape == before_shape, "%s art replacement never moves the controller, replaces collision, or changes health" % profile)
		var sole_y := (shape.global_transform * Vector3(0,-height*0.5,0)).y if shape != null else INF
		check.call(absf(visual.global_position.y-sole_y) < 0.00001 and absf(visual.position.y-(centre-height*0.5)) < 0.00001, "%s normalized soles align to the unchanged capsule bottom, including the hero's 2.5cm controller offset" % profile)
		actor.free()

static func run(world: Node3D, check: Callable) -> bool:
	for profile in PROFILES:
		if not await _profile_checks(world, check, profile):
			return false
	_capsule_checks(world, check)
	return true
