class_name BladeTrail
extends MeshInstance3D

## A short world-space ribbon sampled from the displayed blade, never a hitbox.
const LIFETIME := 0.12
const HEAVY_LIFETIME := 0.16
const CHARGED_LIFETIME := 0.22
const MAX_SAMPLES := 16
const MAX_DISCONTINUITY_METERS := 4.0
var tint := Color("8bd9cb")
var _samples: Array[Dictionary] = []
var _epoch := 0
var _initialized := false
var _attack := ""
var _elapsed := 0.0
var _last_tip := Vector3.ZERO
var _has_tip := false
var _charged := false
var _heavy := false
var _triangles := 0
var _ribbon := ArrayMesh.new()
var _light_material: StandardMaterial3D
var _charged_fill_material: StandardMaterial3D
var _edge_material: StandardMaterial3D

func _ready() -> void:
	# History must stay where the sword passed when its owner moves or turns.
	top_level = true
	global_transform = Transform3D.IDENTITY
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_light_material = _material(BaseMaterial3D.BLEND_MODE_ADD)
	_charged_fill_material = _material(BaseMaterial3D.BLEND_MODE_MIX)
	_edge_material = _material(BaseMaterial3D.BLEND_MODE_ADD)
	hide()

func _material(blend: BaseMaterial3D.BlendMode) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.blend_mode = blend
	material.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.vertex_color_use_as_albedo = true
	material.albedo_color = Color.WHITE
	return material

func clear_history() -> void:
	_samples.clear()
	_has_tip = false
	_triangles = 0
	_ribbon.clear_surfaces()
	mesh = null
	hide()

func reset() -> void:
	clear_history()
	_initialized = false
	_attack = ""
	_elapsed = 0.0
	_charged = false
	_heavy = false

func _lifetime() -> float:
	return CHARGED_LIFETIME if _charged else (HEAVY_LIFETIME if _heavy else LIFETIME)

func presentation_report() -> Dictionary:
	return {"samples":_samples.size(), "triangles":_triangles,
		"visible":visible, "lifetime":_lifetime(), "style":"charged" if _charged else ("heavy" if _heavy else "light"),
		"layers":_ribbon.get_surface_count(),"maximum_samples":MAX_SAMPLES,
		"radial_fraction_bounds":[0.18,1.0],"marker_history_only":true,
		"depth_tested":true, "gameplay_authority":false}

func sample_pose(delta: float, snapshot: Dictionary, grip: Vector3, tip: Vector3) -> void:
	if not is_finite(delta) or not grip.is_finite() or not tip.is_finite():
		reset()
		return
	var epoch := int(snapshot.get("presentation_epoch", _epoch))
	var attack := String(snapshot.get("attack_id", ""))
	var elapsed := float(snapshot.get("attack_elapsed", 0.0))
	var startup := float(snapshot.get("attack_startup", 0.0))
	var active := float(snapshot.get("attack_active", 0.0))
	if not is_finite(elapsed) or not is_finite(startup) or not is_finite(active):
		reset()
		return
	var priority := bool(snapshot.get("dead", false)) or float(snapshot.get("stagger", 0.0)) > 0.0 or float(snapshot.get("dodge_remaining", 0.0)) > 0.0 or float(snapshot.get("parry_remaining", 0.0)) > 0.0
	var discontinuity := _has_tip and tip.distance_to(_last_tip) > MAX_DISCONTINUITY_METERS
	var changed := attack != _attack or (not attack.is_empty() and elapsed < _elapsed-0.000001)
	var exact_seek := delta <= 0.0 and (changed or absf(elapsed-_elapsed) > 0.000001)
	if not _initialized or epoch != _epoch or priority or discontinuity or exact_seek or (changed and not attack.is_empty()):
		clear_history()
	_epoch = epoch
	_attack = attack
	if not attack.is_empty():
		_charged = attack == "charged_heavy"
		_heavy = attack == "heavy"
	_elapsed = elapsed
	_initialized = true
	_last_tip = tip
	_has_tip = not priority
	if priority or delta <= 0.0:
		return # Hit pause retains both the sampled geometry and its age.
	for point in _samples:
		point.age = float(point.age) + delta
	while not _samples.is_empty() and float(_samples[0].age) >= _lifetime():
		_samples.pop_front()
	# Use the actual authoritative half-open active window. Preparation, charge,
	# recovery and radial VFX cannot create speculative sword contacts.
	if not attack.is_empty() and active > 0.0 and elapsed >= startup and elapsed < startup+active:
		_samples.append({"base":grip.lerp(tip, 0.18), "tip":tip, "age":0.0})
		while _samples.size() > MAX_SAMPLES:
			_samples.pop_front()
	_rebuild()

func _rebuild() -> void:
	_ribbon.clear_surfaces()
	_triangles = 0
	if _samples.size() < 2:
		mesh = null
		hide()
		return
	var vertices := PackedVector3Array()
	var colors := PackedColorArray()
	var strong := _charged or _heavy
	# More temporal history makes the fan longer; every radial band remains
	# inside the actual past sharp-base/tip segments. There are no predicted
	# points, extra weapon length or added samples during preparation/hitstop.
	var radial: Array[float] = [0.0,1.0]
	if strong:
		radial = [0.0,0.45,0.82,1.0]
	var palette: Array[Color] = [Color(0.12,0.56,0.85,0.04),Color(0.22,0.78,1.0,0.23),
		Color(1.0,0.64,0.18,0.46),Color(1.0,0.90,0.56,0.58)]
	for index in range(_samples.size()-1):
		var a: Dictionary = _samples[index]
		var b: Dictionary = _samples[index+1]
		var fade_a := pow(clampf(1.0-float(a.age)/_lifetime(),0.0,1.0),1.25)
		var fade_b := pow(clampf(1.0-float(b.age)/_lifetime(),0.0,1.0),1.25)
		for band in range(radial.size()-1):
			for corner in [0,1,2,2,1,3]:
				var point: Dictionary = b if corner>=2 else a
				var distal: bool = corner%2 == 1
				var radial_index := band+(1 if distal else 0)
				var fade: float = fade_b if corner>=2 else fade_a
				vertices.append(Vector3(point.base).lerp(point.tip,radial[radial_index]))
				var color: Color = palette[radial_index] if strong else Color(tint,0.54 if distal else 0.075)
				colors.append(Color(color,color.a*fade))
	_add_surface(vertices,colors,_charged_fill_material if strong else _light_material)
	vertices = PackedVector3Array()
	colors = PackedColorArray()
	for index in range(_samples.size()-1):
		var a: Dictionary = _samples[index]
		var b: Dictionary = _samples[index+1]
		for corner in [0,1,2,2,1,3]:
			var point: Dictionary = b if corner>=2 else a
			var distal: bool = corner%2 == 1
			var fade := pow(clampf(1.0-float(point.age)/_lifetime(),0.0,1.0),1.65)
			vertices.append(point.tip if distal else Vector3(point.tip).lerp(point.base,0.11 if strong else 0.07))
			var hot := Color(1.0,0.98,0.80) if strong else Color(0.85,1.0,1.0)
			var cool := Color(0.32,0.79,1.0)
			colors.append(Color(hot if distal else cool,fade*(1.0 if distal else 0.26)))
	_add_surface(vertices,colors,_edge_material)
	mesh = _ribbon
	show()

func _add_surface(vertices: PackedVector3Array, colors: PackedColorArray, material: StandardMaterial3D) -> void:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_COLOR] = colors
	_ribbon.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	_ribbon.surface_set_material(_ribbon.get_surface_count()-1,material)
	_triangles += vertices.size()/3
