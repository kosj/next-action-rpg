extends Node3D
## Idle-only presentation. Sanctuary owns placement and Game owns interaction.
## Imported resources are never edited; each instance owns its idle animation.

const ROLE_PATHS := {
	"erin": "res://assets/models/production/erin_idle_gameplay.glb",
	"roen": "res://assets/models/production/roen_idle_gameplay.glb",
}
const PROFILE_ID := "hub_idle_v013"
const HUB_GROUNDING = preload("res://scripts/world/hub_grounding_shadow.gd")

var role := ""
var animation_player: AnimationPlayer
var model: Node3D
var grounding_shadow: Node3D
var _structure: Dictionary = {}
var _failure := "not_configured"

func configure(value: String) -> void:
	if not is_inside_tree():
		role = value

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE
	set_meta("presentation_profile", PROFILE_ID)
	if not ROLE_PATHS.has(role):
		_fallback("unknown_role")
		return
	var path: String = ROLE_PATHS[role]
	if not ResourceLoader.exists(path):
		_fallback("asset_missing")
		return
	var scene := load(path) as PackedScene
	if scene == null or not _mount_asset(scene):
		_fallback(_failure)
		return
	grounding_shadow = HUB_GROUNDING.new()
	add_child(grounding_shadow)

func _mount_asset(scene: PackedScene) -> bool:
	var raw_root := scene.instantiate()
	var candidate := raw_root as Node3D
	if candidate == null:
		raw_root.free()
		_failure = "asset_root_not_3d"
		return false
	var players: Array[AnimationPlayer] = []
	var nodes: Array[Node] = [candidate]
	var selected: AnimationPlayer
	var idle_name := ""
	while not nodes.is_empty():
		var node: Node = nodes.pop_back()
		if node is CollisionObject3D or node is CollisionShape3D or node is CollisionPolygon3D or node is Light3D or node is NavigationRegion3D or node is NavigationLink3D or node is AnimationTree or node is Timer or node is GPUParticles3D or node is CPUParticles3D or node is AudioStreamPlayer or node is AudioStreamPlayer3D or node.get_script() != null:
			candidate.free()
			_failure = "asset_has_non_presentation_authority"
			return false
		if node is AnimationPlayer:
			var player := node as AnimationPlayer
			player.autoplay = ""
			player.stop()
			players.append(player)
			for clip in player.get_animation_list():
				if String(clip).get_slice("/", String(clip).get_slice_count("/")-1) == "idle":
					if selected != null:
						candidate.free()
						_failure = "ambiguous_idle"
						return false
					selected = player
					idle_name = clip
		for child in node.get_children():
			nodes.append(child)
	if selected == null:
		candidate.free()
		_failure = "idle_missing"
		return false
	var original := selected.get_animation(idle_name)
	var animation_root := selected.get_node_or_null(selected.root_node)
	if animation_root == null or (animation_root != candidate and not candidate.is_ancestor_of(animation_root)) or not is_finite(original.length) or original.length <= 0.0:
		candidate.free()
		_failure = "invalid_idle_root_or_length"
		return false
	for index in range(original.get_track_count()):
		var track_type := original.track_get_type(index)
		var path := original.track_get_path(index)
		var target := animation_root.get_node_or_null(NodePath(path.get_concatenated_names()))
		if track_type not in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D, Animation.TYPE_BLEND_SHAPE] or path.is_absolute() or target == null or (target != candidate and not candidate.is_ancestor_of(target)):
			candidate.free()
			_failure = "unsafe_idle_track"
			return false
	var idle := original.duplicate(true) as Animation
	idle.loop_mode = Animation.LOOP_LINEAR
	for library_name in selected.get_animation_library_list():
		selected.remove_animation_library(library_name)
	var library := AnimationLibrary.new()
	library.add_animation("idle", idle)
	selected.add_animation_library("", library)
	for player in players:
		player.active = player == selected
		player.process_mode = Node.PROCESS_MODE_PAUSABLE
	selected.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_IDLE
	model = candidate
	animation_player = selected
	add_child(model)
	# Explicitly evaluate t=0 even when the containing scene is already paused.
	animation_player.play("idle")
	animation_player.advance(0.0)
	_failure = ""
	_structure = _structural_report(scene.resource_path, original.loop_mode, idle)
	if not _structure.rigged or _structure.mesh_nodes <= 0 or _structure.surfaces <= 0 or _structure.vertices <= 0 or _structure.triangles <= 0:
		remove_child(model)
		model.free()
		model = null
		animation_player = null
		_structure.clear()
		_failure = "asset_missing_skinned_geometry"
		return false
	return true

func _fallback(reason: String) -> void:
	_failure = reason
	var placeholder := MeshInstance3D.new()
	placeholder.name = "UnreadyNPCPlaceholder"
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.27
	capsule.height = 1.7
	placeholder.mesh = capsule
	placeholder.position.y = 0.85
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.22, 0.25, 0.30)
	placeholder.material_override = material
	add_child(placeholder)
	_structure = {"source_path": "", "mesh_nodes": 1, "rigged": false, "skeletons": [], "materials": [], "geometry_scope": "fallback_only"}

func _structural_report(source_path: String, source_loop: int, idle: Animation) -> Dictionary:
	var result := {"source_path": source_path, "mesh_nodes": 0, "surfaces": 0, "vertices": 0, "triangles": 0, "skinned_meshes": 0, "skeletons": [], "materials": [], "geometry_scope": "rest_mesh_arrays_not_animated_skin_support", "source_idle_loop": source_loop, "instance_idle_loop": idle.loop_mode, "idle_length": idle.length, "idle_tracks": idle.get_track_count()}
	var nodes: Array[Node] = [model]
	var has_bounds := false
	var bounds := AABB()
	while not nodes.is_empty():
		var node: Node = nodes.pop_back()
		if node is Skeleton3D:
			var skeleton := node as Skeleton3D
			result.skeletons.append({"path": String(model.get_path_to(skeleton)), "bones": skeleton.get_bone_count()})
		if node is MeshInstance3D and node.mesh != null:
			var mesh_node := node as MeshInstance3D
			var mesh := mesh_node.mesh
			result.mesh_nodes += 1
			if mesh_node.skin != null:
				result.skinned_meshes += 1
			var local_bounds: AABB = (global_transform.affine_inverse() * mesh_node.global_transform) * mesh.get_aabb()
			bounds = bounds.merge(local_bounds) if has_bounds else local_bounds
			has_bounds = true
			for surface in range(mesh.get_surface_count()):
				result.surfaces += 1
				if mesh is ArrayMesh:
					var vertices: int = mesh.surface_get_array_len(surface)
					var indices: int = mesh.surface_get_array_index_len(surface)
					result.vertices += vertices
					result.triangles += int((indices if indices > 0 else vertices) / 3)
				var material := mesh_node.get_active_material(surface)
				var item := {"path": material.resource_path if material != null else "", "class": material.get_class() if material != null else "missing"}
				if material is BaseMaterial3D:
					item["albedo_texture"] = material.albedo_texture.resource_path if material.albedo_texture != null else ""
				result.materials.append(item)
		for child in node.get_children():
			nodes.append(child)
	result["rigged"] = not result.skeletons.is_empty() and result.skinned_meshes > 0
	result["rest_bounds"] = {"position": _vector(bounds.position), "size": _vector(bounds.size)}
	return result

func get_idle_player() -> AnimationPlayer:
	return animation_player

func presentation_report() -> Dictionary:
	var report := _structure.duplicate(true)
	report.merge({"profile": PROFILE_ID, "role": role, "mode": "asset_idle" if animation_player != null else "fallback", "asset_ready": animation_player != null, "failure": _failure, "intended_source": ROLE_PATHS.get(role, ""), "npc_index": get_meta("npc", -1), "position": _vector(global_position), "forward": _vector(-global_basis.z), "can_process": can_process(), "process_mode": process_mode}, true)
	if animation_player != null:
		report["idle"] = {"clip": String(animation_player.current_animation), "time": animation_player.current_animation_position, "playing": animation_player.is_playing(), "can_process": animation_player.can_process(), "loop": animation_player.get_animation("idle").loop_mode, "length": animation_player.get_animation("idle").length}
	if is_instance_valid(grounding_shadow):
		report["grounding_shadow"] = grounding_shadow.presentation_report()
	return report

func _vector(value: Vector3) -> Array:
	return [value.x, value.y, value.z]
