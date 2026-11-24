class_name ActorFeedback
extends Node3D

## Presentation-only feedback for one actor: confirmed-hit rim flash, ember
## dissolve on death, the billboarded health/poise plate and the attack
## warning glyph. It reads values handed to it by the actor and never writes
## health, timers, collision, damage ledgers or the shared gameplay RNG.

const OVERLAY_SHADER: Shader = preload("res://assets/shaders/actor_feedback.gdshader")
const BAR_SHADER: Shader = preload("res://assets/shaders/enemy_status_bar.gdshader")
const TELEGRAPH_SHADER: Shader = preload("res://assets/shaders/attack_telegraph.gdshader")
const EMBER_SHADER: Shader = preload("res://assets/shaders/ember.gdshader")
const FLASH_DURATION := {"light":0.09, "heavy":0.13, "charged":0.16, "skill":0.14, "hurt":0.16}
const FLASH_PEAK := {"light":0.95, "heavy":1.25, "charged":1.55, "skill":1.3, "hurt":1.1}
const DISSOLVE_DELAY := 1.15
const DISSOLVE_DURATION := 1.45
## Body transparency only begins after the ember front has crossed most of
## the silhouette, so the burn reads before the body thins out.
const FADE_START := 0.3
const TRAIL_HOLD := 0.42
const TRAIL_SPEED := 0.85

var visual: Node3D
var actor_height := 1.95
var _quality := 0
var _overlay: ShaderMaterial
var _overlay_meshes: Array[GeometryInstance3D] = []
var _flash := 0.0
var _flash_peak := 0.0
var _flash_elapsed := 0.0
var _flash_duration := 0.1
var _flash_kind := ""
var flash_count := 0
var dying := false
var death_elapsed := 0.0
var dissolve := 0.0
var _fade_entries: Array[Dictionary] = []
var fade := 0.0
var embers: MultiMeshInstance3D
var embers_started := false
var _embers: Array[Dictionary] = []
var _ember_rng := RandomNumberGenerator.new()
var status_bar: MeshInstance3D
var _bar_material: ShaderMaterial
var bar_health := 1.0
var bar_trail := 1.0
var bar_poise := 0.0
var _trail_hold := 0.0
var _bar_flash := 0.0
var telegraph: MeshInstance3D
var _telegraph_material: ShaderMaterial
var telegraph_progress := 0.0
var telegraph_danger := 0.0

func setup(target_visual: Node3D, height: float, quality: int) -> void:
	name = "ActorFeedback"
	visual = target_visual
	actor_height = maxf(0.5, height)
	_quality = clampi(quality, 0, 1)
	_overlay = ShaderMaterial.new()
	_overlay.shader = OVERLAY_SHADER

func make_status_bar(size: Vector2, elite: bool) -> MeshInstance3D:
	status_bar = MeshInstance3D.new()
	status_bar.name = "StatusPlate"
	var quad := QuadMesh.new()
	quad.size = size
	status_bar.mesh = quad
	status_bar.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_bar_material = ShaderMaterial.new()
	_bar_material.shader = BAR_SHADER
	_bar_material.set_shader_parameter("aspect", size.x / maxf(size.y, 0.001))
	if elite:
		_bar_material.set_shader_parameter("fill_color", Color("e6b25c"))
		_bar_material.set_shader_parameter("fill_low_color", Color("9a5a22"))
	status_bar.material_override = _bar_material
	status_bar.visible = false
	return status_bar

func make_telegraph(size: Vector2) -> MeshInstance3D:
	telegraph = MeshInstance3D.new()
	telegraph.name = "AttackTelegraph"
	var quad := QuadMesh.new()
	quad.size = size
	telegraph.mesh = quad
	telegraph.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_telegraph_material = ShaderMaterial.new()
	_telegraph_material.shader = TELEGRAPH_SHADER
	telegraph.material_override = _telegraph_material
	telegraph.visible = false
	return telegraph

func update_status(health_ratio: float, poise_ratio: float) -> void:
	var health := clampf(health_ratio, 0.0, 1.0) if is_finite(health_ratio) else 0.0
	if health < bar_health - 0.0001:
		_trail_hold = TRAIL_HOLD
		_bar_flash = 1.0
	bar_health = health
	if bar_trail < bar_health:
		bar_trail = bar_health
	bar_poise = clampf(poise_ratio, 0.0, 1.0) if is_finite(poise_ratio) else 0.0
	_push_bar()

func set_telegraph(progress: float, danger: bool) -> void:
	telegraph_progress = clampf(progress, 0.0, 1.0) if is_finite(progress) else 0.0
	telegraph_danger = 1.0 if danger else 0.0
	if _telegraph_material != null:
		_telegraph_material.set_shader_parameter("progress", telegraph_progress)
		_telegraph_material.set_shader_parameter("danger", telegraph_danger)
		if is_instance_valid(telegraph):
			# A slight pop-in as the strike nears; quad size stays authored.
			var grow := 0.85 + 0.3 * telegraph_progress
			telegraph.scale = Vector3(grow, grow, 1.0)

func flash(kind: String, blocked: bool = false, killed: bool = false) -> void:
	if dying and not killed:
		return
	if not FLASH_DURATION.has(kind):
		kind = "light"
	_flash_kind = kind
	_flash_duration = float(FLASH_DURATION[kind]) * (1.35 if killed else 1.0)
	_flash_peak = float(FLASH_PEAK[kind]) * (0.6 if blocked else 1.0) * (1.25 if killed else 1.0)
	_flash_elapsed = 0.0
	_flash = _flash_peak
	var color := Color("ffeed0")
	if kind == "hurt":
		color = Color("ff6a55")
	elif blocked:
		color = Color("a9cdf2")
	_overlay.set_shader_parameter("flash_color", color)
	_overlay.set_shader_parameter("flash", _flash)
	flash_count += 1
	_attach_overlay()
	set_process(true)

func begin_death() -> void:
	if dying:
		return
	dying = true
	death_elapsed = 0.0
	dissolve = 0.0
	if is_instance_valid(status_bar):
		status_bar.hide()
	if is_instance_valid(telegraph):
		telegraph.hide()
	set_process(true)

func _ready() -> void:
	# Idle actors cost nothing per frame; any trigger re-enables processing.
	set_process(_flash_peak > 0.0 or dying or _bar_animating())

func _process(delta: float) -> void:
	var keep := false
	if _flash_peak > 0.0:
		_flash_elapsed += delta
		var t := clampf(_flash_elapsed / maxf(_flash_duration, 0.001), 0.0, 1.0)
		_flash = _flash_peak * pow(1.0 - t, 2.0)
		if t >= 1.0:
			_flash = 0.0
			_flash_peak = 0.0
		else:
			keep = true
		_overlay.set_shader_parameter("flash", _flash)
	if dying:
		death_elapsed += delta
		var previous := dissolve
		dissolve = clampf((death_elapsed - DISSOLVE_DELAY) / DISSOLVE_DURATION, 0.0, 1.0)
		if dissolve > 0.0:
			if previous <= 0.0:
				_attach_overlay()
				_start_embers()
			_overlay.set_shader_parameter("dissolve", dissolve)
			_apply_fade(clampf((dissolve - FADE_START) / (1.0 - FADE_START), 0.0, 1.0))
		var embers_alive := _update_embers(delta) if embers_started else false
		keep = keep or dissolve < 1.0 or embers_alive
	if _bar_animating():
		_trail_hold = maxf(0.0, _trail_hold - delta)
		if _trail_hold <= 0.0 and bar_trail > bar_health:
			# Ease out: long chips fall quickly, the last sliver settles.
			bar_trail = maxf(bar_health, bar_trail - delta * maxf(TRAIL_SPEED * (bar_trail - bar_health) * 2.4, 0.18))
		_bar_flash = maxf(0.0, _bar_flash - delta * 7.0)
		_push_bar()
		keep = keep or _bar_animating()
	if _flash_peak <= 0.0 and not dying and not _overlay_meshes.is_empty():
		_detach_overlay()
	if not keep:
		set_process(false)

func _bar_animating() -> bool:
	return _trail_hold > 0.0 or bar_trail > bar_health or _bar_flash > 0.0

func _push_bar() -> void:
	if _bar_material == null:
		return
	_bar_material.set_shader_parameter("health", bar_health)
	_bar_material.set_shader_parameter("trail", bar_trail)
	_bar_material.set_shader_parameter("poise", bar_poise)
	_bar_material.set_shader_parameter("flash", _bar_flash)
	if _bar_animating() and not is_processing():
		set_process(true)

func _presentation_meshes() -> Array[GeometryInstance3D]:
	var result: Array[GeometryInstance3D] = []
	if not is_instance_valid(visual):
		return result
	for node in visual.find_children("*", "GeometryInstance3D", true, false):
		var geometry := node as GeometryInstance3D
		if geometry == null or geometry is BladeTrail or geometry is MultiMeshInstance3D:
			continue
		if geometry.is_in_group("grounding_shadows") or geometry.is_in_group("hub_grounding_shadows"):
			continue
		if shown_under(geometry, visual):
			result.append(geometry)
	return result

static func shown_under(node: Node, ancestor: Node) -> bool:
	# Visibility relative to the actor's own visual root. An actor inside a
	# hidden review/test stage still reports which body is the presented one.
	var current := node
	while current != null and current != ancestor:
		if current is Node3D and not (current as Node3D).visible:
			return false
		current = current.get_parent()
	return current == ancestor and (not ancestor is Node3D or (ancestor as Node3D).visible)

func _attach_overlay() -> void:
	# Skeletal and prototype bodies can swap visibility; attach to what is drawn.
	for mesh in _overlay_meshes:
		if is_instance_valid(mesh) and mesh.material_overlay == _overlay:
			mesh.material_overlay = null
	_overlay_meshes = _presentation_meshes()
	for mesh in _overlay_meshes:
		mesh.material_overlay = _overlay

func _detach_overlay() -> void:
	for mesh in _overlay_meshes:
		if is_instance_valid(mesh) and mesh.material_overlay == _overlay:
			mesh.material_overlay = null
	_overlay_meshes.clear()

func _apply_fade(amount: float) -> void:
	# GeometryInstance3D.transparency did not thin the body in the 4.7.2
	# Compatibility renderer. Dying actors instead get per-actor duplicates of
	# their own materials with alpha-hash transparency (a dithered dissolve in
	# the opaque pass); originals are never edited. Unknown material types are
	# hidden at the end of the fade.
	if _fade_entries.is_empty() and amount > 0.0 and is_instance_valid(visual):
		# The headless dummy renderer has no storage for these material copies
		# and reports an engine error on assignment; copies are still built so
		# native checks can inspect them, and the end-of-fade hide still runs.
		var assign := DisplayServer.get_name() != "headless"
		for node in visual.find_children("*", "GeometryInstance3D", true, false):
			var geometry := node as GeometryInstance3D
			if geometry == null or geometry is BladeTrail:
				continue
			var entry := {"node":geometry, "materials":[]}
			if geometry is MeshInstance3D and geometry.material_override == null and (geometry as MeshInstance3D).mesh != null:
				var mesh_instance := geometry as MeshInstance3D
				for surface in range(mesh_instance.mesh.get_surface_count()):
					var dissolving := _dissolve_copy(mesh_instance.get_active_material(surface))
					if dissolving != null:
						if assign:
							mesh_instance.set_surface_override_material(surface, dissolving)
						entry.materials.append({"material":dissolving, "alpha":dissolving.albedo_color.a})
			elif geometry.material_override is BaseMaterial3D:
				var dissolving := _dissolve_copy(geometry.material_override)
				if assign:
					geometry.material_override = dissolving
				entry.materials.append({"material":dissolving, "alpha":dissolving.albedo_color.a})
			_fade_entries.append(entry)
	fade = amount
	for entry in _fade_entries:
		var geometry: GeometryInstance3D = entry.node
		if not is_instance_valid(geometry):
			continue
		for record in entry.materials:
			var material: BaseMaterial3D = record.material
			material.albedo_color.a = float(record.alpha) * (1.0 - amount)
		if amount >= 0.999:
			geometry.visible = false

static func _dissolve_copy(source: Material) -> BaseMaterial3D:
	if not source is BaseMaterial3D:
		return null
	var copy := source.duplicate() as BaseMaterial3D
	copy.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_HASH
	copy.alpha_hash_scale = 1.0
	return copy

func _start_embers() -> void:
	if embers_started:
		return
	embers_started = true
	# Own RNG and a bounded MultiMesh: no particle node may draw from the
	# global RNG that enemy timing uses.
	_ember_rng.seed = hash(get_instance_id()) & 0x7fffffff
	var count := 40 if _quality == 0 else 16
	var width := 0.32 * maxf(1.0, actor_height / 1.95)
	var origin := global_position
	_embers.clear()
	for index in range(count):
		_embers.append({
			"position":origin + Vector3(_ember_rng.randf_range(-width, width), _ember_rng.randf_range(0.1, actor_height * 0.92), _ember_rng.randf_range(-width, width)),
			"velocity":Vector3(_ember_rng.randf_range(-0.35, 0.35), _ember_rng.randf_range(0.45, 1.55), _ember_rng.randf_range(-0.35, 0.35)),
			"delay":_ember_rng.randf_range(0.0, 0.55), "life":_ember_rng.randf_range(0.7, 1.2),
			"size":_ember_rng.randf_range(0.6, 1.25), "age":0.0})
	var multimesh := MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.use_colors = true
	var quad := QuadMesh.new()
	quad.size = Vector2(0.11, 0.11)
	var material := ShaderMaterial.new()
	material.shader = EMBER_SHADER
	quad.material = material
	multimesh.mesh = quad
	multimesh.instance_count = count
	embers = MultiMeshInstance3D.new()
	embers.name = "DeathEmbers"
	embers.multimesh = multimesh
	embers.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	embers.top_level = true
	add_child(embers)
	embers.global_transform = Transform3D.IDENTITY
	_update_embers(0.0)

func _update_embers(delta: float) -> bool:
	if not is_instance_valid(embers):
		return false
	var alive := false
	var multimesh := embers.multimesh
	for index in range(_embers.size()):
		var ember: Dictionary = _embers[index]
		ember.age += delta
		var local_age: float = ember.age - ember.delay
		var t: float = local_age / ember.life
		if local_age < 0.0 or t >= 1.0:
			multimesh.set_instance_transform(index, Transform3D(Basis.from_scale(Vector3.ONE * 0.0001), ember.position))
			multimesh.set_instance_color(index, Color(0, 0, 0, 0))
			alive = alive or local_age < 0.0
			continue
		alive = true
		var velocity: Vector3 = ember.velocity
		velocity.y += 1.35 * delta
		velocity *= maxf(0.0, 1.0 - 0.7 * delta)
		ember.velocity = velocity
		ember.position += velocity * delta
		var color := Color(1.0, 0.72, 0.32).lerp(Color(0.45, 0.92, 0.9), smoothstep(0.2, 0.7, t))
		color.a = (1.0 - t) * minf(1.0, t * 8.0)
		var size: float = ember.size * (1.0 - 0.5 * t)
		multimesh.set_instance_transform(index, Transform3D(Basis.from_scale(Vector3.ONE * size), ember.position))
		multimesh.set_instance_color(index, color)
	return alive

func _faded_surface_count() -> int:
	var count := 0
	for entry in _fade_entries:
		count += entry.materials.size()
	return count

func presentation_report() -> Dictionary:
	return {"flash":_flash, "flash_kind":_flash_kind, "flash_count":flash_count,
		"overlay_meshes":_overlay_meshes.size(), "dying":dying, "death_elapsed":death_elapsed,
		"dissolve":dissolve, "fade":fade, "faded_surfaces":_faded_surface_count(), "embers":embers_started,
		"ember_count":_embers.size(),
		"bar_health":bar_health, "bar_trail":bar_trail, "bar_poise":bar_poise,
		"telegraph_visible":is_instance_valid(telegraph) and telegraph.visible,
		"telegraph_progress":telegraph_progress, "telegraph_danger":telegraph_danger}
