extends RefCounted

# A second actual Game exercises its production signal handler and lifecycle
# methods. Existing scene group members are isolated and restored because the
# production reset intentionally enumerates SceneTree-wide combat groups.
class HitTarget:
	extends StaticBody3D
	var hits := 0
	var damage := 0.0
	func receive_hit(amount: float, _poise: float, _origin: Vector3, _parryable: bool = true, _context: Dictionary = {}) -> void:
		hits += 1
		damage += amount

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _target(parent: Node3D, point: Vector3) -> HitTarget:
	var target := HitTarget.new()
	target.collision_layer = 4
	target.collision_mask = 0
	var collision := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.06
	collision.shape = sphere
	collision.position.y = 1.05
	target.add_child(collision)
	parent.add_child(target)
	target.global_position = point
	return target

static func _launch(game: Node3D, source_point: Vector3) -> RuneSwordWave:
	var player: RunePlayer = game.player
	player.set_physics_process(false)
	player.restore(source_point)
	player.active = true
	var attack := CombatStrike.new(player, RunePlayer.LIGHTS[2])
	player.strike = attack
	# This invokes the actual Game connection; do not construct a replacement
	# wave or fake the reset path in the test.
	player.wave_requested.emit(attack, Vector3.FORWARD)
	for child in game.get_children():
		if child is RuneSwordWave and not child.is_queued_for_deletion():
			child.set_physics_process(false)
			return child as RuneSwordWave
	return null

static func _cancelled(wave: RuneSwordWave) -> bool:
	return (is_instance_valid(wave) and not bool(wave.presentation_report().valid)
		and not wave.is_physics_processing() and wave.is_queued_for_deletion())

static func run(world: Node3D, check: Callable) -> bool:
	var tree := world.get_tree()
	var saved_world_physics := world.is_physics_processing()
	var saved_player_physics: bool = world.player.is_physics_processing()
	var saved_pause := tree.paused
	var saved_mouse := Input.mouse_mode
	var saved_touch_requested := bool(TouchControls.get("_wanted_active"))
	var saved_camera: Camera3D = world.get_viewport().get_camera_3d()
	var saved_render_scale := world.get_viewport().scaling_3d_scale
	world.set_physics_process(false)
	world.player.set_physics_process(false)
	tree.paused = false
	var isolated: Dictionary = {}
	for group: StringName in [&"enemies", &"impact_effects", &"sword_waves"]:
		for node in tree.get_nodes_in_group(group):
			var id := node.get_instance_id()
			if not isolated.has(id):
				isolated[id] = {"node":node, "groups":[], "physics":node.is_physics_processing()}
			isolated[id].groups.append(group)
			node.remove_from_group(group)
			node.set_physics_process(false)
	var game: Node3D = load("res://scenes/main.tscn").instantiate()
	game.position = Vector3(2000.0, 30.0, -2000.0)
	world.add_child(game)
	game.set_physics_process(false)
	game.player.set_physics_process(false)
	game.hide()
	var start := game.global_position + Vector3(500.0, 30.0, 500.0)
	var near := _target(game, start + Vector3.FORWARD * 1.5)
	var after_reset := _target(game, start + Vector3.FORWARD * 3.2)
	var wave := _launch(game, start)
	check.call(wave != null, "The actual Game wave_requested connection creates a live sword wave for its own RunePlayer")
	await _tick(tree)
	await _tick(tree)
	var reset_ref: WeakRef = weakref(wave) if wave != null else weakref(game)
	if wave != null:
		wave._physics_process(0.08)
		check.call(near.hits == 1 and near.damage > 0.0 and after_reset.hits == 0,
			"The pre-reset wave is functional: it hits a real near hurtbox but has not reached the later receiver")
		game.reset_encounter()
		check.call(_cancelled(wave), "Actual Game.reset_encounter immediately invalidates and disables its wave before queued deletion")
		wave._physics_process(0.2)
		check.call(near.hits == 1 and after_reset.hits == 0,
			"A reset wave cannot produce additional damage even if its callback is invoked before the frame deletes it")
	await _tick(tree)
	await _tick(tree)
	check.call(reset_ref.get_ref() == null, "Encounter reset releases the wave and its retained attack after the frame boundary")

	var title_start := start + Vector3.RIGHT * 12.0
	var title_target := _target(game, title_start + Vector3.FORWARD * 1.5)
	wave = _launch(game, title_start)
	check.call(wave != null, "A fresh actual Game wave can be launched after encounter reset")
	await _tick(tree)
	await _tick(tree)
	var title_ref: WeakRef = weakref(wave) if wave != null else weakref(game)
	if wave != null:
		game.started = true
		game.return_to_title()
		check.call(not game.started and not game.player.active and _cancelled(wave),
			"Actual return_to_title reuses its player while immediately cancelling the old encounter's wave")
		wave._physics_process(0.3)
		check.call(title_target.hits == 0, "A title transition leaves no old-wave damage during the same frame")
	await _tick(tree)
	await _tick(tree)
	check.call(title_ref.get_ref() == null, "Title transition removes the old wave node and owner callback")

	var restore_start := start + Vector3.RIGHT * 24.0
	var restore_target := _target(game, restore_start + Vector3.FORWARD * 1.5)
	wave = _launch(game, restore_start)
	check.call(wave != null, "The reused actual player can launch another wave before a checkpoint restore")
	await _tick(tree)
	await _tick(tree)
	var restore_ref: WeakRef = weakref(wave) if wave != null else weakref(game)
	if wave != null:
		var before_epoch: int = game.player.presentation_epoch
		# Checkpoint interaction calls restore directly without reset_encounter.
		# Keep the source alive/active, so only the changed generation cancels it.
		game.player.restore(restore_start + Vector3.BACK * 4.0)
		check.call(game.player.active and not game.player.dead and game.player.presentation_epoch != before_epoch,
			"Actual RunePlayer.restore changes the generation without freeing or deactivating its source")
		wave._physics_process(0.3)
		check.call(_cancelled(wave) and restore_target.hits == 0,
			"An old-generation wave cancels before querying damage after direct checkpoint restore")
	await _tick(tree)
	await _tick(tree)
	check.call(restore_ref.get_ref() == null, "A restore-invalidated wave releases its retained strike and callback")
	game.queue_free()
	await tree.process_frame
	await tree.process_frame
	for record: Dictionary in isolated.values():
		if is_instance_valid(record.node):
			for group: StringName in record.groups:
				record.node.add_to_group(group)
			record.node.set_physics_process(bool(record.physics))
	world.set_physics_process(saved_world_physics)
	world.player.set_physics_process(saved_player_physics)
	world.get_viewport().scaling_3d_scale = saved_render_scale
	if is_instance_valid(saved_camera):
		saved_camera.make_current()
	Input.mouse_mode = saved_mouse
	TouchControls.set_gameplay_active(saved_touch_requested)
	tree.paused = saved_pause
	return true
