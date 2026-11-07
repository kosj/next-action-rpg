extends RefCounted

# Actual Game signal wiring plus real hurtbox receipts. Presentation geometry,
# clock/lifecycle contracts do not establish normal-speed art or hardware QA.
const ACTIONS: Array[StringName] = [&"light", &"heavy", &"dodge", &"parry", &"heal", &"skill_1", &"skill_2", &"skill_3", &"left", &"right", &"forward", &"back", &"sprint"]

class HitTarget:
	extends StaticBody3D
	var hits := 0
	var damage := 0.0
	var poise := 0.0
	var context: Dictionary = {}
	var notify_player: RunePlayer
	func receive_hit(amount: float, received_poise: float, _origin: Vector3, _parryable: bool = true, packet: Dictionary = {}) -> void:
		hits += 1
		damage += amount
		poise = received_poise
		context = packet.duplicate(true)
		if is_instance_valid(notify_player):
			notify_player.on_hit(amount, packet.get("point", global_position), packet)

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _target(parent: Node3D, point: Vector3, player: RunePlayer = null) -> HitTarget:
	var target := HitTarget.new()
	target.collision_layer = 4
	target.collision_mask = 0
	target.notify_player = player
	var collision := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.12
	collision.shape = sphere
	collision.position.y = 1.1
	target.add_child(collision)
	parent.add_child(target)
	target.global_position = point
	return target

static func _body(parent: Node3D, point: Vector3, size: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 0
	var collision := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	collision.shape = box
	body.add_child(collision)
	parent.add_child(body)
	body.global_position = point
	return body

static func _effects(game: Node3D) -> Array[Node3D]:
	var result: Array[Node3D] = []
	for child in game.get_children():
		if child.is_in_group("skill_effects") and not child.is_queued_for_deletion():
			result.append(child as Node3D)
	return result

static func _latest(game: Node3D) -> Node3D:
	var effects := _effects(game)
	return effects[-1] if not effects.is_empty() else null

static func _rings(game: Node3D) -> int:
	var result := 0
	for child in game.get_children():
		if child is RuneEffect and not child.is_queued_for_deletion():
			result += 1
	return result

static func _cancel(game: Node3D) -> void:
	for effect in _effects(game):
		effect.call("cancel")

static func _prepare(player: RunePlayer, point: Vector3) -> void:
	player.set_physics_process(false)
	player.restore(point)
	player.active = true
	player.ui_input_guard = 0
	player.facing = Vector3.FORWARD
	player.camera_yaw = 0.0
	player.rune = 100.0
	player.velocity = Vector3.ZERO

static func _state(effect: Node3D) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for child in effect.find_children("*", "MeshInstance3D", true, false):
		var instance := child as MeshInstance3D
		var record := {"name":String(instance.name), "transform":instance.transform, "visible":instance.visible, "uniforms":{}}
		var material := instance.material_override
		if material is ShaderMaterial and material.shader != null:
			for property: Dictionary in material.shader.get_shader_uniform_list():
				var key := StringName(property.name)
				record.uniforms[key] = material.get_shader_parameter(key)
		elif material is StandardMaterial3D:
			record.uniforms["albedo"] = material.albedo_color
			record.uniforms["energy"] = material.emission_energy_multiplier
		result.append(record)
	return result.duplicate(true)

static func _geometry_signature(effect: Node3D) -> int:
	var data: Array = []
	for child in effect.find_children("*", "MeshInstance3D", true, false):
		var instance := child as MeshInstance3D
		if instance.mesh == null:
			continue
		var surfaces: Array = []
		for surface in range(instance.mesh.get_surface_count()):
			var arrays := instance.mesh.surface_get_arrays(surface)
			surfaces.append(arrays[Mesh.ARRAY_VERTEX])
		data.append({"name":String(instance.name), "vertices":surfaces, "transform":instance.transform})
	return hash(data)

static func _cancelled(effect: Node3D) -> bool:
	return is_instance_valid(effect) and effect.is_queued_for_deletion() and not bool(effect.call("presentation_report").get("valid", true))

static func run(world: Node3D, check: Callable) -> bool:
	var tree := world.get_tree()
	var saved_world_physics := world.is_physics_processing()
	var saved_player_physics: bool = world.player.is_physics_processing()
	var saved_pause := tree.paused
	var saved_mouse := Input.mouse_mode
	var saved_touch_requested := bool(TouchControls.get("_wanted_active"))
	var saved_camera: Camera3D = world.get_viewport().get_camera_3d()
	var saved_render_scale := world.get_viewport().scaling_3d_scale
	var saved_quality := Session.quality
	var saved_shake := Session.shake
	var saved_upgrades: Array = Session.upgrades.duplicate()
	var saved_audio_stopped := bool(Audio.presentation_report().stopped)
	var actions: Dictionary = {}
	for action in ACTIONS:
		actions[action] = Input.get_action_strength(action)
		Input.action_release(action)
	world.set_physics_process(false)
	world.player.set_physics_process(false)
	tree.paused = false
	Session.upgrades[0] = 0
	Session.shake = true
	Audio.start()
	var isolated: Dictionary = {}
	for group: StringName in [&"enemies", &"impact_effects", &"sword_waves", &"skill_effects"]:
		for node in tree.get_nodes_in_group(group):
			var id := node.get_instance_id()
			if not isolated.has(id):
				isolated[id] = {"node":node, "groups":[], "physics":node.is_physics_processing(), "process":node.is_processing()}
			isolated[id].groups.append(group)
			node.remove_from_group(group)
			node.set_physics_process(false)
			node.set_process(false)
	var game: Node3D = load("res://scenes/main.tscn").instantiate()
	game.position = Vector3(2300.0, 40.0, -2300.0)
	world.add_child(game)
	game.set_physics_process(false)
	game.player.set_physics_process(false)
	game.rig.set_physics_process(false)
	game.rig.cinematic = false
	game.hide()
	var player: RunePlayer = game.player
	var start := game.global_position + Vector3(500.0, 20.0, 500.0)
	_prepare(player, start)
	var front := _target(game, start + Vector3.FORWARD * 2.2, player)
	var rear := _target(game, start + Vector3.BACK * 3.0)
	var far_side := _target(game, start + Vector3.RIGHT * 6.4)
	var outside := _target(game, start + Vector3.RIGHT * 8.2)
	await _tick(tree)
	await _tick(tree)
	var signatures: Dictionary = {}
	var pulses: Array[float] = []
	var geometry_budget: Array[Dictionary] = []
	for index in range(3):
		_cancel(game)
		await _tick(tree)
		_prepare(player, start)
		Session.quality = 0
		game.rig.snap()
		for target in [front, rear, far_side, outside]:
			target.hits = 0
			target.damage = 0.0
		var ring_count := _rings(game)
		var cast_count := int(game.skill_presentation_report().cast_count)
		var accepted := player.use_skill(index)
		var effect := _latest(game)
		var attack: CombatStrike = player.strike
		check.call(accepted and effect != null and _effects(game).size() == 1 and int(game.skill_presentation_report().cast_count) == cast_count + 1,
			"Actual accepted skill %d passes through Game wiring to exactly one skill presentation" % (index + 1))
		check.call(_rings(game) == ring_count and is_equal_approx(player.rune, 100.0 - [25.0, 45.0, 80.0][index]),
			"Actual skill %d keeps its rune cost and replaces the old generic cast torus" % (index + 1))
		if effect == null or attack == null:
			continue
		effect.set_physics_process(false)
		var report: Dictionary = effect.call("presentation_report")
		check.call(bool(report.valid) and String(report.attack_id) == "skill_%d" % (index + 1) and int(report.attack_instance_id) == attack.attack_instance_id and int(report.owner_id) == player.get_instance_id(),
			"Skill %d presentation belongs to its real source and originating strike" % (index + 1))
		attack.step(0.159, Vector3.FORWARD, 4)
		effect.call("_physics_process", 0.159)
		report = effect.call("presentation_report")
		check.call(String(report.phase) == "preparation" and front.hits == 0 and rear.hits == 0 and game.impact_count == index,
			"Skill %d preparation is visible without fabricated contact, damage, or extra impact receipts" % (index + 1))
		check.call(game.rig.impact_age >= RuneCamera.IMPACT_DURATION and is_equal_approx(game.rig.camera.fov, RuneCamera.BASE_FOV),
			"Skill %d cast and preparation do not kick the confirmed-contact camera" % (index + 1))
		var preparation := _state(effect)
		attack.step(0.191, Vector3.FORWARD, 4)
		effect.call("_physics_process", 0.191)
		report = effect.call("presentation_report")
		check.call(String(report.phase) == "active" and not _state(effect).is_empty() and preparation != _state(effect),
			"Skill %d release changes real mesh or material state at the authoritative active phase" % (index + 1))
		check.call(front.hits == 1 and is_equal_approx(front.damage, [65.0, 55.0, 150.0][index]) and is_equal_approx(front.poise, [65.0, 65.0, 160.0][index]) and rear.hits == (0 if index == 0 else 1) and far_side.hits == (1 if index == 2 else 0) and outside.hits == 0,
			"Skill %d retains real directional/radial damage, poise and range exclusions with its new VFX" % (index + 1))
		var impacts: Array[Node] = tree.get_nodes_in_group("impact_effects")
		var variant_found := false
		for impact in impacts:
			if not impact.is_queued_for_deletion():
				var contact: Dictionary = impact.presentation_report()
				if String(contact.get("skill_variant", "")) == "skill_%d" % (index + 1):
					variant_found = true
		check.call(variant_found and player.hit_pause > 0.0,
			"Skill %d real hit dispatches its own confirmed-contact variant and attacker stop" % (index + 1))
		game.rig._physics_process(0.04)
		pulses.append(game.rig.impact_amplitude)
		check.call(game.rig.camera.fov < RuneCamera.BASE_FOV,
			"Skill %d confirmed contact produces a finite camera pulse" % (index + 1))
		if index == 2:
			var audio: Dictionary = Audio.presentation_report().last_impact
			check.call(bool(audio.get("accepted", false)) and String(audio.get("style", "")) == "judgement" and audio.get("layers", []).size() == 5,
				"The actual ultimate contact synchronously allocates its five-layer judgement audio profile")
		var stopped := _state(effect)
		var stopped_age := float(report.age_s)
		for tick in range(3):
			effect.call("_physics_process", 0.05)
		check.call(stopped == _state(effect) and is_equal_approx(float(effect.call("presentation_report").age_s), stopped_age),
			"Skill %d hitstop preserves the sampled release meshes, material uniforms and clock" % (index + 1))
		check.call(front.hits == 1 and outside.hits == 0,
			"Advancing only skill %d presentation cannot add damage or bypass the target ledger" % (index + 1))
		signatures[_geometry_signature(effect)] = true
		geometry_budget.append({"skill":index + 1, "triangles":int(report.triangles), "meshes":int(report.mesh_count)})
		check.call(int(report.triangles) > 0 and int(report.triangles) <= 4000 and int(report.mesh_count) > 0,
			"Skill %d uses finite nonempty procedural presentation geometry" % (index + 1))
		player.hit_pause = 0.0
		attack.step(0.23, Vector3.FORWARD, 4)
		effect.call("_physics_process", 0.23)
		check.call(String(effect.call("presentation_report").phase) == "recovery" and front.hits == 1,
			"Skill %d settles through its original recovery without extra hits" % (index + 1))
		attack.step(0.23, Vector3.FORWARD, 4)
		player.strike = null
		effect.call("_physics_process", 0.001)
		check.call(String(effect.call("presentation_report").phase) == "tail", "A normally completed skill %d releases into its finite tail" % (index + 1))
		if index == 1:
			effect.set_physics_process(true)
			var paused_state := _state(effect)
			var paused_tail := float(effect.call("presentation_report").tail_s)
			tree.paused = true
			for frame in range(3):
				await tree.process_frame
			check.call(paused_state == _state(effect) and is_equal_approx(float(effect.call("presentation_report").tail_s), paused_tail),
				"Scene pause freezes an already detached skill tail through ordinary processing")
			tree.paused = false
			effect.set_physics_process(false)
		var lifetime: WeakRef = weakref(effect)
		for tick in range(20):
			if effect.is_queued_for_deletion():
				break
			effect.call("_physics_process", 0.1)
		await _tick(tree)
		check.call(lifetime.get_ref() == null, "Skill %d releases all presentation after a bounded tail" % (index + 1))
	check.call(signatures.size() == 3, "The three skill releases use structurally distinct actual mesh geometry")
	check.call(pulses.size() == 3 and pulses[0] < pulses[1] and pulses[1] < pulses[2], "Confirmed skill camera punctuation increases from dash through storm to judgement")

	# Resolve the actual skill motor against a real wall. The wake must use
	# measured source positions, never continue thirteen-metre-per-second
	# nominal travel after move_and_slide has stopped the caster.
	var floor_body := _body(game, start + Vector3.DOWN * 0.5, Vector3(30.0, 1.0, 30.0))
	var wall := _body(game, start + Vector3(0.0, 1.0, -1.0), Vector3(6.0, 4.0, 0.2))
	_prepare(player, start)
	for target in [front, rear, far_side, outside]:
		target.hits = 0
	await _tick(tree)
	await _tick(tree)
	check.call(player.use_skill(0), "A real wall-resolved dash begins through normal accepted skill wiring")
	var moving_effect := _latest(game)
	player.set_physics_process(true)
	for tick in range(12):
		await _tick(tree)
	if moving_effect != null and is_instance_valid(moving_effect):
		var moving: Dictionary = moving_effect.call("presentation_report")
		var actual_travel := Vector2(player.global_position.x - start.x, player.global_position.z - start.z).length()
		var history_count := int(moving.history_count)
		var honest_history := history_count >= 2
		for point: Vector3 in moving.history_points:
			if Vector2(point.x - start.x, point.z - start.z).length() > actual_travel + 0.01:
				honest_history = false
		check.call(actual_travel > 0.2 and actual_travel < 0.7 and honest_history and Vector3(moving.position).is_equal_approx(player.global_position),
			"The live dash VFX follows the actual collision-resolved root and its bounded world wake")
		for tick in range(6):
			await _tick(tree)
		if is_instance_valid(moving_effect):
			check.call(int(moving_effect.call("presentation_report").history_count) == history_count and front.hits == 0,
				"A wall-stopped dash adds no fictitious forward wake samples or through-wall target hit")
	else:
		check.call(false, "A live accepted dash retains its presentation during the measured active interval")
	player.set_physics_process(false)
	_cancel(game)
	player.strike = null
	floor_body.queue_free()
	wall.queue_free()
	await _tick(tree)
	await _tick(tree)

	# Rejection must never allocate a visual or spend rune.
	_prepare(player, start)
	player.rune = 0.0
	var rejected_casts := int(game.skill_presentation_report().cast_count)
	check.call(not player.use_skill(0) and not player.use_skill(-1) and not player.use_skill(3) and _effects(game).is_empty() and player.rune == 0.0 and int(game.skill_presentation_report().cast_count) == rejected_casts,
		"Invalid and resource-gated actual skill requests produce no cast effect or cost")
	player.skill_effect.emit(start, 1.6, Color("8deac2"))
	check.call(_rings(game) == 1, "The existing nonattack heal signal retains its ordinary ring presentation")
	for child in game.get_children():
		if child is RuneEffect:
			child.queue_free()
	# Quality is selected at creation, not by inverting the saved setting roles.
	var quality_triangles: Array[int] = []
	for quality in range(2):
		_prepare(player, start)
		Session.quality = quality
		check.call(player.use_skill(1), "Quality %d accepts the real storm cast" % quality)
		var effect := _latest(game)
		if effect != null:
			quality_triangles.append(int(effect.call("presentation_report").triangles))
			effect.call("cancel")
		await _tick(tree)
	check.call(quality_triangles.size() == 2 and quality_triangles[1] <= quality_triangles[0], "Performance quality does not exceed balanced skill geometry cost")

	# Terminal owner paths and replacement differ from normal tail completion.
	for terminal: String in ["replacement", "restore", "inactive", "death", "encounter_reset"]:
		_prepare(player, start)
		player.use_skill(0)
		var effect := _latest(game)
		if effect == null:
			check.call(false, "Terminal skill fixture must create its actual effect")
			continue
		effect.set_physics_process(false)
		match terminal:
			"replacement": player.strike = CombatStrike.new(player, RunePlayer.LIGHTS[0])
			"restore": player.restore(start + Vector3.RIGHT)
			"inactive": player.active = false
			"death": player.dead = true
			"encounter_reset": game.reset_encounter()
		if not effect.is_queued_for_deletion():
			effect.call("_physics_process", 0.016)
		check.call(_cancelled(effect), "A skill cancels instead of lingering after %s" % terminal)
		var reference: WeakRef = weakref(effect)
		await _tick(tree)
		check.call(reference.get_ref() == null, "Cancelled skill nodes release after %s" % terminal)

	_prepare(player, start)
	for index in range(10):
		player.strike = null
		player.rune = 100.0
		player.use_skill(index % 3)
	check.call(_effects(game).size() <= 4, "Same-frame accepted casts cannot bypass the four-effect crowd cap through queued deletion")
	_cancel(game)
	await _tick(tree)
	check.call(_effects(game).is_empty(), "Cancelling a crowded skill scene releases every surviving effect")
	print("RUNEFALL_SKILL_VFX_CONTRACTS " + JSON.stringify({"geometry":geometry_budget, "quality_triangles":quality_triangles, "scope":"Actual Game cast/receipt/clock/lifecycle contracts; normal-speed art, hearing and hardware approval separate"}))
	game.queue_free()
	await tree.process_frame
	await tree.process_frame
	for record: Dictionary in isolated.values():
		if is_instance_valid(record.node):
			for group: StringName in record.groups:
				record.node.add_to_group(group)
			record.node.set_physics_process(bool(record.physics))
			record.node.set_process(bool(record.process))
	Session.quality = saved_quality
	Session.shake = saved_shake
	Session.upgrades.assign(saved_upgrades)
	world.set_physics_process(saved_world_physics)
	world.player.set_physics_process(saved_player_physics)
	world.get_viewport().scaling_3d_scale = saved_render_scale
	if is_instance_valid(saved_camera):
		saved_camera.make_current()
	for action in ACTIONS:
		if float(actions[action]) > 0.0:
			Input.action_press(action, float(actions[action]))
	Input.mouse_mode = saved_mouse
	TouchControls.set_gameplay_active(saved_touch_requested)
	if saved_audio_stopped:
		Audio.stop_all()
	tree.paused = saved_pause
	return true
