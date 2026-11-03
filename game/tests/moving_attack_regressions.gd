extends RefCounted

# Actual production clips, evaluated by the production AnimationTree. These
# checks establish layering/clock contracts, not foot IK or visual acceptance.
const DT := 1.0 / 60.0
const LOWER_BONES := ["Root", "Hips", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase", "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"]
const DIRECTIONS := [Vector2(0.0, -1.0), Vector2(0.0, 1.0), Vector2(-1.0, 0.0), Vector2(1.0, 0.0)]
const GAITS := [&"walk", &"walk_back", &"walk_left", &"walk_right"]

static func _pose(visual: ActorVisual, snapshot: Dictionary, delta: float = 0.0) -> void:
	visual.pose(delta, float(snapshot.get("speed", 0.0)), -1.0, false, false, false, snapshot)

static func _attack(visual: ActorVisual, state: StringName, fraction: float = 0.4) -> Dictionary:
	var duration := visual.skeletal_bridge.animation_player.get_animation(visual.skeletal_bridge.clips[state]).length
	return {"speed":0.0, "attack_id":state, "attack_elapsed":duration * fraction,
		"attack_duration":duration, "attack_startup":0.0}

static func _moving(visual: ActorVisual, state: StringName, direction: Vector2 = Vector2(0.0, -1.0), distance: float = 0.32) -> Dictionary:
	var snapshot := _attack(visual, state)
	snapshot.merge({"speed":6.4, "combat_locomotion":true, "movement_distance":distance,
		"move_local_x":direction.x, "move_local_z":direction.y}, true)
	return snapshot

static func _gait(direction: Vector2, distance: float) -> Dictionary:
	return {"speed":6.4, "movement_distance":distance, "move_local_x":direction.x, "move_local_z":direction.y}

static func _bones(visual: ActorVisual) -> Array[Transform3D]:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var result: Array[Transform3D] = []
	for bone in range(skeleton.get_bone_count()):
		result.append(skeleton.get_bone_pose(bone))
	return result

static func _same(a: Array[Transform3D], b: Array[Transform3D]) -> bool:
	if a.size() != b.size():
		return false
	for bone in range(a.size()):
		if not a[bone].is_equal_approx(b[bone]):
			return false
	return true

static func _upper(skeleton: Skeleton3D, bone: int) -> bool:
	while bone >= 0:
		if skeleton.get_bone_name(bone) == &"Spine":
			return true
		bone = skeleton.get_bone_parent(bone)
	return false

static func _matches_layers(moving: ActorVisual, gait: ActorVisual, attack: ActorVisual) -> bool:
	var skeleton := moving.skeletal_bridge.get_skeleton()
	var gait_skeleton := gait.skeletal_bridge.get_skeleton()
	var attack_skeleton := attack.skeletal_bridge.get_skeleton()
	for bone in range(skeleton.get_bone_count()):
		var expected := attack_skeleton.get_bone_pose(bone) if _upper(skeleton, bone) else gait_skeleton.get_bone_pose(bone)
		if not skeleton.get_bone_pose(bone).is_equal_approx(expected):
			return false
	return true

static func _socket_matches(visual: ActorVisual) -> bool:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	return visual.weapon_socket.global_transform.is_equal_approx(skeleton.global_transform * skeleton.get_bone_global_pose(skeleton.find_bone("RightHand")))

static func _reset(visuals: Array[ActorVisual], epoch: int) -> void:
	for visual in visuals:
		visual.skeletal_bridge.reset_presentation(epoch)

static func _wall_distance(world: Node3D, check: Callable) -> float:
	var fixture := Node3D.new()
	fixture.position = Vector3(1500.0, 0.0, 1500.0)
	world.add_child(fixture)
	var body := CharacterBody3D.new()
	var body_collision := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.3
	capsule.height = 1.8
	body_collision.shape = capsule
	body.add_child(body_collision)
	fixture.add_child(body)
	var wall := StaticBody3D.new()
	wall.position.x = 0.8
	var wall_collision := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.5, 5.0, 5.0)
	wall_collision.shape = box
	wall.add_child(wall_collision)
	fixture.add_child(wall)
	# physics_frame is emitted before the physics server step. Wait through a
	# complete step after adding the shapes, then approach on distinct ticks so
	# broadphase registration and contact recovery cannot masquerade as travel.
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	var distance := 0.0
	var settled := false
	var trace: Array[Dictionary] = []
	for attempt in range(8):
		var before := body.global_position
		var contact := body.move_and_collide(Vector3.RIGHT)
		var displacement := body.global_position - before
		distance = Vector2(displacement.x, displacement.z).length()
		trace.append({"attempt":attempt, "contact":contact != null, "distance":distance, "position":str(body.global_position)})
		if contact != null and distance < 0.000001:
			settled = true
			break
		await world.get_tree().physics_frame
	if not settled:
		print("RUNEFALL_MOVING_ATTACK_WALL_FAILURE: ", JSON.stringify(trace))
	check.call(settled, "A real CharacterBody collision resolves a held movement command to zero horizontal wall displacement")
	fixture.free()
	return distance

static func run(world: Node3D, check: Callable) -> bool:
	var visuals: Array[ActorVisual] = []
	for index in range(3):
		var visual := ActorVisual.new()
		visual.setup("hero")
		world.add_child(visual)
		var mounted := visual.use_production_profile("hero")
		check.call(mounted.ok, "Moving attack fixture mounts the actual production hero rig %d: %s" % [index, mounted.reason])
		if not mounted.ok:
			visual.free()
			for previous in visuals:
				previous.free()
			return false
		visuals.append(visual)
	var moving := visuals[0]
	var gait := visuals[1]
	var attack := visuals[2]
	gait.skeletal_bridge.enable_transition_polish(false)
	attack.skeletal_bridge.enable_transition_polish(false)
	var bridge := moving.skeletal_bridge
	var skeleton := bridge.get_skeleton()
	var epoch := 89000
	for state: StringName in [&"light_1", &"light_2", &"light_3", &"skill_1"]:
		for index in range(DIRECTIONS.size()):
			epoch += 1
			_reset(visuals, epoch)
			var direction: Vector2 = DIRECTIONS[index]
			# One resolved displacement, irrespective of nominal requested speed.
			_pose(moving, _moving(moving, state, direction), 0.08)
			_pose(gait, _gait(direction, 0.32), 0.08)
			_pose(attack, _attack(attack, state))
			check.call(bridge.selected_state == state and bridge.transition_report().combat_locomotion_state == GAITS[index]
				and bridge.transition_report().combat_layer_weight == 1.0 and _matches_layers(moving, gait, attack)
				and _socket_matches(moving), "%s moving %s uses the real directional gait below Spine and the exact authored attack above it" % [state, GAITS[index]])
	_reset(visuals, 89050)
	_pose(moving, _gait(Vector2(0.0, -1.0), 0.42), 0.08)
	_pose(moving, _moving(moving, &"light_2", Vector2(0.0, 1.0), 0.17), 0.08)
	_pose(gait, _gait(Vector2(0.0, 1.0), 0.59), 0.08)
	_pose(attack, _attack(attack, &"light_2"))
	check.call(_matches_layers(moving, gait, attack), "Entering an attack while changing travel direction preserves the foot phase accumulated by the previous real walk")
	var carried_phase: float = bridge.transition_report().gait_phase
	_pose(moving, _gait(Vector2(1.0, 0.0), 0.0))
	check.call(bridge.selected_state == &"walk_right" and bridge.transition_report().gait_phase == carried_phase,
		"Leaving an attack resumes the real directional walk at its accumulated foot phase")
	_reset(visuals, 89100)
	var step := _moving(moving, &"light_1")
	_pose(moving, step, 0.08)
	var first_pose := _bones(moving)
	var phase: float = bridge.transition_report().gait_phase
	_pose(moving, step, DT)
	var legs_moved := false
	for name: String in LOWER_BONES:
		var bone := skeleton.find_bone(name)
		legs_moved = legs_moved or not first_pose[bone].is_equal_approx(skeleton.get_bone_pose(bone))
	var walk_length := bridge.animation_player.get_animation(bridge.clips[&"walk"]).length
	check.call(legs_moved and absf(float(bridge.transition_report().gait_phase) - fposmod(phase + 0.32 / 6.4 / walk_length, 1.0)) < 0.000001,
		"Real lower-body clip motion advances by resolved distance even when the attack sample is held fixed")
	var frozen := _bones(moving)
	var frozen_grip := moving.weapon_grip.global_transform
	var frozen_report := bridge.transition_report()
	var frozen_clock := bridge.locomotion_clock
	var pause := step.duplicate(true)
	pause.merge({"movement_distance":0.0, "speed":0.0, "move_local_x":0.0, "move_local_z":0.0}, true)
	for index in range(8):
		_pose(moving, pause)
	await world.get_tree().process_frame
	check.call(_same(frozen, _bones(moving)) and frozen_grip.is_equal_approx(moving.weapon_grip.global_transform)
		and bridge.transition_report() == frozen_report and bridge.locomotion_clock == frozen_clock,
		"Zero-delta hit pause retains the exact moving attack pose, gait direction, layer weight and weapon even when the controller reports zero distance")
	phase = bridge.transition_report().gait_phase
	var stop := pause.duplicate(true)
	stop.speed = 6.4 # Held input/nominal velocity must not drive the gait.
	_pose(moving, stop, DT)
	var stop_weight: float = bridge.transition_report().combat_layer_weight
	check.call(stop_weight > 0.0 and stop_weight < 1.0 and bridge.transition_report().gait_phase == phase,
		"Stopping freezes gait phase immediately and blends the lower body toward the stationary attack within 80ms")
	_pose(moving, stop, 0.08)
	_pose(attack, _attack(attack, &"light_1"))
	check.call(not bridge.transition_report().combat_upper_body and bridge.transition_report().gait_phase == phase and _same(_bones(moving), _bones(attack)),
		"Stationary movement attacks return to the original full-body authored pose without consuming gait phase")
	var wall_distance: float = await _wall_distance(world, check)
	_pose(moving, step, 0.08)
	phase = bridge.transition_report().gait_phase
	stop.movement_distance = wall_distance
	_pose(moving, stop, 0.08)
	check.call(bridge.transition_report().gait_phase == phase and not bridge.transition_report().combat_upper_body,
		"Actual collision-resolved zero wall travel does not march the attack's legs from requested speed")
	# Keep the same gait phase while the upper-body swing advances independently.
	_pose(moving, step, 0.08)
	var hand := skeleton.find_bone("RightHand")
	var first_hand := skeleton.get_bone_pose(hand)
	var second := _moving(moving, &"light_1", Vector2(0.0, -1.0), 0.000002)
	second.attack_elapsed = float(second.attack_duration) * 0.7
	_pose(moving, second, DT)
	var action_oracle := second.duplicate(true)
	action_oracle.erase("combat_locomotion")
	_pose(attack, action_oracle)
	check.call(not first_hand.is_equal_approx(skeleton.get_bone_pose(hand))
		and skeleton.get_bone_pose(hand).is_equal_approx(attack.skeletal_bridge.get_skeleton().get_bone_pose(hand)) and _socket_matches(moving),
		"The exact authored upper-body swing and same-frame weapon socket keep advancing independently of the walking legs")
	for state: StringName in [&"heavy", &"charged_heavy", &"skill_2", &"skill_3"]:
		var spec := _moving(moving, state)
		_pose(moving, spec)
		_pose(attack, _attack(attack, state))
		check.call(not bridge.transition_report().combat_upper_body and _same(_bones(moving), _bones(attack)),
			"%s retains its exact full-body authored motion despite a moving-attack request" % state)
	for interrupt in [
		{"dead":true, "death_elapsed":0.2, "death_duration":1.1},
		{"stagger":0.1, "hit_elapsed":0.05, "hit_duration":0.15},
		{"dodge_remaining":0.16, "dodge_elapsed":0.16, "dodge_duration":0.32, "dodge_local_x":1.0, "dodge_local_z":0.0},
		{"parry_remaining":0.1, "parry_elapsed":0.1, "parry_duration":0.22},
	]:
		_pose(moving, step, 0.08)
		phase = bridge.transition_report().gait_phase
		var spec := step.duplicate(true)
		spec.merge(interrupt, true)
		_pose(moving, spec, DT)
		_pose(attack, spec)
		check.call(not bridge.transition_report().combat_upper_body and bridge.transition_report().gait_phase == phase and _same(_bones(moving), _bones(attack)),
			"%s immediately interrupts the moving attack without advancing or discarding saved gait phase" % bridge.selected_state)
		var resume := step.duplicate(true)
		resume.attack_elapsed = float(resume.attack_duration) * 0.6
		_pose(moving, resume)
		check.call(bridge.transition_report().gait_phase == phase and bridge.transition_report().combat_upper_body,
			"Returning from %s resumes the saved foot phase" % String(interrupt.keys()[0]))
	var reset := step.duplicate(true)
	reset.presentation_epoch = 89200
	_pose(moving, reset)
	check.call(bridge.transition_report().gait_phase == 0.0 and bridge.transition_report().combat_locomotion_time == 0.0,
		"A presentation epoch discards previous movement phase before sampling the new attack")
	var legacy := step.duplicate(true)
	legacy.erase("combat_locomotion")
	legacy.erase("movement_distance")
	_pose(moving, legacy)
	_pose(attack, legacy)
	check.call(not bridge.transition_report().combat_upper_body and _same(_bones(moving), _bones(attack)),
		"Snapshots without the new opt-in fields retain the original full-body attack contract")
	for visual in visuals:
		visual.free()
	return true
