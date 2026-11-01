extends Node

var failures: int = 0
var checks: int = 0
var world: Node3D
var session: Node

func _ready() -> void:
	var watchdog := Timer.new()
	watchdog.one_shot = true
	watchdog.wait_time = 45.0
	watchdog.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(watchdog)
	watchdog.timeout.connect(func():
		push_error("Regression suite timed out before completing")
		get_tree().quit(1))
	watchdog.start()
	run.call_deferred()

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures += 1
		push_error("FAIL: " + message)

func run() -> void:
	session = get_tree().root.get_node("Session")
	session.save_path = "user://regression_save.json"
	for suffix in ["", ".bak", ".tmp"]:
		DirAccess.remove_absolute(session.save_path + suffix)
	session.new_game()
	var original: Dictionary = session.snapshot()
	check(not session.apply_save({"version":99}), "Reject unknown save versions")
	var invalid: Dictionary = original.duplicate(true)
	invalid.upgrades = [-1,0,0]
	check(not session.apply_save(invalid), "Reject invalid upgrades")
	check(session.upgrades == [0,0,0], "Invalid saves cannot partially mutate progress")
	invalid = original.duplicate(true)
	invalid.checkpoint = 12
	check(not session.apply_save(invalid), "Reject invalid checkpoint")
	invalid = original.duplicate(true)
	invalid.shards = "not a number"
	check(not session.apply_save(invalid), "Reject malformed currency")
	session.shards = 500
	check(session.buy_upgrade(0), "Purchase first upgrade")
	check(session.shards == 465 and session.upgrades[0] == 1, "Purchase charges exact cost")
	check(session.buy_upgrade(0) and session.buy_upgrade(0), "Purchase up to cap")
	check(not session.buy_upgrade(0) and not session.buy_upgrade(-1), "Upgrade cap and invalid index")
	session.shards = 0
	check(not session.buy_upgrade(1), "Cannot buy without currency")
	session.new_game()
	session.shards = 41
	check(session.save_game(), "First atomic save")
	session.shards = 52
	check(session.save_game(), "Second atomic save and backup")
	var file := FileAccess.open(session.save_path, FileAccess.WRITE)
	file.store_string("{broken")
	file.close()
	check(session.load_game() and session.shards == 41, "Recover a damaged primary from backup")
	session.new_game()
	session.journey_started = false
	check(session.save_game() and not session.has_save, "Saving title settings does not create a journey slot")
	world = load("res://scenes/main.tscn").instantiate()
	get_tree().root.add_child(world)
	await get_tree().physics_frame
	check(not world.start_game(false) and not world.started and world.ui.menu.visible, "Settings-only saves cannot be used to skip the new-journey prologue")
	var valid_save_path: String = session.save_path
	session.save_path = "user://missing_regression_directory/save.json"
	world.ui.start_game(true)
	check(not world.started and world.ui.menu.visible and not world.ui.hud.visible, "Failed new-game save leaves the title and prior journey intact")
	var previous_checkpoint: int = session.checkpoint
	world.interaction_kind = "checkpoint"
	world.interaction_index = (previous_checkpoint + 1) % 3
	world.player.health = 50
	world.interact()
	check(session.checkpoint == previous_checkpoint and world.player.health == 50, "Failed checkpoint save cannot claim a new rest point or restore health")
	session.save_path = valid_save_path
	world.player.rune = 90.0
	world.start_game(true)
	check(world.player.rune == 35.0, "A fresh journey resets rune instead of inheriting the previous run")
	await get_tree().process_frame
	var dialog_panel: Control = world.ui.modal.get_child(1).get_child(0)
	check(dialog_panel.global_position.x >= 0 and dialog_panel.global_position.y >= 0, "Dialog remains inside viewport")
	world.ui.close_modal()
	check(world.ui.health_bar.global_position.y > 0, "HUD anchors remain inside viewport")
	world.ui.show_settings()
	await get_tree().process_frame
	check(is_instance_valid(world.ui.modal), "Settings opens with working control hierarchy")
	world.ui.close_modal()
	var player: RunePlayer = world.player
	check(player.active and not player.dead, "Start a new playable journey")
	await get_tree().physics_frame
	world.set_paused(true)
	Input.action_press("light")
	world.set_paused(false)
	player._physics_process(1.0 / 60.0)
	check(player.strike == null and player.input_buffer == 0, "A continue or resume click cannot leak into a sword attack")
	Input.action_release("light")
	await get_tree().physics_frame
	await get_tree().physics_frame
	Input.action_press("light")
	player._physics_process(1.0 / 60.0)
	check(player.strike != null, "Fresh attacks work after the UI input guard expires")
	Input.action_release("light")
	player.strike = null
	player.discard_ui_actions()
	player.invulnerability = 0
	player.parry_time = 0.22
	player.facing = Vector3.FORWARD
	var hp := player.health
	player.receive_hit(20, 10, player.global_position + Vector3.FORWARD * 2)
	check(player.health == hp and player.rune == 57, "Frontal parry prevents damage and restores rune")
	player.invulnerability = 0
	player.parry_time = 0.22
	player.receive_hit(20, 10, player.global_position + Vector3.BACK * 2)
	check(player.health == hp-20, "Parry does not protect from behind")
	player.receive_hit(20, 10, player.global_position + Vector3.BACK * 2)
	check(player.health == hp-20, "Post-hit invulnerability prevents stun lock")
	player.strike = null
	player.stagger = 0
	player.dodge_time = 0
	player.rune = 0
	check(not player.use_skill(0) and player.rune == 0, "Skills cannot overdraw rune")
	player.rune = 100
	check(player.use_skill(2) and player.rune == 20, "Finisher consumes 80 rune")
	player.strike = null
	player.active = false
	var attack: AttackData = load("res://data/light_1.tres")
	check(not attack.is_active(attack.startup-0.001) and attack.is_active(attack.startup), "Startup boundary")
	check(not attack.is_active(attack.startup+attack.active) and attack.can_cancel(attack.startup+attack.active), "Recovery and cancel boundary")
	var ledger := CombatStrike.new(player, attack)
	check(ledger.register_target(42) and not ledger.register_target(42), "One damage registration per target per swing")
	var second := CombatStrike.new(player, attack)
	check(second.register_target(42), "New swings can hit the same target")
	# Actual physics sweep at low frame rate: one large step must still hit once.
	var enemy := RuneEnemy.new()
	enemy.player = player
	enemy.world = world
	get_tree().root.add_child(enemy)
	enemy.global_position = player.global_position + Vector3.FORWARD * 2.0
	await get_tree().physics_frame
	await get_tree().physics_frame
	var initial_hp := enemy.health
	var sweep := CombatStrike.new(player, attack)
	sweep.step(attack.startup + attack.active, Vector3.FORWARD, 4)
	check(enemy.health < initial_hp, "Swept blade hits between distant physics samples")
	var after_hit := enemy.health
	sweep.step(0.01, Vector3.FORWARD, 4)
	check(enemy.health == after_hit, "Physics sweep cannot duplicate damage")
	var wall := StaticBody3D.new()
	var wall_shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(4,3,0.2)
	wall_shape.shape = box
	wall.add_child(wall_shape)
	get_tree().root.add_child(wall)
	wall.global_position = player.global_position + Vector3.FORWARD + Vector3.UP
	await get_tree().physics_frame
	await get_tree().physics_frame
	var blocked_swing := CombatStrike.new(player, attack)
	blocked_swing.step(attack.startup + attack.active, Vector3.FORWARD, 4)
	check(enemy.health == after_hit, "Walls block melee damage")
	blocked_swing = null
	wall.queue_free()
	enemy.queue_free()
	await get_tree().physics_frame
	player.active = true
	player.health = 1
	player.invulnerability = 0
	player.receive_hit(5, 10, player.global_position + Vector3.BACK, false)
	await get_tree().create_timer(1.4).timeout
	check(player.dead and is_instance_valid(world.ui.modal), "Death opens checkpoint recovery dialog")
	var recovery_column: VBoxContainer = world.ui.modal.get_child(1).get_child(0).get_child(0)
	var retry: Button = recovery_column.get_child(recovery_column.get_child_count()-2)
	retry.pressed.emit()
	check(not player.dead and player.health == player.max_health and world.active_encounter == -1, "Retry restores health and resets the encounter")
	check(player.global_position.distance_to(Sanctuary.CHECKPOINTS[session.checkpoint]) < 0.5 and player.locked_target == null, "Retry uses the checkpoint and clears stale targets")
	player.active = false
	# Drive the entire authored progression, including gates, rewards and checkpoint reload.
	for index in range(7):
		world.begin_encounter(index)
		await get_tree().physics_frame
		check(world.active_encounter == index and world.active_enemies.size() > 0, "Encounter %d spawns" % index)
		var gate: Node3D = world.sanctuary.gates[index][0]
		check(gate.visible and not gate.get_child(0).get_child(0).disabled, "Encounter %d closes collision gates" % index)
		if index == 6:
			var boss: RuneEnemy = world.boss
			boss.health = boss.max_health * 0.49
			player.active = true
			await get_tree().physics_frame
			await get_tree().physics_frame
			check(boss.phase == 2, "Boss enters second phase")
			player.active = false
		for target: RuneEnemy in world.active_enemies.duplicate():
			target.receive_hit(10000, 10000, player.global_position)
		await get_tree().physics_frame
		check(index in session.completed and world.active_encounter == -1, "Encounter %d completion persists" % index)
		check(not gate.visible and gate.get_child(0).get_child(0).disabled, "Encounter %d opens collision gates" % index)
	check(session.completed.size() == 7 and session.load_game(), "Entire chapter completion survives reload")
	world.started = false
	# Let the chapter-ending timer release its coroutine before freeing its owner.
	await get_tree().create_timer(2.1).timeout
	check(load("res://tests/save_regressions.gd").run(session, check) == true, "Save regression suite completes")
	check(await load("res://tests/combat_regressions.gd").run(world, check) == true, "Combat regression suite completes")
	check(await load("res://tests/charged_impact_regressions.gd").run(world, check) == true, "Charged blade contacts, shared hitstop and collision recoil suite completes")
	check(await load("res://tests/impact_presentation_regressions.gd").run(world, check) == true, "Contact camera, effect crowd budget and lifetime suite completes")
	check(await load("res://tests/skeletal_regressions.gd").run(world, check) == true, "Skeletal presentation suite completes")
	check(await load("res://tests/art_integration_regressions.gd").run(world, check) == true, "Generated static art integration suite completes")
	check(await load("res://tests/production_character_regressions.gd").run(world, check) == true, "Production character skin, socket and gameplay presentation suite completes")
	check(await load("res://tests/charged_blade_alignment_regressions.gd").run(world, check) == true, "Imported charged blade, planted foot and moving charge agree with gameplay")
	check(load("res://tests/weight_recovery_regressions.gd").run(world, check) == true, "Weight transfer, held-charge continuity and full strong-hit recovery preserve presentation clocks")
	check(await load("res://tests/skeletal_transition_regressions.gd").run(world, check) == true, "Production skeletal transitions preserve clocks, priority and same-frame sockets")
	check(await load("res://tests/blade_trail_regressions.gd").run(world, check) == true, "Displayed blade trails preserve action windows, world-space history and lifecycle")
	check(await load("res://tests/character_eye_regressions.gd").run(world, check) == true, "Actual eye geometry preserves source anchors, Head sockets, units and imported colors")
	check(await load("res://tests/mobile_input_regressions.gd").run(world, check) == true, "Actual touch pointers preserve actions, ownership, viewport and device lifecycle")
	check(await load("res://tests/audio_lifecycle_regressions.gd").run(world, check) == true, "Audio shutdown, deferred callbacks and explicit restart preserve playback lifetime")
	check(await load("res://tests/impact_audio_regressions.gd").run(world, check) == true, "Confirmed impact audio layers, crowd voices and shutdown preserve playback lifetime")
	ledger = null
	second = null
	sweep = null
	world.queue_free()
	var audio := get_tree().root.get_node("Audio")
	audio.stop_all()
	check(await audio.wait_until_stopped(), "Audio shutdown releases actual playback references and queued players before exit")
	await get_tree().process_frame
	await get_tree().process_frame
	for suffix in ["", ".bak", ".tmp"]:
		DirAccess.remove_absolute(session.save_path + suffix)
	print("RUNEFALL_TESTS: %d checks, %d failures" % [checks, failures])
	get_tree().quit(1 if failures > 0 else 0)
