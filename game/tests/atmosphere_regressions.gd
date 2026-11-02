extends RefCounted

static func _world_rect(mesh: MeshInstance3D) -> Rect2:
	var bounds: AABB = mesh.global_transform * mesh.get_aabb()
	return Rect2(Vector2(bounds.position.x,bounds.position.z),Vector2(bounds.size.x,bounds.size.z))

static func run(world: Node3D, check: Callable) -> bool:
	var sanctuary: Sanctuary = world.sanctuary
	var landing := sanctuary.get_node_or_null("LandingFlagstone") as MeshInstance3D
	var approach := sanctuary.get_node_or_null("CourtyardApproachFlagstone") as MeshInstance3D
	var courtyard := sanctuary.get_node_or_null("CourtyardFlagstone") as MeshInstance3D
	check.call(landing != null and approach != null and courtyard != null,"Actual landing, connector and courtyard have separate visible stone skins")
	if landing == null or approach == null or courtyard == null:
		return false
	var materials_ok := true
	var surfaces_have_no_physics := true
	for mesh in [landing,approach,courtyard]:
		var material := mesh.material_override as StandardMaterial3D
		var plane := mesh.mesh as PlaneMesh
		materials_ok = materials_ok and plane != null and material != null
		if plane != null and material != null:
			materials_ok = materials_ok and material.albedo_texture != null and material.normal_enabled and material.normal_texture != null
			materials_ok = materials_ok and is_equal_approx(material.uv1_scale.x,plane.size.x/1.8) and is_equal_approx(material.uv1_scale.y,plane.size.y/1.8)
		surfaces_have_no_physics = surfaces_have_no_physics and mesh.find_children("*","CollisionObject3D",true,false).is_empty() and mesh.find_children("*","CollisionShape3D",true,false).is_empty()
	check.call(materials_ok,"All three actual surfaces use textured normal-mapped stone at the same1.8m physical tile scale")
	check.call(surfaces_have_no_physics,"Visible floor skins do not own replacement collision bodies or shapes")
	var landing_rect := _world_rect(landing)
	var approach_rect := _world_rect(approach)
	var court_rect := _world_rect(courtyard)
	check.call(approach_rect.size.is_equal_approx(Vector2(12,5)) and absf(approach_rect.position.y+18.0)<.0001 and absf(approach_rect.end.y+13.0)<.0001,"Connector skin covers only the real5m gap rather than its longer overlapping collider")
	# PI rotation produces sub-micrometre AABB rounding at the shared edge.
	var interior := approach_rect.grow(-.0001)
	check.call(not interior.intersects(landing_rect) and not interior.intersects(court_rect),"Adjacent stone skins meet at their edges without coplanar interior overlap beyond floating-point rounding")
	var hidden_road: StaticBody3D
	for node in sanctuary.find_children("*","CollisionShape3D",true,false):
		var shape := node as CollisionShape3D
		if shape.shape is BoxShape3D and shape.shape.size.is_equal_approx(Vector3(12,.7,7)) and shape.global_position.is_equal_approx(Vector3(0,-.35,-16.5)):
			hidden_road = shape.get_parent() as StaticBody3D
	check.call(is_instance_valid(hidden_road) and not hidden_road.get_parent().visible and hidden_road.collision_layer==1,"The original hidden road retains its original physical dimensions, transform and floor layer")
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	var support_ok := true
	var support_rows: Array[Dictionary] = []
	for z in [6.0,-12.9,-13.1,-16.5,-17.9,-18.1,-24.0]:
		var query := PhysicsRayQueryParameters3D.create(Vector3(0,3,z),Vector3(0,-.1,z),1)
		var hit := sanctuary.get_world_3d().direct_space_state.intersect_ray(query)
		var supported := not hit.is_empty() and absf(hit.position.y)<.001 and Vector3(hit.normal).dot(Vector3.UP)>.999
		support_ok = support_ok and supported
		support_rows.append({"z":z,"supported":supported,"height":float(hit.position.y) if not hit.is_empty() else -999.0})
	check.call(support_ok,"Actual floor rays remain supported across spawn, both visual seams, connector and combat floor")
	var environment := sanctuary.get_node("SanctuaryEnvironment") as WorldEnvironment
	var sky := environment.environment.sky
	var sky_material := sky.sky_material as ShaderMaterial
	var key := sanctuary.get_node("SanctuaryKey") as DirectionalLight3D
	check.call(sky_material != null and sky_material.get_meta("sky_profile","")=="sanctuary_static_clouds_002" and sky.process_mode==Sky.PROCESS_MODE_QUALITY,"Actual atmosphere selects the static cached sky profile instead of per-frame sky processing")
	if sky_material == null:
		return false
	var sun: Vector3 = sky_material.get_shader_parameter("sun_direction")
	check.call(sun.is_finite() and absf(sun.length()-1)<.0001 and sun.dot(key.global_basis.z.normalized())>.99999,"Actual sky sun direction is finite, unit length and aligned to the actual key-light source")
	var backdrop := sanctuary.get_node_or_null("SanctuaryBackdrop") as Node3D
	check.call(backdrop != null,"Actual Sanctuary includes its visual-only atmosphere backdrop")
	if backdrop == null:
		return false
	var no_authority := backdrop.find_children("*","CollisionObject3D",true,false).is_empty() and backdrop.find_children("*","CollisionShape3D",true,false).is_empty() and backdrop.find_children("*","Light3D",true,false).is_empty() and backdrop.find_children("*","NavigationRegion3D",true,false).is_empty()
	check.call(no_authority and not backdrop.is_processing() and not backdrop.is_physics_processing(),"Static background geometry owns no physics, navigation, lights or per-frame process callbacks")
	var meshes := backdrop.find_children("*","MeshInstance3D",true,false)
	var triangles := 0
	var vertices_count := 0
	var safe_geometry := true
	var resources_ok := true
	for child in meshes:
		var mesh := child as MeshInstance3D
		resources_ok = resources_ok and mesh.mesh != null and mesh.cast_shadow==GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		if mesh.mesh == null:
			continue
		for surface in range(mesh.mesh.get_surface_count()):
			var arrays := mesh.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var index_array = arrays[Mesh.ARRAY_INDEX]
			var indices: PackedInt32Array = index_array if index_array is PackedInt32Array else PackedInt32Array()
			vertices_count += vertices.size()
			triangles += indices.size()/3 if not indices.is_empty() else vertices.size()/3
			for vertex in vertices:
				var point: Vector3 = mesh.global_transform * vertex
				safe_geometry = safe_geometry and point.is_finite() and (absf(point.x)>=45.99 or point.z<=-464.99)
	check.call(meshes.size()>0 and meshes.size()<=6 and triangles>0 and triangles<=24000 and vertices_count<=72000 and resources_ok,"Actual merged backdrop arrays remain within the six-mesh geometry budget and cast no distant real-time shadows")
	check.call(safe_geometry,"Every actual backdrop vertex stays outside the gameplay and camera corridor clearance")
	var legacy_count := 0
	var legacy_hidden := true
	for child in sanctuary.get_children():
		if child.has_meta("legacy_skyline_block"):
			legacy_count += 1
			legacy_hidden = legacy_hidden and not child.visible
	check.call(legacy_count==45 and legacy_hidden,"Legacy random skyline boxes retain their seeded construction but no longer render over authored scenery")
	var report := {"scope":"Actual native sky/floor/backdrop contracts; no raster, hardware performance, AV or AAA approval","support_rays":support_rows,"backdrop_meshes":meshes.size(),"triangles":triangles,"stored_vertices":vertices_count,"safe_geometry":safe_geometry,"sun_direction":[sun.x,sun.y,sun.z],"legacy_hidden_count":legacy_count}
	var path := ProjectSettings.globalize_path("res://../build/verification/atmosphere/native.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report,"\t")+"\n")
		file.close()
	return true
