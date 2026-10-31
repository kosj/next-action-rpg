extends SceneTree

const OUTPUT := "res://godot-audit-result.json"
const EXPECTED_SHA256 := "35091c9898d5860f5b2d3ca5528055dd44dcf7a23576254d4339d3d54797b1d6"
var report: Dictionary = {"engine": Engine.get_version_info(), "status":"running", "errors":[], "scope":"Actual GLB import, CPU-skinned REST/world bounds, Skin binding presence, clips and manual AnimationTree bone sampling only", "limitations":["No visual quality, full deformation, loop-seam, foot contact, BoneMap, dynamic root-motion or hardware performance approval", "REST CPU skin uses Skeleton global rest x Skin inverse bind x weighted vertex, then skeleton world transform; no rendered GPU deformation audit", "The eight added stock candidates are not authored gameplay clips; raw source fidelity, timing and combat-quality approval remain pending"]}

func _initialize() -> void:
	var digest := FileAccess.get_sha256("res://candidate.glb")
	report["input_sha256"] = digest
	require(digest == EXPECTED_SHA256,"Input SHA-256 differs from this audit fixture")
	call_deferred("audit" if report.errors.is_empty() else "finish")

func require(value: bool, reason: String) -> void:
	if not value:
		report.errors.append(reason)

func collect(node: Node, class_string: String) -> Array[Node]:
	var found: Array[Node] = []
	if node.is_class(class_string):
		found.append(node)
	for child in node.get_children():
		found.append_array(collect(child, class_string))
	return found

func pose(skeleton: Skeleton3D) -> Array[Transform3D]:
	var result: Array[Transform3D] = []
	for index in skeleton.get_bone_count():
		result.append(skeleton.get_bone_pose(index))
	return result

func pose_change(first: Array[Transform3D], second: Array[Transform3D]) -> Dictionary:
	var changed := 0
	var max_position := 0.0
	var max_rotation := 0.0
	for index in first.size():
		var distance := first[index].origin.distance_to(second[index].origin)
		var angle := first[index].basis.get_rotation_quaternion().angle_to(second[index].basis.get_rotation_quaternion())
		if distance > 0.000001 or angle > 0.000001:
			changed += 1
		max_position = maxf(max_position, distance)
		max_rotation = maxf(max_rotation, angle)
	return {"changed_bones":changed,"max_bone_local_position_change_m":max_position,"max_bone_rotation_change_rad":max_rotation}

func audit() -> void:
	var packed := load("res://candidate.glb") as PackedScene
	require(packed != null, "GLB failed to load as PackedScene")
	if packed == null:
		finish()
		return
	var instance := packed.instantiate() as Node3D
	root.add_child(instance)
	await process_frame
	var skeletons := collect(instance,"Skeleton3D")
	var meshes := collect(instance,"MeshInstance3D")
	var players := collect(instance,"AnimationPlayer")
	require(skeletons.size() == 1,"Expected one Skeleton3D")
	require(players.size() == 1,"Expected one AnimationPlayer")
	require(meshes.size() == 1,"Expected one body MeshInstance3D")
	if skeletons.size() != 1 or players.size() != 1:
		instance.queue_free()
		finish()
		return
	var skeleton := skeletons[0] as Skeleton3D
	var player := players[0] as AnimationPlayer
	player.stop()
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	skeleton.reset_bone_poses()
	report["skeleton"] = {"path":String(instance.get_path_to(skeleton)),"bones":skeleton.get_bone_count(),"motion_scale":skeleton.motion_scale}
	require(skeleton.get_bone_count() == 53,"Expected 53 actual bones")
	var lower := Vector3(INF,INF,INF)
	var upper := Vector3(-INF,-INF,-INF)
	var mesh_reports: Array = []
	for item in meshes:
		var mesh := item as MeshInstance3D
		var count := 0
		for surface in mesh.mesh.get_surface_count():
			var arrays := mesh.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var bone_ids: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
			var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
			var influences: int = weights.size() / vertices.size()
			for index in vertices.size():
				var point := Vector3.ZERO
				for influence in influences:
					var offset := index*influences+influence
					var bind: int = bone_ids[offset]
					var bone: int = mesh.skin.get_bind_bone(bind)
					if bone < 0:
						bone = skeleton.find_bone(mesh.skin.get_bind_name(bind))
					point += (skeleton.get_bone_global_rest(bone)*mesh.skin.get_bind_pose(bind)*vertices[index])*weights[offset]
				point = skeleton.global_transform * point
				lower = lower.min(point)
				upper = upper.max(point)
			count += vertices.size()
		var valid_skin := mesh.skin != null and mesh.skin.get_bind_count() > 0 and mesh.get_node_or_null(mesh.skeleton) == skeleton
		require(valid_skin,"Mesh Skin bindings/Skeleton path did not resolve")
		require(mesh.skin != null and mesh.skin.get_bind_count() == 53,"Expected 53 Skin binds")
		mesh_reports.append({"path":String(instance.get_path_to(mesh)),"surface_vertices":count,"skin_present":mesh.skin != null,"skin_bind_count":mesh.skin.get_bind_count() if mesh.skin else 0,"skeleton_path_resolves":mesh.get_node_or_null(mesh.skeleton) == skeleton})
	report["meshes"] = mesh_reports
	report["rest_bounds_godot_y_up"] = {"min":[lower.x,lower.y,lower.z],"max":[upper.x,upper.y,upper.z],"height_m":upper.y-lower.y,"floor_y_m":lower.y,"method":"CPU linear skinning: skeleton_world * sum(weight * bone_global_rest * inverse_bind * vertex)"}
	require(absf(upper.y-lower.y-1.82) < 0.0001,"REST height does not equal 1.82m")
	require(absf(lower.y) < 0.0001,"REST floor is not Y=0")
	var names := player.get_animation_list()
	report["clips"] = {}
	for name in names:
		var animation := player.get_animation(name)
		report.clips[String(name)] = {"duration_seconds":animation.length,"tracks":animation.get_track_count(),"loop_mode":animation.loop_mode,"loop_mode_name":"NONE" if animation.loop_mode == Animation.LOOP_NONE else ("LINEAR" if animation.loop_mode == Animation.LOOP_LINEAR else "PINGPONG")}
	var expected_clips: Array[StringName] = [&"candidate_combo_slash", &"candidate_cross_block", &"candidate_double_slash", &"candidate_hit_fall", &"candidate_left_sidestep", &"candidate_light_hit_back", &"candidate_right_sidestep", &"candidate_sword_slash", &"idle", &"RESET", &"run", &"walk"]
	require(names.size() == expected_clips.size(),"Expected exactly twelve imported clips")
	for name in expected_clips:
		require(player.has_animation(name),"Missing actual imported clip: " + String(name))
	var tree := AnimationTree.new()
	instance.add_child(tree)
	tree.anim_player = tree.get_path_to(player)
	tree.root_node = tree.get_path_to(player.get_node(player.root_node))
	tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	var blend := AnimationNodeBlendTree.new()
	var clip := AnimationNodeAnimation.new()
	clip.animation = &"idle"
	var clock := AnimationNodeTimeSeek.new()
	blend.add_node(&"Clip",clip)
	blend.add_node(&"Clock",clock)
	blend.connect_node(&"Clock",0,&"Clip")
	blend.connect_node(&"output",0,&"Clock")
	tree.tree_root = blend
	tree.active = true
	report["manual_animation_tree_samples"] = {}
	for name in expected_clips:
		if name == &"RESET" or not player.has_animation(name):
			continue
		skeleton.reset_bone_poses()
		clip.animation = name
		tree.set("parameters/Clock/seek_request",0.0)
		tree.advance(0.0)
		var first := pose(skeleton)
		var sample_reports: Array = []
		for fraction in [0.25,0.5]:
			var sample_time: float = player.get_animation(name).length*float(fraction)
			tree.set("parameters/Clock/seek_request",sample_time)
			tree.advance(0.0)
			var current := pose(skeleton)
			var detail := pose_change(first,current)
			detail["sample_fraction"] = fraction
			detail["sample_time_seconds"] = sample_time
			sample_reports.append(detail)
		report.manual_animation_tree_samples[String(name)] = {"baseline_time_seconds":0.0,"samples":sample_reports,"tree_active":tree.active,"motion_change_required":false}
	tree.active = false
	instance.queue_free()
	await process_frame
	finish()

func finish() -> void:
	report.status = "passed" if report.errors.is_empty() else "failed"
	var file := FileAccess.open(OUTPUT,FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  ") + "\n")
	file.close()
	print("RUNEFALL_MOTION_LIBRARY_IMPORT_" + String(report.status).to_upper() + ": " + OUTPUT)
	quit(0 if report.errors.is_empty() else 1)
