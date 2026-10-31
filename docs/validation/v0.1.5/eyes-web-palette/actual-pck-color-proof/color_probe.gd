extends SceneTree

func _initialize() -> void:
	call_deferred("run")

func collect(node: Node, into: Array[MeshInstance3D]) -> void:
	if node is MeshInstance3D:
		into.append(node as MeshInstance3D)
	for child in node.get_children():
		collect(child, into)

func run() -> void:
	var args := OS.get_cmdline_user_args()
	assert(args.size() == 2)
	assert(ProjectSettings.load_resource_pack(args[0], true))
	# This minimal inspection project has no assets; this path resolves only
	# through the actual Web PCK's .remap to its baked imported PackedScene.
	var scene := load("res://assets/models/production/lyra_eyes.glb") as PackedScene
	assert(scene != null)
	var root := scene.instantiate()
	var meshes: Array[MeshInstance3D] = []
	collect(root, meshes)
	var surfaces := []
	for mesh in meshes:
		for index in range(mesh.mesh.get_surface_count()):
			var arrays := mesh.mesh.surface_get_arrays(index)
			var positions: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var colors: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
			var material := mesh.get_active_material(index) as BaseMaterial3D
			var rows := []
			for vertex in range(positions.size()):
				var position := positions[vertex]
				var color := colors[vertex]
				rows.append([position.x,position.y,position.z,color.r,color.g,color.b,color.a])
			surfaces.append({"surface":index, "material":material.resource_name,
				"vertex_colors_as_albedo":material.vertex_color_use_as_albedo,
				"rows":rows, "indices":Array(arrays[Mesh.ARRAY_INDEX])})
	var file := FileAccess.open(args[1], FileAccess.WRITE)
	assert(file != null)
	file.store_string(JSON.stringify({"scope":"Actual Web PCK remapped eye PackedScene color arrays; no application scene loaded",
		"pack_sha256":FileAccess.get_sha256(args[0]), "scene_resource_path":scene.resource_path,
		"surfaces":surfaces},"\t")+"\n")
	file.close()
	root.free()
	quit()
