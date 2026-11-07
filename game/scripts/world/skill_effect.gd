class_name RuneSkillEffect3D
extends Node3D

## Cast presentation only: no collision, hit queries, damage, actor writes or
## shared gameplay randomness. Real hurtbox contact owns the separate impact.
const ENERGY: Shader = preload("res://assets/shaders/skill_energy.gdshader")
const MAX_ACTIVE := 4
const MAX_HISTORY := 7
const MAX_TAIL := 0.36
var _source: RunePlayer
var _attack: CombatStrike
var _source_epoch := 0
var _owner_id := 0
var _attack_id := ""
var _kind := ""
var _valid := false
var _reason := "not_configured"
var _quality := 0
var _age := 0.0
var _tail := 0.0
var _phase := "preparation"
var _origin := Vector3.ZERO
var _facing := Vector3.FORWARD
var _orientation := Basis.IDENTITY
var _reach := 0.0
var _triangles := 0
var _visual_updates := 0
var _last_history_frame := -1
var _history: Array[Vector3] = []
var _layers: Dictionary = {}
var _materials: Array[Dictionary] = []
var _wake: Array[MeshInstance3D] = []

func _ready() -> void:
	add_to_group("skill_effects")
	top_level = true
	process_physics_priority = 10
	set_physics_process(false)

func setup(source: RunePlayer, attack: CombatStrike, quality: int) -> void:
	if not is_inside_tree() or not is_instance_valid(source) or not source.is_inside_tree() or attack == null or attack.source != source:
		_expire("invalid_owner")
		return
	var id := String(attack.presentation_id)
	if not id in ["skill_1", "skill_2", "skill_3"] or source.strike != attack or source.dead or not source.active:
		_expire("invalid_cast")
		return
	if not source.global_position.is_finite() or not source.facing.is_finite() or Vector2(source.facing.x, source.facing.z).length_squared() < 0.000001:
		_expire("invalid_direction")
		return
	_source = source
	_attack = attack
	_source_epoch = source.presentation_epoch
	_owner_id = source.get_instance_id()
	_attack_id = id
	_kind = {"skill_1":"dash", "skill_2":"cyclone", "skill_3":"judgement"}[id]
	_quality = clampi(quality, 0, 1)
	_reach = attack.data.reach
	_origin = source.global_position
	_facing = Vector3(source.facing.x, 0.0, source.facing.z).normalized()
	_orientation = Basis(Vector3.UP, atan2(-_facing.x, -_facing.z))
	global_transform = Transform3D(_orientation, _origin)
	_source.tree_exiting.connect(_owner_exiting)
	_age = maxf(0.0, attack.elapsed)
	_history.append(_origin)
	if _kind == "dash":
		_build_dash()
	elif _kind == "cyclone":
		_build_cyclone()
	else:
		_build_judgement()
	_valid = true
	_reason = "playing"
	_update_visuals()
	var active: Array[Node] = []
	for effect in get_tree().get_nodes_in_group("skill_effects"):
		if not effect.is_queued_for_deletion():
			active.append(effect)
	while active.size() > MAX_ACTIVE:
		var oldest: Node = active.pop_front()
		if oldest.has_method("cancel"):
			oldest.call("cancel")
		else:
			oldest.queue_free()
	set_physics_process(true)

func cancel() -> void:
	_expire("cancelled")

func _owner_exiting() -> void:
	_expire("owner_exited")

func _exit_tree() -> void:
	if is_instance_valid(_source) and _source.tree_exiting.is_connected(_owner_exiting):
		_source.tree_exiting.disconnect(_owner_exiting)
	_attack = null
	_source = null

func _expire(reason: String) -> void:
	_valid = false
	_reason = reason
	set_physics_process(false)
	hide()
	for segment in _wake:
		segment.hide()
	queue_free()

func _physics_process(delta: float) -> void:
	if not _valid or not is_finite(delta) or delta <= 0.0:
		return
	if not is_instance_valid(_source) or not _source.is_inside_tree() or _source.dead:
		_expire("owner_unavailable")
		return
	if not _source.active or _source.presentation_epoch != _source_epoch:
		_expire("owner_inactive_or_restored")
		return
	if _source.strike != _attack:
		if _source.strike != null or _attack.elapsed < _attack.data.duration() - 0.000001:
			_expire("cast_interrupted")
			return
		_age = maxf(_age, _attack.elapsed)
		_tail += delta
		_phase = "tail"
		if _tail >= MAX_TAIL:
			_expire("completed")
			return
	else:
		# Even when step() just confirmed contact and set hit_pause, consume its
		# new authoritative elapsed once. Unchanged contact samples then freeze.
		var next_age := maxf(0.0, _attack.elapsed)
		if absf(next_age - _age) < 0.0000001:
			return
		_age = next_age
		_phase = "preparation" if _age < _attack.data.startup else ("active" if _age < _attack.data.startup + _attack.data.active else "recovery")
	if _kind == "dash":
		global_position = _source.global_position
		_record_resolved_history()
	_update_visuals()

func _record_resolved_history() -> void:
	var frame := Engine.get_physics_frames()
	if frame == _last_history_frame:
		return
	_last_history_frame = frame
	var point := _source.global_position
	var displacement := point - _history[-1]
	if Vector2(displacement.x, displacement.z).length() < 0.09:
		return
	_history.append(point)
	if _history.size() > MAX_HISTORY:
		_history.remove_at(0)

func _triangle(vertices: PackedVector3Array, uvs: PackedVector2Array, a: Vector3, b: Vector3, c: Vector3, ta: Vector2, tb: Vector2, tc: Vector2) -> void:
	vertices.append(a)
	vertices.append(b)
	vertices.append(c)
	uvs.append(ta)
	uvs.append(tb)
	uvs.append(tc)
	_triangles += 1

func _quad(vertices: PackedVector3Array, uvs: PackedVector2Array, a: Vector3, b: Vector3, c: Vector3, d: Vector3, first: float = 0.0, last: float = 1.0) -> void:
	_triangle(vertices, uvs, a, b, c, Vector2(first, 0), Vector2(last, 0), Vector2(last, 1))
	_triangle(vertices, uvs, a, c, d, Vector2(first, 0), Vector2(last, 1), Vector2(first, 1))

func _material(tint: Color, hot: Color, gain: float, pattern: int) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = ENERGY
	material.set_shader_parameter("tint", tint)
	material.set_shader_parameter("hot_tint", hot)
	material.set_shader_parameter("energy", gain)
	material.set_shader_parameter("pattern", pattern)
	_materials.append({"material":material, "weight":1.0})
	return material

func _mesh(label: String, vertices: PackedVector3Array, uvs: PackedVector2Array, material: ShaderMaterial) -> MeshInstance3D:
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.material_override = material
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(instance)
	_layers[label] = instance
	return instance

func _arc(label: String, radius: float, span: float, width: float, thickness: float, twist: float, material: ShaderMaterial) -> MeshInstance3D:
	var vertices := PackedVector3Array()
	var uvs := PackedVector2Array()
	var count := 28 if _quality == 0 else 18
	for index in range(count):
		var sections: Array[PackedVector3Array] = []
		for endpoint in range(2):
			var t := float(index + endpoint) / count
			var angle := deg_to_rad((t - 0.5) * span)
			var radial := Vector3(sin(angle), 0, -cos(angle))
			var center := radial * radius + Vector3.UP * sin(angle * 1.4) * twist
			var taper := 0.18 + 0.82 * sin(PI * t)
			sections.append(PackedVector3Array([center + radial * width * taper * 0.5, center + Vector3.UP * thickness * taper * 0.5, center - radial * width * taper * 0.5, center - Vector3.UP * thickness * taper * 0.5]))
		for edge in range(4):
			var next := (edge + 1) % 4
			_quad(vertices, uvs, sections[0][edge], sections[1][edge], sections[1][next], sections[0][next], float(index) / count, float(index + 1) / count)
	return _mesh(label, vertices, uvs, material)

func _lance(label: String, length: float, width: float, thickness: float, material: ShaderMaterial) -> MeshInstance3D:
	var v := PackedVector3Array()
	var uv := PackedVector2Array()
	var base := PackedVector3Array([Vector3(-width * 0.5, 0, 0), Vector3(0, thickness * 0.5, 0), Vector3(width * 0.5, 0, 0), Vector3(0, -thickness * 0.5, 0)])
	var tip := Vector3(0, 0, -length)
	for index in range(4):
		_triangle(v, uv, base[index], tip, base[(index + 1) % 4], Vector2(0, 0), Vector2(0.99, 0.5), Vector2(0, 1))
	return _mesh(label, v, uv, material)

func _rune(label: String, radius: float, material: ShaderMaterial, inner: bool = false) -> MeshInstance3D:
	var vertices := PackedVector3Array()
	var uvs := PackedVector2Array()
	var count := 24 if _quality == 0 else 16
	for index in range(count):
		var a := TAU * float(index) / count
		var b := a + TAU / count * 0.68
		var r0 := radius * (0.54 if inner else 0.93)
		var r1 := radius * (0.57 if inner else 1.0)
		_quad(vertices, uvs, Vector3(sin(a) * r0, 0, cos(a) * r0), Vector3(sin(b) * r0, 0, cos(b) * r0), Vector3(sin(b) * r1, 0.025, cos(b) * r1), Vector3(sin(a) * r1, 0.025, cos(a) * r1))
		if index % 2 == 0:
			var radial := Vector3(sin(a), 0, cos(a))
			var side := Vector3(cos(a), 0, -sin(a)) * radius * 0.012
			_quad(vertices, uvs, radial * radius * 0.72 - side, radial * radius * 0.89 - side, radial * radius * 0.89 + side, radial * radius * 0.72 + side)
	return _mesh(label, vertices, uvs, material)

func _motes(label: String, radius: float, height: float, count: int, material: ShaderMaterial) -> MeshInstance3D:
	var v := PackedVector3Array()
	var uv := PackedVector2Array()
	for index in range(count):
		var angle := index * 2.3999632
		var center := Vector3(sin(angle) * radius * (0.55 + float(index % 4) * 0.12), float(index % 5) / 5.0 * height, cos(angle) * radius * (0.55 + float(index % 4) * 0.12))
		var size := 0.06 + float(index % 3) * 0.027
		var ring := PackedVector3Array([center + Vector3.RIGHT * size, center + Vector3.BACK * size, center + Vector3.LEFT * size, center + Vector3.FORWARD * size])
		for edge in range(4):
			_triangle(v, uv, ring[edge], center + Vector3.UP * size * 2.4, ring[(edge + 1) % 4], Vector2(0, 0), Vector2(0.5, 1), Vector2(1, 0))
			_triangle(v, uv, ring[(edge + 1) % 4], center - Vector3.UP * size, ring[edge], Vector2(0, 0), Vector2(0.5, 1), Vector2(1, 0))
	return _mesh(label, v, uv, material)

func _build_dash() -> void:
	var body := _material(Color("1fa8ef"), Color("b4f5ff"), 1.65, 0)
	var accent := _material(Color("217dd0"), Color("81eaff"), 1.2, 3)
	var forward_edge := _material(Color("089ba7"), Color("66e8df"), 1.4, 0)
	var wake_material := _material(Color("1265c7"), Color("67d9ff"), 1.3, 3)
	var glyph := _material(Color("21b6bb"), Color("c0ffff"), 1.0, 1)
	# A tall diamond section survives the rear camera's foreshortening. The
	# tip still ends inside the unchanged attack reach; this is no hit volume.
	var lance := _lance("DashBlade", minf(_reach - 0.3, 4.2), 1.0, 0.84, body)
	lance.position = Vector3(0, 1.3, -0.15)
	# Rear gameplay cameras foreshorten a straight lance into the actor. A
	# broad, tall FORWARD crescent carries the readable release instead.
	# Both arcs stay inside the unchanged 160-degree / 4.5m attack envelope;
	# neither rotates behind the caster or becomes a full cyclone ring.
	var left := _arc("DashWingLeft", 3.6, 148, 0.42, 0.60, 0.16, forward_edge)
	left.position.y = 1.05
	var right := _arc("DashWingRight", 3.15, 138, 0.20, 0.28, -0.15, accent)
	right.position.y = 1.4
	var rune := _rune("DashRunes", 0.85, glyph)
	rune.position.y = 0.06
	var count := 6 if _quality == 0 else 4
	for index in range(count):
		var segment := _lance("Wake%d" % index, 1.0, 0.8, 0.32, wake_material)
		segment.top_level = true
		segment.hide()
		_wake.append(segment)

func _build_cyclone() -> void:
	var violet := _material(Color("7042d9"), Color("d2b1ff"), 1.65, 0)
	var cyan := _material(Color("168bc5"), Color("a1efff"), 1.4, 0)
	var rune_material := _material(Color("6b4a9a"), Color("ac8bd8"), 0.85, 1)
	var mote_material := _material(Color("785ce1"), Color("d1baff"), 1.15, 2)
	_arc("CycloneOuter", 1.0, 225, 0.16, 0.23, 0.28, violet)
	_arc("CycloneInner", 0.73, 245, 0.17, 0.20, -0.35, cyan)
	var rune := _rune("CycloneRunes", _reach, rune_material)
	rune.position.y = 0.055
	var inner := _rune("CycloneInnerRunes", _reach, rune_material, true)
	inner.position.y = 0.075
	var motes := _motes("CycloneMotes", _reach * 0.8, 0.85, 18 if _quality == 0 else 10, mote_material)
	motes.position.y = 0.18

func _build_judgement() -> void:
	var gold := _material(Color("d9a12b"), Color("ffe3a0"), 1.4, 0)
	var orange := _material(Color("c26b1e"), Color("ffd78b"), 1.35, 0)
	var rune_material := _material(Color("c0953b"), Color("ffe3a2"), 0.92, 1)
	var shards := _material(Color("bc8d36"), Color("fff0bc"), 1.15, 2)
	# Keep the same ground tip (.12m), leaving room above the blade for a
	# readable crossguard and short grip inside the gameplay camera.
	var blade := _lance("JudgementBlade", 3.2, 0.68, 0.32, gold)
	blade.rotation.x = -PI * 0.5
	blade.position = Vector3(0, 3.32, -1.55)
	var hilt_vertices := PackedVector3Array()
	var hilt_uvs := PackedVector2Array()
	_box_geometry(hilt_vertices, hilt_uvs, Vector3.ZERO, Vector3(0.72, 0.075, 0.10))
	_box_geometry(hilt_vertices, hilt_uvs, Vector3(0, 0.23, 0), Vector3(0.065, 0.19, 0.065))
	var guard := _mesh("JudgementGuard", hilt_vertices, hilt_uvs, orange)
	guard.position = Vector3(0, 3.35, -1.55)
	var crown := _arc("JudgementCrown", 1.0, 300, 0.13, 0.15, 0.0, gold)
	crown.position = Vector3(0, 0.18, -1.55)
	var rune := _rune("JudgementRunes", _reach, rune_material)
	rune.position.y = 0.055
	var inner := _rune("JudgementInnerRunes", _reach, rune_material, true)
	inner.position.y = 0.08
	var fissures := PackedVector3Array()
	var uv := PackedVector2Array()
	var count := 14 if _quality == 0 else 9
	for index in range(count):
		var angle := TAU * float(index) / count + 0.12 * sin(float(index) * 2.7)
		var radial := Vector3(sin(angle), 0, cos(angle))
		var side := Vector3(cos(angle), 0, -sin(angle))
		var start := radial * (0.8 + float(index % 3) * 0.16)
		var middle := radial * _reach * 0.48 + side * 0.2 * sin(float(index))
		var end := radial * _reach * (0.82 + float(index % 3) * 0.07)
		_quad(fissures, uv, start - side * 0.08, middle - side * 0.045 + Vector3.UP * 0.09, middle + side * 0.045 + Vector3.UP * 0.09, start + side * 0.08)
		_triangle(fissures, uv, middle - side * 0.045, end, middle + side * 0.045, Vector2(0, 0), Vector2(1, 0.5), Vector2(0, 1))
	var fissure := _mesh("JudgementFissures", fissures, uv, orange)
	fissure.position.y = 0.07
	var fragments := _motes("JudgementShards", _reach * 0.68, 1.0, 20 if _quality == 0 else 11, shards)
	fragments.position.y = 0.08

func _node(label: String) -> MeshInstance3D:
	return _layers[label] as MeshInstance3D

func _box_geometry(vertices: PackedVector3Array, uvs: PackedVector2Array, center: Vector3, half_size: Vector3) -> void:
	var a := center + Vector3(-half_size.x, -half_size.y, -half_size.z)
	var b := center + Vector3(half_size.x, -half_size.y, -half_size.z)
	var c := center + Vector3(half_size.x, half_size.y, -half_size.z)
	var d := center + Vector3(-half_size.x, half_size.y, -half_size.z)
	var e := center + Vector3(-half_size.x, -half_size.y, half_size.z)
	var f := center + Vector3(half_size.x, -half_size.y, half_size.z)
	var g := center + Vector3(half_size.x, half_size.y, half_size.z)
	var h := center + Vector3(-half_size.x, half_size.y, half_size.z)
	_quad(vertices, uvs, a, b, c, d)
	_quad(vertices, uvs, e, h, g, f)
	_quad(vertices, uvs, a, e, f, b)
	_quad(vertices, uvs, d, c, g, h)
	_quad(vertices, uvs, a, d, h, e)
	_quad(vertices, uvs, b, f, g, c)

func _update_visuals() -> void:
	_visual_updates += 1
	var preparation := clampf(_age / maxf(_attack.data.startup, 0.000001), 0.0, 1.0)
	var active := clampf((_age - _attack.data.startup) / maxf(_attack.data.active, 0.000001), 0.0, 1.0)
	var recovery := clampf((_age - _attack.data.startup - _attack.data.active) / maxf(_attack.data.recovery, 0.000001), 0.0, 1.0)
	var is_preparation := _age < _attack.data.startup
	var fade := (1.0 - recovery * 0.86) * (1.0 - _tail / MAX_TAIL)
	var opacity := (0.16 + preparation * 0.22) if is_preparation else (0.74 - active * 0.16) * fade
	for entry in _materials:
		var material := entry.material as ShaderMaterial
		material.set_shader_parameter("effect_age", _age + _tail)
		material.set_shader_parameter("opacity", opacity * float(entry.weight))
	if _kind == "dash":
		# Authoritative active entry owns a brief thick release, then the long
		# blade collapses during recovery. No separate wall-clock flash.
		var release := exp(-active * 14.0) if not is_preparation else 0.0
		var extension := 0.10 + preparation * 0.18 if is_preparation else (1.0 - active * 0.08) * (1.0 - recovery * 0.62)
		var blade := _node("DashBlade")
		blade.scale = Vector3(0.78 + release * 0.48, 0.80 + release * 0.24, extension)
		var blade_material := blade.material_override as ShaderMaterial
		blade_material.set_shader_parameter("energy", 1.45 + release * 0.55)
		blade_material.set_shader_parameter("opacity", (0.08 + preparation * 0.24) if is_preparation else (0.62 + release * 0.22) * fade)
		var wing_scale := 0.30 + preparation * 0.25 if is_preparation else 1.0 - recovery * 0.12
		var forward_edge := _node("DashWingLeft")
		forward_edge.scale = Vector3(wing_scale, 1.0, wing_scale)
		forward_edge.rotation.y = -0.07 + active * 0.14
		forward_edge.position.y = 1.05 + sin(active * PI) * 0.12
		var edge_material := forward_edge.material_override as ShaderMaterial
		edge_material.set_shader_parameter("energy", 1.25 + release * 0.4)
		edge_material.set_shader_parameter("opacity", (0.08 + preparation * 0.22) if is_preparation else (0.72 + release * 0.12) * fade)
		_node("DashWingRight").scale = Vector3(wing_scale, 1.0, wing_scale)
		_node("DashWingRight").rotation.y = 0.06 - active * 0.12
		_node("DashRunes").scale = Vector3.ONE * (0.65 + preparation * 0.35)
		_update_wake()
	elif _kind == "cyclone":
		var radius := 0.28 + preparation * 0.16 if is_preparation else 1.0
		var outer := _node("CycloneOuter")
		outer.scale = Vector3(_reach * 0.89 * radius, 1.0, _reach * 0.89 * radius)
		outer.rotation.y = -_age * 10.5
		outer.position.y = 0.95 + sin(active * PI) * 0.2
		var inner := _node("CycloneInner")
		inner.scale = Vector3(_reach * radius, 1.0, _reach * radius)
		inner.rotation.y = _age * 12.0 + 2.2
		inner.position.y = 1.45 - active * 0.5
		_node("CycloneMotes").rotation.y = -_age * 2.1
		_node("CycloneMotes").position.y = 0.18 + active * 0.65
		_node("CycloneInnerRunes").rotation.y = _age * 1.5
	else:
		var drop := 2.7 * (1.0 - preparation * preparation * preparation) if is_preparation else 0.0
		var blade := _node("JudgementBlade")
		blade.position.y = 3.32 + drop
		blade.scale = Vector3.ONE * (1.0 - active * 0.35)
		blade.visible = is_preparation or active < 0.73
		_node("JudgementGuard").position.y = 3.35 + drop
		_node("JudgementGuard").visible = blade.visible
		var eruption := 0.15 + preparation * 0.2 if is_preparation else 0.7 + sin(active * PI * 0.5) * 0.3
		_node("JudgementCrown").scale = Vector3.ONE * (0.65 + active * 1.4)
		_node("JudgementCrown").rotation.y = _age * 2.4
		_node("JudgementFissures").scale = Vector3(eruption, 1.0, eruption)
		_node("JudgementFissures").visible = not is_preparation
		_node("JudgementShards").visible = not is_preparation
		_node("JudgementShards").scale = Vector3(eruption, 1.0, eruption)
		_node("JudgementShards").position.y = 0.08 + active * 1.7 - active * active * 0.8
		_node("JudgementInnerRunes").rotation.y = -_age * 0.9

func _update_wake() -> void:
	for index in range(_wake.size()):
		var segment := _wake[index]
		var history_index := _history.size() - 2 - index
		if history_index < 0:
			segment.hide()
			continue
		var newer := _history[history_index + 1] + Vector3.UP * 0.48
		var older := _history[history_index] + Vector3.UP * 0.48
		var difference := older - newer
		if difference.length_squared() < 0.000001:
			segment.hide()
			continue
		segment.show()
		# Leave a gap at both ends of each actual resolved motion segment so
		# the trailing streaks read separately from the forward release blade.
		segment.global_transform = Transform3D(Basis.looking_at(difference.normalized(), Vector3.UP), newer + difference * 0.15)
		segment.scale = Vector3(1.0 - float(index) / _wake.size() * 0.65, 1.0, difference.length() * 0.70)

func presentation_report() -> Dictionary:
	return {"valid":_valid, "reason":_reason, "attack_id":_attack_id, "kind":_kind,
		"attack_instance_id":_attack.attack_instance_id if _attack != null else 0,
		"owner_id":_owner_id, "source_epoch":_source_epoch, "quality":_quality,
		"phase":_phase, "age_s":_age, "tail_s":_tail,
		"triangles":_triangles, "mesh_count":_layers.size(),
		"history_points":_history.duplicate(), "history_count":_history.size(),
		"origin":_origin, "position":global_position, "visual_update_count":_visual_updates,
		"reach_m":_reach, "tail_limit_s":MAX_TAIL}
