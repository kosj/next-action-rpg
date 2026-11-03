extends RefCounted

static func _attack(time: float, epoch: int = 92001) -> Dictionary:
	var data: AttackData = load("res://data/light_1.tres")
	return {"speed":0.0, "attack_id":"light_1", "attack_elapsed":time,
		"attack_duration":data.duration(), "attack_startup":data.startup,
		"attack_active":data.active, "presentation_epoch":epoch}

static func _pose(visual: ActorVisual, snapshot: Dictionary, delta: float) -> void:
	visual.pose(delta, 0.0, -1.0, false, false, false, snapshot)

static func _vertices(trail: BladeTrail) -> PackedVector3Array:
	return trail.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX] if trail.mesh != null else PackedVector3Array()

static func _start(visual: ActorVisual) -> void:
	visual.blade_trail.reset()
	_pose(visual, _attack(0.14), 1.0/60.0)
	_pose(visual, _attack(0.17), 0.03)

static func run(world: Node3D, check: Callable) -> bool:
	var wrapper := Node3D.new()
	world.add_child(wrapper)
	wrapper.position = Vector3(4,0,-4)
	wrapper.rotation.y = 0.35
	wrapper.scale = Vector3.ONE*1.25
	var visual := ActorVisual.new()
	visual.setup("hero")
	wrapper.add_child(visual)
	var mounted := visual.use_production_profile("hero")
	check.call(mounted.ok and is_instance_valid(visual.blade_trail), "Actual skinned hero mounts a visual-only blade ribbon")
	if not mounted.ok:
		wrapper.free()
		return false
	var trail := visual.blade_trail
	var grip := visual.rig_weapon.find_child("GripOrigin",true,false) as Node3D
	var tip := visual.rig_weapon.find_child("BladeTip",true,false) as Node3D
	var data: AttackData = load("res://data/light_1.tres")
	_pose(visual, _attack(data.startup-0.001), 1.0/60.0)
	check.call(not trail.visible and trail.presentation_report().samples == 0, "Preparation cannot emit a speculative blade trail")
	var first := _attack(data.startup+0.001)
	var original := first.duplicate(true)
	_pose(visual, first, 1.0/60.0)
	var old_base := grip.global_position.lerp(tip.global_position,0.18)
	wrapper.position += Vector3(0.6,0,0.2)
	wrapper.rotation.y += 0.4
	_pose(visual, _attack(data.startup+0.025), 0.024)
	var vertices := _vertices(trail)
	var tip_matches := trail.visible and vertices.size()==6 and vertices[-1].distance_to(tip.global_position)<0.0001
	var history_world_space := vertices.size()==6 and vertices[0].distance_to(old_base)<0.0001 and trail.global_transform.is_equal_approx(Transform3D.IDENTITY)
	check.call(tip_matches, "The ribbon ends at this exact displayed blade tip with external actor scale preserved")
	check.call(history_world_space, "Past blade samples remain in world space when the actor translates and rotates")
	var light_spine: PackedVector3Array = trail.mesh.surface_get_arrays(1)[Mesh.ARRAY_VERTEX]
	var light_colors: PackedColorArray = trail.mesh.surface_get_arrays(1)[Mesh.ARRAY_COLOR]
	check.call(trail.mesh.get_surface_count()==2 and light_spine[-1].distance_to(tip.global_position)<0.0001 and light_colors[-1].a>0.8,
		"The light slash has a bright narrow spine at the actual tip rather than an invented extended arc")
	check.call(first==original, "Blade presentation only reads the authoritative action snapshot")
	var frozen_mesh := trail.mesh
	var frozen_report := trail.presentation_report()
	for index in range(4):
		_pose(visual, _attack(data.startup+0.025), 0.0)
	await world.get_tree().process_frame
	await world.get_tree().process_frame
	check.call(trail.mesh==frozen_mesh and trail.presentation_report()==frozen_report, "Hit pause freezes the visible ribbon and sample ages without automatic playback")
	frozen_mesh = null
	_pose(visual, _attack(data.startup+data.active), 0.001)
	check.call(trail.presentation_report().samples==frozen_report.samples, "The exact active-end boundary stops emission rather than extending the damage window visually")
	_pose(visual, {"speed":0.0,"presentation_epoch":92001}, BladeTrail.LIFETIME+0.001)
	check.call(not trail.visible and trail.mesh==null, "Recovery history fades away within its bounded presentation lifetime")
	for stop in [{"stagger":0.1,"hit_elapsed":0.05,"hit_duration":0.15},
		{"dodge_remaining":0.1,"dodge_elapsed":0.22,"dodge_duration":0.32},
		{"parry_remaining":0.1,"parry_elapsed":0.12,"parry_duration":0.22},
		{"dead":true,"death_elapsed":0.1,"death_duration":1.1}]:
		_start(visual)
		var state: Dictionary = {"speed":0.0,"presentation_epoch":92001}
		state.merge(stop)
		_pose(visual,state,1.0/60.0)
		check.call(not trail.visible and trail.presentation_report().samples==0, "Priority interruption clears old blade geometry: %s" % str(stop.keys()[0]))
	_start(visual)
	_pose(visual,_attack(0.18,92002),1.0/60.0)
	check.call(not trail.visible and trail.presentation_report().samples==1, "Checkpoint epoch discards history before sampling the new life")
	_start(visual)
	_pose(visual,_attack(0.22),0.0)
	check.call(not trail.visible and trail.presentation_report().samples==0, "An explicit zero-delta art seek never draws a false swept path")
	_start(visual)
	_pose(visual,_attack(0.14),1.0/60.0)
	check.call(not trail.visible and trail.presentation_report().samples==1, "Restarting the same action cannot connect to the previous swing")
	_start(visual)
	wrapper.position += Vector3(15,0,0)
	_pose(visual,_attack(0.19),1.0/60.0)
	check.call(not trail.visible and trail.presentation_report().samples==1, "A teleport cannot produce a room-spanning slash")
	trail.reset()
	for index in range(60):
		_pose(visual,_attack(data.startup+0.001+index*0.001),0.001)
	var high_rate_geometry := trail.presentation_report()
	check.call(trail.presentation_report().samples<=BladeTrail.MAX_SAMPLES and trail.presentation_report().triangles<64 and trail.get_child_count()==0, "High-rate light presentation stays below64triangles with two reusable layers and no physics objects")
	_start(visual)
	var oversized := _attack(0.19)
	oversized["attack_reach"] = 100000.0
	_pose(visual, oversized, 0.02)
	var physical_vertices := _vertices(trail)
	check.call(absf(physical_vertices[-1].distance_to(physical_vertices[-3])-grip.global_position.distance_to(tip.global_position)*0.82) < 0.0001, "Even a generous damage reach cannot stretch the visual ribbon beyond its real blade markers")
	var charged: AttackData = load("res://data/charged_heavy.tres")
	trail.reset()
	var historical_blades: Array[Dictionary] = []
	for index in range(16):
		var charged_snapshot: Dictionary = {"speed":0.0,"presentation_epoch":92003,"attack_id":"charged_heavy",
			"attack_elapsed":charged.startup+.001+index*.004,"attack_duration":charged.duration(),"attack_startup":charged.startup,"attack_active":charged.active}
		_pose(visual,charged_snapshot,.004)
		historical_blades.append({"base":grip.global_position.lerp(tip.global_position,.18),"tip":tip.global_position})
	var contained: bool = true
	var cool_band: bool = false
	var warm_band: bool = false
	for surface in range(trail.mesh.get_surface_count()):
		var arrays: Array = trail.mesh.surface_get_arrays(surface)
		var fan_vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		for vertex: Vector3 in fan_vertices:
			var nearest: float = INF
			for sample: Dictionary in historical_blades:
				nearest = minf(nearest,vertex.distance_to(Geometry3D.get_closest_point_to_segment(vertex,sample.base,sample.tip)))
			contained = contained and nearest<0.0001
		if surface==0:
			var fan_colors: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
			for color: Color in fan_colors:
				cool_band = cool_band or color.b>color.r+.2
				warm_band = warm_band or color.r>color.b+.2
	check.call(contained and cool_band and warm_band and trail.presentation_report().triangles<=120 and trail.mesh.get_surface_count()==2,
		"The broad charged fan contains cool/warm radial bands entirely on sixteen recorded real blade segments within120triangles")
	var charged_frozen_body: Array = trail.mesh.surface_get_arrays(0)
	var charged_frozen_spine: Array = trail.mesh.surface_get_arrays(1)
	var held_snapshot: Dictionary = {"speed":0.0,"presentation_epoch":92003,"attack_id":"charged_heavy",
		"attack_elapsed":charged.startup+.061,"attack_duration":charged.duration(),"attack_startup":charged.startup,"attack_active":charged.active}
	_pose(visual,held_snapshot,0.0)
	check.call(trail.mesh.surface_get_arrays(0)==charged_frozen_body and trail.mesh.surface_get_arrays(1)==charged_frozen_spine,
		"Hitstop freezes every charged fan band and hot spine vertex/color without adding future samples")
	var output := ProjectSettings.globalize_path("res://../build/verification/character-polish/blade-trail.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(output.get_base_dir())
	var file := FileAccess.open(output,FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify({"scope":"Actual blade-marker ribbon timing, world-space history and lifetime; no AAA or target GPU approval",
			"source_sha256":FileAccess.get_sha256("res://scripts/actors/blade_trail.gd"),
			"bounded_geometry":high_rate_geometry,"same_frame_tip":tip_matches,
			"world_space_history":history_world_space,"external_scale":wrapper.scale.x},"\t")+"\n")
		file.close()
	wrapper.free()
	return true
