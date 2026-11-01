class_name GroundingShadow
extends Node3D

## Finite, physics-grounded ellipse used only by the performance preset.
## No collision, light, animation or gameplay authority. It is not a light's
## physical contact shadow and does not attempt to match the animated feet.
const SHADER: Shader = preload("res://assets/shaders/grounding_shadow.gdshader")
const MAX_VISIBLE := 8
const QUERY_INTERVAL := 0.10
const FORCED_QUERY_INTERVAL := 1.0 / 30.0
const MAX_CACHE_MOTION := 0.75
const MAX_HEIGHT := 1.0
const OPACITY := 0.21
static var _plane: PlaneMesh
static var _slots: Dictionary = {}

var visual: Node3D
var actor: CharacterBody3D
var patch: MeshInstance3D
var material: ShaderMaterial
var _collider: CollisionShape3D
var _age := QUERY_INTERVAL
var _valid_ground := false
var _query_foot := Vector3.ZERO
var _ground := Vector3.ZERO
var _normal := Vector3.UP
var _last_scale := 0.0
var _queries := 0
var _last_query_frame := -1
var _reason := "not_initialized"
var _height := 0.0

static func _clean_slots() -> void:
	for key in _slots.keys():
		var reference: WeakRef = _slots[key]
		if reference.get_ref() == null:
			_slots.erase(key)

static func visible_budget_used() -> int:
	_clean_slots()
	return _slots.size()

func _ready() -> void:
	visual = get_parent() as Node3D
	actor = visual.get_parent() as CharacterBody3D if visual != null else null
	if actor == null:
		set_physics_process(false)
		return
	for child in actor.get_children():
		if child is CollisionShape3D and child.shape is CapsuleShape3D:
			_collider = child as CollisionShape3D
			break
	if _plane == null:
		_plane = PlaneMesh.new()
		_plane.size = Vector2.ONE
	patch = MeshInstance3D.new()
	patch.name = "ApproximateGroundingEllipse"
	patch.mesh = _plane
	patch.top_level = true
	patch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	patch.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	material = ShaderMaterial.new()
	material.shader = SHADER
	material.set_shader_parameter("opacity", 0.0)
	patch.material_override = material
	add_child(patch)
	patch.hide()
	add_to_group("grounding_shadows")
	process_physics_priority = 50
	_reason = "awaiting_ground"

func _exit_tree() -> void:
	_slots.erase(get_instance_id())

func _hide(reason: String, clear_cache: bool = false) -> void:
	_reason = reason
	if is_instance_valid(patch):
		patch.hide()
		material.set_shader_parameter("opacity", 0.0)
	_slots.erase(get_instance_id())
	if clear_cache:
		_valid_ground = false

func refresh_quality() -> void:
	# May be called by the ordinary quality UI; the next physics frame supplies
	# a fresh query when enabling. Balanced mode never doubles real shadows.
	if Session.quality != 1:
		_hide("balanced_uses_light_shadows", true)
	else:
		_valid_ground = false

func _claim_slot() -> bool:
	_clean_slots()
	var id := get_instance_id()
	if _slots.has(id):
		return true
	if _slots.size() >= MAX_VISIBLE:
		return false
	_slots[id] = weakref(self)
	return true

func _physics_process(delta: float) -> void:
	if not is_finite(delta) or delta < 0.0 or not is_instance_valid(actor) or not is_instance_valid(_collider) or not _collider.shape is CapsuleShape3D:
		_hide("invalid_owner", true)
		return
	_age += delta
	if Session.quality != 1:
		_hide("balanced_uses_light_shadows", true)
		return
	if not visual.is_visible_in_tree() or actor.get("dead") == true or _collider.disabled:
		_hide("hidden_or_dead", true)
		return
	var camera := get_viewport().get_camera_3d()
	if camera != null and actor.global_position.distance_squared_to(camera.global_position) > 38.0*38.0:
		_hide("outside_near_budget", true)
		return
	var scale_value := _collider.global_basis.get_scale()
	if not scale_value.is_finite() or scale_value.x <= 0.0 or scale_value.x > 4.0 or absf(scale_value.x-scale_value.y) > .001 or absf(scale_value.x-scale_value.z) > .001 or _collider.global_basis.determinant() <= 0.0 or _collider.global_basis.y.normalized().dot(Vector3.UP) < .95:
		_hide("unsupported_capsule_scale_or_tilt", true)
		return
	var capsule := _collider.shape as CapsuleShape3D
	var foot := _collider.global_position-Vector3.UP*(capsule.height*scale_value.y*.5)
	if not foot.is_finite():
		_hide("non_finite_foot", true)
		return
	var moved := foot.distance_squared_to(_query_foot) > MAX_CACHE_MOTION*MAX_CACHE_MOTION
	if moved or absf(scale_value.x-_last_scale) > .001:
		_valid_ground = false
	if not _claim_slot():
		_hide("visible_budget", true)
		return
	var frame := Engine.get_physics_frames()
	if frame != _last_query_frame and (_age >= QUERY_INTERVAL or (not _valid_ground and _age >= FORCED_QUERY_INTERVAL)):
		var query := PhysicsRayQueryParameters3D.create(foot+Vector3.UP*.35, foot+Vector3.DOWN*1.2, 1)
		query.exclude = [actor.get_rid()]
		var hit := get_world_3d().direct_space_state.intersect_ray(query)
		_queries += 1
		_last_query_frame = frame
		_age = 0.0
		_query_foot = foot
		_last_scale = scale_value.x
		_valid_ground = not hit.is_empty() and Vector3(hit.normal).dot(Vector3.UP) >= .65
		if _valid_ground:
			_ground = hit.position
			_normal = Vector3(hit.normal).normalized()
	if not _valid_ground:
		_hide("no_supported_ground")
		return
	var projected := Vector3(foot.x, _ground.y, foot.z)
	projected.y -= (_normal.x*(foot.x-_ground.x)+_normal.z*(foot.z-_ground.z))/_normal.y
	_height = (foot-projected).dot(Vector3.UP)
	if _height < -.12 or _height >= MAX_HEIGHT:
		_hide("outside_ground_height")
		return
	var z_axis := actor.global_basis.z.slide(_normal).normalized()
	if z_axis.length_squared() < .001:
		_hide("invalid_ground_basis")
		return
	var x_axis := _normal.cross(z_axis).normalized()
	z_axis = x_axis.cross(_normal).normalized()
	var width := clampf(capsule.radius*scale_value.x*2.5,.3,2.0)
	patch.global_transform = Transform3D(Basis(x_axis,_normal,z_axis).scaled_local(Vector3(width,1.0,width*.72)), projected+_normal*.012)
	var fade := 1.0-smoothstep(.05,MAX_HEIGHT,maxf(0.0,_height))
	material.set_shader_parameter("opacity",OPACITY*fade)
	patch.show()
	_reason = "approximate_grounding"

func presentation_report() -> Dictionary:
	return {"scope":"Finite performance-mode grounding ellipse; not physical light/foot shadow or AAA approval",
		"visible":is_instance_valid(patch) and patch.visible,"reason":_reason,"query_count":_queries,
		"cached_ground":_valid_ground,"ground_point":_ground,"ground_normal":_normal,"height_m":_height,
		"opacity":float(material.get_shader_parameter("opacity")) if material != null else 0.0,
		"visible_budget_used":visible_budget_used(),"maximum_visible":MAX_VISIBLE,
		"normal_query_interval_s":QUERY_INTERVAL,"minimum_forced_interval_s":FORCED_QUERY_INTERVAL,
		"last_query_physics_frame":_last_query_frame,"gameplay_authority":false}
