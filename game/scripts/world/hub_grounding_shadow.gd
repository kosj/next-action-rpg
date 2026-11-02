extends Node3D
## Two stationary hub roots only. A cached support ellipse, not animated-foot
## contact or a physical light shadow. Queries occur on initial/q1 refresh only.

const SHADER: Shader = preload("res://assets/shaders/grounding_shadow.gdshader")
const OPACITY := 0.21
const OFFSET := 0.012
static var _plane: PlaneMesh
static var _owners: Dictionary = {}

var npc: Node3D
var patch: MeshInstance3D
var material: ShaderMaterial
var _index := -1
var _owner_key := ""
var _pending_frames := 0
var _queries := 0
var _valid_ground := false
var _ground := Vector3.ZERO
var _normal := Vector3.UP
var _reason := "not_initialized"
var _anchor := Transform3D.IDENTITY
var _anchored := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE
	set_notify_transform(true)
	npc = get_parent() as Node3D
	_index = int(npc.get_meta("npc", -1)) if npc != null else -1
	set_physics_process(false)
	if _index not in [0, 1] or npc.get("role") != ["erin", "roen"][_index]:
		_reason = "not_authored_hub_role"
		return
	# Independent native worlds/Sanctuaries each retain their own two roots.
	_owner_key = str(npc.get_parent().get_instance_id()) + ":" + str(_index)
	if _owners.has(_owner_key) and _owners[_owner_key].get_ref() != null:
		_reason = "authored_role_already_owned"
		return
	_owners[_owner_key] = weakref(self)
	if _plane == null:
		_plane = PlaneMesh.new()
		_plane.size = Vector2.ONE
	patch = MeshInstance3D.new()
	patch.name = "StaticHubGroundingEllipse"
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
	add_to_group("hub_grounding_shadows")
	refresh_quality()

func _exit_tree() -> void:
	if _owners.has(_owner_key) and _owners[_owner_key].get_ref() == self:
		_owners.erase(_owner_key)

func _notification(what: int) -> void:
	if what == NOTIFICATION_TRANSFORM_CHANGED and _anchored and is_instance_valid(npc) and not npc.global_transform.is_equal_approx(_anchor):
		patch.hide()
		material.set_shader_parameter("opacity", 0.0)
		_valid_ground = false
		_reason = "outside_stationary_root_contract"
		set_physics_process(false)

func refresh_quality() -> void:
	if patch == null:
		return
	patch.hide()
	material.set_shader_parameter("opacity", 0.0)
	_valid_ground = false
	_pending_frames = 0
	set_physics_process(false)
	if Session.quality != 1:
		_reason = "balanced_uses_light_shadows"
		return
	# The first physics step registers newly-created real floor bodies. The
	# second performs this one query, then disables this callback again.
	_reason = "awaiting_registered_support"
	_pending_frames = 1
	set_physics_process(true)

func _physics_process(_delta: float) -> void:
	if Session.quality != 1:
		refresh_quality()
		return
	if _pending_frames > 0:
		_pending_frames -= 1
		return
	set_physics_process(false)
	var sanctuary := npc.get_parent() as Node3D
	var positions: Variant = sanctuary.get("npc_positions")
	if not positions is Array or _index >= positions.size() or not positions[_index] is Vector3:
		_reason = "missing_authored_root_positions"
		return
	var authored: Vector3 = sanctuary.to_global(positions[_index])
	if not npc.global_position.is_finite() or not npc.global_position.is_equal_approx(authored) or not npc.global_basis.get_scale().is_equal_approx(Vector3.ONE) or npc.global_basis.y.dot(Vector3.UP) < 0.9999 or (_anchored and not npc.global_transform.is_equal_approx(_anchor)):
		_reason = "outside_stationary_root_contract"
		return
	var root_point := npc.global_position
	var ray := PhysicsRayQueryParameters3D.create(root_point + Vector3.UP * 0.35, root_point + Vector3.DOWN * 1.2, 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(ray)
	_queries += 1
	if hit.is_empty() or not Vector3(hit.normal).is_finite() or Vector3(hit.normal).dot(Vector3.UP) < 0.65:
		_reason = "no_supported_ground"
		return
	_ground = hit.position
	_normal = Vector3(hit.normal).normalized()
	var height := (root_point - _ground).dot(Vector3.UP)
	if not _ground.is_finite() or height < -0.12 or height > 0.25:
		_reason = "outside_static_support_height"
		return
	var z_axis := npc.global_basis.z.slide(_normal).normalized()
	var x_axis := _normal.cross(z_axis).normalized()
	z_axis = x_axis.cross(_normal).normalized()
	var width := 1.0 if _index == 0 else 1.05
	patch.global_transform = Transform3D(Basis(x_axis * width, _normal, z_axis * width * 0.72), _ground + _normal * OFFSET)
	material.set_shader_parameter("opacity", OPACITY)
	patch.show()
	_valid_ground = true
	_anchor = npc.global_transform
	_anchored = true
	_reason = "static_hub_grounding"

func presentation_report() -> Dictionary:
	return {"scope":"Two authored stationary NPC roots per Sanctuary; cached initial/toggle support only, not animated feet or physical light shadow",
		"visible":patch != null and patch.is_visible_in_tree(), "cached_ground":_valid_ground,
		"reason":_reason, "query_count":_queries, "query_pending":is_physics_processing(),
		"ground_point":[_ground.x,_ground.y,_ground.z], "ground_normal":[_normal.x,_normal.y,_normal.z],
		"opacity":float(material.get_shader_parameter("opacity")) if material != null else 0.0,
		"offset_m":OFFSET,"maximum_visible":2,"actor_budget_shared":false,
		"shader_path":SHADER.resource_path,"shader_sha256":SHADER.code.sha256_text(),
		"gameplay_authority":false,"static_root_only":true}
