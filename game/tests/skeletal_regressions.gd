extends RefCounted

static func _scene(missing_clip: StringName = &"", with_skin: bool = true, broken_track: bool = false, with_death: bool = false, zero_weights: bool = false, forbidden_track: String = "", extra_states: Array[StringName] = []) -> PackedScene:
	var root: Node3D = CharacterBody3D.new() if forbidden_track == "gameplay" else Node3D.new()
	root.name = "SyntheticRig"
	var skeleton := Skeleton3D.new()
	skeleton.name = "Skeleton3D"
	skeleton.add_bone("Root")
	root.add_child(skeleton)
	skeleton.owner = root
	var mesh := MeshInstance3D.new()
	mesh.name = "SkinMesh"
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3.ZERO, Vector3.RIGHT, Vector3.UP])
	arrays[Mesh.ARRAY_BONES] = PackedInt32Array([0,0,0,0,0,0,0,0,0,0,0,0])
	arrays[Mesh.ARRAY_WEIGHTS] = PackedFloat32Array([1,0,0,0,1,0,0,0,1,0,0,0])
	if zero_weights:
		arrays[Mesh.ARRAY_WEIGHTS] = PackedFloat32Array([0,0,0,0,0,0,0,0,0,0,0,0])
	arrays[Mesh.ARRAY_INDEX] = PackedInt32Array([0,1,2])
	var surface := ArrayMesh.new()
	surface.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.mesh = surface
	mesh.skeleton = NodePath("../Skeleton3D")
	if with_skin:
		var skin := Skin.new()
		skin.add_bind(0, Transform3D.IDENTITY)
		mesh.skin = skin
	root.add_child(mesh)
	mesh.owner = root
	var player := AnimationPlayer.new()
	player.name = "AnimationPlayer"
	player.root_node = NodePath("..")
	root.add_child(player)
	player.owner = root
	var library := AnimationLibrary.new()
	var reset := Animation.new()
	reset.length = 0.01
	var reset_track := reset.add_track(Animation.TYPE_POSITION_3D)
	reset.track_set_path(reset_track, NodePath("Skeleton3D:Root"))
	reset.position_track_insert_key(reset_track, 0.0, Vector3.ZERO)
	library.add_animation(&"RESET", reset)
	var states: Array[StringName] = SkeletalVisualBridge.REQUIRED_STATES.duplicate()
	if with_death:
		states.append(&"death")
	for state in extra_states:
		if not state in states:
			states.append(state)
	for state: StringName in states:
		if state == missing_clip:
			continue
		var animation := Animation.new()
		animation.length = 1.0
		animation.loop_mode = Animation.LOOP_LINEAR if state in SkeletalVisualBridge.LOOP_STATES else Animation.LOOP_NONE
		var track := animation.add_track(Animation.TYPE_POSITION_3D)
		animation.track_set_path(track, NodePath("Missing:Root" if broken_track else "Skeleton3D:Root"))
		animation.position_track_insert_key(track, 0.0, Vector3.ZERO)
		animation.position_track_insert_key(track, 1.0, Vector3.RIGHT)
		if state == &"light_1" and not forbidden_track.is_empty():
			if forbidden_track == "absolute":
				animation.track_set_path(track, NodePath("/root/Session:position"))
			elif forbidden_track == "gameplay":
				animation.track_set_path(track, NodePath("."))
			elif forbidden_track == "property":
				var value_track := animation.add_track(Animation.TYPE_VALUE)
				animation.track_set_path(value_track, NodePath(".:position"))
				animation.track_insert_key(value_track, 0.0, Vector3.ZERO)
		library.add_animation(state, animation)
	player.add_animation_library(&"", library)
	var scene := PackedScene.new()
	assert(scene.pack(root) == OK)
	root.free()
	return scene

static func run(world: Node3D, check: Callable) -> bool:
	var visual := ActorVisual.new()
	world.add_child(visual)
	visual.setup("hero")
	var result := visual.mount_rig(_scene(&"light_2"))
	check.call(not result.ok and "light_2" in result.reason and visual.skeletal_bridge == null and visual.model.visible, "Missing authored clip rejects the rig and preserves the prototype fallback")
	result = visual.mount_rig(_scene(&"", false))
	check.call(not result.ok and "Skin" in result.reason and visual.skeletal_bridge == null, "A Skeleton without actual skin bindings is not a finished rig")
	result = visual.mount_rig(_scene(&"", true, false, false, true))
	check.call(not result.ok and "weights" in result.reason, "A Skin with zero vertex weights cannot masquerade as a deforming character")
	result = visual.mount_rig(_scene(&"", true, true))
	check.call(not result.ok and "target" in result.reason, "Unresolved animation tracks reject the rig before playback")
	for forbidden in ["absolute", "property", "gameplay"]:
		result = visual.mount_rig(_scene(&"", true, false, false, false, forbidden))
		check.call(not result.ok and visual.skeletal_bridge == null, "Rig rejects %s animation tracks without reaching gameplay state" % forbidden)
	result = visual.mount_rig(PackedScene.new())
	check.call(not result.ok and visual.skeletal_bridge == null, "An empty PackedScene fails cleanly without instantiation errors")
	result = visual.mount_rig(_scene())
	check.call(result.ok and visual.skeletal_bridge != null, "A weighted synthetic rig with the complete clip contract mounts")
	var bridge: SkeletalVisualBridge = visual.skeletal_bridge
	check.call(is_equal_approx(bridge.rig.rotation.y, PI), "Humanoid forward correction is applied once in the visual wrapper")
	check.call(bridge.animation_tree.active and not bridge.animation_player.active and bridge.animation_tree.callback_mode_process == AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL, "AnimationTree alone owns manually sampled skeletal playback")
	visual.pose(0.1, 0.0, -1.0, false, false, false, {"speed":0.0})
	check.call(bridge.selected_state == &"idle" and not visual.model.visible and bridge.visible, "A mounted rig replaces the pivot model only when a clip can be presented")
	visual.pose(0.1, 6.4, -1.0, false, false, false, {"speed":6.4})
	check.call(bridge.selected_state == &"walk", "Normal gameplay movement selects the authored walk/jog state")
	visual.pose(0.1, 8.5, -1.0, false, false, false, {"speed":8.5})
	check.call(bridge.selected_state == &"run", "Sprint gameplay movement selects run")
	var attack := {"speed":0.0, "attack_id":"light_1", "attack_elapsed":0.26, "attack_duration":0.52}
	visual.pose(0.0, 0.0, 0.5, false, false, false, attack)
	check.call(bridge.selected_state == &"light_1" and is_equal_approx(bridge.sampled_time, 0.5), "Attack clip time is normalized from authoritative gameplay elapsed and duration")
	var skeleton := bridge.rig.get_node("Skeleton3D") as Skeleton3D
	check.call(absf(skeleton.get_bone_pose_position(0).x - 0.5) < 0.01, "AnimationTree seeks and applies the actual bone track pose")
	await world.get_tree().process_frame
	await world.get_tree().process_frame
	check.call(absf(skeleton.get_bone_pose_position(0).x - 0.5) < 0.01, "Without a new gameplay snapshot a hit-paused rig does not advance independently")
	var dodge := attack.duplicate()
	dodge.merge({"dodge_remaining":0.16, "dodge_elapsed":0.16, "dodge_duration":0.32}, true)
	visual.pose(0.0, 0.0, -1.0, true, false, false, dodge)
	check.call(bridge.selected_state == &"dodge" and is_equal_approx(bridge.sampled_time, 0.5), "Dodge cancels an old attack presentation and uses gameplay dodge time")
	var parry := attack.duplicate()
	parry.merge({"parry_remaining":0.11, "parry_elapsed":0.11, "parry_duration":0.22}, true)
	visual.pose(0.0, 0.0, -1.0, false, true, false, parry)
	check.call(bridge.selected_state == &"parry", "Parry state overrides a stale attack in presentation")
	parry.merge({"stagger":0.1, "hit_elapsed":0.05, "hit_duration":0.15}, true)
	visual.pose(0.0, 0.0, -1.0, false, false, false, parry)
	check.call(bridge.selected_state == &"hit", "Hit reaction cancels parry and attack presentation")
	visual.pose(0.0, 0.0, 0.2, false, false, false, {"attack_id":"heavy", "attack_elapsed":0.1, "attack_duration":0.8})
	check.call(visual.model.visible and not bridge.visible and "heavy" in visual.rig_status, "An unauthored heavy attack visibly falls back instead of pretending an unrelated clip exists")
	visual.pose(0.0, 0.0, -1.0, false, false, true, {"dead":true})
	check.call(visual.model.visible and not bridge.visible and "death" in visual.rig_status, "An unauthored death keeps the existing death presentation")
	visual.pose(0.0, 0.0, -1.0, false, false, false, {"speed":0.0})
	check.call(bridge.visible and not visual.model.visible and bridge.selected_state == &"idle", "The valid rig resumes when gameplay returns to a supported state")
	result = visual.mount_rig(_scene(&"hit"))
	check.call(not result.ok and visual.skeletal_bridge == bridge, "A rejected replacement cannot discard an already validated rig")
	visual.clear_rig()
	check.call(visual.skeletal_bridge == null and visual.model.visible, "Detaching the rig restores the prototype visual")
	result = visual.mount_rig(_scene(), {}, SkeletalVisualBridge.REQUIRED_STATES, 0.0)
	check.call(result.ok and is_zero_approx(visual.skeletal_bridge.rig.rotation.y), "An already aligned imported wrapper can explicitly disable forward correction")
	visual.clear_rig()
	result = visual.mount_rig(_scene(&"", true, false, true), {&"death":&"death"})
	visual.pose(0.0, 0.0, -1.0, false, false, true, {"dead":true, "death_elapsed":0.5})
	check.call(result.ok and visual.skeletal_bridge.selected_state == &"death" and is_equal_approx(visual.skeletal_bridge.sampled_time, 0.5), "An explicitly authored optional death clip uses the gameplay death clock")
	visual.free()
	var player := RunePlayer.new()
	world.add_child(player)
	player.strike = CombatStrike.new(player, RunePlayer.LIGHTS[0])
	player.strike.elapsed = 0.26
	var snapshot := player.presentation_snapshot()
	check.call(snapshot.attack_id == "light_1" and is_equal_approx(snapshot.attack_duration, 0.52), "Player snapshot identifies the actual light attack and authoritative duration")
	check.call(is_equal_approx(snapshot.attack_startup, 0.13) and is_equal_approx(snapshot.attack_active, 0.17) and is_equal_approx(snapshot.attack_reach, 2.7) and is_equal_approx(snapshot.attack_arc, 130.0), "Attack audit scalars report the actual strike phase, reach and arc")
	snapshot.attack_elapsed = 99.0
	snapshot.attack_id = "heavy"
	check.call(is_equal_approx(player.strike.elapsed, 0.26) and player.strike.presentation_id == &"light_1", "Editing a presentation snapshot cannot mutate the combat strike")
	var custom := CombatStrike.new(player, RunePlayer.HEAVY.duplicate())
	check.call(custom.presentation_id == &"unmapped_attack", "An unidentified transient attack requests an explicit fallback instead of masquerading as idle")
	custom = null
	player.restore(Vector3.ZERO)
	snapshot = player.presentation_snapshot()
	check.call(snapshot.attack_id == "" and snapshot.stagger == 0.0 and snapshot.dodge_remaining == 0.0 and snapshot.parry_remaining == 0.0, "Checkpoint restore also clears every transient presentation source")
	player.free()
	check.call(await _full_presentation_checks(world, check), "Directional and full-action skeletal presentation checks complete")
	return true

static func _full_presentation_checks(world: Node3D, check: Callable) -> bool:
	var extras: Array[StringName] = [&"heavy", &"charge", &"skill_1", &"skill_2", &"skill_3", &"death", &"heal", &"walk_back", &"walk_left", &"walk_right"]
	var states: Array[StringName] = SkeletalVisualBridge.REQUIRED_STATES.duplicate()
	states.append_array(extras)
	var player := RunePlayer.new()
	player.world = world
	world.add_child(player)
	player.set_physics_process(false)
	player.collision_mask = 0
	player.restore(Vector3(240, 10, 240))
	player.active = true
	player.ui_input_guard = 0
	var result := player.visual.mount_rig(_scene(&"", true, false, false, false, "", extras), {}, states)
	check.call(result.ok, "A full hero profile mounts directional loops and optional authored actions")
	if not result.ok:
		player.free()
		return false
	var bridge := player.visual.skeletal_bridge
	check.call(bridge.get_skeleton() != null and bridge.bone_report().names == [&"Root"] and bridge.bone_report().roles.is_empty(), "Skeleton access reports real bone names without inventing a missing right-hand mapping")
	var actor_transform := player.global_transform
	player.facing = Vector3.FORWARD
	for direction in [Vector3.FORWARD, Vector3.RIGHT, Vector3.BACK, Vector3.LEFT]:
		player.dodge_time = 0.16
		player.dodge_direction = direction
		player.visual.pose(0.0, 0.0, -1.0, true, false, false, player.presentation_snapshot())
		var rig_forward := bridge.rig.basis * Vector3.BACK
		check.call(bridge.selected_state == &"dodge" and rig_forward.normalized().dot(direction) > 0.999, "Dodge rig faces the actual %s burst direction" % str(direction))
		check.call(player.global_transform == actor_transform and player.facing == Vector3.FORWARD, "Directional dodge presentation cannot rotate or translate the gameplay actor")
	player.dodge_time = 0.0
	player.velocity = Vector3.ZERO
	player.visual.pose(0.0, 0.0, -1.0, false, false, false, player.presentation_snapshot())
	check.call((bridge.rig.basis * Vector3.BACK).dot(Vector3.FORWARD) > 0.999, "Leaving dodge restores the normal rig facing before the next state")
	for spec in [[Vector3.FORWARD, 6.4, &"walk"], [Vector3.BACK, 6.4, &"walk_back"], [Vector3.LEFT, 6.4, &"walk_left"], [Vector3.RIGHT, 6.4, &"walk_right"], [Vector3.FORWARD, 8.5, &"run"], [Vector3.RIGHT, 8.5, &"walk_right"], [Vector3(1,0,-1), 6.4, &"walk"], [Vector3(1,0,1), 6.4, &"walk_back"]]:
		player.velocity = spec[0].normalized() * float(spec[1])
		var before := player.velocity
		player.visual.pose(0.1, float(spec[1]), -1.0, false, false, false, player.presentation_snapshot())
		check.call(bridge.selected_state == spec[2] and player.velocity == before and player.facing == Vector3.FORWARD, "Lock-on locomotion %s selects %s without changing movement or facing" % [str(spec[0]), String(spec[2])])
	bridge.reset_presentation(player.presentation_epoch)
	bridge.present(0.1, {"speed":8.5, "move_local_x":1.0, "move_local_z":0.0})
	check.call(bridge.selected_state == &"walk_right" and is_equal_approx(bridge.sampled_time, 0.1328125), "Side sprint scales the authored 6.4m/s directional cycle instead of playing forward run")
	bridge.reset_presentation(player.presentation_epoch)
	bridge.present(0.1, {"speed":3.6, "move_local_x":0.0, "move_local_z":-1.0, "locomotion_reference_speed":3.6})
	check.call(bridge.selected_state == &"walk" and is_equal_approx(bridge.sampled_time, 0.1), "Enemy locomotion uses its 3.6m/s reference without changing controller speed")
	bridge.present(0.0, {"speed":0.1, "move_local_x":1.0, "move_local_z":0.0})
	check.call(bridge.selected_state == &"idle", "The exact 0.1m/s locomotion threshold stays idle")
	bridge.present(0.0, {"speed":0.0, "move_local_x":0.0, "move_local_z":0.0})
	check.call(bridge.selected_state == &"idle" and is_finite(bridge.sampled_time), "A zero direction at rest remains a finite idle pose")
	check.call(not bridge.present(0.1, {"speed":6.4, "move_local_x":NAN, "move_local_z":-1.0}) and not bridge.present(0.1, {"speed":0.0, "dodge_remaining":0.1, "dodge_local_x":INF}), "Non-finite motion directions fail without applying a non-finite rig transform")
	player.facing = Vector3.RIGHT
	player.velocity = Vector3.BACK * 6.4
	var snapshot := player.presentation_snapshot()
	check.call(is_equal_approx(snapshot.move_local_x, 1.0) and is_zero_approx(snapshot.move_local_z), "Movement snapshots use actual facing rather than a fixed world axis")
	snapshot.move_local_x = -99.0
	check.call(player.velocity == Vector3.BACK * 6.4 and player.facing == Vector3.RIGHT, "Editing direction snapshot values cannot mutate actor authority")
	player.facing = Vector3.FORWARD
	player.velocity = Vector3.ZERO
	player.heavy_held = 0.325
	Input.action_press("heavy")
	player.visual.pose(0.0, 0.0, -1.0, false, false, false, player.presentation_snapshot())
	check.call(bridge.selected_state == &"charge" and is_equal_approx(bridge.sampled_time, 0.5), "Stationary charge samples the actual held-heavy gameplay clock")
	player.heavy_held = 1.3
	player.visual.pose(0.0, 0.0, -1.0, false, false, false, player.presentation_snapshot())
	check.call(bridge.selected_state == &"charge" and is_equal_approx(bridge.sampled_time, 1.0) and is_equal_approx(player.heavy_held, 1.3), "A ready charge holds its final pose without looping or changing heavy power time")
	player.velocity = Vector3.BACK * 6.4
	player.visual.pose(0.1, 6.4, -1.0, false, false, false, player.presentation_snapshot())
	check.call(bridge.selected_state == &"walk_back" and player.presentation_snapshot().charge_active, "Moving charge preserves directional footsteps while charging continues")
	Input.action_release("heavy")
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	player.velocity = Vector3.ZERO
	player.visual.pose(0.0, 0.0, -1.0, false, false, false, player.presentation_snapshot())
	check.call(bridge.selected_state == &"idle" and not player.presentation_snapshot().charge_active, "Released heavy input cannot leave a stale charge pose")
	player.health = player.max_health * 0.25
	player.potions = 3
	player.hit_pause = 0.0
	var health_before := player.health
	# Leave the physics_frame signal boundary before injecting a new press.
	# Godot schedules action_press's physics "just pressed" flag for the next
	# physics tick; a same-signal manual _physics_process call is too early.
	await world.get_tree().process_frame
	Input.action_press("heal")
	Input.action_press("forward")
	player._physics_process(1.0/60.0)
	check.call(player.health > health_before and player.potions == 2 and player.velocity.z < -6.0 and player.strike == null, "Healing applies immediately and does not lock movement or start an attack")
	check.call(bridge.selected_state == &"walk" and is_equal_approx(player.presentation_heal_remaining, 0.35), "Moving heal keeps locomotion and the existing instant potion effect")
	Input.action_release("heal")
	Input.action_release("forward")
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	player._physics_process(0.1)
	check.call(bridge.selected_state == &"heal" and is_equal_approx(player.presentation_snapshot().heal_elapsed, 0.1), "Stationary healing uses its independent visual-only elapsed clock")
	var heal_remaining := player.presentation_heal_remaining
	var sampled_before := bridge.sampled_time
	player.hit_pause = 0.035
	player._physics_process(0.02)
	check.call(is_equal_approx(player.presentation_heal_remaining, heal_remaining) and is_equal_approx(bridge.sampled_time, sampled_before), "Hit pause freezes the heal presentation clock and the skeletal sample")
	player.hit_pause = 0.0
	player.begin_attack(false, 0)
	check.call(player.presentation_heal_remaining == 0.0, "Starting an attack cancels a pending heal gesture without delaying the attack")
	player.strike = null
	for action in [&"heavy", &"skill_1", &"skill_2", &"skill_3"]:
		player.strike = CombatStrike.new(player, RunePlayer.HEAVY, 1.0, action)
		player.strike.elapsed = player.strike.data.duration() * 0.5
		player.visual.pose(0.0, 0.0, -1.0, false, false, false, player.presentation_snapshot())
		check.call(bridge.selected_state == action and is_equal_approx(bridge.sampled_time, 0.5), "Authored %s follows its actual strike clock instead of falling back to idle" % String(action))
	player.strike = null
	player.presentation_heal_remaining = 0.2
	player.invulnerability = 0.0
	player.receive_hit(1.0, 0.0, player.global_position + Vector3.FORWARD)
	check.call(player.presentation_heal_remaining == 0.0 and player.stagger > 0.0, "A real hit cancels the heal gesture through the existing interruption path")
	player.dead = true
	player.presentation_death_elapsed = 0.5
	player.visual.pose(0.0, 0.0, -1.0, false, false, true, player.presentation_snapshot())
	check.call(bridge.selected_state == &"death" and bridge.visible and not player.visual.model.visible, "A full profile uses an authored death pose rather than silently selecting idle")
	var epoch_before := player.presentation_epoch
	player.restore(actor_transform.origin)
	player.visual.pose(0.0, 0.0, -1.0, false, false, false, player.presentation_snapshot())
	snapshot = player.presentation_snapshot()
	check.call(player.presentation_epoch == epoch_before + 1 and snapshot.heal_remaining == 0.0 and snapshot.charge_elapsed == 0.0 and snapshot.dodge_remaining == 0.0, "Restore clears visual action sources and advances the presentation epoch")
	check.call(bridge.selected_state == &"idle" and is_zero_approx(bridge.locomotion_clock) and is_zero_approx(bridge.sampled_time) and (bridge.rig.basis * Vector3.BACK).dot(Vector3.FORWARD) > 0.999, "A restored epoch clears stale locomotion phase, death pose and directional rig yaw")
	var enemy := RuneEnemy.new()
	enemy.facing = Vector3.RIGHT
	enemy.velocity = Vector3.BACK * 3.6
	var enemy_snapshot := enemy.presentation_snapshot()
	check.call(is_equal_approx(enemy_snapshot.move_local_x, 1.0) and is_equal_approx(enemy_snapshot.locomotion_reference_speed, 3.6) and enemy.velocity == Vector3.BACK * 3.6, "Enemy snapshots expose facing-relative motion and the native walk reference without changing velocity")
	enemy.free()
	player.free()
	return true
