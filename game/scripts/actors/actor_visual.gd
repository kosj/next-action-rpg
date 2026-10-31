class_name ActorVisual
extends Node3D

const RUNE_SWORD_SCENE: PackedScene = preload("res://assets/models/production/rune_sword_web.glb")

var model: Node3D
var joints: Dictionary = {}
var clock: float = 0.0
var base_scale: Vector3 = Vector3.ONE
var skeletal_bridge: SkeletalVisualBridge
var rig_status: String = "Prototype pivot visual"
var production_profile: String = ""
var weapon_socket: BoneAttachment3D
var weapon_grip: Node3D
var rig_weapon: Node3D
var ground_offset_y: float = 0.0
var blade_trail: BladeTrail
var _blade_grip_marker: Node3D
var _blade_tip_marker: Node3D
var eye_socket: BoneAttachment3D
var eye_model: Node3D

func use_production_profile(profile: String) -> Dictionary:
	var prepared := ProductionCharacterArt.prepare(profile)
	if not prepared.ok:
		rig_status = prepared.reason
		return prepared
	var grip := _read_grip(profile)
	if not grip.ok:
		rig_status = grip.reason
		return grip
	var result := mount_rig(prepared.scene, {}, prepared.states)
	if not result.ok:
		return result
	var transitions := skeletal_bridge.enable_transition_polish()
	if not transitions.ok:
		clear_rig()
		rig_status = transitions.reason
		return transitions
	production_profile = profile
	ground_offset_y = _capsule_floor_offset()
	var skeleton := ProductionCharacterArt.find_type(skeletal_bridge.rig, "Skeleton3D") as Skeleton3D
	if prepared.eyes != null and not _mount_eyes(skeleton, prepared.eyes):
		clear_rig()
		rig_status = "Character eyes require a positive uniform rig scale and identity asset root"
		return {"ok":false, "reason":rig_status}
	weapon_socket = BoneAttachment3D.new()
	weapon_socket.name = "RightHandWeaponSocket"
	weapon_socket.bone_name = &"RightHand"
	skeleton.add_child(weapon_socket)
	weapon_socket.on_skeleton_update()
	weapon_grip = Node3D.new()
	weapon_grip.name = "WeaponGrip"
	weapon_socket.add_child(weapon_grip)
	# The GLB's height-normalization wrapper is inherited by the hand. Cancel
	# that uniform scale here, preserving the actor's own scale and 1.35m sword.
	var relative := skeletal_bridge.global_transform.affine_inverse() * weapon_socket.global_transform
	var inherited := relative.basis.get_scale()
	if inherited.x <= 0.0 or absf(inherited.x-inherited.y) > 0.0001 or absf(inherited.x-inherited.z) > 0.0001:
		clear_rig()
		rig_status = "Weapon socket requires a uniform, positive rig scale"
		return {"ok":false, "reason":rig_status}
	weapon_grip.transform = Transform3D(grip.basis.scaled(Vector3.ONE/inherited.x), grip.offset/inherited.x)
	rig_weapon = RUNE_SWORD_SCENE.instantiate() as Node3D
	rig_weapon.name = "Runeblade"
	weapon_grip.add_child(rig_weapon)
	_blade_grip_marker = rig_weapon.find_child("GripOrigin", true, false) as Node3D
	_blade_tip_marker = rig_weapon.find_child("BladeTip", true, false) as Node3D
	blade_trail = BladeTrail.new()
	blade_trail.name = "BladeMotionRibbon"
	blade_trail.tint = Color("8bd9cb") if profile == "hero" else Color("d3bda3")
	add_child(blade_trail)
	pose(0.0, 0.0, -1.0, false, false, false, {"speed":0.0})
	return result

func _mount_eyes(skeleton: Skeleton3D, scene: PackedScene) -> bool:
	eye_socket = BoneAttachment3D.new()
	eye_socket.name = "HeadEyeSocket"
	eye_socket.bone_name = &"Head"
	skeleton.add_child(eye_socket)
	eye_socket.on_skeleton_update()
	var relative := skeletal_bridge.global_transform.affine_inverse() * eye_socket.global_transform
	var inherited := relative.basis.get_scale()
	if inherited.x <= 0.0 or absf(inherited.x-inherited.y) > 0.0001 or absf(inherited.x-inherited.z) > 0.0001:
		return false
	eye_model = scene.instantiate() as Node3D
	if eye_model == null or not eye_model.transform.is_equal_approx(Transform3D.IDENTITY):
		if eye_model != null:
			eye_model.free()
		eye_model = null
		return false
	eye_model.name = "LyraEyes"
	eye_socket.add_child(eye_model)
	# Vertices are already physical meters in the original Head-local rigid
	# basis. Cancel only the imported normalization, preserving actor scale.
	eye_model.scale = Vector3.ONE/inherited.x
	return true

func _capsule_floor_offset() -> float:
	# The player's capsule bottom is .025m above its controller origin. Align
	# the normalized boot sole to that bottom without moving the collider/body.
	if get_parent() is CharacterBody3D:
		for child in get_parent().get_children():
			if child is CollisionShape3D and child.shape is CapsuleShape3D and not child.disabled:
				return child.position.y - child.shape.height * 0.5
	return 0.0

func _read_grip(profile: String) -> Dictionary:
	var path := "res://data/character_grips.json"
	if not FileAccess.file_exists(path):
		return {"ok":false, "reason":"Character weapon grip is not installed"}
	var document = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not document is Dictionary or not document.get(profile) is Dictionary:
		return {"ok":false, "reason":"Character weapon grip is not defined: " + profile}
	var entry: Dictionary = document[profile]
	var axes = entry.get("basis_columns", [])
	var offset = entry.get("offset_m", [])
	if not axes is Array or axes.size() != 9 or not offset is Array or offset.size() != 3:
		return {"ok":false, "reason":"Character weapon grip has invalid dimensions"}
	for value in axes + offset:
		if not (value is float or value is int) or not is_finite(float(value)):
			return {"ok":false, "reason":"Character weapon grip must be finite"}
	var basis := Basis(Vector3(axes[0],axes[1],axes[2]), Vector3(axes[3],axes[4],axes[5]), Vector3(axes[6],axes[7],axes[8]))
	var point := Vector3(offset[0],offset[1],offset[2])
	if not basis.is_equal_approx(basis.orthonormalized()) or basis.determinant() < 0.9999 or point.length() > 0.25:
		return {"ok":false, "reason":"Character weapon grip must be a right-handed unit basis near the palm"}
	return {"ok":true, "basis":basis, "offset":point}

func presentation_report() -> Dictionary:
	var skeletal := is_instance_valid(skeletal_bridge) and skeletal_bridge.visible
	var length := 0.0
	if is_instance_valid(rig_weapon):
		var grip := rig_weapon.find_child("GripOrigin", true, false) as Node3D
		var tip := rig_weapon.find_child("BladeTip", true, false) as Node3D
		if grip != null and tip != null:
			length = grip.global_position.distance_to(tip.global_position)
	return {"mode":"skeletal" if skeletal else "prototype", "profile":production_profile,
		"state":String(skeletal_bridge.selected_state) if skeletal else "", "weapon_attached":is_instance_valid(weapon_socket),
		"grip_to_tip_m":length, "status":rig_status,
		"eyes_attached":is_instance_valid(eye_socket) and is_instance_valid(eye_model),
		"blade_trail":blade_trail.presentation_report() if is_instance_valid(blade_trail) else {}}

func mount_rig(scene: PackedScene, aliases: Dictionary = {}, required_states: Array[StringName] = SkeletalVisualBridge.REQUIRED_STATES, facing_correction: float = PI) -> Dictionary:
	var candidate := SkeletalVisualBridge.new()
	add_child(candidate)
	var result := candidate.mount_scene(scene, aliases, required_states, facing_correction)
	if not result.ok:
		rig_status = result.reason
		candidate.free()
		return result
	clear_rig()
	skeletal_bridge = candidate
	rig_status = "Rig ready; visual quality remains subject to art review"
	return result

func clear_rig() -> void:
	if is_instance_valid(blade_trail):
		blade_trail.free()
	blade_trail = null
	_blade_grip_marker = null
	_blade_tip_marker = null
	weapon_socket = null
	weapon_grip = null
	rig_weapon = null
	eye_socket = null
	eye_model = null
	production_profile = ""
	ground_offset_y = 0.0
	if is_instance_valid(skeletal_bridge):
		skeletal_bridge.free()
	skeletal_bridge = null
	if is_instance_valid(model):
		model.show()
	rig_status = "Prototype pivot visual"

func setup(kind: String) -> void:
	model = load("res://assets/models/%s.glb" % kind).instantiate()
	# Blender faces -Y, which glTF maps to +Z. Face Godot forward (-Z).
	model.rotation.y = PI
	add_child(model)
	_collect(model)
	if kind == "hero":
		_replace_hero_sword()

func _replace_hero_sword() -> void:
	var socket := joints.get("Sword") as Node3D
	if socket == null:
		return
	# Keep the existing grip transform and pivot animation. The replacement lives
	# inside the prototype model so rig visibility and fallback include its weapon.
	for child in socket.get_children():
		if child is MeshInstance3D:
			child.hide()
	var replacement := RUNE_SWORD_SCENE.instantiate() as Node3D
	replacement.name = "RuneSwordPreview"
	# Canonical blade +Y -> prototype blade -Y; keep its broad face normal +Z.
	replacement.rotation.z = PI
	socket.add_child(replacement)

func _collect(node: Node) -> void:
	if node is Node3D:
		joints[String(node.name)] = node
	for child in node.get_children():
		_collect(child)

func pose(delta: float, speed: float, swing: float = -1.0, dodge: bool = false, parry: bool = false, dead: bool = false, snapshot: Dictionary = {}) -> void:
	if is_instance_valid(skeletal_bridge):
		var presented := skeletal_bridge.present(delta, snapshot if not snapshot.is_empty() else {"speed":speed, "dead":dead})
		skeletal_bridge.visible = presented
		if is_instance_valid(model):
			model.visible = not presented
		if presented:
			position.y = ground_offset_y
			rotation.z = 0.0
			if is_instance_valid(weapon_socket):
				# Skeleton's normal notification is deferred. The baked rig has no
				# modifiers: update this hand socket after this exact manual sample.
				weapon_socket.on_skeleton_update()
			if is_instance_valid(eye_socket):
				eye_socket.on_skeleton_update()
			if is_instance_valid(blade_trail) and is_instance_valid(_blade_grip_marker) and is_instance_valid(_blade_tip_marker):
				blade_trail.sample_pose(delta, snapshot, _blade_grip_marker.global_position, _blade_tip_marker.global_position)
			return
		rig_status = skeletal_bridge.last_error
		if is_instance_valid(blade_trail):
			blade_trail.reset()
	clock += delta * (5.0 + speed * 1.8)
	var stride := minf(speed / 6.0, 1.0)
	_set_joint("LegL", Vector3(sin(clock) * 0.65 * stride, 0, 0))
	_set_joint("LegR", Vector3(-sin(clock) * 0.65 * stride, 0, 0))
	_set_joint("KneeL", Vector3(-maxf(0, -sin(clock)) * 0.7 * stride, 0, 0))
	_set_joint("KneeR", Vector3(-maxf(0, sin(clock)) * 0.7 * stride, 0, 0))
	_set_joint("ArmL", Vector3(-sin(clock) * 0.45 * stride, 0, -0.12))
	_set_joint("ArmR", Vector3(sin(clock) * 0.35 * stride - 0.2, 0, 0.15))
	_set_joint("ElbowR", Vector3(0.15, 0, 0))
	_set_joint("Torso", Vector3(0.07 * stride, 0, 0))
	if swing >= 0.0:
		var motion := sin(swing * PI)
		_set_joint("ArmR", Vector3(-1.1 - motion * 0.6, -1.5 + swing * 3.5, 0.7))
		_set_joint("ElbowR", Vector3(-0.45, 0, 0))
		_set_joint("Torso", Vector3(0.08, -0.55 + swing * 1.1, 0))
		_set_joint("ArmL", Vector3(-0.4, 0, -0.4))
	if parry:
		_set_joint("ArmR", Vector3(-1.35, -0.5, 0.65))
		_set_joint("ArmL", Vector3(-0.9, 0, -0.25))
	if dodge:
		_set_joint("Torso", Vector3(0.5, 0, 0))
	position.y = absf(sin(clock)) * 0.04 * stride
	rotation.z = lerp_angle(rotation.z, -1.45 if dead else 0.0, minf(1.0, delta * 6.0))

func _set_joint(joint: String, angles: Vector3) -> void:
	if joints.has(joint):
		joints[joint].rotation = angles
