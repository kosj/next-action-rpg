class_name Sanctuary
extends Node3D

const CENTERS: Array[Vector3] = [Vector3(0,0,-38), Vector3(10,0,-90), Vector3(-10,0,-145), Vector3(10,0,-200), Vector3(-10,0,-255), Vector3(0,0,-310), Vector3(0,0,-375)]
const CHECKPOINTS: Array[Vector3] = [Vector3(0,0,6), Vector3(0,0,-116), Vector3(-5,0,-281)]
const TITLES: Array[String] = ["순례자의 뜰", "침묵의 회랑", "깨진 서약", "달빛의 정원", "잿빛 제단", "마지막 문", "타락한 성역"]
var stone: Material
var trim: Material
var dark: Material
var glow: Material
var gates: Dictionary = {}
var crystals: Array[Node3D] = []
var npc_positions: Array[Vector3] = [Vector3(-4,0,5), Vector3(4,0,5)]
var lore_positions: Array[Vector3] = [Vector3(-8,0,-5), Vector3(30,0,-145), Vector3(-35,0,-255)]
var rng := RandomNumberGenerator.new()

func _ready() -> void:
	rng.seed = 19421
	stone = ShaderMaterial.new()
	stone.shader = preload("res://assets/shaders/stone.gdshader")
	trim = mat(Color("9a8259"), 0.65)
	dark = mat(Color("19292f"), 0.2)
	glow = mat(Color("6ccbbf"), 0.25, true)
	lighting()
	build_room(Vector3(0,0,5), 18, -1)
	var previous := Vector3(0,0,5)
	for index in range(CENTERS.size()):
		var center := CENTERS[index]
		build_road(previous, center)
		build_room(center, 23 if index == 6 else 20, index)
		previous = center
	for index in range(CHECKPOINTS.size()):
		var point := CHECKPOINTS[index]
		block(point + Vector3(0,-0.2,0), Vector3(10,0.4,10), stone, true)
		checkpoint(point, index)
	for index in range(npc_positions.size()):
		var visual := ActorVisual.new()
		add_child(visual)
		visual.position = npc_positions[index]
		visual.setup("keeper" if index == 0 else "sentinel")
		visual.rotation.y = -0.7 if index == 0 else 0.7
		visual.set_meta("npc", index)
	for index in range(lore_positions.size()):
		var point := lore_positions[index]
		if index > 0:
			build_road(Vector3(CENTERS[2 if index == 1 else 4].x,0,point.z), point, 5)
		block(point + Vector3(0,-0.3,0), Vector3(7,0.6,7), stone, true)
		block(point + Vector3(0,0.5,0), Vector3(1.1,1.0,0.8), dark)
		var tablet := block(point + Vector3(0,1.2,0), Vector3(0.6,0.15,0.8), trim)
		tablet.rotation.x = -0.2
		ring(point + Vector3.UP * 0.03, 1.6, glow)
	# Distant silhouettes give the sanctuary scale without expensive geometry.
	for index in range(45):
		var z := rng.randf_range(-450, 60)
		var x := rng.randf_range(65, 140) * (-1 if index % 2 else 1)
		var height := rng.randf_range(18, 55)
		block(Vector3(x, height * 0.5 - 12, z), Vector3(rng.randf_range(3,8), height, 4), dark)

func mat(color: Color, metal: float = 0, emissive: bool = false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metal
	material.roughness = 0.55
	if emissive:
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.emission_enabled = true
		material.emission = color
		material.emission_energy_multiplier = 0.5
	return material

func lighting() -> void:
	var environment_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("182b36")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("8faab4")
	env.ambient_light_energy = 0.65
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color("344c53")
	env.fog_density = 0.0065
	environment_node.environment = env
	add_child(environment_node)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-38, -30, 0)
	sun.light_color = Color("ffe3b0")
	sun.light_energy = 1.65
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 65
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-25, 145, 0)
	fill.light_color = Color("79b7cf")
	fill.light_energy = 0.55
	add_child(fill)

func block(point: Vector3, size: Vector3, material: Material, collision: bool = false) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	node.mesh = mesh
	node.material_override = material
	node.position = point
	add_child(node)
	if collision:
		var body := StaticBody3D.new()
		body.collision_layer = 1
		var shape := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = size
		shape.shape = box
		body.add_child(shape)
		node.add_child(body)
	return node

func ring(point: Vector3, radius: float, material: Material) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	var mesh := TorusMesh.new()
	mesh.inner_radius = radius - 0.035
	mesh.outer_radius = radius
	mesh.rings = 48
	mesh.ring_segments = 6
	node.mesh = mesh
	node.material_override = material
	node.position = point
	node.scale.y = 0.25
	add_child(node)
	return node

func build_road(start: Vector3, end: Vector3, width: float = 12.0) -> void:
	var direction := (end - start).normalized()
	start += direction * 18.0
	if width >= 10:
		end -= direction * 18.0
	var distance := start.distance_to(end)
	var middle := (start + end) * 0.5
	var angle := atan2(end.x - start.x, end.z - start.z)
	var road := block(middle + Vector3(0,-0.35,0), Vector3(width,0.7,distance), stone, true)
	road.rotation.y = angle
	for side in [-1, 1]:
		var offset := Vector3(side * (width * 0.5 - 0.12),0,0).rotated(Vector3.UP, angle)
		var rail := block(middle + offset + Vector3.UP * 0.35, Vector3(0.22,0.7,distance), dark, true)
		rail.rotation.y = angle
		var line := block(middle + offset + Vector3.UP * 0.73, Vector3(0.05,0.04,distance), trim)
		line.rotation.y = angle

func build_room(center: Vector3, half: float, index: int) -> void:
	block(center + Vector3(0,-2.0,0), Vector3(half * 2,4,half * 2), dark, true)
	block(center + Vector3(0,-0.12,0), Vector3(half * 2,0.25,half * 2), stone)
	for radius in [3.2, 4.0, 8.5]:
		ring(center + Vector3.UP * 0.035, radius, trim if radius != 3.2 else glow)
	for side in [-1, 1]:
		for z_offset in [-half + 3, -5, 7, half - 3]:
			column(center + Vector3(side * (half - 2),0,z_offset), 5.5 + rng.randf_range(0,2.5))
		block(center + Vector3(side * half,0.65,0), Vector3(0.65,1.3,half * 2), dark, true)
		block(center + Vector3(side * half,1.33,0), Vector3(0.8,0.08,half * 2), trim)
		for z_offset in [-11, 11]:
			brazier(center + Vector3(side * (half - 4),0,z_offset))
	for spoke in range(8):
		var angle := spoke * TAU / 8
		var position_offset := Vector3(sin(angle),0,cos(angle)) * 6.4
		var inlay := block(center + position_offset + Vector3.UP * 0.015, Vector3(0.045,0.035,4.8), trim)
		inlay.rotation.y = angle
	for decoration in range(16):
		var side := -1 if decoration % 2 else 1
		var position_offset := Vector3(side * rng.randf_range(12,half-1),0,rng.randf_range(-half+2,half-2))
		var slab := block(center + position_offset + Vector3.UP * 0.12, Vector3(rng.randf_range(0.3,1),0.24,rng.randf_range(0.4,1.3)), dark)
		slab.rotation.y = rng.randf_range(0,TAU)
	if index >= 0:
		var pair: Array[Node3D] = []
		for side in [-1, 1]:
			var gate := block(center + Vector3(0,2,side * (half - 0.5)), Vector3(half*2,4,0.3), mat(Color(0.22,0.55,0.52,0.24)), true)
			var gate_mat: StandardMaterial3D = gate.material_override
			gate_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
			gate_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			gate.hide()
			var gate_shape: CollisionShape3D = gate.get_child(0).get_child(0)
			gate_shape.disabled = true
			pair.append(gate)
		gates[index] = pair
	# Broken monumental doorway at the far side.
	for side in [-1, 1]:
		column(center + Vector3(side * 7.5,0,-half+2), 8.5 if index == 6 else 7.0)
	block(center + Vector3(0,7,-half+2), Vector3(17,1.1,1.4), dark)
	block(center + Vector3(0,7.65,-half+2), Vector3(17.5,0.18,1.65), trim)

func column(point: Vector3, height: float) -> void:
	block(point + Vector3.UP * 0.3, Vector3(1.6,0.6,1.6), dark, true)
	var node := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = 0.46
	mesh.bottom_radius = 0.6
	mesh.height = height
	mesh.radial_segments = 8
	node.mesh = mesh
	node.material_override = stone
	node.position = point + Vector3.UP * (height * 0.5 + 0.6)
	add_child(node)
	block(point + Vector3.UP * (height+0.7), Vector3(1.35,0.35,1.35), trim)
	block(point + Vector3(0,-0.01,-0.61) + Vector3.UP * 1.5, Vector3(0.045,1.8,0.035), glow)

func brazier(point: Vector3) -> void:
	block(point + Vector3.UP * 0.65, Vector3(0.6,1.3,0.6), dark)
	var crystal := block(point + Vector3.UP * 1.65, Vector3(0.3,0.7,0.3), glow)
	crystal.rotation.z = 0.25
	var light := OmniLight3D.new()
	light.position = point + Vector3.UP * 2
	light.light_color = Color("68d5c6")
	light.light_energy = 1.1
	light.omni_range = 7
	add_child(light)

func checkpoint(point: Vector3, index: int) -> void:
	var root := Node3D.new()
	root.position = point + Vector3(2,0,0)
	add_child(root)
	var crystal := block(root.position + Vector3.UP * 1.4, Vector3(0.5,1.5,0.5), glow)
	crystal.rotation_degrees = Vector3(0,45,25)
	crystals.append(crystal)
	ring(root.position + Vector3.UP * 0.05, 2.0, glow)
	root.set_meta("checkpoint", index)

func set_gates(index: int, closed: bool) -> void:
	for gate: Node3D in gates[index]:
		gate.visible = closed
		var shape: CollisionShape3D = gate.get_child(0).get_child(0)
		shape.set_deferred("disabled", not closed)

func _process(delta: float) -> void:
	for crystal in crystals:
		crystal.rotate_y(delta * 0.45)
