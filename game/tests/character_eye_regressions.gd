extends RefCounted

# Attachment/units/material checks against frozen source geometry. These are
# not eyelid collision, visual acceptance, gaze/blink or AAA quality checks.
const FIT_PATH := "res://tests/fixtures/lyra_eye_fit.json"

static func _v(value: Array) -> Vector3:
	return Vector3(value[0], value[1], value[2])

static func _matrix(rows: Array) -> Transform3D:
	return Transform3D(Basis(Vector3(rows[0][0], rows[1][0], rows[2][0]), Vector3(rows[0][1], rows[1][1], rows[2][1]), Vector3(rows[0][2], rows[1][2], rows[2][2])), Vector3(rows[0][3], rows[1][3], rows[2][3]))

static func _meshes(node: Node) -> Array[MeshInstance3D]:
	var result: Array[MeshInstance3D] = []
	if node is MeshInstance3D:
		result.append(node)
	for child in node.get_children():
		result.append_array(_meshes(child))
	return result

static func _pose(visual: ActorVisual, snapshot: Dictionary, delta: float = 0.0) -> void:
	visual.pose(delta, float(snapshot.get("speed", 0.0)), -1.0, false, false, false, snapshot)

static func _head(visual: ActorVisual) -> Transform3D:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	return skeleton.global_transform * skeleton.get_bone_global_pose(skeleton.find_bone("Head"))

static func _rest(visual: ActorVisual) -> void:
	# The actual Skeleton REST is the oracle, not the RESET animation's first
	# pose. Actual-state tests below never update the socket on runtime's behalf.
	visual.skeletal_bridge.reset_presentation()
	visual.skeletal_bridge.get_skeleton().reset_bone_poses()
	visual.eye_socket.on_skeleton_update()

static func _material_report(eyes: Node3D, fixture: Dictionary) -> Dictionary:
	var valid := true
	var materials: Dictionary = {}
	var triangles := 0
	var points: Array[Vector3] = []
	var colored_points: Array[Dictionary] = []
	var expected: Dictionary = {}
	for material in fixture.materials:
		expected[material.name] = material
	var meshes := _meshes(eyes)
	for mesh in meshes:
		valid = valid and mesh.skin == null and mesh.mesh != null and mesh.material_override == null
		if mesh.mesh == null:
			continue
		var into_eye := eyes.global_transform.affine_inverse() * mesh.global_transform
		for surface in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(surface) as BaseMaterial3D
			valid = valid and material != null and mesh.get_surface_override_material(surface) == null
			if material == null:
				continue
			materials[material.resource_name] = true
			valid = valid and expected.has(material.resource_name)
			valid = valid and material.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED and material.shading_mode == BaseMaterial3D.SHADING_MODE_PER_PIXEL
			valid = valid and material.vertex_color_use_as_albedo and material.albedo_texture == null and material.normal_texture == null
			var color := material.albedo_color
			valid = valid and is_finite(color.r) and is_finite(color.g) and is_finite(color.b) and is_equal_approx(color.a, 1.0)
			valid = valid and is_finite(material.metallic) and is_finite(material.roughness) and is_finite(material.clearcoat) and is_finite(material.clearcoat_roughness)
			if expected.has(material.resource_name):
				valid = valid and absf(material.metallic-float(expected[material.resource_name].metallic)) < 0.00001 and absf(material.roughness-float(expected[material.resource_name].roughness)) < 0.00001
			var arrays := mesh.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var colors: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			valid = valid and not vertices.is_empty() and normals.size() == vertices.size() and colors.size() == vertices.size()
			triangles += (indices.size() if not indices.is_empty() else vertices.size()) / 3
			for index in range(vertices.size()):
				points.append(into_eye * vertices[index])
				valid = valid and vertices[index].is_finite()
				if index < normals.size():
					valid = valid and normals[index].is_finite() and absf(normals[index].length()-1.0) < 0.002
				if index < colors.size():
					var vertex_color := colors[index]
					valid = valid and is_finite(vertex_color.r) and is_finite(vertex_color.g) and is_finite(vertex_color.b) and is_equal_approx(vertex_color.a, 1.0)
					colored_points.append({"position":into_eye*vertices[index],"color":vertex_color})
	valid = valid and meshes.size() == 1 and materials.size() == 3 and triangles == int(fixture.expected_triangles)
	return {"ok":valid, "materials":materials.keys(), "triangles":triangles, "points":points, "colored_points":colored_points}

static func _source_colors_preserved(points: Array[Dictionary], fixture: Dictionary) -> bool:
	for sample in fixture.samples:
		var position := _v(sample.head_rigid_local_m)
		var source: Array = sample.source_linear_rgba
		var found := false
		for point in points:
			if point.position.distance_to(position) > float(fixture.import_vertex_tolerance_m):
				continue
			var color: Color = point.color
			# Actual imported vertex colors use byte channels. Allow one channel
			# step, rather than treating replacement by white as equivalent.
			if maxf(maxf(absf(color.r-source[0]),absf(color.g-source[1])),maxf(absf(color.b-source[2]),absf(color.a-source[3]))) <= float(fixture.import_vertex_color_channel_tolerance):
				found = true
				break
		if not found:
			return false
	return true

static func _body_materials_valid(visual: ActorVisual, fixture: Dictionary) -> bool:
	var contract: Dictionary = fixture.body_material_contract
	var bodies := 0
	for mesh in _meshes(visual.skeletal_bridge.rig):
		if mesh.skin == null:
			continue
		bodies += 1
		if mesh.mesh == null or mesh.skin.get_bind_count() != int(contract.skin_bind_count) or mesh.mesh.get_surface_count() != int(contract.surfaces) or mesh.material_override != null:
			return false
		for surface in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(surface) as BaseMaterial3D
			if material == null or mesh.get_surface_override_material(surface) != null:
				return false
			if surface == int(contract.textured_surface.index):
				if material.resource_name != contract.textured_surface.name or material.albedo_texture == null or material.normal_texture == null:
					return false
			elif surface == int(contract.new_inner_wall.index):
				var lid: Dictionary = contract.new_inner_wall
				var arrays := mesh.mesh.surface_get_arrays(surface)
				var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
				if material.resource_name != lid.name or material.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED or material.albedo_color.a != 1.0 or material.metallic != 0.0 or absf(material.roughness-float(lid.roughness)) > 0.00001 or material.albedo_texture != null or material.normal_texture != null or indices.size() != int(lid.triangles)*3:
					return false
			else:
				return false
	return bodies == int(contract.body_meshes)

static func _bindings(points: Array[Vector3], fixture: Dictionary) -> Dictionary:
	var bound: Dictionary = {}
	var maximum := 0.0
	for sample in fixture.samples:
		var expected := _v(sample.head_rigid_local_m)
		var distance := INF
		var nearest := Vector3.ZERO
		for point in points:
			if point.distance_to(expected) < distance:
				distance = point.distance_to(expected)
				nearest = point
		maximum = maxf(maximum, distance)
		bound[sample.name] = nearest
	return {"positions":bound, "maximum_error_m":maximum}

static func _world_points(visual: ActorVisual, bindings: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	for name in bindings:
		result[name] = visual.eye_model.global_transform * bindings[name]
	return result

static func _rest_error(visual: ActorVisual, bindings: Dictionary, fixture: Dictionary) -> float:
	var maximum := 0.0
	var actual := _world_points(visual, bindings)
	# Independent original-source anchor, not the current Head/socket matrix.
	var source_to_world := visual.global_transform * Transform3D(Basis(Vector3.UP, PI), Vector3.ZERO)
	for sample in fixture.samples:
		var expected := source_to_world * _v(sample.source_world_y_up_m)
		maximum = maxf(maximum, expected.distance_to(actual[sample.name]))
	return maximum

static func _head_error(visual: ActorVisual, bindings: Dictionary) -> float:
	var head := _head(visual)
	var actor_scale := visual.global_basis.get_scale().x
	var physical := Transform3D(head.basis.orthonormalized().scaled(Vector3.ONE*actor_scale), head.origin)
	var actual := _world_points(visual, bindings)
	var maximum := 0.0
	for name in bindings:
		maximum = maxf(maximum, (physical*bindings[name]).distance_to(actual[name]))
	return maximum

static func _diameters(visual: ActorVisual, bindings: Dictionary) -> Array[float]:
	var points := _world_points(visual, bindings)
	var result: Array[float] = []
	for eye in ["image_left", "image_right"]:
		result.append(points[eye+"_front_pole"].distance_to(points[eye+"_back_pole"]))
	return result

static func _diameters_valid(values: Array[float], fixture: Dictionary, scale: float) -> bool:
	return values.size() == 2 and values.all(func(value: float): return value >= float(fixture.diameter_range_m[0])*scale and value <= float(fixture.diameter_range_m[1])*scale)

static func _snapshot(state: StringName, time: float, length: float) -> Dictionary:
	if state in SkeletalVisualBridge.LOOP_STATES:
		return {"speed":0.0 if state == &"idle" else (8.5 if state == &"run" else 6.4), "move_local_x":-1.0 if state == &"walk_left" else (1.0 if state == &"walk_right" else 0.0), "move_local_z":1.0 if state == &"walk_back" else (0.0 if state in [&"walk_left", &"walk_right"] else -1.0)}
	match state:
		&"dodge": return {"dodge_remaining":maxf(0.0001,length-time), "dodge_elapsed":time, "dodge_duration":length, "dodge_local_x":1.0, "dodge_local_z":0.0}
		&"parry": return {"parry_remaining":maxf(0.0001,length-time), "parry_elapsed":time, "parry_duration":length}
		&"hit": return {"stagger":maxf(0.0001,length-time), "hit_elapsed":time, "hit_duration":length}
		&"charge": return {"charge_active":true, "charge_elapsed":time, "charge_duration":length}
		&"heal": return {"heal_remaining":maxf(0.0001,length-time), "heal_elapsed":time, "heal_duration":length}
		&"death": return {"dead":true, "death_elapsed":time, "death_duration":length}
	return {"attack_id":String(state), "attack_elapsed":time, "attack_duration":length}

static func run(world: Node3D, check: Callable) -> bool:
	var fixture = JSON.parse_string(FileAccess.get_file_as_string(FIT_PATH))
	var fixture_ok: bool = fixture is Dictionary and fixture.get("schema_version") == 1 and fixture.get("samples", []).size() == 6
	check.call(fixture_ok, "Eye fit uses frozen actual Web vertices and independent original Head REST anchors")
	if not fixture_ok:
		return false
	var definition := ProductionCharacterArt.definition("hero")
	check.call(definition.has("eye_path") and FileAccess.get_sha256(definition.get("eye_path", "")) == fixture.eye_glb_sha256 and FileAccess.get_sha256(definition.path) == fixture.socket_body_sha256, "Runtime body and eye geometry match the separately measured frozen input assets")
	var holder := Node3D.new()
	world.add_child(holder)
	var visual := ActorVisual.new()
	visual.setup("hero")
	holder.add_child(visual)
	var mounted := visual.use_production_profile("hero")
	var attached: bool = mounted.ok and is_instance_valid(visual.eye_socket) and is_instance_valid(visual.eye_model)
	check.call(attached, "Actual production hero mounts the dedicated eye scene and attachment")
	if not attached:
		holder.free()
		return false
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var head_index := skeleton.find_bone("Head")
	check.call(visual.eye_socket.get_parent() == skeleton and visual.eye_socket.bone_name == &"Head" and visual.eye_model.get_parent() == visual.eye_socket, "Eyes attach directly to the actual Head bone instead of a prototype joint or extra rotated wrapper")
	check.call(visual.eye_model.position.is_zero_approx() and visual.eye_model.basis.orthonormalized().is_equal_approx(Basis.IDENTITY) and ProductionCharacterArt.find_type(visual.eye_model,"Skeleton3D") == null and ProductionCharacterArt.find_type(visual.eye_model,"AnimationPlayer") == null, "Eye asset stays rigid with identity local rotation/translation and no independent skin or playback")
	var material_report := _material_report(visual.eye_model, fixture)
	check.call(material_report.ok, "Only the three procedural eye parts use finite opaque vertex-colored PBR with the measured Web topology")
	check.call(_body_materials_valid(visual,fixture), "Original body surface keeps albedo/normal textures; only the named 136-triangle inner lid uses its exact dedicated opaque PBR contract")
	var binding_report := _bindings(material_report.points, fixture)
	var bindings: Dictionary = binding_report.positions
	check.call(binding_report.maximum_error_m <= float(fixture.import_vertex_tolerance_m), "Actual imported eye vertices match the independent recorded front/back/outer source samples")
	check.call(_source_colors_preserved(material_report.colored_points,fixture), "Actual imported nonwhite vertex colors retain the measured source samples within their byte-channel precision")
	_rest(visual)
	var expected_head_rest := visual.global_transform*Transform3D(Basis(Vector3.UP,PI),Vector3.ZERO)*_matrix(fixture.source_head_rest_world_y_up_rows)
	var actual_head_rest := _head(visual)
	check.call(actual_head_rest.is_equal_approx(expected_head_rest), "Actual Skeleton REST Head matches the independent source glTF Head basis, origin and inherited scale")
	var rest_error := _rest_error(visual, bindings, fixture)
	print("RUNEFALL_EYE_REST: ", JSON.stringify({"head_origin_error_m":actual_head_rest.origin.distance_to(expected_head_rest.origin),"eye_anchor_max_error_m":rest_error,"expected_head":str(expected_head_rest),"actual_head":str(actual_head_rest)}))
	check.call(rest_error <= float(fixture.position_tolerance_m), "REST eye vertices match original source-world anchors with exactly one gameplay PI facing correction")
	var diameter := _diameters(visual, bindings)
	check.call(_diameters_valid(diameter, fixture, 1.0), "Actual eye diameter stays near 24mm after internal normalization-scale compensation")
	holder.transform = Transform3D(Basis.from_euler(Vector3(0.13,-0.61,0.08)).scaled(Vector3.ONE*1.25), Vector3(3.2,1.7,-4.3))
	_rest(visual)
	var transformed_error := _rest_error(visual, bindings, fixture)
	check.call(transformed_error <= float(fixture.position_tolerance_m), "External translation, rotation and 1.25 scale preserve independent REST anchors without double scale or orientation")
	var scaled_diameter := _diameters(visual, bindings)
	check.call(_diameters_valid(scaled_diameter, fixture, 1.25), "External actor scale correctly changes actual eye diameter to about 31mm")
	var maximum_pose_error := 0.0
	var samples := 0
	var clips_ok := true
	for state: StringName in ProductionCharacterArt.HERO_STATES:
		var length := visual.skeletal_bridge.animation_player.get_animation(visual.skeletal_bridge.clips[state]).length
		for fraction: float in [0.0,0.37,0.78]:
			visual.skeletal_bridge.reset_presentation()
			var time := length*fraction
			_pose(visual, _snapshot(state,time,length), time if state in SkeletalVisualBridge.LOOP_STATES else 0.0)
			maximum_pose_error = maxf(maximum_pose_error,_head_error(visual,bindings))
			clips_ok = clips_ok and visual.skeletal_bridge.selected_state == state and visual.eye_socket.global_transform.is_equal_approx(_head(visual))
			samples += 1
	check.call(clips_ok and samples == 57 and maximum_pose_error <= float(fixture.position_tolerance_m), "All 19 actual gameplay clips keep eye vertices on the current Head pose in 57 same-frame samples")
	visual.skeletal_bridge.reset_presentation()
	_pose(visual, {"speed":0.0})
	_pose(visual, {"speed":8.5}, 1.0/60.0)
	check.call(visual.skeletal_bridge.transition_report().active and visual.eye_socket.global_transform.is_equal_approx(_head(visual)) and _head_error(visual,bindings) <= float(fixture.position_tolerance_m), "Eyes follow the final blended Head pose in the same frame as a production transition")
	var frozen_head := _head(visual)
	var frozen_eyes := visual.eye_model.global_transform
	await world.get_tree().process_frame
	await world.get_tree().process_frame
	_pose(visual, {"speed":8.5})
	check.call(frozen_head.is_equal_approx(_head(visual)) and frozen_eyes.is_equal_approx(visual.eye_model.global_transform), "Hitpause holds both Head and eyes without independent eye animation or a blend-clock advance")
	for angles in [Vector2(deg_to_rad(24.0),0.0),Vector2(0.0,deg_to_rad(-17.0))]:
		_rest(visual)
		var original_head := _head(visual)
		var original_points := _world_points(visual,bindings)
		var rotation := skeleton.get_bone_pose_rotation(head_index)
		skeleton.set_bone_pose_rotation(head_index,rotation*Quaternion(Vector3.UP,angles.x)*Quaternion(Vector3.RIGHT,angles.y))
		visual.eye_socket.on_skeleton_update() # Explicit manual art-fixture update.
		var moved_head := _head(visual)
		var delta: Basis = moved_head.basis*original_head.basis.inverse()
		var actual := _world_points(visual,bindings)
		var error := 0.0
		var movement := 0.0
		for name in bindings:
			error = maxf(error,(moved_head.origin+delta*(original_points[name]-original_head.origin)).distance_to(actual[name]))
			movement = maxf(movement,original_points[name].distance_to(actual[name]))
		check.call(error <= float(fixture.position_tolerance_m) and movement > 0.005, "Explicit Head %s rotates real eye vertices through the expected rigid delta" % ("yaw" if angles.x != 0.0 else "pitch"))
	var eye_reference: WeakRef = weakref(visual.eye_model)
	var socket_reference: WeakRef = weakref(visual.eye_socket)
	print("RUNEFALL_EYE_ATTACHMENT: ",JSON.stringify({"body_sha256":FileAccess.get_sha256(definition.path),"eyes_sha256":FileAccess.get_sha256(definition.eye_path),"rest_anchor_max_error_m":rest_error,"external_transform_anchor_max_error_m":transformed_error,"actual_pose_samples":samples,"actual_pose_max_error_m":maximum_pose_error,"import_vertex_max_error_m":binding_report.maximum_error_m,"diameters_m":diameter,"external_1_25_diameters_m":scaled_diameter,"scope":"Attachment/units/materials only; eyelid collisions and AAA visual approval are separate."}))
	visual.clear_rig()
	check.call(visual.eye_model == null and visual.eye_socket == null and eye_reference.get_ref() == null and socket_reference.get_ref() == null, "Clearing the character releases eye geometry and its Head socket with the old rig")
	holder.free()
	return true
