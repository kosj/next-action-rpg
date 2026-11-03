class_name RuneSwordWave
extends Node3D

## A translated, solid crescent. The rendered prism vertices also own its
## collision volumes; there is no wider invisible fan or endpoint-only query.
const MAX_ACTIVE := 6
const MAX_TARGETS := 32
const FADE_SECONDS := 0.10
const HEIGHT := 0.22
const DEPTH := 0.24
const CURVATURE := 0.34
const SPAWN_OFFSET := 0.6
const ENERGY_SHADER: Shader = preload("res://assets/shaders/sword_wave.gdshader")
var _source: CharacterBody3D
var _attack: CombatStrike
var _forward := Vector3.FORWARD
var _spawn_origin := Vector3.ZERO
var _source_origin := Vector3.ZERO
var _reach := 0.0
var _max_travel := 0.0
var _width := 0.0
var _speed := 0.0
var _damage_scale := 0.0
var _travel := 0.0
var _age := 0.0
var _fade := 0.0
var _fading := false
var _valid := false
var _reason := "not_configured"
var _quality := 0
var _source_has_dead := false
var _source_has_active := false
var _source_has_epoch := false
var _source_epoch := 0
var _segments: Array[Dictionary] = []
var _materials: Array[ShaderMaterial] = []
var _triangles := 0
var _confirmed_hits := 0

func _ready() -> void:
	add_to_group("sword_waves")
	top_level = true
	set_physics_process(false)

func setup(source: CharacterBody3D, attack: CombatStrike, forward: Vector3, reach: float, width: float, speed: float, damage_scale: float) -> void:
	if not is_inside_tree() or not is_instance_valid(source) or not source.is_inside_tree() or attack == null or attack.source != source:
		_expire("invalid_owner")
		return
	if not forward.is_finite() or Vector2(forward.x,forward.z).length_squared() < 0.000001:
		_expire("invalid_direction")
		return
	for value: float in [reach,width,speed,damage_scale]:
		if not is_finite(value) or value <= 0.0:
			_expire("invalid_dimensions")
			return
	if reach <= SPAWN_OFFSET:
		_expire("invalid_reach")
		return
	_source = source
	_attack = attack
	_forward = Vector3(forward.x,0.0,forward.z).normalized()
	_reach = reach
	_max_travel = reach-SPAWN_OFFSET
	_width = width
	_speed = speed
	_damage_scale = damage_scale
	_quality = clampi(Session.quality,0,1)
	_source_origin = source.global_position
	_spawn_origin = _source_origin+Vector3.UP*1.05+_forward*SPAWN_OFFSET
	global_transform = Transform3D(Basis(Vector3.UP,atan2(-_forward.x,-_forward.z)),_spawn_origin)
	for property: Dictionary in source.get_property_list():
		if property.name == "dead":
			_source_has_dead = true
		elif property.name == "active":
			_source_has_active = true
		elif property.name == "presentation_epoch":
			_source_has_epoch = true
	if _source_has_epoch:
		_source_epoch = int(source.get("presentation_epoch"))
	_source.tree_exiting.connect(_owner_exiting)
	_build_crescent()
	_valid = true
	_reason = "flying"
	# Count only live nodes: queued deletions cannot bypass the same-frame cap.
	var active: Array[Node] = []
	for wave in get_tree().get_nodes_in_group("sword_waves"):
		if not wave.is_queued_for_deletion():
			active.append(wave)
	while active.size() > MAX_ACTIVE:
		var oldest := active.pop_front() as Node
		if oldest.has_method("_expire"):
			oldest.call("_expire","scene_cap")
		else:
			oldest.queue_free()
	set_physics_process(true)

func _owner_exiting() -> void:
	_expire("owner_exited")

func cancel() -> void:
	_expire("encounter_reset")

func _exit_tree() -> void:
	if is_instance_valid(_source) and _source.tree_exiting.is_connected(_owner_exiting):
		_source.tree_exiting.disconnect(_owner_exiting)
	_attack = null
	_source = null

func _expire(reason: String) -> void:
	_valid = false
	_reason = reason
	set_physics_process(false)
	queue_free()

func _physics_process(delta: float) -> void:
	if not _valid or not is_finite(delta) or delta <= 0.0:
		return
	if not is_instance_valid(_source) or not _source.is_inside_tree() or (_source_has_dead and bool(_source.get("dead"))):
		_expire("owner_unavailable")
		return
	if _source_has_active and not bool(_source.get("active")):
		_expire("owner_inactive")
		return
	if _source_has_epoch and int(_source.get("presentation_epoch")) != _source_epoch:
		_expire("owner_restored")
		return
	_age += delta
	for material in _materials:
		material.set_shader_parameter("wave_age",_age)
	if _fading:
		_fade += delta
	else:
		var distance := minf(_speed*delta,maxf(0.0,_max_travel-_travel))
		var resolved := _advance(distance)
		if resolved < distance-0.000001 or _travel >= _max_travel-0.000001:
			_fading = true
			_fade += maxf(0.0,delta-resolved/_speed)
	if _fading:
		var alpha := clampf(1.0-_fade/FADE_SECONDS,0.0,1.0)
		for material in _materials:
			material.set_shader_parameter("wave_fade",alpha)
		if _fade >= FADE_SECONDS:
			_expire(_reason if _reason in ["wall_stopped","wall_initial_overlap"] else "travel_complete")
	# Defensive finite bound, independent of whether a strike remains equipped.
	if _age > _max_travel/_speed+FADE_SECONDS+0.05:
		_expire("lifetime")

func _shape_query(shape: Shape3D, origin: Vector3, mask: int) -> PhysicsShapeQueryParameters3D:
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = shape
	query.transform = Transform3D(global_basis,origin)
	query.collision_mask = mask
	query.margin = 0.0
	query.exclude = [_source.get_rid()]
	return query

func _advance(distance: float) -> float:
	var space := get_world_3d().direct_space_state
	var start := global_position
	var safe := 1.0
	# cast_motion deliberately ignores initial overlaps, so test those first.
	for segment in _segments:
		var query := _shape_query(segment.shape,start,1)
		if not space.intersect_shape(query,1).is_empty():
			_reason = "wall_initial_overlap"
			_fading = true
			return 0.0
		query.motion = _forward*distance
		var fractions := space.cast_motion(query)
		if fractions.size() >= 2:
			safe = minf(safe,float(fractions[0]))
	var travel := distance*safe
	if safe < 1.0:
		_reason = "wall_stopped"
		_fading = true
	# For each convex prism, a translational sweep is exactly the convex hull
	# of its starting and ending vertices. intersect_shape itself ignores motion.
	for segment in _segments:
		if _confirmed_hits >= MAX_TARGETS:
			break
		var points: PackedVector3Array = segment.points.duplicate()
		var displacement := Vector3.FORWARD*travel
		for point: Vector3 in segment.points:
			points.append(point+displacement)
		var swept := segment.swept as ConvexPolygonShape3D
		swept.points = points
		var query := _shape_query(swept,start,4)
		for result in space.intersect_shape(query,MAX_TARGETS):
			if _confirmed_hits >= MAX_TARGETS:
				break
			var target := result.collider as Node3D
			if not is_instance_valid(target) or not target.has_method("receive_hit") or _attack.hit_ids.has(target.get_instance_id()):
				continue
			var context := _contact_context(target,start,travel,segment)
			# Resolve blockers before sharing the melee ledger. A stopped wave
			# never registers targets from its untravelled interval.
			if _attack.register_target(target.get_instance_id()):
				_confirmed_hits += 1
				target.call("receive_hit",_attack.data.damage*_attack.multiplier*_damage_scale,_attack.data.poise*_attack.multiplier*_damage_scale,_spawn_origin-_forward,_attack.data.parryable,context)
				if not is_instance_valid(_source) or not _source.is_inside_tree() or is_queued_for_deletion() or _attack == null:
					return travel
	_travel += travel
	global_position = start+_forward*travel
	return travel

func _contact_context(target: Node3D, start: Vector3, travel: float, segment: Dictionary) -> Dictionary:
	var center := target.global_position+Vector3.UP*1.05
	for child in target.get_children():
		if child is CollisionShape3D and not child.disabled and child.shape != null:
			center = child.global_position
			break
	var local := global_basis.inverse()*(center-start)
	var x := clampf(local.x,float(segment.left),float(segment.right))
	var blend := inverse_lerp(float(segment.left),float(segment.right),x)
	var front := lerpf(float(segment.front_left),float(segment.front_right),blend)
	var y := clampf(local.y,-HEIGHT*0.5,HEIGHT*0.5)
	var ray_start := start+global_basis*Vector3(x,y,front+DEPTH)
	var ray_end := start+global_basis*Vector3(x,y,front-travel)
	var point := start+global_basis*Vector3(x,y,clampf(local.z,front-travel,front+DEPTH))
	var normal := -_forward
	var contact_source := "hurtbox_proxy"
	var ray := PhysicsRayQueryParameters3D.create(ray_start,ray_end,4)
	ray.exclude = [_source.get_rid()]
	var surface := get_world_3d().direct_space_state.intersect_ray(ray)
	if not surface.is_empty() and surface.collider == target and Vector3(surface.normal).length_squared() > 0.000001:
		point = surface.position
		normal = Vector3(surface.normal).normalized()
		contact_source = "hurtbox_ray"
	var strength := _attack.data.impact_strength
	if strength.is_empty():
		strength = "heavy" if _attack.presentation_id == &"heavy" else "light"
	return {"attack_id":String(_attack.presentation_id),"attack_instance_id":_attack.attack_instance_id,
		"source":"player" if (_source.collision_layer&2) != 0 else "enemy",
		"strength":strength,"point":point,"normal":normal,"direction":_forward,
		"source_position":_source_origin,"target_position":target.global_position,
		"contact_source":contact_source,"material":"metal","target_id":target.get_instance_id(),
		"sword_wave":true,"wave_origin":_spawn_origin,"wave_travel_m":_travel+travel,
		"wave_sweep_start_m":_travel,"wave_sweep_end_m":_travel+travel,"wave_age_s":_age,
		"attack_elapsed":_attack.elapsed,"contact_phase":-1.0}

func _material(layer: int) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = ENERGY_SHADER
	material.render_priority = 1 if layer == 1 else 0
	material.set_shader_parameter("wave_width",_width)
	material.set_shader_parameter("curvature",CURVATURE)
	material.set_shader_parameter("prism_depth",DEPTH)
	material.set_shader_parameter("wave_age",_age)
	material.set_shader_parameter("wave_fade",1.0)
	material.set_shader_parameter("energy_layer",layer)
	_materials.append(material)
	return material

func _triangle(vertices: PackedVector3Array, a: Vector3, b: Vector3, c: Vector3) -> void:
	vertices.append(a)
	vertices.append(b)
	vertices.append(c)
	_triangles += 1

func _quad(vertices: PackedVector3Array, a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
	_triangle(vertices,a,b,c)
	_triangle(vertices,a,c,d)

func _mesh(vertices: PackedVector3Array, material: ShaderMaterial, label: String) -> void:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.material_override = material
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(instance)

func _build_crescent() -> void:
	var body := PackedVector3Array()
	var core := PackedVector3Array()
	var trail := PackedVector3Array()
	var count := 8 if _quality == 0 else 6
	for index in range(count):
		var x0 := _width*(float(index)/count-0.5)
		var x1 := _width*(float(index+1)/count-0.5)
		var z0 := CURVATURE*pow(2.0*x0/_width,2.0)
		var z1 := CURVATURE*pow(2.0*x1/_width,2.0)
		var h := HEIGHT*0.5
		var points := PackedVector3Array([Vector3(x0,-h,z0),Vector3(x1,-h,z1),Vector3(x1,h,z1),Vector3(x0,h,z0),Vector3(x0,-h,z0+DEPTH),Vector3(x1,-h,z1+DEPTH),Vector3(x1,h,z1+DEPTH),Vector3(x0,h,z0+DEPTH)])
		var shape := ConvexPolygonShape3D.new()
		shape.margin = 0.0
		shape.points = points
		var swept := ConvexPolygonShape3D.new()
		swept.margin = 0.0
		_segments.append({"shape":shape,"swept":swept,"points":points,"left":x0,"right":x1,"front_left":z0,"front_right":z1})
		# Adjacent physics prisms share interior caps. Only the union boundary
		# belongs in the transparent mesh, otherwise additive caps show seams.
		var faces := [[0,1,2,3],[5,4,7,6],[3,2,6,7],[4,5,1,0]]
		if index == 0:
			faces.append([4,0,3,7])
		if index == count-1:
			faces.append([1,5,6,2])
		for face in faces:
			_quad(body,points[face[0]],points[face[1]],points[face[2]],points[face[3]])
		# Thin hot face embedded at the leading edge, with a shallow top ridge.
		_quad(core,Vector3(x0,-0.025,z0),Vector3(x1,-0.025,z1),Vector3(x1,0.025,z1),Vector3(x0,0.025,z0))
		_quad(core,Vector3(x0,0.025,z0),Vector3(x1,0.025,z1),Vector3(x1,0.025,z1+0.09),Vector3(x0,0.025,z0+0.09))
		_quad(trail,Vector3(x0,0,z0+DEPTH),Vector3(x1,0,z1+DEPTH),Vector3(x1,0,z1+DEPTH+0.32),Vector3(x0,0,z0+DEPTH+0.32))
	_mesh(body,_material(0),"SolidCrescent")
	_mesh(core,_material(1),"HotLeadingEdge")
	_mesh(trail,_material(2),"ShortWake")

func presentation_report() -> Dictionary:
	return {"valid":_valid,"reason":_reason,"quality":_quality,"triangles":_triangles,
		"travel_m":_travel,"reach_m":_reach,"max_center_travel_m":_max_travel,"width_m":_width,"speed_m_s":_speed,
		"age_s":_age,"fading":_fading,"collision_segments":_segments.size(),
		"collision_geometry":"rendered_convex_prisms","confirmed_targets":_confirmed_hits,"attack_instance_id":_attack.attack_instance_id if _attack != null else 0}
