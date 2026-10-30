extends RefCounted

static func _scene(missing_clip: StringName = &"", with_skin: bool = true, broken_track: bool = false, with_death: bool = false, zero_weights: bool = false, forbidden_track: String = "") -> PackedScene:
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
	return true
