class_name RuneAfterimage
extends Node3D

## One-shot rune ghost of the hero's displayed pose for a perfect dodge.
## Skinned surfaces are baked from the current skeleton pose once; nothing is
## animated, collided or written back to the hero. The node frees itself.

const OVERLAY_SHADER: Shader = preload("res://assets/shaders/actor_feedback.gdshader")
const DURATION := 0.5
const PEAK := 1.45

var elapsed := 0.0
var mesh_count := 0
var skinned_count := 0
var drift := Vector3.ZERO
var _material: ShaderMaterial

func _ready() -> void:
	add_to_group("afterimages")
	top_level = true

func capture(source: Node3D, drift_direction: Vector3) -> bool:
	_material = ShaderMaterial.new()
	_material.shader = OVERLAY_SHADER
	_material.set_shader_parameter("flash_color", Color("6fe9ff"))
	_material.set_shader_parameter("flash", PEAK)
	if not is_inside_tree() or not is_instance_valid(source):
		queue_free()
		return false
	for node in source.find_children("*", "MeshInstance3D", true, false):
		var source_mesh := node as MeshInstance3D
		if source_mesh == null or source_mesh is BladeTrail or source_mesh.mesh == null or not ActorFeedback.shown_under(source_mesh, source):
			continue
		if source_mesh.is_in_group("grounding_shadows") or source_mesh.is_in_group("hub_grounding_shadows"):
			continue
		var baked: Mesh = source_mesh.mesh
		if source_mesh.skin != null:
			# A skinned surface is only usable as its current pose. Without a
			# registered skin reference (e.g. a headless dummy renderer) the rest
			# pose would be wrong, so that surface is skipped.
			var skin_reference := source_mesh.get_skin_reference()
			if skin_reference == null or not skin_reference.get_skeleton().is_valid() or not source_mesh.mesh is ArrayMesh:
				continue
			baked = source_mesh.bake_mesh_from_current_skeleton_pose()
			skinned_count += 1
		if baked == null:
			continue
		var ghost := MeshInstance3D.new()
		ghost.name = "Ghost%d" % mesh_count
		ghost.mesh = baked
		ghost.material_override = _material
		ghost.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(ghost)
		ghost.global_transform = source_mesh.global_transform
		mesh_count += 1
	drift = drift_direction.normalized() * 0.8 if drift_direction.length_squared() > 0.0001 else Vector3.ZERO
	if mesh_count == 0:
		queue_free()
		return false
	return true

func _process(delta: float) -> void:
	elapsed += delta
	var t := clampf(elapsed / DURATION, 0.0, 1.0)
	if _material != null:
		_material.set_shader_parameter("flash", PEAK * pow(1.0 - t, 1.5))
	global_position += drift * delta * (1.0 - t)
	if elapsed >= DURATION:
		queue_free()
