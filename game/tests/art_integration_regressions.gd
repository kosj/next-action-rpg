extends RefCounted

static func _meshes(root: Node) -> Array[MeshInstance3D]:
	var result: Array[MeshInstance3D] = []
	if root is MeshInstance3D:
		result.append(root)
	for child in root.get_children():
		result.append_array(_meshes(child))
	return result

static func _bounds(root: Node3D) -> AABB:
	var result := AABB()
	var first := true
	for mesh in _meshes(root):
		var bounds := mesh.get_aabb()
		var relative := root.global_transform.affine_inverse() * mesh.global_transform
		for corner in range(8):
			var point := relative * bounds.get_endpoint(corner)
			if first:
				result = AABB(point, Vector3.ZERO)
				first = false
			else:
				result = result.expand(point)
	return result

static func _ray(space: PhysicsDirectSpaceState3D, start: Vector3, end: Vector3, exclude: Array[RID] = []) -> Dictionary:
	var query := PhysicsRayQueryParameters3D.create(start, end, 1)
	query.exclude = exclude
	return space.intersect_ray(query)

static func _passage_motion(space: PhysicsDirectSpaceState3D, frame: Node3D) -> PackedFloat32Array:
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.36
	capsule.height = 1.85
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = capsule
	query.transform.origin = frame.global_position + Vector3(0,0.95,2)
	query.motion = Vector3(0,0,-4)
	query.margin = 0.005
	query.collision_mask = 1
	return space.cast_motion(query)

static func _textured_material(mesh: MeshInstance3D) -> bool:
	if mesh == null or mesh.material_override != null or mesh.get_surface_override_material(0) != null:
		return false
	var material := mesh.get_active_material(0) as BaseMaterial3D
	return material != null and material.albedo_texture != null and material.normal_texture != null

static func run(world: Node3D, check: Callable) -> bool:
	var sanctuary: Sanctuary = world.sanctuary
	var pillars: Array[Node3D] = []
	var frames: Array[Node3D] = []
	for child in sanctuary.get_children():
		if child.get_meta("production_asset", "") == "sanctuary_pillar":
			pillars.append(child)
		elif child.get_meta("production_asset", "") == "pilgrim_gateway":
			frames.append(child)
	check.call(pillars.size() == 8 and frames.size() == 1, "Generated environment is limited to eight first-courtyard pillars and one exit frame")
	if pillars.size() != 8 or frames.size() != 1:
		return false
	var frame := frames[0]
	var centre := Sanctuary.CENTERS[0]
	var placement_ok := true
	var pillar_bounds_ok := true
	for pillar in pillars:
		var bounds := _bounds(pillar)
		pillar_bounds_ok = pillar_bounds_ok and bounds.size.is_equal_approx(Vector3(1.6,7,1.6)) and absf(bounds.position.y) < 0.0001
		var relative := pillar.position-centre
		placement_ok = placement_ok and absf(absf(relative.x)-18.0) < 0.0001 and (relative.z in [-17.0,-5.0,7.0,17.0]) and is_zero_approx(relative.y)
	check.call(pillar_bounds_ok and placement_ok, "Actual imported pillar bounds are Y-up, grounded, and remain outside the clear combat area")
	var gateway_bounds := _bounds(frame)
	check.call(gateway_bounds.size.is_equal_approx(Vector3(17,7.8,1.6)) and absf(gateway_bounds.position.y) < 0.0001 and frame.position.is_equal_approx(centre+Vector3(0,0,-18)), "Actual gateway mesh keeps its canonical dimensions and north exit position")
	var space := sanctuary.get_world_3d().direct_space_state
	var barrier: Node3D = sanctuary.gates[0][0]
	var barrier_body := barrier.get_child(0) as StaticBody3D
	var barrier_shape := barrier_body.get_child(0) as CollisionShape3D
	var original_closed := barrier.visible
	sanctuary.set_gates(0, false)
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	# Exclude only the added visual-prop bodies: these rays must still hit the
	# original hidden 1.6 x .6 x 1.6m bases, not substitute collisions.
	var bases_ok := true
	for pillar in pillars:
		var body := pillar.get_node("ColumnCollision") as StaticBody3D
		var hit := _ray(space, pillar.global_position+Vector3(0.77,1,0), pillar.global_position+Vector3(0.77,0.2,0), [body.get_rid()])
		bases_ok = bases_ok and not hit.is_empty() and absf(hit.position.y-(pillar.global_position.y+0.6)) < 0.001
	var frame_body := frame.get_node("FrameCollision") as StaticBody3D
	for side in [-1,1]:
		var point := frame.global_position+Vector3(side*7.5,0,0)
		var hit := _ray(space, point+Vector3(0.77,1,0), point+Vector3(0.77,0.2,0), [frame_body.get_rid()])
		bases_ok = bases_ok and not hit.is_empty() and absf(hit.position.y-(point.y+0.6)) < 0.001
	check.call(bases_ok, "All ten original first-room pillar and doorway base colliders survive the visual replacement")
	var pillar := pillars[0]
	var pillar_body := pillar.get_node("ColumnCollision")
	var pillar_rays_ok := true
	for height in [0.9,3.5,6.4]:
		var hit := _ray(space, pillar.global_position+Vector3(0,height,2), pillar.global_position+Vector3(0,height,-2))
		pillar_rays_ok = pillar_rays_ok and not hit.is_empty() and hit.collider == pillar_body
	check.call(pillar_rays_ok, "Camera-height rays hit the added pillar shaft and collar collisions instead of passing through the model")
	var post_rays_ok := true
	for offset in [Vector3(-7.25,3,0), Vector3(7.25,3,0), Vector3(0,6.9,0)]:
		var hit := _ray(space, frame.global_position+offset+Vector3(0,0,2), frame.global_position+offset-Vector3(0,0,2))
		post_rays_ok = post_rays_ok and not hit.is_empty() and hit.collider == frame_body
	check.call(post_rays_ok, "Gateway posts and lintel stop camera rays while remaining independent of encounter barriers")
	var clear_motion := _passage_motion(space, frame)
	var centre_ray := _ray(space, frame.global_position+Vector3(0,3,2), frame.global_position+Vector3(0,3,-2))
	check.call(centre_ray.is_empty() and clear_motion.size() == 2 and clear_motion[0] > 0.999, "The visible gateway leaves the actual player capsule passage clear when the encounter is open")
	sanctuary.set_gates(0, true)
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	var blocked_motion := _passage_motion(space, frame)
	var closed_hit := _ray(space, frame.global_position+Vector3(0,3,2), frame.global_position+Vector3(0,3,-2))
	check.call(frame.is_visible_in_tree() and not barrier_shape.disabled and blocked_motion.size() == 2 and blocked_motion[0] < 0.99 and not closed_hit.is_empty() and closed_hit.collider == barrier_body and barrier.get_child(0).get_child(0) == barrier_shape, "Encounter lock retains its original barrier tree and blocks the capsule without hiding the new static frame")
	sanctuary.set_gates(0, false)
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	var reopened := _passage_motion(space, frame)
	check.call(frame.is_visible_in_tree() and barrier_shape.disabled and reopened.size() == 2 and reopened[0] > 0.999, "Unlock reopens the capsule passage and keeps the independent gateway frame visible")
	sanctuary.set_gates(0, original_closed)
	var visual := ActorVisual.new()
	world.add_child(visual)
	visual.setup("hero")
	var socket := visual.joints["Sword"] as Node3D
	var sword := socket.get_node("RuneSwordPreview") as Node3D
	var old_hidden := true
	for child_name in ["Hilt", "Guard", "Blade", "Blade light"]:
		old_hidden = old_hidden and not socket.get_node(NodePath(child_name)).visible
	check.call(old_hidden and sword.is_visible_in_tree() and visual.model.is_ancestor_of(sword), "Only the hero's old sword geometry is hidden and the imported weapon inherits prototype visibility")
	# Godot adds an imported scene wrapper above the canonical GLB root.
	var tip := sword.find_child("BladeTip", true, false) as Node3D
	var grip := sword.find_child("GripOrigin", true, false) as Node3D
	if tip == null or grip == null:
		visual.free()
		return false
	var tip_in_socket := socket.to_local(tip.global_position)
	var original_model := load("res://assets/models/hero.glb").instantiate() as Node3D
	var original_socket := original_model.find_child("Sword", true, false) as Node3D
	check.call(socket.to_local(grip.global_position).length() < 0.0001 and absf(tip_in_socket.y+1.19) < 0.0001 and Vector2(tip_in_socket.x,tip_in_socket.z).length() < 0.002 and socket.transform.is_equal_approx(original_socket.transform), "Actual grip and tip markers align the canonical +Y blade to prototype -Y without moving its hand socket")
	original_model.free()
	var sword_mesh := _meshes(sword)[0]
	check.call(_textured_material(sword_mesh), "Imported hero sword keeps its textured PBR material without prototype color overrides")
	var sentinel := ActorVisual.new()
	world.add_child(sentinel)
	sentinel.setup("sentinel")
	var sentinel_socket := sentinel.joints["Sword"] as Node3D
	check.call(sentinel_socket.get_node("Blade").visible and not sentinel_socket.has_node("RuneSwordPreview"), "The hero sword preview does not change recurring enemy weapons")
	sentinel.free()
	var fixture = load("res://tests/skeletal_regressions.gd")
	var mounted := visual.mount_rig(fixture._scene())
	var hidden_with_rig := false
	var restored_on_fallback := false
	if mounted.ok:
		visual.pose(0,0,-1,false,false,false,{"speed":0.0})
		hidden_with_rig = not sword.is_visible_in_tree()
		visual.pose(0,0,-1,false,false,false,{"attack_id":"heavy","attack_elapsed":0.1,"attack_duration":0.8})
		restored_on_fallback = sword.is_visible_in_tree() and not socket.get_node("Blade").visible
		visual.clear_rig()
	check.call(mounted.ok and hidden_with_rig and restored_on_fallback and sword.is_visible_in_tree(), "The imported sword hides with a mounted rig and returns cleanly through unsupported-state fallback and detachment")
	var original_quality: int = Session.quality
	var qualities_ok := true
	for quality in [0,1]:
		Session.quality = quality
		world.apply_quality()
		qualities_ok = qualities_ok and frame.is_visible_in_tree() and sword.is_visible_in_tree() and _textured_material(sword_mesh)
		for detailed_pillar in pillars:
			qualities_ok = qualities_ok and detailed_pillar.is_visible_in_tree() and _textured_material(_meshes(detailed_pillar)[0])
	Session.quality = original_quality
	world.apply_quality()
	check.call(qualities_ok, "Both existing quality modes preserve the generated static visuals and their source PBR materials")
	visual.free()
	return true
