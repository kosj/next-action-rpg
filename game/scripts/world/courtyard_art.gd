extends Node3D
## Mesh-only first-courtyard dressing. It owns no gameplay collision or lights.
## Keep a private seed: adding art must never move later encounter decoration.

const LIMESTONE: StandardMaterial3D = preload("res://assets/materials/courtyard/wall_limestone.tres")
const GROUND: StandardMaterial3D = preload("res://assets/materials/courtyard/ground_detail.tres")
const CLEAR_HALF_EXTENT := 11.0
var art_rng := RandomNumberGenerator.new()
var stone_material: StandardMaterial3D
var logical_instances := 0
var logical_triangles := 0
var surface_batches := 0

func _ready() -> void:
	art_rng.seed = 61583
	stone_material = LIMESTONE.duplicate() as StandardMaterial3D
	stone_material.uv1_triplanar = true
	stone_material.uv1_world_triplanar = true
	stone_material.uv1_scale = Vector3.ONE / 2.0
	_ground_weathering()
	_edge_masonry()
	_ruined_arcades()
	set_meta("mesh_only", true)
	set_meta("clear_half_extent_meters", CLEAR_HALF_EXTENT)
	set_meta("logical_instances", logical_instances)
	set_meta("logical_triangles", logical_triangles)
	set_meta("surface_batches", surface_batches)

func _batch(mesh: Mesh, poses: Array[Transform3D], label: String, shadows: bool = true) -> void:
	var instances := MultiMesh.new()
	instances.transform_format = MultiMesh.TRANSFORM_3D
	instances.mesh = mesh
	instances.instance_count = poses.size()
	for index in range(poses.size()):
		instances.set_instance_transform(index, poses[index])
	var node := MultiMeshInstance3D.new()
	node.name = label
	node.multimesh = instances
	node.material_override = stone_material
	if not shadows:
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(node)
	logical_instances += poses.size()
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		logical_triangles += (indices.size() / 3 if not indices.is_empty() else vertices.size() / 3) * poses.size()
	surface_batches += mesh.get_surface_count()

func _pose(point: Vector3, size: Vector3, yaw: float = 0.0) -> Transform3D:
	return Transform3D(Basis(Vector3.UP, yaw).scaled_local(size), point)

func _chip_mesh(variant: int) -> ArrayMesh:
	var sphere := SphereMesh.new()
	sphere.radius = 0.5
	sphere.height = 1.0
	sphere.radial_segments = 7
	sphere.rings = 3
	var arrays := sphere.get_mesh_arrays()
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	for index in range(vertices.size()):
		var point := vertices[index]
		var distortion := 1.0 + 0.14 * sin(point.x * 13 + point.z * 11 + variant * 2.3)
		point.x *= distortion
		point.z *= distortion
		point.y = maxf(0.0, point.y + 0.5)
		vertices[index] = point
	arrays[Mesh.ARRAY_VERTEX] = vertices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh

func _edge_masonry() -> void:
	# Low rubble is outside the existing side-wall collision, or inside an
	# existing 1.6m pillar base. No traversable route gains a false obstacle.
	for variant in range(3):
		var poses: Array[Transform3D] = []
		for side in [-1, 1]:
			for index in range(16):
				var point := Vector3(side * art_rng.randf_range(20.4,22.0), -0.15, art_rng.randf_range(-19.3,19.3))
				poses.append(_pose(point, Vector3(art_rng.randf_range(0.4,1.25), art_rng.randf_range(0.25,0.8), art_rng.randf_range(0.6,1.6)), art_rng.randf_range(-PI,PI)))
			for z in [-17.0, -5.0, 7.0, 17.0]:
				for index in range(3):
					var point := Vector3(side * 18 + art_rng.randf_range(-0.6,0.6), 0.015, z + art_rng.randf_range(-0.6,0.6))
					poses.append(_pose(point, Vector3(art_rng.randf_range(0.12,0.35), art_rng.randf_range(0.08,0.18), art_rng.randf_range(0.13,0.4)), art_rng.randf_range(-PI,PI)))
		_batch(_chip_mesh(variant), poses, "LimestoneChips%d" % variant)
	# Uneven coping breaks the uninterrupted gold ruler of the prototype wall.
	var coping := BoxMesh.new()
	coping.size = Vector3.ONE
	var caps: Array[Transform3D] = []
	for side in [-1, 1]:
		for index in range(20):
			caps.append(_pose(Vector3(side * 20, 1.41, -19 + index * 2), Vector3(0.88,0.16,art_rng.randf_range(1.72,1.93)), art_rng.randf_range(-0.018,0.018)))
	_batch(coping, caps, "WeatheredCoping")

func _ground_weathering() -> void:
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var tangents := PackedFloat32Array()
	var uvs := PackedVector2Array()
	var colors := PackedColorArray()
	# Baked radial alpha is portable to Compatibility; no screen-space AO,
	# decals, depth-reading shader or volumetric feature is needed for Web.
	for side in [-1, 1]:
		for index in range(10):
			var center := Vector3(side * art_rng.randf_range(16.6,18.8), 0.012 + index * 0.0001, -17.5 + index * 3.8)
			var radius := Vector2(art_rng.randf_range(1.1,2.3), art_rng.randf_range(1.3,2.9))
			for segment in range(20):
				var angle_a := TAU * segment / 20
				var angle_b := TAU * (segment + 1) / 20
				var edge_a := center + Vector3(cos(angle_a) * radius.x,0,sin(angle_a) * radius.y)
				var edge_b := center + Vector3(cos(angle_b) * radius.x,0,sin(angle_b) * radius.y)
				for point in [center, edge_a, edge_b]:
					vertices.append(point)
					normals.append(Vector3.UP)
					tangents.append_array(PackedFloat32Array([1,0,0,1]))
					uvs.append(Vector2(point.x,point.z) / 2.0)
					colors.append(Color(0.8,0.84,0.72,0.78 if point == center else 0.0))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_TANGENT] = tangents
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_COLOR] = colors
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var material := GROUND.duplicate() as StandardMaterial3D
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.vertex_color_use_as_albedo = true
	var node := MeshInstance3D.new()
	node.name = "FeatheredGroundWeathering"
	node.mesh = mesh
	node.material_override = material
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(node)
	logical_instances += 20
	logical_triangles += vertices.size() / 3
	surface_batches += 1

func _ruined_arcades() -> void:
	# The rear arcades must enter the default gameplay frame, not sit entirely
	# outside its frustum. X42 also clears the widest later room's camera sweep:
	# room edge X30 + 6.7m camera reach. No new art owns collision.
	var piers: Array[Transform3D] = []
	var voussoirs: Array[Transform3D] = []
	for side in [-1, 1]:
		for z in [-75.0, -57.0, -39.0, -21.0]:
			piers.append(_pose(Vector3(side * 42,0,z), Vector3(3.0,36,2.7)))
		for center_z in [-66.0, -48.0, -30.0]:
			for segment in range(15):
				# With the last block missing, each outer bay reads as a ruin.
				if (segment == 0 and center_z == -66) or (segment == 14 and center_z == -30):
					continue
				var angle := PI * (segment + 0.5) / 15
				var point := Vector3(side * 42, 18 + sin(angle) * 9, center_z + cos(angle) * 9)
				var basis := Basis(Vector3.RIGHT, angle - PI * 0.5)
				voussoirs.append(Transform3D(basis.scaled_local(Vector3(2.8,1.7,1.94)), point))
	# A broad segmental vault joins the skyline into one sanctuary silhouette.
	# Its opening is 84m wide and never dips into player/camera height. The
	# piers remain outside the rooms; the arch is overhead at world Z-98.
	for side in [-1, 1]:
		piers.append(_pose(Vector3(side * 42,-4,-60), Vector3(4.0,28,4.0)))
	var vault: Array[Transform3D] = []
	var broken_coping: Array[Transform3D] = []
	for segment in range(47):
		var angle := PI * (segment + 0.5) / 47
		var point := Vector3(cos(angle) * 42, 10 + sin(angle) * 14, -60)
		var tangent := Vector3(42 * sin(angle), -14 * cos(angle), 0)
		var normal := Vector3(14 * cos(angle), 42 * sin(angle), 0).normalized()
		var basis := Basis(tangent.normalized(), normal, Vector3.BACK)
		var length := tangent.length() * PI / 47
		vault.append(Transform3D(basis.scaled_local(Vector3(length * 0.985,2.4,3.4)), point))
		if segment % 7 not in [0, 1]:
			broken_coping.append(Transform3D(basis.scaled_local(Vector3(length * 0.92,0.6,3.75)), point + normal * 1.5))
	var stone := BoxMesh.new()
	stone.size = Vector3.ONE
	_batch(stone, piers, "DistantArcadePiers", false)
	_batch(stone, voussoirs, "DistantArcadeArchStones", false)
	_batch(stone, vault, "SanctuarySkylineVault", false)
	_batch(stone, broken_coping, "BrokenSkylineCoping", false)
