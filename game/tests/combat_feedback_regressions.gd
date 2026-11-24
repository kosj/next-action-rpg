extends RefCounted

# v0.1.19 combat presentation: enemy hit flash/dissolve/status plate/telegraph,
# perfect dodge Rune Haste, screen FX, HUD trails and balanced-mode glow.
# Native functional contracts only; not continuous AV, device or AAA approval.
const GAME_SCRIPT := preload("res://scripts/game.gd")
const ACTIONS: Array[StringName] = [&"light", &"heavy", &"dodge", &"parry", &"heal", &"skill_1", &"skill_2", &"skill_3", &"left", &"right", &"forward", &"back", &"sprint"]

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _context(strength: String, point: Vector3, extra: Dictionary = {}) -> Dictionary:
	var context := {"attack_id":"charged_heavy" if strength == "charged" else ("heavy" if strength == "heavy" else "light_1"),
		"strength":strength, "point":point, "normal":Vector3.BACK, "direction":Vector3.FORWARD,
		"contact_source":"hurtbox_ray", "source":"player", "attack_instance_id":1}
	context.merge(extra, true)
	return context

static func _surface_materials(enemy: RuneEnemy) -> Array:
	var result: Array = []
	for node in enemy.visual.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		if mesh.mesh == null:
			continue
		for surface in range(mesh.mesh.get_surface_count()):
			result.append(mesh.get_active_material(surface))
	return result

static func _spawn(game: Node3D, point: Vector3, kind: String = "melee") -> RuneEnemy:
	var enemy := RuneEnemy.new()
	enemy.kind = kind
	enemy.player = game.player
	enemy.world = game
	game.add_child(enemy)
	enemy.global_position = point
	enemy.set_physics_process(false)
	return enemy

static func run(world: Node3D, check: Callable) -> bool:
	var tree := world.get_tree()
	var saved_world_physics := world.is_physics_processing()
	var saved_player_physics: bool = world.player.is_physics_processing()
	var saved_pause := tree.paused
	var saved_quality := Session.quality
	var saved_shake := Session.shake
	var saved_shards := Session.shards
	var saved_camera: Camera3D = world.get_viewport().get_camera_3d()
	var saved_render_scale := world.get_viewport().scaling_3d_scale
	var actions: Dictionary = {}
	for action in ACTIONS:
		actions[action] = Input.get_action_strength(action)
		Input.action_release(action)
	world.set_physics_process(false)
	world.player.set_physics_process(false)
	tree.paused = false
	Session.quality = 0
	Session.shake = true
	var isolated: Dictionary = {}
	for group: StringName in [&"enemies", &"impact_effects", &"sword_waves", &"skill_effects", &"afterimages"]:
		for node in tree.get_nodes_in_group(group):
			var id := node.get_instance_id()
			if not isolated.has(id):
				isolated[id] = {"node":node, "groups":[], "physics":node.is_physics_processing(), "process":node.is_processing()}
			isolated[id].groups.append(group)
			node.remove_from_group(group)
			node.set_physics_process(false)
			node.set_process(false)
	var game: Node3D = load("res://scenes/main.tscn").instantiate()
	game.position = Vector3(-2600.0, 30.0, 2600.0)
	world.add_child(game)
	game.set_physics_process(false)
	game.rig.set_physics_process(false)
	game.rig.cinematic = false
	game.hide()
	var player: RunePlayer = game.player
	player.set_physics_process(false)
	var start: Vector3 = game.global_position + Vector3(400.0, 15.0, -400.0)
	player.restore(start)
	player.active = true
	player.ui_input_guard = 0
	player.facing = Vector3.FORWARD
	game.started = true
	await _tick(tree)

	# --- Enemy status plate, flash overlay and authored materials -----------
	var enemy := _spawn(game, start + Vector3.FORWARD * 6.0)
	await _tick(tree)
	var feedback: ActorFeedback = enemy.feedback
	var bar_material := enemy.bar.material_override as ShaderMaterial
	var warn_material := enemy.warning.material_override as ShaderMaterial
	check.call(is_instance_valid(feedback) and bar_material != null and bar_material.shader.resource_path.ends_with("enemy_status_bar.gdshader")
		and warn_material != null and warn_material.shader.resource_path.ends_with("attack_telegraph.gdshader") and not enemy.bar.visible and not enemy.warning.visible,
		"Enemies own a shader status plate and telegraph glyph that start hidden")
	var materials_before := _surface_materials(enemy)
	var hp_before := enemy.health
	var rng_probe_seed := 91357
	seed(rng_probe_seed)
	var expected_global := randf()
	seed(rng_probe_seed)
	enemy.receive_hit(18.0, 20.0, player.global_position, true, _context("light", enemy.global_position + Vector3.UP * 1.1))
	var report := feedback.presentation_report()
	var overlay_ok := int(report.overlay_meshes) > 0
	for mesh in feedback._overlay_meshes:
		overlay_ok = overlay_ok and mesh.material_overlay is ShaderMaterial and (mesh.material_overlay as ShaderMaterial).shader.resource_path.ends_with("actor_feedback.gdshader")
	check.call(is_equal_approx(enemy.health, hp_before - 18.0) and int(report.flash_count) == 1 and float(report.flash) > 0.9 and overlay_ok,
		"A confirmed hit keeps its damage and adds one rim-flash overlay on every displayed body surface")
	check.call(_surface_materials(enemy) == materials_before, "Hit flash never replaces imported surface materials")
	check.call(enemy.bar.visible and is_equal_approx(float(report.bar_health), enemy.health / enemy.max_health) and is_equal_approx(float(report.bar_trail), 1.0)
		and float(report.bar_poise) == 0.0,
		"Status plate shows actual health and holds a delayed damage chip; an interrupted melee foe has no stored poise")
	feedback._process(0.2)
	report = feedback.presentation_report()
	var detached := true
	for node in enemy.visual.find_children("*", "GeometryInstance3D", true, false):
		detached = detached and (node as GeometryInstance3D).material_overlay == null
	check.call(float(report.flash) == 0.0 and int(report.overlay_meshes) == 0 and detached and float(report.bar_trail) > float(report.bar_health),
		"The flash expires and detaches its overlay while the damage chip is still held")
	for step in range(90):
		feedback._process(1.0 / 60.0)
	report = feedback.presentation_report()
	check.call(is_equal_approx(float(report.bar_trail), float(report.bar_health)) and not feedback.is_processing(),
		"The damage chip settles onto actual health and the idle feedback node stops processing")
	check.call(randf() == expected_global, "Status plate and flash presentation draw nothing from the global gameplay RNG")

	var guard := _spawn(game, start + Vector3.FORWARD * 6.0 + Vector3.RIGHT * 3.0, "shield")
	await _tick(tree)
	guard.facing = (player.global_position - guard.global_position).normalized()
	var guard_hp := guard.health
	guard.receive_hit(20.0, 20.0, player.global_position, true, _context("light", guard.global_position + Vector3.UP))
	check.call(is_equal_approx(guard.health, guard_hp - 6.0) and is_equal_approx(float(guard.feedback.presentation_report().bar_poise), 20.0 / RuneEnemy.POISE_BREAK)
		and String(guard.feedback.presentation_report().flash_kind) == "light",
		"A shield block keeps its 30% damage and shows accumulated guard poise on the plate")
	guard.queue_free()

	# --- Telegraph glyph follows the strike's own startup -------------------
	var strike_data: AttackData = RuneEnemy.BASE_ATTACK.duplicate()
	enemy.strike = CombatStrike.new(enemy, strike_data, 1.0, &"enemy_attack")
	enemy.strike.elapsed = strike_data.startup * 0.5
	enemy._present_status()
	report = feedback.presentation_report()
	check.call(enemy.warning.visible and is_equal_approx(float(report.telegraph_progress), 0.5) and float(report.telegraph_danger) == 0.0,
		"Parryable startup shows a gold glyph at the strike's real startup progress")
	enemy.strike.elapsed = strike_data.startup + 0.01
	enemy._present_status()
	check.call(not enemy.warning.visible, "The glyph hides as soon as the active window opens")
	enemy.strike = null
	enemy.burst_time = 0.3
	enemy._present_status()
	report = feedback.presentation_report()
	check.call(enemy.warning.visible and float(report.telegraph_danger) == 1.0, "Unparryable bursts use the red danger glyph")
	enemy.interrupt_attack(0.2)
	enemy._present_status()
	check.call(not enemy.warning.visible, "Interrupting the attack hides its warning")

	# --- Death: ember dissolve, bounded embers, own RNG ---------------------
	seed(rng_probe_seed)
	expected_global = randf()
	seed(rng_probe_seed)
	enemy.receive_hit(10000.0, 100.0, player.global_position, true, _context("heavy", enemy.global_position + Vector3.UP * 1.1))
	check.call(enemy.dead and feedback.dying and not enemy.bar.visible and not enemy.warning.visible, "A killing blow starts the dissolve and hides the plate")
	feedback._process(ActorFeedback.DISSOLVE_DELAY - 0.05)
	check.call(feedback.dissolve == 0.0 and not feedback.embers_started, "The death pose reads before the dissolve begins")
	feedback._process(0.1)
	report = feedback.presentation_report()
	check.call(feedback.dissolve > 0.0 and feedback.embers_started and int(report.ember_count) == 40 and int(report.overlay_meshes) > 0,
		"Balanced quality burns with a bounded 40-ember MultiMesh")
	var source_states: Array[Dictionary] = []
	for material in materials_before:
		if material is BaseMaterial3D:
			source_states.append({"material":material, "transparency":material.transparency, "alpha":material.albedo_color.a})
	for step in range(30):
		feedback._process(1.0 / 60.0)
	report = feedback.presentation_report()
	check.call(float(report.fade) > 0.0 and int(report.faded_surfaces) > 0, "Mid-dissolve bodies dither out through alpha-hash material copies")
	for step in range(90):
		feedback._process(1.0 / 60.0)
	var all_hidden := true
	for node in enemy.visual.find_children("*", "GeometryInstance3D", true, false):
		if not node is BladeTrail:
			all_hidden = all_hidden and not (node as GeometryInstance3D).visible
	var sources_intact := not source_states.is_empty()
	for state in source_states:
		sources_intact = sources_intact and state.material.transparency == state.transparency and is_equal_approx(state.material.albedo_color.a, state.alpha)
	check.call(is_equal_approx(feedback.dissolve, 1.0) and is_equal_approx(feedback.fade, 1.0) and all_hidden, "The body is gone when the dissolve completes, before the actor's 3s removal")
	check.call(sources_intact, "Dissolve edits only per-actor material copies; shared imported materials keep their transparency and alpha")
	check.call(randf() == expected_global, "Death embers use their own RNG, not the global gameplay RNG")
	enemy.queue_free()
	Session.quality = 1
	var cheap := _spawn(game, start + Vector3.FORWARD * 9.0)
	await _tick(tree)
	cheap.receive_hit(10000.0, 100.0, player.global_position, true, _context("light", cheap.global_position + Vector3.UP))
	cheap.feedback._process(ActorFeedback.DISSOLVE_DELAY + 0.05)
	check.call(int(cheap.feedback.presentation_report().ember_count) == 16, "Performance quality halves the ember budget")
	cheap.queue_free()
	Session.quality = 0
	await _tick(tree)

	# --- Perfect dodge and Rune Haste ----------------------------------------
	var foe := _spawn(game, start + Vector3.FORWARD * 3.0)
	await _tick(tree)
	var dodged: Array[Vector3] = []
	player.perfect_dodged.connect(func(origin: Vector3): dodged.append(origin))
	player.restore(start)
	player.active = true
	player.ui_input_guard = 0
	player.invulnerability = 0.0
	player.rune = 40.0
	Input.action_press("dodge")
	player._physics_process(1.0 / 60.0)
	Input.action_release("dodge")
	check.call(player.dodge_time > 0.0 and player.perfect_dodge_ready, "Actual dodge input arms one perfect-dodge receipt")
	var health := player.health
	player.receive_hit(20.0, 10.0, foe.global_position, true)
	var haste_report: Dictionary = game.combat_feedback_report()
	check.call(player.health == health and is_equal_approx(player.rune, 40.0 + RunePlayer.PERFECT_DODGE_RUNE) and dodged.size() == 1 and player.perfect_dodge_count == 1,
		"An early-dodge hostile contact is avoided, pays rune once and emits one perfect dodge")
	check.call(is_equal_approx(float(haste_report.haste_remaining), GAME_SCRIPT.HASTE_DURATION) and is_equal_approx(game.enemy_time_scale(), GAME_SCRIPT.HASTE_SCALE) and Engine.time_scale == 1.0,
		"Rune Haste slows enemy time only; Engine.time_scale stays at 1")
	check.call(int(haste_report.afterimages) == 1 and tree.get_nodes_in_group("afterimages")[0].mesh_count > 0,
		"Balanced quality leaves one baked afterimage of the displayed pose")
	player.receive_hit(20.0, 10.0, foe.global_position, true)
	check.call(dodged.size() == 1 and is_equal_approx(player.rune, 40.0 + RunePlayer.PERFECT_DODGE_RUNE), "A second contact in the same dodge cannot pay again")
	# Enemy timers advance at the haste scale; its hit stop stays real.
	foe.cooldown = 1.0
	foe.stagger = 0.0
	foe.global_position = player.global_position + Vector3.FORWARD * 30.0
	foe._physics_process(1.0 / 60.0)
	check.call(is_equal_approx(foe.cooldown, 1.0 - GAME_SCRIPT.HASTE_SCALE / 60.0), "Enemy cooldowns advance on hasted time")
	foe.hit_pause = 0.05
	foe.hit_pause_started_frame = Engine.get_physics_frames() - 1
	foe._physics_process(1.0 / 60.0)
	check.call(is_equal_approx(foe.hit_pause, 0.05 - 1.0 / 60.0), "Enemy hit stop keeps real time during Rune Haste")
	var projectile := RuneProjectile.new()
	projectile.player = player
	projectile.world = game
	projectile.direction = Vector3.LEFT
	game.add_child(projectile)
	projectile.global_position = player.global_position + Vector3(40.0, 1.0, 0.0)
	var projectile_start := projectile.global_position
	projectile._physics_process(1.0 / 60.0)
	# Far-from-origin float32 positions: compare travel with a small absolute bound.
	check.call(absf(projectile.global_position.distance_to(projectile_start) - 10.0 * GAME_SCRIPT.HASTE_SCALE / 60.0) < 0.002, "Hostile projectiles share hasted enemy time")
	projectile.queue_free()
	# Late, non-dodge and post-hit invulnerability never qualify.
	player.restore(start)
	player.active = true
	player.invulnerability = 0.2
	player.dodge_time = RunePlayer.DODGE_DURATION - RunePlayer.PERFECT_DODGE_WINDOW - 0.03
	player.perfect_dodge_ready = true
	player.receive_hit(20.0, 10.0, foe.global_position, true)
	check.call(dodged.size() == 1 and player.perfect_dodge_ready, "A contact after the perfect window is an ordinary i-frame avoid")
	player.dodge_time = 0.0
	player.perfect_dodge_ready = true
	player.receive_hit(20.0, 10.0, foe.global_position, true)
	check.call(dodged.size() == 1, "Skill/respawn invulnerability without a dodge is never a perfect dodge")
	# Haste time is real and is cleared by encounter resets.
	game.set_physics_process(true)
	await _tick(tree)
	check.call(float(game.haste_remaining) < GAME_SCRIPT.HASTE_DURATION, "Rune Haste counts down on real physics time")
	game.set_physics_process(false)
	game.haste_remaining = 0.2
	check.call(game.enemy_time_scale() > GAME_SCRIPT.HASTE_SCALE and game.enemy_time_scale() < 1.0, "Haste releases smoothly over its final moment")
	game.reset_encounter()
	check.call(game.haste_remaining == 0.0 and is_equal_approx(game.enemy_time_scale(), 1.0) and tree.get_nodes_in_group("afterimages").all(func(node): return node.is_queued_for_deletion()),
		"Encounter resets clear Rune Haste and afterimages")
	if is_instance_valid(foe):
		foe.queue_free()

	# --- Screen FX ------------------------------------------------------------
	var fx: RuneScreenFX = game.screen_fx
	fx.reset()
	player.restore(start)
	player.active = true
	fx._process(0.016)
	check.call(not fx.grade.visible and not fx.vignette.visible, "Idle full health draws no screen effect and no screen copy")
	player.invulnerability = 0.0
	player.receive_hit(10.0, 5.0, start + Vector3.FORWARD, false)
	fx._process(0.016)
	check.call(fx.vignette.visible and fx.hurt > 0.5 and not fx.grade.visible and String(player.feedback.presentation_report().flash_kind) == "hurt",
		"Taking damage flashes the hero and the screen edge without a screen-read pass")
	player.health = player.max_health * 0.12
	for step in range(30):
		fx._process(1.0 / 30.0)
	check.call(fx.low_health > 0.5 and fx.vignette.visible, "Low health raises a heartbeat vignette")
	player.health = player.max_health
	for step in range(40):
		fx._process(1.0 / 30.0)
	check.call(fx.low_health == 0.0 and not fx.vignette.visible, "Recovered health clears the vignette")
	game.rig.snap()
	var contact: Vector3 = game.rig.camera.global_position + (-game.rig.camera.global_basis.z) * 4.0
	check.call(fx.trigger_impact(_context("charged", contact), game.rig.camera) and fx.grade.visible == false, "Charged contacts arm an impact pulse")
	fx._process(0.001)
	check.call(fx.grade.visible and fx.impact > 0.9, "Balanced quality draws the short radial impact grade")
	for step in range(20):
		fx._process(1.0 / 60.0)
	check.call(not fx.grade.visible, "The impact grade expires and stops copying the screen")
	check.call(not fx.trigger_impact(_context("light", contact), game.rig.camera), "Ordinary light contacts never blur the screen")
	Session.shake = false
	check.call(not fx.trigger_impact(_context("charged", contact), game.rig.camera), "Radial blur follows the screen-shake comfort setting")
	Session.shake = true

	# --- HUD trails, damage numbers, reticle ----------------------------------
	var hud: RuneHUD = game.ui
	hud.hud.show()
	player.health = player.max_health
	hud._process(0.016)
	player.health = player.max_health - 40.0
	hud._process(0.016)
	check.call(hud.health_trail.value > hud.health_bar.value and is_equal_approx(hud.health_bar.value, player.health), "Player damage leaves a delayed chip behind the health bar")
	for step in range(120):
		hud._process(1.0 / 60.0)
	check.call(is_equal_approx(hud.health_trail.value, player.health), "The player damage chip settles onto actual health")
	player.health = player.max_health
	hud._process(0.016)
	check.call(is_equal_approx(hud.health_trail.value, player.health), "Healing raises the chip with the bar")
	seed(rng_probe_seed)
	expected_global = randf()
	seed(rng_probe_seed)
	var number: Label = hud.floating_damage(69.3, contact)
	hud.style_damage(number, _context("charged", contact, {"killed":true}))
	check.call(number.get_theme_font_size("font_size") >= 38 and number.text.begins_with("✦") and number.get_theme_constant("outline_size") > 0,
		"Charged killing blows get a larger outlined number with a kill mark")
	var blocked: Label = hud.floating_damage(9.0, contact)
	hud.style_damage(blocked, _context("light", contact, {"blocked":true}))
	check.call(blocked.text.ends_with("BLOCK"), "Shield blocks are labelled")
	check.call(randf() == expected_global, "Damage-number drift uses the HUD's own RNG")
	check.call(hud.lock_marker is LockReticle, "Lock-on uses the drawn reticle")
	hud.lock_marker.retarget(7, true)
	check.call(hud.lock_marker.emphasis and hud.lock_marker.age == 0.0, "Boss/elite targets emphasise the reticle")

	# --- Verified tone is preserved: glow stays off in both qualities ---------
	var environment: Environment = game.sanctuary.get_node("SanctuaryEnvironment").environment
	Session.quality = 0
	game.apply_quality()
	var balanced_glow := environment.glow_enabled
	Session.quality = 1
	game.apply_quality()
	check.call(not balanced_glow and not environment.glow_enabled,
		"Glow stays off: the Compatibility glow path re-toned the whole frame in the v0.1.19 A/B")

	# --- Restore -----------------------------------------------------------
	game.started = false
	game.queue_free()
	await _tick(tree)
	Session.quality = saved_quality
	Session.shake = saved_shake
	Session.shards = saved_shards
	world.call("apply_quality")
	world.get_viewport().scaling_3d_scale = saved_render_scale
	if is_instance_valid(saved_camera):
		saved_camera.current = true
	for id in isolated:
		var entry: Dictionary = isolated[id]
		if is_instance_valid(entry.node):
			for group in entry.groups:
				entry.node.add_to_group(group)
			entry.node.set_physics_process(entry.physics)
			entry.node.set_process(entry.process)
	for action in actions:
		if float(actions[action]) > 0.0:
			Input.action_press(action, actions[action])
	tree.paused = saved_pause
	world.player.set_physics_process(saved_player_physics)
	world.set_physics_process(saved_world_physics)
	return true
