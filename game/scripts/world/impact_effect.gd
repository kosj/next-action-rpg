class_name RuneImpactEffect
extends Node3D

## Confirmed contact presentation only. No collision/query, damage or actor writes.
const MAX_LIFETIME := 0.68
var duration := 0.44
var elapsed := 0.0
var _valid := false
var _reason := "not_configured"
var _quality := 0
var _strength := "light"
var _skill_variant := ""
var _skill_tint := Color(1.0, 0.70, 0.24)
var _blocked := false
var _normal := Vector3.UP
var _direction := Vector3.FORWARD
var _tangent := Vector3.RIGHT
var _bitangent := Vector3.FORWARD
var _core_duration := 0.035
var _core_flash_duration := 0.016
var _core_radius := 0.032
var _core_edge_alpha := 0.06
var _core_axis := Vector3.RIGHT
var _core_side := Vector3.UP
var _core_plane_normal := Vector3.BACK
var _core_basis_source := "view_plane_fallback"
var _cut_axis := Vector3.RIGHT
var _cut_side := Vector3.UP
var _cut_plane_normal := Vector3.BACK
var _cut_basis_source := "contact_plane_fallback"
var _blade_length := 0.0
var _cut_duration := 0.085
var _cut_length := 0.26
var _cut_width := 0.018
var _cut_visible := false
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
	_skill_variant = String(context.attack_id) if _strength == "skill" and String(context.attack_id) in ["skill_1", "skill_2", "skill_3"] else ""
	_skill_tint = Color("65e8ff") if _skill_variant == "skill_1" else (Color("bd8dff") if _skill_variant == "skill_2" else Color("ffd074"))
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
	_resolve_cut_basis(context)
	global_transform = Transform3D(Basis.IDENTITY, context.point)
	elapsed = 0.0
	_sparks.clear()
	_debris.clear()
	_dust.clear()
	_rng.seed = ("%s|%s|%.3f|%.3f|%.3f" % [_context.attack_id, _context.target_id, context.point.x, context.point.y, context.point.z]).hash()
	var count := 8
	var energy := 1.0
	_core_flash_duration = 0.016
	_core_edge_alpha = 0.12
	_cut_duration = 0.11
	_cut_length = 0.42
	_cut_width = 0.035
	if _strength == "heavy":
		count = 18
		energy = 1.4
		duration = 0.52
		_core_radius = 0.09
		_core_duration = 0.085
		_core_flash_duration = 0.022
		_core_edge_alpha = 0.18
		_cut_duration = 0.17
		_cut_length = 0.85
		_cut_width = 0.07
	elif _strength == "charged":
		count = 24
		energy = 1.75
		duration = 0.64
		# A local white flash gives way to a cooler ember afterglow. This stays
		# attached to the confirmed point; no screen flash or speculative trail.
		_core_radius = 0.15
		_core_duration = 0.11
		_core_flash_duration = 0.03
		_core_edge_alpha = 0.26
		_cut_duration = 0.20
		_cut_length = minf(1.14,_blade_length*0.96) if _blade_length>0.0 else 0.52
		_cut_width = 0.095
	elif _strength == "skill":
		count = 22
		energy = 1.5
		duration = 0.56
		_core_radius = 0.10
		_core_duration = 0.095
		_core_flash_duration = 0.025
		_core_edge_alpha = 0.20
		_cut_duration = 0.18
		_cut_length = 0.95
		_cut_width = 0.08
	else:
		duration = 0.38
		_core_radius = 0.05
		_core_duration = 0.06
	if _skill_variant == "skill_3":
		count = 26
		energy = 1.8
		duration = 0.64
		_core_radius = 0.15
		_core_duration = 0.11
		_cut_length = 1.10
		_cut_width = 0.10
	elif _skill_variant == "skill_1":
		count = 16
		_cut_length = 0.82
		_core_radius = 0.075
	if _blocked:
		count = 14
		energy = 1.0
		duration = 0.40
		_core_radius = 0.045
		_core_duration = 0.05
		_core_flash_duration = 0.012
		_core_edge_alpha = 0.10
		_cut_duration = 0.085
		_cut_length = 0.28
		_cut_width = 0.025
	# The actual Game/UI contract is0=balanced,1=performance. Keep the
	# performance profile cheaper even though the legacy effect inverted it.
	if _quality == 1:
		count = mini(count, 10)
	duration = minf(duration, MAX_LIFETIME)
	var bounce := _direction.bounce(_normal).normalized()
	for index in range(count):
		var angle := _rng.randf_range(-PI, PI)
		var spread := _cut_axis*cos(angle)*0.35 + _cut_side*sin(angle)
		# A few hot flecks lead the cut, with the remainder breaking out of the
		# struck surface. Count stays below the old burst; direction carries force.
		var lead := 1.05 if index<6 and not _blocked else 0.42
		var velocity := (_normal*0.65+bounce*0.15+_cut_axis*lead+spread*_rng.randf_range(0.15,0.65)).normalized()*_rng.randf_range(1.4,3.3)*energy
		_sparks.append({"velocity":velocity, "life":_rng.randf_range(0.15,0.32), "birth":float(index)*0.0004,
			"width":_rng.randf_range(0.005,0.011)*energy,
			"trail_s":0.038 if _strength=="charged" and not _blocked else 0.026})
	if not _blocked and _strength != "light":
		var debris_count := (8 if _strength=="charged" else 6) if _quality==0 else 3
		for index in range(debris_count):
			var lateral := _tangent*_rng.randf_range(-0.6, 0.6) + _bitangent*_rng.randf_range(-0.5, 0.5)
			_debris.append({"velocity":(_normal*0.65+lateral+_cut_axis*0.35)*_rng.randf_range(1.1,2.2)*energy,
				"size":_rng.randf_range(0.015,0.035), "spin":_rng.randf_range(-17.0,17.0), "life":_rng.randf_range(0.25,0.47)})
		# These are contact motes at the struck metal, not a ground explosion.
		# A real ground response requires a separately confirmed ground context.
		for index in range(3 if _quality == 0 else 1):
			_dust.append({"velocity":_normal*0.18+_cut_axis*0.12+_cut_side*_rng.randf_range(-0.10,0.10),
				"size":_rng.randf_range(0.035,0.06),"life":_rng.randf_range(0.26,0.40)})
	_ensure_visuals()
	_valid = true
	_reason = "confirmed_contact"
	show()
	_rebuild()
	set_process(true)

func _resolve_cut_basis(context: Dictionary) -> void:
	_cut_axis = _tangent
	_cut_side = _bitangent
	_cut_plane_normal = _normal
	_cut_basis_source = "contact_plane_fallback"
	_blade_length = 0.0
	var grip: Variant = context.get("contact_blade_grip")
	var tip: Variant = context.get("contact_blade_tip")
	if not grip is Vector3 or not tip is Vector3 or not grip.is_finite() or not tip.is_finite():
		return
	var blade: Vector3 = tip-grip
	if blade.length()<0.05 or blade.length()>5.0:
		return
	_blade_length = blade.length()
	var blade_axis := blade.normalized()
	var motion: Variant = context.get("contact_blade_motion")
	if motion is Vector3 and motion.is_finite() and motion.length_squared()>0.000001:
		_cut_axis = motion.normalized()
		_cut_plane_normal = blade_axis.cross(_cut_axis).normalized()
		if _cut_plane_normal.length_squared()>0.001:
			if _cut_plane_normal.dot(_normal)<0.0:
				_cut_plane_normal = -_cut_plane_normal
			_cut_side = _cut_plane_normal.cross(_cut_axis).normalized()
			_cut_basis_source = "confirmed_blade_motion"
			return
	# A static blade and surface normal define a plane, not the direction of
	# travel. Label this fallback rather than inventing an authored cut velocity.
	_cut_axis = _normal.cross(blade_axis).normalized()
	if _cut_axis.length_squared()<0.001:
		_cut_axis = _tangent
	_cut_side = _normal.cross(_cut_axis).normalized()
	_cut_plane_normal = _normal
	_cut_basis_source = "confirmed_blade_surface_plane"

func _ensure_visuals() -> void:
	for key: String in ["core", "cut", "sparks", "debris", "dust"]:
		if _visuals.has(key):
			continue
		var instance := MeshInstance3D.new()
		instance.name = "Impact" + key.capitalize()
		instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		material.blend_mode = BaseMaterial3D.BLEND_MODE_ADD if key=="core" else BaseMaterial3D.BLEND_MODE_MIX
		material.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
		material.cull_mode = BaseMaterial3D.CULL_DISABLED
		material.vertex_color_use_as_albedo = true
		material.albedo_color = Color.WHITE
		instance.material_override = material
		# Keep the tiny contact core readable from the view without rotating the
		# physical cut. Its reusable ArrayMesh also exposes its actual vertices
		# for independent projection/radius checks. The other groups stay batched.
		var mesh: Mesh = ArrayMesh.new() if key=="core" else ImmediateMesh.new()
		instance.mesh = mesh
		add_child(instance)
		_meshes[key] = mesh
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
	var instance: MeshInstance3D = _visuals[key]
	instance.visible = not vertices.is_empty()
	if key=="core":
		var core: ArrayMesh = _meshes[key]
		core.clear_surfaces()
		if vertices.is_empty():
			return
		var arrays: Array = []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = vertices
		arrays[Mesh.ARRAY_COLOR] = colors
		core.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	else:
		var immediate: ImmediateMesh = _meshes[key]
		immediate.clear_surfaces()
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
	_cut_visible = false
	var camera := get_viewport().get_camera_3d()
	var view := Vector3(0, 0, 1)
	if camera != null:
		view = (camera.global_position-global_position).normalized()
	if view.length_squared()<0.001:
		view = camera.global_basis.z if camera!=null else Vector3.BACK
	var right := view.cross(Vector3.UP).normalized()
	if right.length_squared() < 0.001:
		right = Vector3.RIGHT
	var up := right.cross(view).normalized()
	var vertices := PackedVector3Array()
	var colors := PackedColorArray()
	var tint := (_skill_tint if not _skill_variant.is_empty() else Color(1.0, 0.70, 0.24)) if not _blocked else Color(0.65, 0.82, 1.0)
	# Only the brief point core faces the camera. Project the confirmed cut
	# direction so its orientation still follows contact; a view-parallel cut
	# has no meaningful screen direction and uses the camera's right vector.
	_core_plane_normal = view
	_core_axis = _cut_axis-view*_cut_axis.dot(view)
	_core_basis_source = "projected_confirmed_cut"
	if _core_axis.length_squared()<0.0001:
		_core_axis = camera.global_basis.x if camera!=null else right
		_core_axis = _core_axis-view*_core_axis.dot(view)
		_core_basis_source = "view_plane_fallback"
	_core_axis = _core_axis.normalized()
	_core_side = view.cross(_core_axis).normalized()
	if elapsed < _core_duration:
		var flash := elapsed<_core_flash_duration
		var phase := clampf(elapsed/_core_flash_duration if flash else (elapsed-_core_flash_duration)/(_core_duration-_core_flash_duration),0.0,1.0)
		var fade := 1.0-0.75*phase if flash else 0.25*pow(1.0-phase,1.35)
		var radius := _core_radius*((0.8+0.2*phase) if flash else (1.0-0.22*phase))
		var ember := tint if flash or not _skill_variant.is_empty() else Color(0.28,0.76,1.0)
		var white := Color(1.0,0.97,0.84) if flash else Color(0.65,0.92,1.0)
		for index in range(12):
			var angle_a := TAU*float(index)/12.0
			var angle_b := TAU*float(index+1)/12.0
			var radius_a := radius*(1.0 if index%2 == 0 else 0.27)
			var radius_b := radius*(1.0 if (index+1)%2 == 0 else 0.27)
			vertices.append(_normal*0.009)
			colors.append(Color(white,0.95*fade))
			vertices.append(_normal*0.009+(_core_axis*cos(angle_a)+_core_side*sin(angle_a)*0.48)*radius_a)
			colors.append(Color(ember,_core_edge_alpha*fade))
			vertices.append(_normal*0.009+(_core_axis*cos(angle_b)+_core_side*sin(angle_b)*0.48)*radius_b)
			colors.append(Color(ember,_core_edge_alpha*fade))
	_submit("core", vertices, colors)
	vertices = PackedVector3Array()
	colors = PackedColorArray()
	if elapsed<_cut_duration:
		var age_fraction := elapsed/_cut_duration
		var grow := maxf(0.32,minf(1.0,elapsed/0.018))
		var segments := (10 if _strength in ["charged","skill"] else 8) if _quality==0 else (5 if _strength in ["charged","skill"] else 4)
		# The contact ribbon is a local emitted slash, not a second weapon path.
		# Its broad cool fan, warm body and narrow hot spine share the actual
		# confirmed cut plane and remain depth-tested at the real surface point.
		for layer in range(3):
			var fade := pow(1.0-age_fraction,1.35 if layer==0 else (1.7 if layer==1 else 2.1))
			for index in range(segments):
				for corner in [0,1,2,2,1,3]:
					var fraction := float(index+(1 if corner>=2 else 0))/segments
					var center := _normal*0.014+_cut_axis*((fraction-0.28)*_cut_length*grow)+_cut_side*(sin(PI*fraction)*_cut_width*0.9)
					var width := _cut_width*(1.45 if layer==0 else (0.55 if layer==1 else 0.14))*sin(PI*fraction)
					vertices.append(center+_cut_side*width*(-1.0 if corner%2==0 else 1.0))
					var color := Color(0.20,0.64,1.0) if layer==0 else (Color(1.0,0.58,0.16) if layer==1 else Color(1.0,0.98,0.84))
					if not _skill_variant.is_empty() and not _blocked:
						color = _skill_tint.lerp(Color.WHITE, 0.72) if layer == 2 else _skill_tint
					if _blocked:
						color = Color(0.30,0.57,0.83) if layer==0 else Color(0.76,0.90,1.0)
					colors.append(Color(color,fade*(0.34 if layer==0 else (0.48 if layer==1 else 0.98))))
	_cut_visible = not vertices.is_empty()
	_submit("cut",vertices,colors)
	vertices = PackedVector3Array()
	colors = PackedColorArray()
	for spark in _sparks:
		var age := elapsed-float(spark.birth)
		if age < 0.0 or age >= float(spark.life):
			continue
		var velocity: Vector3 = spark.velocity
		var a := _position(velocity,maxf(0.0,age-float(spark.trail_s)))
		var b := _position(velocity, age)
		var axis := (b-a).normalized()
		var side := axis.cross(view).normalized()*float(spark.width)
		if side.length_squared() < 0.0000001:
			side = right*float(spark.width)
		var alpha := pow(1.0-age/float(spark.life), 1.4)*0.88
		for corner in [0,1,2,2,1,3]:
			var newer: bool = corner>=2
			vertices.append((b if newer else a)+side*(-1.0 if corner%2==0 else 1.0))
			var color := Color(1.0,0.95,0.72) if newer and not _blocked else Color(0.38,0.74,1.0)
			colors.append(Color(color,alpha*(1.0 if newer else 0.28)))
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
		var heat := clampf(1.0-elapsed/0.08,0.0,1.0)
		var steel := Color(0.36,0.46,0.56).lerp(Color(1.0,0.84,0.46),heat)
		for point: Vector3 in [center-u-v*0.5, center+u, center+v]:
			vertices.append(point)
			colors.append(Color(steel,alpha))
	_submit("debris", vertices, colors)
	vertices = PackedVector3Array()
	colors = PackedColorArray()
	for puff in _dust:
		if elapsed >= float(puff.life):
			continue
		var center := _position(puff.velocity, elapsed, 0.7)
		var radius := float(puff.size)+elapsed*0.18
		var alpha := sin(PI*clampf(elapsed/float(puff.life),0.0,1.0))*0.12
		for index in range(8):
			vertices.append(center)
			colors.append(Color(0.43,0.48,0.50,alpha))
			for angle: float in [TAU*float(index)/8.0, TAU*float(index+1)/8.0]:
				vertices.append(center+(right*cos(angle)+up*sin(angle))*radius)
				colors.append(Color(0.43,0.48,0.50,0.0))
	_submit("dust", vertices, colors)

func presentation_report() -> Dictionary:
	return {"valid":_valid, "reason":_reason, "attack_id":String(_context.get("attack_id", "")),
		"style":"blocked_metal" if _blocked else _strength, "skill_variant":_skill_variant, "quality":_quality,
		"spark_count":_sparks.size(), "spark_budget":24 if _quality == 0 else 10,
		"debris_count":_debris.size(), "dust_count":_dust.size(), "triangles":_triangles,
		"age":elapsed, "duration":duration, "maximum_lifetime":MAX_LIFETIME,
		"core_duration":_core_duration, "core_radius":_core_radius, "contact_source":String(_context.get("contact_source", "")),
		"core_flash_duration":_core_flash_duration,"core_phase":"flash" if elapsed<_core_flash_duration else ("afterglow" if elapsed<_core_duration else "expired"),
		"core_edge_alpha":_core_edge_alpha,
		"core_axis":_core_axis,"core_side":_core_side,"core_plane_normal":_core_plane_normal,
		"core_basis_source":_core_basis_source,
		"cut_visible":_cut_visible,"cut_duration":_cut_duration,"cut_length":_cut_length,"cut_width":_cut_width,"cut_layers":3,
		"cut_axis":_cut_axis,"cut_side":_cut_side,"cut_plane_normal":_cut_plane_normal,
		"cut_basis_source":_cut_basis_source,"mesh_groups":_meshes.size(),"ground_response":false,"secondary_style":"metal_spall_and_contact_motes",
		"world_point":global_position, "depth_tested":true, "ring_geometry":false, "gameplay_authority":false}

func _expire() -> void:
	_valid = false
	set_process(false)
	hide()
	if is_inside_tree():
		queue_free()
