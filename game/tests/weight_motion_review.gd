extends Node3D

## Offline deterministic presentation fixture. No RunePlayer/RuneEnemy, input,
## damage, collision motor, gameplay QA setter or interactive acceptance.
const FPS := 60
const STEP := 1.0 / FPS
var _config: Dictionary = {}
var _panels: Array[Dictionary] = []
var _frames: Array[Dictionary] = []
var _frame := 0
var _limit := 0
var _finishing := false
var _time_label: Label
var _audio: Node

func _is_arm_strip() -> bool:
	return String(_config.get("mode", "forward_1x")) == "arm_strip"

func _ready() -> void:
	set_process(false)
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		_fail("Expected one absolute JSON configuration path after --")
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not parsed is Dictionary:
		_fail("Review configuration is not an object")
		return
	_config = parsed
	_limit = int(_config.frames)
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	get_window().size = Vector2i(1280, 720)
	_audio = get_tree().root.get_node("Audio")
	_audio.stop_all()
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var background := ColorRect.new()
	background.color = Color("171e23")
	background.size = Vector2(1280, 720)
	canvas.add_child(background)
	for index in range(2):
		var variant := "before" if index == 0 else "after"
		var panel := _make_panel(canvas, index, variant, String(_config[variant]))
		if panel.is_empty():
			return
		_panels.append(panel)
	_time_label = _label(canvas, Vector2(18, 687), Vector2(1244, 30), 16)
	_time_label.text = "OFFLINE MOTION / logical 1x / 60 fps / no interactive combat or performance approval"
	set_process(true)

func _label(parent: Node, point: Vector2, dimensions: Vector2, font_size: int) -> Label:
	var label := Label.new()
	label.position = point
	label.size = dimensions
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", Color("edf1f3"))
	parent.add_child(label)
	return label

func _prepared_scene(path: String) -> PackedScene:
	# The same isolated loop-flag copy policy as ProductionCharacterArt.prepare.
	# No animation keys, skeleton transforms, mesh or source resource are edited.
	var source := load(path) as PackedScene
	if source == null:
		_fail("Review input is not imported as PackedScene: " + path)
		return null
	var instance := source.instantiate() as Node3D
	var player := ProductionCharacterArt.find_type(instance, "AnimationPlayer") as AnimationPlayer
	if player == null:
		instance.free()
		_fail("Review input lacks its actual AnimationPlayer: " + path)
		return null
	var definition := ProductionCharacterArt.definition(String(_config.profile))
	var states: Array[StringName] = definition.states.duplicate()
	states.append(&"RESET")
	var library := AnimationLibrary.new()
	for state: StringName in states:
		if not player.has_animation(state):
			instance.free()
			_fail("Missing actual input clip: " + String(state))
			return null
		var animation := player.get_animation(state).duplicate(true) as Animation
		animation.loop_mode = Animation.LOOP_LINEAR if state in ProductionCharacterArt.CYCLES else Animation.LOOP_NONE
		library.add_animation(state, animation)
	for library_name in player.get_animation_library_list():
		player.remove_animation_library(library_name)
	player.add_animation_library(&"", library)
	player.autoplay = ""
	var packed := PackedScene.new()
	var status := packed.pack(instance)
	instance.free()
	if status != OK:
		_fail("Could not pack isolated loop-policy copy")
		return null
	return packed

func _make_panel(canvas: CanvasLayer, index: int, variant: String, path: String) -> Dictionary:
	var viewport := SubViewport.new()
	viewport.name = variant.capitalize() + "World"
	viewport.size = Vector2i(640, 620)
	viewport.own_world_3d = true
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.msaa_3d = Viewport.MSAA_2X
	add_child(viewport)
	var image := TextureRect.new()
	image.texture = viewport.get_texture()
	image.position = Vector2(index*640, 64)
	image.size = Vector2(640, 620)
	canvas.add_child(image)
	var title := _label(canvas, Vector2(index*640+18, 10), Vector2(604, 48), 20)
	title.text = "BEFORE / v0.1.8 impact" if variant == "before" else "AFTER / weight-recovery candidate"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("707d86")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("dce5ec")
	environment.ambient_light_energy = 0.55
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	viewport.add_child(world_environment)
	var floor_mesh := PlaneMesh.new()
	floor_mesh.size = Vector2(12, 12)
	var floor_material := StandardMaterial3D.new()
	floor_material.albedo_color = Color("777c80")
	floor_material.metallic = 0.0
	floor_material.roughness = 0.85
	floor_mesh.material = floor_material
	var floor_instance := MeshInstance3D.new()
	floor_instance.mesh = floor_mesh
	viewport.add_child(floor_instance)
	# Thin floor reference bars make planted-foot drift visible without editing
	# the rendered character or using a tracked/recentering camera.
	for z in [-0.60, 0.0, 0.60]:
		var bar := MeshInstance3D.new()
		var bar_mesh := BoxMesh.new()
		bar_mesh.size = Vector3(2.8, 0.002, 0.012)
		var bar_material := StandardMaterial3D.new()
		bar_material.albedo_color = Color("50585c")
		bar_material.roughness = 0.9
		bar_mesh.material = bar_material
		bar.mesh = bar_mesh
		bar.position = Vector3(0, 0.001, z)
		viewport.add_child(bar)
	var key := DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-48, -35, 0)
	key.light_color = Color("fff4e6")
	key.light_energy = 1.25
	key.shadow_enabled = true
	viewport.add_child(key)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, 145, 0)
	fill.light_color = Color("dce9f5")
	fill.light_energy = 0.45
	viewport.add_child(fill)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 1.25 if _is_arm_strip() else 3.65
	var camera_target := Vector3(0, 1.30, -0.60) if _is_arm_strip() else Vector3(0, 1.05, -0.22)
	# Zoom/recenter only; the arm strip retains the full-body viewing angle.
	camera.position = camera_target+Vector3(3.5, 1.40, -5.78)
	viewport.add_child(camera)
	camera.look_at(camera_target)
	camera.current = true
	var actor := CharacterBody3D.new()
	actor.name = variant.capitalize() + "VisualOwnerOnly"
	viewport.add_child(actor)
	# Same player capsule-bottom alignment read by ActorVisual; this owner has
	# no controller script and never calls move_and_slide or applies damage.
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.height = 1.85 if _config.profile == "hero" else 1.95
	capsule.radius = 0.36 if _config.profile == "hero" else 0.4
	shape.shape = capsule
	shape.position.y = 0.95 if _config.profile == "hero" else 0.975
	actor.add_child(shape)
	var visual := ActorVisual.new()
	actor.add_child(visual)
	var scene := _prepared_scene(path)
	if scene == null:
		return {}
	var definition := ProductionCharacterArt.definition(String(_config.profile))
	var result := visual.mount_rig(scene, {}, definition.states)
	if not result.ok:
		_fail("Actual bridge rejected " + variant + ": " + String(result.reason))
		return {}
	var transitions := visual.skeletal_bridge.enable_transition_polish()
	if not transitions.ok:
		_fail("Actual transition guard rejected " + variant + ": " + String(transitions.reason))
		return {}
	visual.production_profile = String(_config.profile)
	visual.ground_offset_y = visual._capsule_floor_offset()
	var skeleton := visual.skeletal_bridge.get_skeleton()
	if definition.has("eye_path"):
		if not visual._mount_eyes(skeleton, load(definition.eye_path) as PackedScene):
			_fail("Actual Head eye socket rejected input")
			return {}
	# Same physical RightHand attachment and rig-scale cancellation as the
	# production wrapper, using its real grip reader and actual sword markers.
	var grip := visual._read_grip(String(_config.profile))
	if not grip.ok:
		_fail(String(grip.reason))
		return {}
	visual.weapon_socket = BoneAttachment3D.new()
	visual.weapon_socket.bone_name = &"RightHand"
	skeleton.add_child(visual.weapon_socket)
	visual.weapon_socket.on_skeleton_update()
	visual.weapon_grip = Node3D.new()
	visual.weapon_socket.add_child(visual.weapon_grip)
	var inherited := (visual.skeletal_bridge.global_transform.affine_inverse()*visual.weapon_socket.global_transform).basis.get_scale()
	if inherited.x <= 0.0 or absf(inherited.x-inherited.y)>0.0001 or absf(inherited.x-inherited.z)>0.0001:
		_fail("Actual weapon socket has nonuniform/negative rig scale")
		return {}
	visual.weapon_grip.transform = Transform3D(grip.basis.scaled(Vector3.ONE/inherited.x), grip.offset/inherited.x)
	visual.rig_weapon = ActorVisual.RUNE_SWORD_SCENE.instantiate() as Node3D
	visual.weapon_grip.add_child(visual.rig_weapon)
	visual.pose(0.0, 0.0, -1.0, false, false, false, {"speed":0.0})
	return {"variant":variant, "path":path, "actor":actor, "visual":visual, "camera":camera,
		"grip":visual.rig_weapon.find_child("GripOrigin", true, false),
		"tip":visual.rig_weapon.find_child("BladeTip", true, false), "skeleton":skeleton}

func _snapshot(time: float) -> Dictionary:
	var result := {"speed":0.0, "presentation_epoch":1}
	if _config.profile == "hero":
		if time >= 0.30 and time < 1.0:
			result.merge({"charge_active":true, "charge_elapsed":time-0.30, "charge_duration":0.65})
		elif time >= 1.0 and time < 2.06:
			result.merge({"attack_id":"charged_heavy", "attack_instance_id":1, "attack_elapsed":time-1.0,
				"attack_duration":1.06, "attack_startup":0.34, "attack_active":0.18})
	else:
		if time >= 0.30 and time < 0.78:
			result.merge({"stagger":0.78-time, "hit_reaction":"heavy_hit", "hit_elapsed":time-0.30, "hit_duration":0.48})
	return result

func _vector(value: Vector3) -> Array:
	return [value.x, value.y, value.z]

func _bone_position(panel: Dictionary, name: String) -> Array:
	var skeleton: Skeleton3D = panel.skeleton
	var index := skeleton.find_bone(name)
	return _vector((skeleton.global_transform*skeleton.get_bone_global_pose(index)).origin)

func _process(delta: float) -> void:
	if _finishing:
		return
	if absf(delta-STEP) > 0.00001:
		_fail("Movie capture must use --fixed-fps 60; actual delta=" + str(delta))
		return
	if _frame >= _limit:
		_finish()
		return
	var time := 1.0+float(_config.review_times_s[_frame]) if _is_arm_strip() else float(_frame)/FPS
	var snapshot := _snapshot(time)
	var row := {"frame":_frame, "logical_time_s":time, "received_delta_s":delta, "panels":[]}
	for panel in _panels:
		var actor: CharacterBody3D = panel.actor
		var visual: ActorVisual = panel.visual
		var travel := 3.2*clampf(time-1.34,0.0,0.18) if _config.profile == "hero" else -0.35*clampf((time-0.30)/0.24,0.0,1.0)
		actor.position = Vector3(0,-visual.ground_offset_y,-travel)
		visual.pose(0.0 if _is_arm_strip() else STEP, 0.0, -1.0, false, false, false, snapshot)
		if not visual.skeletal_bridge.last_error.is_empty() or not visual.skeletal_bridge.visible:
			_fail("Actual bridge failed during forward playback: " + visual.skeletal_bridge.last_error)
			return
		row.panels.append({"variant":panel.variant, "state":String(visual.skeletal_bridge.selected_state),
			"clip":String(visual.skeletal_bridge.selected_clip), "sampled_time_s":visual.skeletal_bridge.sampled_time,
			"fixture_actor_translation_m":_vector(actor.position), "grip_m":_vector(panel.grip.global_position),
			"tip_m":_vector(panel.tip.global_position), "left_foot_m":_bone_position(panel,"LeftFoot"),
			"right_foot_m":_bone_position(panel,"RightFoot"), "transition":visual.skeletal_bridge.transition_report()})
	_frames.append(row)
	if _is_arm_strip():
		_time_label.text = "STATIC SUBFRAME AUDIT / charged t=%.4fs / zero-delta actual bridge seek / effects off / NOT 1x MOTION" % (time-1.0)
	else:
		_time_label.text = "%s / t=%.3fs / %s / logical 1x, 60fps / OFFLINE PRESENTATION, NO GAMEPLAY OR GPU APPROVAL" % [String(_config.profile), time, String(row.panels[0].state)]
	_frame += 1

func _finish() -> void:
	_finishing = true
	set_process(false)
	var cameras: Array = []
	for panel in _panels:
		var camera: Camera3D = panel.camera
		cameras.append({"variant":panel.variant, "position_m":_vector(camera.position), "basis_columns":[_vector(camera.basis.x),_vector(camera.basis.y),_vector(camera.basis.z)], "orthographic_size":camera.size})
	var report := {"scope":"Actual imported GLBs through ActorVisual.pose and SkeletalVisualBridge. Neutral offline matched-camera comparison only, not interactive combat, contact/collision acceptance, audio listening, target GPU performance or AAA approval.",
		"sampling_mode":"Five explicit zero-delta subframe poses, not 1x motion" if _is_arm_strip() else "Forward fixed60Hz MovieMaker, logical1x",
		"inputs":_config, "fps":FPS, "logical_speed":null if _is_arm_strip() else 1.0, "engine_time_scale":Engine.time_scale,
		"frames":_frames, "camera":cameras, "engine_version":Engine.get_version_info(),
		"renderer":RenderingServer.get_video_adapter_name(), "backend":RenderingServer.get_current_rendering_method(),
		"fixture_motion":"Prescribed open-space actor travel: charged lunge0.576m during active0.34..0.52; sentinel0.35m recoil in0.24s. No physics resolution or gameplay motor. No contact/VFX/audio is generated.",
		"preparation":"Source clips are duplicated only to apply ProductionCharacterArt cycle flags; actual mesh/rest/skin/key data remains loaded from each original PackedScene. Real bridge complete-channel guard, transition polish, actual physical sword and Head eyes are used.",
		"pose_clock":"Explicit zero-delta seek at each listed subframe, static audit only" if _is_arm_strip() else "Strictly forward60Hz, no seek during playback"}
	var file := FileAccess.open(String(_config.snapshot),FileAccess.WRITE)
	if file == null:
		_fail("Cannot write frame snapshot")
		return
	file.store_string(JSON.stringify(report,"\t")+"\n")
	file.close()
	_audio.stop_all()
	var drained: bool = await _audio.wait_until_stopped()
	print("RUNEFALL_WEIGHT_MOTION_REVIEW ",JSON.stringify({"frames":_frame,"fps":FPS,"audio_drained":drained,"snapshot":_config.snapshot}))
	get_tree().quit(0 if drained else 1)

func _fail(message: String) -> void:
	_finishing = true
	set_process(false)
	push_error("Offline weight review: " + message)
	get_tree().quit(1)
