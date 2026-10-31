@tool
extends EditorScenePostImport

# Godot 4.7.2 reads the first primitive's material before detecting COLOR_0.
# Apply the generated eye asset's explicit color contract at import, leaving
# the original GLB and all other imported character materials untouched.
const PARTS := [&"EyeSclera", &"GrayGreenIris", &"Pupil"]

func _post_import(scene: Node) -> Object:
	var meshes: Array[MeshInstance3D] = []
	_collect(scene, meshes)
	if meshes.size() != 1 or meshes[0].mesh == null or meshes[0].mesh.get_surface_count() != PARTS.size():
		push_error("Generated eyes require one mesh with exactly three colored PBR parts")
		return null
	var instance := meshes[0]
	var corrected := instance.mesh.duplicate() as ArrayMesh
	for index in range(corrected.get_surface_count()):
		var material := corrected.surface_get_material(index) as BaseMaterial3D
		var arrays := corrected.surface_get_arrays(index)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var colors: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
		if material == null or material.resource_name != PARTS[index] or colors.size() != vertices.size() or colors.is_empty():
			push_error("Generated eye PBR part or COLOR_0 is missing")
			return null
		var local := material.duplicate() as BaseMaterial3D
		local.vertex_color_use_as_albedo = true
		corrected.surface_set_material(index, local)
	instance.mesh = corrected
	return scene

func _collect(node: Node, result: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D:
		result.append(node)
	for child in node.get_children():
		_collect(child, result)
