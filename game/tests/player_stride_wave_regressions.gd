extends RefCounted

# Actual Input -> RunePlayer -> move_and_slide -> presentation snapshots.
# The projectile's swept geometry/receivers are covered by its own suite.
# These checks do not approve footplant, rendered motion, or audiovisual feel.
const ACTIONS: Array[StringName] = [&"light", &"heavy", &"dodge", &"parry", &"heal", &"skill_1", &"skill_2", &"skill_3", &"left", &"right", &"forward", &"back", &"sprint"]

class TickRecorder:
	extends Node
	var player: RunePlayer
	var previous: Vector3
	var records: Array[Dictionary] = []
	func arm() -> void:
		records.clear()
		previous = player.global_position
		set_physics_process(true)
	func _physics_process(delta: float) -> void:
		var displacement := player.global_position - previous
		displacement.y = 0.0
		previous = player.global_position
		var snapshot := player.presentation_snapshot()
		records.append({"actual":displacement, "distance":snapshot.movement_distance,
			"resolved_velocity":player.resolved_velocity, "delta":delta,
			"attack_id":snapshot.attack_id, "attack_elapsed":snapshot.attack_elapsed,
			"combat_locomotion":snapshot.combat_locomotion,
			"local_x":snapshot.move_local_x, "local_z":snapshot.move_local_z})

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _body(parent: Node3D, point: Vector3, size: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.collision_layer = 1
	var collision := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	collision.shape = box
	body.add_child(collision)
	parent.add_child(body)
	body.position = point
	return body

static func _prepare(player: RunePlayer, observer: TickRecorder, point: Vector3) -> void:
	player.set_physics_process(false)
	observer.set_physics_process(false)
	player.restore(point)
	player.ui_input_guard = 0
	player.active = true
	player.facing = Vector3.FORWARD
	player.camera_yaw = 0.0
	player.visual.rotation.y = 0.0

static func _matching_movement(records: Array[Dictionary]) -> bool:
	if records.is_empty():
		return false
	for record in records:
		var actual: Vector3 = record.actual
		var resolved: Vector3 = record.resolved_velocity
		if absf(float(record.distance) - actual.length()) > 0.000001:
			return false
		if resolved.distance_to(actual / float(record.delta)) > 0.0001:
			return false
	return true

static func run(world: Node3D, check: Callable) -> bool:
	var tree := world.get_tree()
	var original_player: RunePlayer = world.player
	var saved_world_physics := world.is_physics_processing()
	var saved_player_physics := original_player.is_physics_processing()
	world.set_physics_process(false)
	original_player.set_physics_process(false)
	var saved_enemies: Array[Dictionary] = []
	for enemy in tree.get_nodes_in_group("enemies"):
		saved_enemies.append({"node":enemy, "physics":enemy.is_physics_processing()})
		enemy.set_physics_process(false)
	var saved_actions: Dictionary = {}
	for action in ACTIONS:
		saved_actions[action] = Input.get_action_strength(action)
		Input.action_release(action)
	var fixture := Node3D.new()
	world.add_child(fixture)
	fixture.position = Vector3(1200.0, 8.0, -1200.0)
	_body(fixture, Vector3(0.0, -0.5, 0.0), Vector3(30.0, 1.0, 30.0))
	var player := RunePlayer.new()
	player.world = world
	fixture.add_child(player)
	player.set_physics_process(false)
	var observer := TickRecorder.new()
	observer.player = player
	# Read after the real player's physics callback, not before its movement.
	observer.process_physics_priority = 100
	observer.set_physics_process(false)
	fixture.add_child(observer)
	var waves: Array[Dictionary] = []
	player.wave_requested.connect(func(attack: CombatStrike, forward: Vector3) -> void:
		waves.append({"id":attack.attack_instance_id, "elapsed":attack.elapsed,
			"release_time":attack.data.startup + attack.data.active * attack.data.wave_release_fraction, "forward":forward,
			"range":attack.data.wave_range, "presentation_id":attack.presentation_id}))
	var impacts: Array[Dictionary] = []
	player.impact_confirmed.connect(func(context: Dictionary) -> void: impacts.append(context.duplicate(true)))
	await _tick(tree)
	await _tick(tree)
	var start := fixture.global_position + Vector3(0.0, 0.02, 0.0)
	_prepare(player, observer, start)
	Input.action_press("right")
	Input.action_press("light")
	observer.arm()
	player.set_physics_process(true)
	await _tick(tree)
	Input.action_release("light")
	for index in range(5):
		await _tick(tree)
	player.set_physics_process(false)
	observer.set_physics_process(false)
	var directional := player.global_position - start
	var light_samples := 0
	var right_motion := true
	for record in observer.records:
		if String(record.attack_id) != "light_1":
			continue
		light_samples += 1
		var actual: Vector3 = record.actual
		right_motion = right_motion and actual.x > 0.0 and absf(actual.z) < 0.0001
		right_motion = right_motion and absf(actual.length() / float(record.delta) - 4.2) < 0.02
		right_motion = right_motion and bool(record.combat_locomotion) and float(record.local_x) > 0.9
	check.call(light_samples >= 3 and player.strike != null and player.strike.presentation_id == &"light_1"
		and directional.x > 0.2 and absf(directional.z) < 0.0001 and player.facing.is_equal_approx(Vector3.FORWARD) and right_motion,
		"Actual light input permits 4.2m/s rightward movement during a forward-facing swing and reports the resolved local gait direction")
	check.call(_matching_movement(observer.records), "Every actual moving-light physics sample reports measured move_and_slide displacement and resolved velocity")
	Input.action_release("right")
	await _tick(tree)

	# Press into a physical wall while the light remains alive. Nominal input
	# remains nonzero; neither velocity nor a helper's result stands in for travel.
	_body(fixture, Vector3(0.85, 1.5, 0.0), Vector3(0.2, 3.0, 6.0))
	await _tick(tree)
	_prepare(player, observer, start)
	player.begin_attack(false, 0)
	Input.action_press("right")
	observer.arm()
	player.set_physics_process(true)
	for index in range(18):
		await _tick(tree)
	player.set_physics_process(false)
	observer.set_physics_process(false)
	var blocked_samples := 0
	for record in observer.records:
		if String(record.attack_id) == "light_1" and float(record.attack_elapsed) > 0.15 and float(record.distance) < 0.000001:
			blocked_samples += 1
	var wall_report := player.visual.skeletal_bridge.transition_report()
	check.call(player.strike != null and blocked_samples >= 3 and player.global_position.x < start.x + 0.5
		and is_zero_approx(player.movement_distance) and player.resolved_velocity.is_zero_approx()
		and float(wall_report.combat_layer_weight) == 0.0,
		"Held light movement stops at an actual wall, reports zero resolved distance, and stops the lower-body gait after its bounded fade")
	check.call(_matching_movement(observer.records), "Wall-blocked light snapshots still match actual per-tick CharacterBody movement rather than requested speed")
	Input.action_release("right")
	await _tick(tree)

	# Use the real factory and physics timeline for the L3 launch signal.
	# No elapsed injection or direct call to the emission helper is involved.
	_prepare(player, observer, start + Vector3(0.0, 0.0, 8.0))
	waves.clear()
	player.begin_attack(false, 2)
	var launched_strike := player.strike
	var launched_id := launched_strike.attack_instance_id
	player.set_physics_process(true)
	var release_checked := false
	var release_time := launched_strike.data.startup + launched_strike.data.active * launched_strike.data.wave_release_fraction
	for index in range(90):
		await _tick(tree)
		if player.strike == launched_strike and launched_strike.elapsed > 0.0 and launched_strike.elapsed < release_time:
			release_checked = true
			check.call(waves.is_empty(), "Actual L3 physics cannot emit a sword wave before the authored forward-slash release phase")
		if player.strike == null:
			break
	player.set_physics_process(false)
	check.call(release_checked and player.strike == null and waves.size() == 1
		and int(waves[0].id) == launched_id and String(waves[0].presentation_id) == "light_3"
		and float(waves[0].elapsed) >= float(waves[0].release_time) and is_equal_approx(float(waves[0].range), 4.5),
		"One actual L3 physics timeline emits exactly one wave with its original strike identity at or after its authored slash release time")

	var old_contact := {"sword_wave":true, "attack_instance_id":launched_id, "hitstop":0.06}
	player.rune = 0.0
	Input.action_press("back")
	player.on_hit(5.0, player.global_position + Vector3.FORWARD * 4.0, old_contact)
	var walking_start := player.global_position
	observer.arm()
	player.set_physics_process(true)
	await _tick(tree)
	player.set_physics_process(false)
	observer.set_physics_process(false)
	check.call(player.hit_pause == 0.0 and player.strike == null and player.global_position.z > walking_start.z + 0.04
		and player.rune > 0.0 and impacts.size() == 1,
		"A late wave contact still grants hit feedback and rune while allowing unrelated real walking to continue")
	Input.action_release("back")
	await _tick(tree)
	player.begin_attack(false, 0)
	var next_strike := player.strike
	var next_elapsed := next_strike.elapsed
	player.on_hit(5.0, player.global_position + Vector3.FORWARD * 4.0, old_contact)
	player.set_physics_process(true)
	await _tick(tree)
	player.set_physics_process(false)
	check.call(player.hit_pause == 0.0 and player.strike == next_strike and next_strike.elapsed > next_elapsed
		and next_strike.attack_instance_id != launched_id and impacts.size() == 2,
		"An older wave cannot pause a different new strike; its actual gameplay attack clock keeps advancing")
	var same_contact := {"sword_wave":true, "attack_instance_id":next_strike.attack_instance_id, "hitstop":0.06}
	player.on_hit(5.0, player.global_position + Vector3.FORWARD * 4.0, same_contact)
	var frozen_elapsed := next_strike.elapsed
	var frozen_root := player.global_position
	observer.arm()
	player.set_physics_process(true)
	await _tick(tree)
	player.set_physics_process(false)
	observer.set_physics_process(false)
	check.call(player.hit_pause > 0.0 and player.strike == next_strike and next_strike.elapsed == frozen_elapsed
		and player.global_position.is_equal_approx(frozen_root) and player.movement_distance == 0.0
		and player.resolved_velocity.is_zero_approx() and impacts.size() == 3,
		"A wave from the current strike still applies hitstop and freezes the actual attack clock and controller without repeating movement distance")
	print("RUNEFALL_PLAYER_STRIDE_WAVE " + JSON.stringify({"light_samples":light_samples,
		"blocked_light_samples":blocked_samples, "wave_events":waves,
		"late_feedback_events":impacts.size(), "scope":"Actual RunePlayer input, move_and_slide snapshots, wave signal and late-contact pause ownership; no projectile geometry, continuous visual or footplant approval"}))
	fixture.queue_free()
	await tree.process_frame
	await tree.process_frame
	original_player.set_physics_process(saved_player_physics)
	world.set_physics_process(saved_world_physics)
	for record in saved_enemies:
		if is_instance_valid(record.node):
			record.node.set_physics_process(bool(record.physics))
	for action in ACTIONS:
		if float(saved_actions[action]) > 0.0:
			Input.action_press(action, float(saved_actions[action]))
		else:
			Input.action_release(action)
	return true
