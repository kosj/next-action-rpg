extends Node
# PRIVATE ART FIXTURE ONLY. Not normal gameplay, timing QA or AAA approval.
var world: Node3D
var shot_index := 0
var quality := 0
var eye_center := Vector3.ZERO
var cases := [
	{"name":"wide-front-neutral", "camera":"wide", "yaw":0.0, "pitch":0.0},
	{"name":"face-front-neutral", "camera":"front", "yaw":0.0, "pitch":0.0},
	{"name":"face-threequarter-neutral", "camera":"threequarter", "yaw":0.0, "pitch":0.0},
	{"name":"face-front-yaw15-pitch10", "camera":"front", "yaw":15.0, "pitch":10.0},
	{"name":"face-front-yawminus15-pitchminus10", "camera":"front", "yaw":-15.0, "pitch":-10.0},
	{"name":"face-threequarter-yawminus15-pitch10", "camera":"threequarter", "yaw":-15.0, "pitch":10.0},
]

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("configure")

func _v(value: Vector3) -> Array:
	return [value.x,value.y,value.z]

func _t(value: Transform3D) -> Array:
	return _v(value.origin) + _v(value.basis.x) + _v(value.basis.y) + _v(value.basis.z)

func _meshes(node: Node3D) -> Array[MeshInstance3D]:
	var meshes: Array[MeshInstance3D] = []
	if node is MeshInstance3D:
		meshes.append(node)
	for child in node.find_children("*", "MeshInstance3D", true, false):
		meshes.append(child as MeshInstance3D)
	return meshes

func _mesh_bounds(node: Node3D) -> AABB:
	var bounds := AABB()
	var initialized := false
	for spatial in _meshes(node):
		var local := spatial.get_aabb()
		for corner in range(8):
			var point: Vector3 = spatial.global_transform * local.get_endpoint(corner)
			if not initialized:
				bounds = AABB(point, Vector3.ZERO)
				initialized = true
			else:
				bounds = bounds.expand(point)
	return bounds

func configure() -> void:
	world = get_parent()
	world.player.position = Vector3(0, -0.02, -25)
	world.player.active = false
	world.player.set_physics_process(false)
	world.rig.cinematic = false
	world.rig.yaw = PI
	world.rig.pitch = -0.18
	world.rig.shake_strength = 0
	Session.shake = false
	world.ui.hide()
	await get_tree().physics_frame
	await get_tree().physics_frame
	world.rig.snap()
	world.rig._physics_process(1.0)
	world.rig.set_physics_process(false)
	get_tree().paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	pose_head(0.0, 0.0)
	eye_center = _mesh_bounds(world.player.visual.eye_model).get_center()
	apply_case("ready")

func pose_head(yaw: float, pitch: float) -> void:
	var visual: ActorVisual = world.player.visual
	# Reset and sample the actual idle presentation deterministically, then
	# rotate only the actual Head bone for this explicitly labelled art fixture.
	visual.skeletal_bridge.reset_presentation(77001)
	visual.pose(0.25, 0, -1.0, false, false, false, {"speed":0.0,"presentation_epoch":77001})
	var skeleton := ProductionCharacterArt.find_type(visual.skeletal_bridge.rig, "Skeleton3D") as Skeleton3D
	var head := skeleton.find_bone("Head")
	var base_rotation := skeleton.get_bone_pose_rotation(head)
	skeleton.set_bone_pose_rotation(head, base_rotation * Quaternion.from_euler(Vector3(deg_to_rad(pitch), deg_to_rad(yaw), 0)))
	skeleton.force_update_all_bone_transforms()
	# Read updated pose and invoke the exact attachment method the runtime uses.
	skeleton.get_bone_global_pose(head)
	visual.eye_socket.on_skeleton_update()
	visual.weapon_socket.on_skeleton_update()

func apply_case(stage: String) -> void:
	var entry: Dictionary = cases[shot_index]
	pose_head(float(entry.yaw), float(entry.pitch))
	Session.quality = quality
	world.apply_quality()
	if entry.camera == "wide":
		world.rig.yaw = PI
		world.rig.snap()
		world.rig._physics_process(1.0)
	else:
		var offset := Vector3(0, 0, -0.34) if entry.camera == "front" else Vector3(0.26, 0.01, -0.29)
		world.rig.camera.global_position = eye_center + offset
		world.rig.camera.look_at(eye_center + Vector3(0,-0.025,0))
	report(stage)

func report(stage: String) -> void:
	var visual: ActorVisual = world.player.visual
	var skeleton := ProductionCharacterArt.find_type(visual.skeletal_bridge.rig, "Skeleton3D") as Skeleton3D
	var head := skeleton.find_bone("Head")
	var expected := skeleton.global_transform * skeleton.get_bone_global_pose(head)
	var expected_values := _t(expected)
	var socket_values := _t(visual.eye_socket.global_transform)
	var max_error := 0.0
	for index in range(expected_values.size()):
		max_error = maxf(max_error, absf(expected_values[index]-socket_values[index]))
	var materials := []
	for mesh in _meshes(visual.eye_model):
		for index in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(index) as StandardMaterial3D
			materials.append({"node":String(mesh.name), "surface":index,
				"name":material.resource_name, "vertex_colors_as_albedo":material.vertex_color_use_as_albedo,
				"albedo":material.albedo_color.to_html(), "roughness":material.roughness,
				"cull_mode":material.cull_mode, "shading_mode":material.shading_mode})
	var bounds := _mesh_bounds(visual.eye_model)
	var snapshot := {"scope":"Fixed paused art fixture; Head local pose rotations, no gameplay/timing QA or AAA proof",
		"stage":stage, "case_index":shot_index, "case":cases[shot_index], "quality":quality,
		"camera_transform":_t(world.rig.camera.global_transform), "camera_fov":world.rig.camera.fov,
		"hero_transform":_t(world.player.global_transform), "actual_idle_sampled_time":visual.skeletal_bridge.sampled_time,
		"head_world_transform":expected_values, "eye_socket_world_transform":socket_values,
		"head_socket_max_component_error":max_error, "eye_model_world_transform":_t(visual.eye_model.global_transform),
		"eye_world_aabb_position":_v(bounds.position), "eye_world_aabb_size":_v(bounds.size),
		"eye_materials":materials, "hero_art":visual.presentation_report()}
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.__RUNEFALL_EYE_ART = " + JSON.stringify(snapshot), true)
	print("RUNEFALL_EYE_ART " + JSON.stringify(snapshot))

func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo or world == null:
		return
	match event.physical_keycode:
		KEY_Q:
			quality = 1-quality
		KEY_N:
			shot_index = (shot_index+1) % cases.size()
		_:
			return
	apply_case("changed")
