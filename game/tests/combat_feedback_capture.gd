extends Node

## Offline review stills for v0.1.19 combat presentation in the actual Game
## scene. Run with a real display driver (see tools/render_combat_feedback.py).
## Staged poses and directly-triggered presentation: these frames are a
## finite visual review, not normal-input gameplay, AV or device evidence.

var output_dir := ""
var quality := 0
var world: Node3D
var player: RunePlayer
var rig: RuneCamera
var report := {"frames":[], "quality":0}

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	output_dir = args[0] if args.size() > 0 else "user://combat_feedback_capture"
	quality = int(args[1]) if args.size() > 1 else 0
	DirAccess.make_dir_recursive_absolute(output_dir)
	_run.call_deferred()

func _frames(count: int) -> void:
	for index in range(count):
		await get_tree().process_frame

func _capture(label: String, extra: Dictionary = {}) -> void:
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	var path := output_dir.path_join("%s_q%d.png" % [label, quality])
	image.save_png(path)
	var entry := {"label":label, "path":path, "process_frame":Engine.get_process_frames(),
		"feedback":world.call("combat_feedback_report")}
	entry.merge(extra, true)
	report.frames.append(entry)

func _context(strength: String, enemy: RuneEnemy, extra: Dictionary = {}) -> Dictionary:
	var point := enemy.global_position + Vector3.UP * 1.15 + (player.global_position - enemy.global_position).normalized() * 0.35
	var context := {"attack_id":"charged_heavy" if strength == "charged" else ("heavy" if strength == "heavy" else "light_1"),
		"strength":strength, "point":point, "normal":(player.global_position - enemy.global_position).normalized(),
		"direction":(enemy.global_position - player.global_position).normalized(), "contact_source":"hurtbox_ray",
		"source":"player", "attack_instance_id":1}
	context.merge(extra, true)
	return context

func _run() -> void:
	Session.save_path = "user://combat_feedback_capture_%d.json" % Time.get_ticks_usec()
	Session.quality = quality
	Session.shake = true
	report.quality = quality
	world = load("res://scenes/main.tscn").instantiate()
	add_child(world)
	await _frames(2)
	var ui: RuneHUD = world.get("ui")
	ui.start_game(true)
	if not bool(world.get("started")):
		push_error("Capture could not start a journey")
		get_tree().quit(2)
		return
	ui.close_modal()
	ui.banner_time = 0.0
	ui.toast_time = 0.0
	world.call("apply_quality")
	player = world.get("player")
	rig = world.get("rig")
	world.set_physics_process(false)
	var center: Vector3 = Sanctuary.CENTERS[0]
	player.global_position = center + Vector3(0.0, 0.1, 5.5)
	player.facing = Vector3.FORWARD
	player.visual.rotation.y = 0.0
	world.call("begin_encounter", 0)
	ui.banner_time = 0.0
	ui.toast_time = 0.0
	var enemies: Array[RuneEnemy] = []
	for enemy in world.get("active_enemies"):
		enemies.append(enemy)
	var spots := [Vector3(-1.3, 0.1, 2.6), Vector3(1.5, 0.1, 2.2), Vector3(0.2, 0.1, 0.2)]
	for index in range(enemies.size()):
		enemies[index].global_position = center + spots[index]
		enemies[index].facing = Vector3.BACK
		enemies[index].visual.rotation.y = 0.0
	# Hold AI still (inactive player) while idle and death poses keep playing.
	player.active = false
	rig.cinematic = false
	rig.yaw = 0.0
	rig.pitch = -0.2
	rig.snap()
	await _frames(20)
	# Adopted scene (glow off) and the rejected glow candidate on the same
	# frozen camera. The candidate is restored to off before any other still.
	var environment: Environment = world.get("sanctuary").get_node("SanctuaryEnvironment").environment
	rig.set_physics_process(false)
	await _frames(2)
	await _capture("scene")
	environment.glow_enabled = true
	await _frames(2)
	await _capture("scene_glow_rejected")
	environment.glow_enabled = false
	rig.set_physics_process(true)
	await _frames(2)

	# Hit flash + status plate trail + poise, and a parryable telegraph.
	enemies[0].receive_hit(32.0, 30.0, player.global_position, true, _context("heavy", enemies[0]))
	var flash_damage: Label = ui.damage_numbers[-1].label if not ui.damage_numbers.is_empty() else null
	if flash_damage != null:
		ui.style_damage(flash_damage, _context("heavy", enemies[0]))
	await _frames(1)
	await _capture("hit_flash")
	var data: AttackData = RuneEnemy.BASE_ATTACK.duplicate()
	enemies[1].strike = CombatStrike.new(enemies[1], data, 1.0, &"enemy_attack")
	enemies[1].strike.elapsed = data.startup * 0.8
	enemies[1]._present_status()
	await _frames(14)
	await _capture("status_trail_telegraph")

	# HUD: lock reticle, combo tier, styled numbers, player damage chip.
	player.locked_target = enemies[1]
	player.combo_hits = 12
	player.combo_timeout = 2.2
	player.health = player.max_health * 0.62
	enemies[0].receive_hit(69.3, 40.0, player.global_position, true, _context("charged", enemies[0]))
	if not ui.damage_numbers.is_empty():
		ui.style_damage(ui.damage_numbers[-1].label, _context("charged", enemies[0]))
	await _frames(6)
	await _capture("hud_combat")

	# Charged impact radial grade.
	var screen_fx: RuneScreenFX = world.get("screen_fx")
	screen_fx.trigger_impact(_context("charged", enemies[1]), rig.camera)
	await _frames(1)
	await _capture("impact_grade")
	await _frames(20)

	# Perfect dodge: Rune Haste grade, cyan frame and the baked afterimage.
	player.locked_target = null
	player.active = true
	player.dodge_time = RunePlayer.DODGE_DURATION - 0.02
	player.dodge_direction = Vector3.RIGHT
	player.invulnerability = 0.25
	player.perfect_dodge_ready = true
	player.receive_hit(20.0, 10.0, enemies[1].global_position, true)
	player.active = false
	ui.toast_time = 0.0
	player.global_position += Vector3.RIGHT * 0.9
	await _frames(4)
	await _capture("perfect_dodge_haste")
	world.set("haste_remaining", 0.0)
	await _frames(15)

	# Death ember dissolve at two moments.
	enemies[2].receive_hit(10000.0, 100.0, player.global_position, true, _context("heavy", enemies[2]))
	await _frames(int((ActorFeedback.DISSOLVE_DELAY + 0.45) * 60.0))
	await _capture("dissolve_early")
	await _frames(int(0.55 * 60.0))
	await _capture("dissolve_late")

	# Low-health heartbeat vignette.
	player.health = player.max_health * 0.12
	await _frames(45)
	await _capture("low_health")
	player.health = player.max_health
	await _frames(45)

	# Final skill contact: skill VFX with the impact grade and kill styling.
	player.active = true
	player.rune = 100.0
	player.strike = null
	player.stagger = 0.0
	player.dodge_time = 0.0
	player.use_skill(2)
	for step in range(20):
		await get_tree().physics_frame
	player.active = false
	await _capture("skill3_contact")

	var file := FileAccess.open(output_dir.path_join("capture_q%d.json" % quality), FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t"))
	file.close()
	world.call("return_to_title")
	Audio.stop_all()
	await _frames(3)
	for suffix in ["", ".bak", ".tmp", ".bak.tmp"]:
		DirAccess.remove_absolute(Session.save_path + suffix)
	get_tree().quit(0)
