extends RefCounted

static func _bucket(point: Vector3, uv: Vector2) -> Vector3i:
	return Vector3i(floori(point.y*1000),floori(uv.x*1000),floori(uv.y*1000))

static func _expected(point: Vector3) -> Vector3:
	var begin := smoothstep(.24,.34,point.y)
	var end := 1.0-smoothstep(1.03,1.185,point.y)
	return Vector3(point.x*(1.0+.8*begin*end),point.y,point.z)

static func _corner(point: Vector3, uv: Vector2) -> String:
	return "%.8f|%.8f|%.8f|%.8f|%.8f" % [point.x,point.y,point.z,uv.x,uv.y]

static func _triangles(indices: PackedInt32Array, canonical: PackedInt32Array) -> Dictionary:
	var result := {}
	for index in range(0,indices.size(),3):
		var corners := PackedInt32Array([canonical[indices[index]],canonical[indices[index+1]],canonical[indices[index+2]]])
		corners.sort()
		var key := "%d|%d|%d" % [corners[0],corners[1],corners[2]]
		result[key] = int(result.get(key,0))+1
	return result

static func run(world: Node3D, check: Callable) -> bool:
	var original := ActorVisual.RUNE_SWORD_SCENE.instantiate() as Node3D
	var hero := ActorVisual.RUNE_SWORD_SCENE.instantiate() as Node3D
	world.add_child(original)
	world.add_child(hero)
	var source_mesh := original.find_child("CanonicalGeometry", true, false) as MeshInstance3D
	var hero_mesh := hero.find_child("CanonicalGeometry", true, false) as MeshInstance3D
	var source_resource := source_mesh.mesh
	var source_material := source_mesh.get_active_material(0)
	check.call(ActorVisual.apply_hero_blade_profile(hero), "Hero broader blade installs on the actual canonical sword scene")
	check.call(hero_mesh.mesh != source_resource and source_mesh.mesh == source_resource and hero_mesh.get_active_material(0) == source_material, "Hero geometry changes while the original sword and shared PBR resources stay intact")
	var markers_match := true
	for name in ["GripOrigin", "BladeTip", "Guard"]:
		var a := original.find_child(name, true, false) as Node3D
		var b := hero.find_child(name, true, false) as Node3D
		markers_match = markers_match and a.transform.is_equal_approx(b.transform)
	check.call(markers_match, "Broader blade preserves the actual grip, tip and guard marker transforms")
	var before := source_resource.surface_get_arrays(0)
	var after := hero_mesh.mesh.surface_get_arrays(0)
	var old_points: PackedVector3Array = before[Mesh.ARRAY_VERTEX]
	var new_points: PackedVector3Array = after[Mesh.ARRAY_VERTEX]
	var old_uv: PackedVector2Array = before[Mesh.ARRAY_TEX_UV]
	var new_uv: PackedVector2Array = after[Mesh.ARRAY_TEX_UV]
	# Godot optimizes vertex/index order and compresses attributes according to
	# imported material usage. Compare actual geometric/UV correspondence and
	# the triangle multiset, not importer ordering. Raw GLB topology is also
	# recorded unchanged by the offline derivative.
	var buckets := {}
	var aliases := {}
	var old_canonical := PackedInt32Array()
	for index in range(old_points.size()):
		var bucket := _bucket(old_points[index],old_uv[index])
		if not buckets.has(bucket):
			buckets[bucket] = []
		buckets[bucket].append(index)
		var key := _corner(old_points[index],old_uv[index])
		if not aliases.has(key):
			aliases[key] = index
		old_canonical.append(int(aliases[key]))
	var new_canonical := PackedInt32Array()
	var correspondence_valid := old_points.size()==new_points.size()
	var uv_error := 0.0
	var protected_error := 0.0
	var longitudinal_error := 0.0
	var old_min := INF
	var old_max := -INF
	var new_min := INF
	var new_max := -INF
	var correspondence_error := 0.0
	for index in range(new_points.size()):
		var b := new_points[index]
		var bucket := _bucket(b,new_uv[index])
		var best := -1
		var distance := INF
		for dy in range(-1,2):
			for du in range(-1,2):
				for dv in range(-1,2):
					for candidate: int in buckets.get(bucket+Vector3i(dy,du,dv),[]):
						var error := _expected(old_points[candidate]).distance_to(b)
						if error<distance and old_uv[candidate].distance_to(new_uv[index])<.0001:
							distance = error
							best = candidate
		if best<0 or distance>.0001:
			correspondence_valid = false
			new_canonical.append(-1)
			continue
		new_canonical.append(old_canonical[best])
		var a := old_points[best]
		correspondence_error = maxf(correspondence_error,distance)
		uv_error = maxf(uv_error, old_uv[best].distance_to(new_uv[index]))
		longitudinal_error = maxf(longitudinal_error, Vector2(a.y,a.z).distance_to(Vector2(b.y,b.z)))
		if a.y <= .24 or a.y >= 1.185:
			protected_error = maxf(protected_error, a.distance_to(b))
		if a.y >= .50 and a.y <= .80:
			old_min = minf(old_min,a.x)
			old_max = maxf(old_max,a.x)
			new_min = minf(new_min,b.x)
			new_max = maxf(new_max,b.x)
	var topology_valid := correspondence_valid and _triangles(before[Mesh.ARRAY_INDEX],old_canonical)==_triangles(after[Mesh.ARRAY_INDEX],new_canonical)
	check.call(topology_valid, "The imported broader blade preserves every original geometric/UV triangle despite importer reordering")
	check.call(correspondence_valid and protected_error < .0001 and longitudinal_error < .0001, "Imported hilt/guard/apex and longitudinal positions retain the source within0.1mm attribute compression")
	check.call(correspondence_valid and uv_error < .0001, "Original atlas coordinates are retained within native attribute compression without an extra texture atlas")
	check.call(new_max-new_min > .09 and new_max-new_min > (old_max-old_min)*1.7, "Actual central blade silhouette exceeds9cm and materially broadens the original sword")
	var normals: PackedVector3Array = after[Mesh.ARRAY_NORMAL]
	var tangents: PackedFloat32Array = after[Mesh.ARRAY_TANGENT]
	var valid_frames := normals.size() == new_points.size() and tangents.size() == new_points.size()*4
	for index in range(normals.size()):
		var tangent := Vector3(tangents[index*4],tangents[index*4+1],tangents[index*4+2])
		valid_frames = valid_frames and normals[index].is_finite() and tangent.is_finite() and absf(normals[index].length()-1.0) < .01 and absf(tangent.length()-1.0) < .01 and absf(normals[index].dot(tangent)) < .01
	check.call(valid_frames, "Imported broader-blade normal/tangent frames remain finite, normalized and orthogonal")
	var report := {"scope":"Actual imported Hero-only geometry/PBR/marker contract; raw GLB coordinates unchanged outside the blade; native attributes quantized/reordered; no hand clearance, visual quality, triangle contact or AAA approval", "geometry_sha256":FileAccess.get_sha256("res://assets/models/production/rune_greatsword_geometry.glb"), "source_sha256":FileAccess.get_sha256("res://assets/models/production/rune_sword_web.glb"), "old_central_width_m":old_max-old_min, "new_central_width_m":new_max-new_min, "protected_position_error_m":protected_error,"longitudinal_error_m":longitudinal_error,"uv_error":uv_error,"correspondence_error_m":correspondence_error,"triangle_multiset_unchanged":topology_valid,"normal_tangent_frames_valid":valid_frames,"original_material_resource_reused":hero_mesh.get_active_material(0)==source_material}
	var path := ProjectSettings.globalize_path("res://").path_join("../build/verification/combat-polish/weapon.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report,"\t")+"\n")
		file.close()
	else:
		push_error("Cannot write actual greatsword verification")
	original.free()
	hero.free()
	return true
