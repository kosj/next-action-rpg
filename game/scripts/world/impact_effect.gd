class_name RuneImpactEffect
extends Node3D

## Confirmed contact presentation only. No collision/query, damage or actor writes.
const MAX_LIFETIME := 0.68
var duration := 0.44
var elapsed := 0.0
var _valid := false
var _reason := "not_configured"
var _quality := 1
var _strength := "light"
var _blocked := false
var _normal := Vector3.UP
var _direction := Vector3.FORWARD
var _tangent := Vector3.RIGHT
var _bitangent := Vector3.FORWARD
var _core_duration := 0.035
var _core_radius := 0.032
var _sparks: Array[Dictionary] = []
var _debris: Array[Dictionary] = []
var _dust: Array[Dictionary] = []
var _meshes: Dictionary = {}
var _visuals: Dictionary = {}
var _context: Dictionary = {}
var _rng := RandomNumberGenerator.new()
var _triangles := 0

func _ready() -> void:
	add_to_group("impact_effects")
	top_level = true
	set_process(false)

func setup(context: Dictionary, quality: int) -> void:
	_valid = false
	_reason = "invalid_context"
	if not is_inside_tree() or String(context.get("attack_id", "")).is_empty():
		_expire()
		return
	for key: String in ["point", "normal", "direction"]:
		var value: Variant = context.get(key)
		if not value is Vector3 or not value.is_finite():
			_expire()
			return
	if not String(context.get("contact_source", "")) in ["hurtbox_ray", "hurtbox_proxy"]:
		_expire()
		return
	_strength = String(context.get("strength", "light"))
	if not _strength in ["light", "heavy", "charged", "skill"]:
		_expire()
		return
	_context = {"attack_id":String(context.attack_id), "strength":_strength,
		"contact_source":String(context.contact_source), "material":String(context.get("material", "metal")),
		"blocked":bool(context.get("blocked", false)), "killed":bool(context.get("killed", false)),
		"poise_broken":bool(context.get("poise_broken", false)), "target_id":str(context.get("target_id", ""))}
	_quality = clampi(quality, 0, 1)
	_blocked = _context.blocked
	_normal = context.normal.normalized()
	_direction = context.direction.normalized()
	if _direction.length_squared() < 0.001:
		_direction = Vector3.FORWARD
	if _normal.length_squared() < 0.001:
		_normal = -_direction
	if _normal.dot(_direction) > 0.0:
		_normal = -_normal
	_tangent = _normal.cross(Vector3.UP)
	if _tangent.length_squared() < 0.001:
		_tangent = _normal.cross(Vector3.RIGHT)
	_tangent = _tangent.normalized()
	_bitangent = _normal.cross(_tangent).normalized()
	global_transform = Transform3D(Basis.IDENTITY, context.point)
	elapsed = 0.0
	_sparks.clear()
	_debris.clear()
	_dust.clear()
	_rng.seed = ("%s|%s|%.3f|%.3f|%.3f" % [_context.attack_id, _context.target_id, context.point.x, context.point.y, context.point.z]).hash()
	var count := 10
	var energy := 1.0
	if _strength == "heavy":
		count = 16
		energy = 1.35
		duration = 0.52
		_core_radius = 0.052
		_core_duration = 0.045
	elif _strength == "charged":
		count = 24
		energy = 1.7
		duration = 0.62
		_core_radius = 0.075
		_core_duration = 0.052
	elif _strength == "skill":
		count = 18
		energy = 1.45
		duration = 0.56
		_core_radius = 0.062
		_core_duration = 0.045
	else:
		duration = 0.38
		_core_radius = 0.032
		_core_duration = 0.035
	if _blocked:
		count = 14
		energy = 1.0
		duration = 0.40
		_core_radius = 0.040
		_core_duration = 0.038
	if _quality == 0:
		count = mini(count, 10)
	duration = minf(duration, MAX_LIFETIME)
	var bounce := _direction.bounce(_normal).normalized()
	for index in range(count):
		var angle := _rng.randf_range(-PI, PI)
		var spread := _tangent*cos(angle) + _bitangent*sin(angle)
		var velocity := (_normal*0.75 + bounce*0.25 + spread*_rng.randf_range(0.3, 0.85)).normalized()*_rng.randf_range(1.0, 2.4)*energy
		_sparks.append({"velocity":velocity, "life":_rng.randf_range(0.13, 0.29), "birth":float(index)*0.0004,
			"width":_rng.randf_range(0.0035, 0.008)*energy})
	if not _blocked and _strength != "light":
		var debris_count := 6 if _quality == 1 else 3
		for index in range(debris_count):
			var lateral := _tangent*_rng.randf_range(-0.6, 0.6) + _bitangent*_rng.randf_range(-0.5, 0.5)
			_debris.append({"velocity":(_normal*0.6+lateral)*_rng.randf_range(0.8, 1.7)*energy,
				"size":_rng.randf_range(0.009, 0.022), "spin":_rng.randf_range(-13.0, 13.0), "life":_rng.randf_range(0.25, 0.47)})
		for index in range(4 if _quality == 1 else 2):
			_dust.append({"velocity":_normal*0.18+_tangent*_rng.randf_range(-0.22, 0.22)+_bitangent*_rng.randf_range(-0.12, 0.18),
				"size":_rng.randf_range(0.025, 0.055), "life":_rng.randf_range(0.32, 0.50)})
	_ensure_visuals()
	_valid = true
	_reason = "confirmed_contact"
	show()
	_rebuild()
	set_process(true)

func _ensure_visuals() -> void:
	for key: String in ["core", "sparks", "debris", "dust"]:
		if _visuals.has(key):
			continue
		var instance := MeshInstance3D.new()
		instance.name = "Impact" + key.capitalize()
		instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		material.blend_mode = BaseMaterial3D.BLEND_MODE_MIX
		material.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
		material.cull_mode = BaseMaterial3D.CULL_DISABLED
		material.vertex_color_use_as_albedo = true
		material.albedo_color = Color.WHITE
		instance.material_override = material
		var immediate := ImmediateMesh.new()
		instance.mesh = immediate
		add_child(instance)
		_meshes[key] = immediate
		_visuals[key] = instance

func _process(delta: float) -> void:
	if not _valid or not is_finite(delta) or delta <= 0.0:
		return
	elapsed += delta
	if elapsed >= duration:
		_expire()
		return
	_rebuild()

func _position(velocity: Vector3, age: float, gravity: float = 6.0) -> Vector3:
	return _normal*0.006 + velocity*age + Vector3.DOWN*(gravity*age*age*0.5)

func _submit(key: String, vertices: PackedVector3Array, colors: PackedColorArray) -> void:
	var immediate: ImmediateMesh = _meshes[key]
	immediate.clear_surfaces()
	var instance: MeshInstance3D = _visuals[key]
	instance.visible = not vertices.is_empty()
	if vertices.is_empty():
		return
	immediate.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	for index in range(vertices.size()):
		immediate.surface_set_color(colors[index])
		immediate.surface_add_vertex(vertices[index])
	immediate.surface_end()
	_triangles += vertices.size()/3

func _rebuild() -> void:
	_triangles = 0
	var camera := get_viewport().get_camera_3d()
	var view := Vector3(0, 0, 1)
	if camera != null:
		view = (camera.global_position-global_position).normalized()
	var right := view.cross(Vector3.UP).normalized()
	if right.length_squared() < 0.001:
		right = Vector3.RIGHT
	var up := right.cross(view).normalized()
	var vertices := PackedVector3Array()
	var colors := PackedColorArray()
	var tint := Color(1.0, 0.70, 0.24) if not _blocked else Color(0.65, 0.82, 1.0)
	if elapsed < _core_duration:
		var fade := pow(1.0-elapsed/_core_duration, 1.5)
		for index in range(12):
			var angle_a := TAU*float(index)/12.0
			var angle_b := TAU*float(index+1)/12.0
			var radius_a := _core_radius*(1.0 if index%2 == 0 else 0.27)
			var radius_b := _core_radius*(1.0 if (index+1)%2 == 0 else 0.27)
			vertices.append(_normal*0.009)
			colors.append(Color(1.0, 0.96, 0.82, 0.95*fade))
			vertices.append(_normal*0.009+(_tangent*cos(angle_a)+_bitangent*sin(angle_a))*radius_a)
			colors.append(Color(tint, 0.06*fade))
			vertices.append(_normal*0.009+(_tangent*cos(angle_b)+_bitangent*sin(angle_b))*radius_b)
			colors.append(Color(tint, 0.06*fade))
	_submit("core", vertices, colors)
	vertices = PackedVector3Array()
	colors = PackedColorArray()
	for spark in _sparks:
		var age := elapsed-float(spark.birth)
		if age < 0.0 or age >= float(spark.life):
			continue
		var velocity: Vector3 = spark.velocity
		var a := _position(velocity, maxf(0.0, age-0.022))
		var b := _position(velocity, age)
		var axis := (b-a).normalized()
		var side := axis.cross(view).normalized()*float(spark.width)
		if side.length_squared() < 0.0000001:
			side = right*float(spark.width)
		var alpha := pow(1.0-age/float(spark.life), 1.4)*0.88
		for point: Vector3 in [a-side, a+side, b-side, b-side, a+side, b+side]:
			vertices.append(point)
			colors.append(Color(tint, alpha))
	_submit("sparks", vertices, colors)
	vertices = PackedVector3Array()
	colors = PackedColorArray()
	for piece in _debris:
		if elapsed >= float(piece.life):
			continue
		var center := _position(piece.velocity, elapsed, 8.0)
		var size := float(piece.size)
		var u := right.rotated(_normal, float(piece.spin)*elapsed)*size
		var v := up.rotated(_normal, float(piece.spin)*elapsed)*size
		var alpha := 0.9*(1.0-elapsed/float(piece.life))
		for point: Vector3 in [center-u-v*0.5, center+u, center+v]:
			vertices.append(point)
			colors.append(Color(0.22, 0.18, 0.11, alpha))
	_submit("debris", vertices, colors)
	vertices = PackedVector3Array()
	colors = PackedColorArray()
	for puff in _dust:
		if elapsed >= float(puff.life):
			continue
		var center := _position(puff.velocity, elapsed, 0.7)
		var radius := float(puff.size)+elapsed*0.18
		var alpha := sin(PI*clampf(elapsed/float(puff.life), 0.0, 1.0))*0.12
		for index in range(8):
			vertices.append(center)
			colors.append(Color(0.36, 0.28, 0.18, alpha))
			for angle: float in [TAU*float(index)/8.0, TAU*float(index+1)/8.0]:
				vertices.append(center+(right*cos(angle)+up*sin(angle))*radius)
				colors.append(Color(0.36, 0.28, 0.18, 0.0))
	_submit("dust", vertices, colors)

func presentation_report() -> Dictionary:
	return {"valid":_valid, "reason":_reason, "attack_id":String(_context.get("attack_id", "")),
		"style":"blocked_metal" if _blocked else _strength, "quality":_quality,
		"spark_count":_sparks.size(), "spark_budget":24 if _quality == 1 else 10,
		"debris_count":_debris.size(), "dust_count":_dust.size(), "triangles":_triangles,
		"age":elapsed, "duration":duration, "maximum_lifetime":MAX_LIFETIME,
		"core_duration":_core_duration, "core_radius":_core_radius, "contact_source":String(_context.get("contact_source", "")),
		"world_point":global_position, "depth_tested":true, "ring_geometry":false, "gameplay_authority":false}

func _expire() -> void:
	_valid = false
	set_process(false)
	hide()
	if is_inside_tree():
		queue_free()
