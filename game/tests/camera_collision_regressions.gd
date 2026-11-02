extends RefCounted

# Real Camera3D projection and PhysicsServer gate/overhang queries. Actor paths
# are prescribed to reproduce recorded camera lag; this is not controller,
# evaluated-skin, continuous video, target-GPU or AAA acceptance.
const STEP := 1.0/60.0

static func _box(parent: Node3D, label: String, point: Vector3, size: Vector3, enabled: bool) -> StaticBody3D:
	var body: StaticBody3D = StaticBody3D.new()
	body.name = label
	body.collision_layer = 1
	body.collision_mask = 0
	var shape: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = size
	shape.shape = box
	shape.disabled = not enabled
	body.add_child(shape)
	parent.add_child(body)
	body.position = point
	return body

static func _enable(body: StaticBody3D, enabled: bool) -> void:
	var shape: CollisionShape3D = body.get_child(0) as CollisionShape3D
	shape.set_deferred("disabled",not enabled)

static func _nominal_projection(rig: RuneCamera, hero: RunePlayer, viewport: SubViewport) -> Dictionary:
	var base: Vector3 = hero.global_position+hero.global_basis.y*hero.visual.ground_offset_y
	var right: Vector3 = rig.camera.global_basis.x.normalized()
	var points: Array[Vector3] = [base,base+Vector3.UP*1.82,
		base+Vector3.UP*.91-right*.38,base+Vector3.UP*.91+right*.38]
	var uv: Array[Vector2] = []
	var fits: bool = true
	for point: Vector3 in points:
		var pixel: Vector2 = rig.camera.unproject_position(point)
		var projected: Vector2 = pixel/Vector2(viewport.size)
		uv.append(projected)
		fits = fits and projected.is_finite() and not rig.camera.is_position_behind(point)
		fits = fits and projected.x>=.079 and projected.x<=.921 and projected.y>=.069 and projected.y<=.801
	return {"fits":fits,"points_uv":uv,"position":rig.camera.global_position,"fov":rig.camera.fov}

static func _endpoint_clear(stage: Node3D, position: Vector3, radius: float) -> bool:
	var query: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
	var sphere: SphereShape3D = SphereShape3D.new()
	sphere.radius = radius
	query.shape = sphere
	query.transform = Transform3D(Basis.IDENTITY,position)
	query.collision_mask = 1
	return stage.get_world_3d().direct_space_state.intersect_shape(query,1).is_empty()

static func _ray(stage: Node3D, start: Vector3, end: Vector3) -> Dictionary:
	return stage.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(start,end,1))

static func _motion_fraction(stage: Node3D, start: Vector3, end: Vector3, radius: float) -> float:
	var query: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
	var sphere: SphereShape3D = SphereShape3D.new()
	sphere.radius = radius
	query.shape = sphere
	query.transform = Transform3D(Basis.IDENTITY,start)
	query.motion = end-start
	query.collision_mask = 1
	var fractions: PackedFloat32Array = stage.get_world_3d().direct_space_state.cast_motion(query)
	return fractions[0] if fractions.size()==2 else 0.0

static func _prime_approach(hero: RunePlayer, rig: RuneCamera) -> void:
	hero.locked_target = null
	hero.position = Vector3(0,-hero.visual.ground_offset_y,-17)
	rig.yaw = 0.0
	rig.pitch = -.18
	rig.snap()
	# Reproduce the observed sprint and its ordinary smoothed focus before the
	# entrance closes. Bodies are not moved through an enabled collision wall.
	for index in range(20):
		hero.position.z -= 8.5*STEP
		rig._physics_process(STEP)
	hero.position.z = -19.8063716888428

static func _energy_gate(parent: Node3D) -> StaticBody3D:
	var visual: MeshInstance3D = MeshInstance3D.new()
	visual.name = "TemporaryEnergyGate"
	var mesh: BoxMesh = BoxMesh.new()
	mesh.size = Vector3(40,4,.3)
	visual.mesh = mesh
	var material: StandardMaterial3D = StandardMaterial3D.new()
	material.albedo_color = Color(.22,.55,.52,.24)
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	visual.material_override = material
	visual.position = Vector3(0,2,-18.5)
	parent.add_child(visual)
	var body: StaticBody3D = _box(visual,"GameplayBarrier",Vector3.ZERO,mesh.size,true)
	body.collision_mask = 1
	body.add_to_group(&"camera_transparent_barriers")
	return body

static func _enemy_projection(rig: RuneCamera, enemy: RuneEnemy, viewport: SubViewport) -> Dictionary:
	var right: Vector3 = rig.camera.global_basis.x.normalized()
	var base: Vector3 = enemy.global_position
	var points: Array[Vector3] = [base,base+Vector3.UP*1.95,
		base+Vector3.UP*.975-right*.42,base+Vector3.UP*.975+right*.42]
	var uv: Array[Vector2] = []
	var fits: bool = true
	for point: Vector3 in points:
		var projected: Vector2 = rig.camera.unproject_position(point)/Vector2(viewport.size)
		uv.append(projected)
		fits = fits and projected.is_finite() and not rig.camera.is_position_behind(point)
		fits = fits and projected.x>=.079 and projected.x<=.921 and projected.y>=.069 and projected.y<=.801
	return {"fits":fits,"points_uv":uv}

static func _transparent_gate_cases(world: Node3D, check: Callable, cases: Array[Dictionary]) -> bool:
	var sanctuary: Sanctuary = world.get("sanctuary") as Sanctuary
	var production_camera: RuneCamera = world.get("rig") as RuneCamera
	var factory_correct: bool = sanctuary!=null and production_camera!=null
	var classified_count: int = 0
	var foreign_body: StaticBody3D
	if sanctuary!=null:
		for pair: Array in sanctuary.gates.values():
			for gate: Node3D in pair:
				var body: StaticBody3D = gate.get_child(0) as StaticBody3D
				var visual: MeshInstance3D = gate as MeshInstance3D
				var material: StandardMaterial3D = visual.get_active_material(0) as StandardMaterial3D
				factory_correct = factory_correct and body.is_in_group(&"camera_transparent_barriers")
				factory_correct = factory_correct and material!=null and is_equal_approx(material.albedo_color.a,.24) and material.transparency==BaseMaterial3D.TRANSPARENCY_ALPHA
				factory_correct = factory_correct and body.collision_layer==1 and body.collision_mask==1 and production_camera._is_camera_transparent_barrier(body)
				foreign_body = body
				classified_count += 1
	check.call(factory_correct and classified_count==Sanctuary.CENTERS.size()*2,
		"Actual Sanctuary temporary gate factory explicitly classifies its existing24%-alpha gameplay barriers without changing layer1")
	for size: Vector2i in [Vector2i(1440,900),Vector2i(390,844)]:
		var viewport: SubViewport = SubViewport.new()
		viewport.size = size
		viewport.own_world_3d = true
		world.add_child(viewport)
		var stage: Node3D = Node3D.new()
		viewport.add_child(stage)
		var hero: RunePlayer = RunePlayer.new()
		stage.add_child(hero)
		hero.active = false
		hero.set_physics_process(false)
		hero.position = Vector3(0,-hero.visual.ground_offset_y,-19.80637169)
		var enemy: RuneEnemy = RuneEnemy.new()
		enemy.player = hero
		stage.add_child(enemy)
		enemy.set_physics_process(false)
		enemy.position = Vector3(0,0,-26.15)
		var rig: RuneCamera = RuneCamera.new()
		rig.player = hero
		stage.add_child(rig)
		rig.set_physics_process(false)
		rig.cinematic = false
		var barrier: StaticBody3D = _energy_gate(stage)
		var visual: MeshInstance3D = barrier.get_parent() as MeshInstance3D
		var material: StandardMaterial3D = visual.material_override as StandardMaterial3D
		var shape: CollisionShape3D = barrier.get_child(0) as CollisionShape3D
		await world.get_tree().physics_frame
		await world.get_tree().physics_frame
		rig.snap()
		var free_report: Dictionary = rig.framing_report()
		var exclusions: Array = free_report.camera_transparent_barriers
		check.call(rig.camera.global_position.z>-18.35 and not free_report.collision_fit.active and not free_report.collision_fit.obstructed and exclusions.size()==1 and String(exclusions[0].collider_id)==str(barrier.get_instance_id()),
			"Only the same-world low-alpha temporary field permits the ordinary camera boom through the still-visible barrier (%s)" % size)
		check.call(not rig._is_camera_transparent_barrier(foreign_body),"A tagged gate from another World3D cannot enter this camera's exclusion list (%s)" % size)
		var pivot: Vector3 = hero.global_position+Vector3.UP*(hero.visual.ground_offset_y+1.4)
		var physical_hit: Dictionary = _ray(stage,pivot,rig.camera.global_position)
		var actor_query: PhysicsShapeQueryParameters3D = PhysicsShapeQueryParameters3D.new()
		var actor_shape: CollisionShape3D = hero.get_child(0) as CollisionShape3D
		actor_query.shape = actor_shape.shape
		actor_query.transform = actor_shape.global_transform
		actor_query.motion = Vector3.BACK*3.0
		actor_query.collision_mask = 1
		var actor_motion: PackedFloat32Array = stage.get_world_3d().direct_space_state.cast_motion(actor_query)
		check.call(physical_hit.get("collider")==barrier and actor_motion.size()==2 and actor_motion[0]<1.0 and visual.visible and not shape.disabled and barrier.collision_layer==1 and barrier.collision_mask==1 and is_equal_approx(material.albedo_color.a,.24),
			"The same visible24 percent alpha field still blocks ordinary layer1 rays and the actual player capsule's movement query (%s)" % size)
		check.call(rig._camera_candidate_clear(pivot,Vector3(0,1.5,-18.5),Vector3(0,2.5,-18.5)) and not _endpoint_clear(stage,Vector3(0,2.5,-18.5),rig.camera.near),
			"Camera pivot/lift rays, near-radius sweep and endpoint query share the explicit energy-field exclusion while ordinary shape queries still collide (%s)" % size)
		# Exact final45s actor arrangement; the normal lock composition must keep
		# the foe as well as the hero, rather than solving only a hero crop.
		hero.position = Vector3(11.65545654,-hero.visual.ground_offset_y,-19.01094055)
		enemy.position = Vector3(10.15527821,0,-23.76930046)
		hero.locked_target = enemy
		rig.yaw = .71166928
		rig.snap()
		for index in range(60):
			rig._physics_process(STEP)
		var hero_projection: Dictionary = _nominal_projection(rig,hero,viewport)
		var foe_projection: Dictionary = _enemy_projection(rig,enemy,viewport)
		var locked_report: Dictionary = rig.framing_report()
		check.call(hero_projection.fits and foe_projection.fits and not locked_report.collision_fit.active and is_equal_approx(rig.camera.fov,56.0),
			"Normal lock framing through the energy field retains both actual hero and foe nominal margins with unchanged FOV (%s)" % size)
		material.albedo_color.a = 1.0
		rig.snap()
		var opaque: Dictionary = rig.framing_report()
		check.call(opaque.camera_transparent_barriers.is_empty() and rig.camera.global_position.z<=-18.949,
			"A misclassified fully opaque alpha-mode barrier keeps camera collision authority (%s)" % size)
		material.albedo_color.a = .24
		material.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
		rig.snap()
		check.call(rig.framing_report().camera_transparent_barriers.is_empty(),"Low color alpha without actual transparent rendering never excludes a marked wall (%s)" % size)
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		barrier.remove_from_group(&"camera_transparent_barriers")
		rig.snap()
		check.call(rig.framing_report().camera_transparent_barriers.is_empty() and rig.camera.global_position.z<=-18.949,
			"An ordinary untagged transparent wall remains camera-solid (%s)" % size)
		barrier.add_to_group(&"camera_transparent_barriers")
		hero.locked_target = null
		hero.position = Vector3(0,-hero.visual.ground_offset_y,-19.80637169)
		rig.yaw = 0.0
		var solid: StaticBody3D = _box(stage,"OpaqueWallBehindField",Vector3(0,2,-17.25),Vector3(40,4,.3),true)
		await world.get_tree().physics_frame
		await world.get_tree().physics_frame
		rig.snap()
		var behind: Dictionary = rig.framing_report()
		var solid_receipt: bool = false
		for receipt: Dictionary in behind.collision_receipts:
			solid_receipt = solid_receipt or String(receipt.collider_id)==str(solid.get_instance_id())
		check.call(solid_receipt and rig.camera.global_position.z<=-17.699 and behind.camera_transparent_barriers.size()==1 and visual.visible and not shape.disabled,
			"A solid wall behind an excluded energy field still clips the camera without hiding or disabling the gameplay barrier (%s)" % size)
		cases.append({"kind":"temporary_energy_gate","viewport":[size.x,size.y],"normal_free":free_report,"normal_locked":locked_report,
			"hero_projection":hero_projection,"enemy_projection":foe_projection,"opaque_negative":opaque,"solid_behind_field":behind,"actor_cast_fraction":actor_motion[0]})
		viewport.free()
	return true

static func run(world: Node3D, check: Callable) -> bool:
	var saved_shake: bool = Session.shake
	Session.shake = false
	var cases: Array[Dictionary] = []
	for size: Vector2i in [Vector2i(1440,900),Vector2i(390,844)]:
		var viewport: SubViewport = SubViewport.new()
		viewport.size = size
		viewport.own_world_3d = true
		world.add_child(viewport)
		var stage: Node3D = Node3D.new()
		viewport.add_child(stage)
		var hero: RunePlayer = RunePlayer.new()
		stage.add_child(hero)
		hero.active = false
		hero.set_physics_process(false)
		var enemy: RuneEnemy = RuneEnemy.new()
		enemy.player = hero
		stage.add_child(enemy)
		enemy.set_physics_process(false)
		enemy.position = Vector3(0,0,-26.15)
		var rig: RuneCamera = RuneCamera.new()
		rig.player = hero
		stage.add_child(rig)
		rig.set_physics_process(false)
		rig.cinematic = false
		# Same dimensions and room-side face as Sanctuary gate0's entrance.
		var gate: StaticBody3D = _box(stage,"RecordedEntranceGate",Vector3(0,2,-18.5),Vector3(40,4,.3),false)
		await world.get_tree().physics_frame
		await world.get_tree().physics_frame
		_prime_approach(hero,rig)
		_enable(gate,true)
		await world.get_tree().physics_frame
		await world.get_tree().physics_frame
		rig._physics_process(STEP)
		var entry: Dictionary = rig.framing_report()
		var fit: Dictionary = entry.collision_fit
		var projection: Dictionary = _nominal_projection(rig,hero,viewport)
		var gate_receipt: bool = false
		for receipt: Dictionary in entry.collision_receipts:
			gate_receipt = gate_receipt or String(receipt.collider_id)==str(gate.get_instance_id())
		check.call(gate_receipt,"Camera cropping fixture confirms the actual entrance gate collider through a production ray receipt (%s)" % size)
		check.call(projection.fits and fit.active and fit.fit and float(fit.lift_m)>0.0 and float(fit.lift_m)<=1.6,
			"A newly closed gate and naturally lagging sprint focus retain the nominal full hero inside combat margins (%s)" % size)
		check.call(rig.camera.global_position.z<=-18.949 and _endpoint_clear(stage,rig.camera.global_position,rig.camera.near) and int(fit.candidate_queries)<=4,
			"Framing lift stays on the gate's room side, keeps near-radius clearance and bounds extra physics queries (%s)" % size)
		var base: Vector3 = hero.global_position+Vector3.UP*hero.visual.ground_offset_y
		var witness: Camera3D = Camera3D.new()
		witness.fov = 56.0
		witness.keep_aspect = Camera3D.KEEP_HEIGHT
		stage.add_child(witness)
		witness.global_position = fit.unadjusted_position
		witness.look_at(base+Vector3.UP*.9)
		var witness_head: Vector2 = witness.unproject_position(base+Vector3.UP*1.82)/Vector2(viewport.size)
		check.call(witness_head.y<0.0,"An actual Camera3D witness proves focus recentering alone cannot fit the recorded short boom (%s)" % size)
		witness.free()
		var stable_follow: Vector3 = rig._follow_position
		for index in range(3):
			rig._physics_process(0.0)
		check.call(absf(rig._follow_position.y-stable_follow.y)<.001,"Repeated zero-time corrected framing does not add the same lift into the follow base again (%s)" % size)
		# Reproduce the final recorded lock arrangement, whose nominal feet were
		# below the frame even though its head and enemy were visible.
		hero.position = Vector3(3.67373395,-hero.visual.ground_offset_y,-21.06045532)
		enemy.position = Vector3(1.11872327,0,-26.15196991)
		hero.locked_target = enemy
		rig.snap()
		var locked_fit: bool = true
		for index in range(45):
			rig._physics_process(STEP)
			locked_fit = locked_fit and bool(_nominal_projection(rig,hero,viewport).fits)
		check.call(locked_fit and is_equal_approx(rig.camera.fov,56.0) and _endpoint_clear(stage,rig.camera.global_position,rig.camera.near),
			"Obstructed lock focus preserves the hero through settled recovery without widening FOV or crossing the gate (%s)" % size)
		var lock_report: Dictionary = rig.framing_report()
		# Put a small overhang above the original camera, outside its pivot ray.
		# A candidate endpoint can be clear while its vertical path is blocked.
		_enable(gate,false)
		var unadjusted: Vector3 = fit.unadjusted_position
		var overhang: StaticBody3D = _box(stage,"LiftPathOverhang",unadjusted+Vector3(.10,.35,0),Vector3(.12,.05,.12),false)
		await world.get_tree().physics_frame
		await world.get_tree().physics_frame
		_prime_approach(hero,rig)
		_enable(gate,true)
		_enable(overhang,true)
		await world.get_tree().physics_frame
		await world.get_tree().physics_frame
		rig._physics_process(STEP)
		var ceiling: Dictionary = rig.framing_report()
		var ceiling_fit: Dictionary = ceiling.collision_fit
		var proposed: Vector3 = ceiling_fit.get("candidate_position",rig.camera.global_position)
		var pivot: Vector3 = hero.global_position+Vector3.UP*(hero.visual.ground_offset_y+1.4)
		var old_position: Vector3 = ceiling_fit.unadjusted_position
		check.call(_ray(stage,pivot,proposed).is_empty() and _ray(stage,old_position,proposed).is_empty() and _endpoint_clear(stage,proposed,rig.camera.near) and _motion_fraction(stage,old_position,proposed,rig.camera.near)<1.0,
			"An off-center overhang blocks the near-radius lift volume despite clear pivot/center rays and candidate endpoint (%s)" % size)
		check.call(not bool(ceiling_fit.fit) and is_zero_approx(float(ceiling_fit.lift_m)) and rig.camera.global_position.distance_to(old_position)<.0001 and _endpoint_clear(stage,rig.camera.global_position,rig.camera.near),
			"A blocked vertical path reports an unfit frame and retains safe wall authority instead of jumping through the overhang (%s)" % size)
		_enable(gate,false)
		_enable(overhang,false)
		hero.locked_target = null
		await world.get_tree().physics_frame
		await world.get_tree().physics_frame
		rig.yaw = .4
		rig.snap()
		var ordinary: Transform3D = rig.camera.global_transform
		rig._physics_process(STEP)
		var free_report: Dictionary = rig.framing_report()
		check.call(rig.camera.global_transform.is_equal_approx(ordinary) and not free_report.collision_fit.active and int(free_report.collision_fit.candidate_queries)==0 and is_equal_approx(rig.yaw,.4),
			"Removing the obstruction restores the ordinary free snap/follow composition, input yaw and zero extra queries (%s)" % size)
		var subjects: Array[Dictionary] = [{"base":Vector3.ZERO,"height":1.82,"radius":.38}]
		check.call(rig._fit_ratio(Vector3.ZERO,Vector3.ZERO,subjects,1.6)>1.0 and rig._fit_ratio(Vector3.ZERO,Vector3.UP,subjects,1.6)>1.0,
			"Coincident and directly overhead look bases cannot be mistaken for a fitting projection (%s)" % size)
		cases.append({"viewport":[size.x,size.y],"entry":entry,"actual_projection":projection,"focus_only_head_uv":[witness_head.x,witness_head.y],"locked_recovery":lock_report,"blocked_lift":ceiling,"free":free_report})
		viewport.free()
	check.call(await _transparent_gate_cases(world,check,cases)==true,"Transparent forcefield policy fixtures finish without altering solid-wall regressions")
	Session.shake = saved_shake
	var report_path: String = ProjectSettings.globalize_path("res://../build/verification/camera-collision/native.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(report_path.get_base_dir())
	var output: FileAccess = FileAccess.open(report_path,FileAccess.WRITE)
	if output!=null:
		output.store_string(JSON.stringify({"scope":"Actual native Camera3D nominal-body projection, production ray collider receipts and near-radius clearance/path queries in isolated gate/overhang fixtures. No gameplay controller, evaluated skin, continuous AV, target hardware or AAA approval",
			"camera_source_sha256":FileAccess.get_sha256("res://scripts/world/camera_rig.gd"),"fixture_source_sha256":FileAccess.get_sha256("res://tests/camera_collision_regressions.gd"),"cases":cases},"\t")+"\n")
		output.close()
	return true
