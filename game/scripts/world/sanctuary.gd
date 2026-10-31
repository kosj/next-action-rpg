class_name Sanctuary
extends Node3D

const COURTYARD_PILLAR_SCENE: PackedScene = preload("res://assets/models/production/sanctuary_pillar_web.glb")
const COURTYARD_GATEWAY_SCENE: PackedScene = preload("res://assets/models/production/pilgrim_gateway.glb")
const COURTYARD_ART = preload("res://scripts/world/courtyard_art.gd")
const COURTYARD_FLOOR: StandardMaterial3D = preload("res://assets/materials/courtyard/floor_stone.tres")
const COURTYARD_WALL: StandardMaterial3D = preload("res://assets/materials/courtyard/wall_limestone.tres")

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
	environment_node.name = "SanctuaryEnvironment"
	var env := Environment.new()
	# A real sky supplies broad reflections to the imported PBR metal. Flat
	# ambient colour made silver hair, stone and black armour equally cyan.
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("344c65")
	sky_material.sky_horizon_color = Color("b7b9af")
	sky_material.ground_horizon_color = Color("a4aaa4")
	sky_material.ground_bottom_color = Color("303d45")
	sky_material.sky_curve = 0.22
	sky_material.sky_energy_multiplier = 0.8
	var sky := Sky.new()
	sky.sky_material = sky_material
	sky.radiance_size = Sky.RADIANCE_SIZE_128
	env.sky = sky
	env.background_mode = Environment.BG_SKY
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.ambient_light_energy = 0.72
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color("8295a1")
	env.fog_light_energy = 0.55
	env.fog_density = 0.003
	env.fog_sky_affect = 0.15
	environment_node.environment = env
	add_child(environment_node)
	var sun := DirectionalLight3D.new()
	sun.name = "SanctuaryKey"
	sun.rotation_degrees = Vector3(-32, -38, 0)
	sun.light_color = Color("fff0da")
	sun.light_energy = 1.25
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 65
	add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.name = "SanctuaryFill"
	fill.rotation_degrees = Vector3(-25, 145, 0)
	fill.light_color = Color("b1c6dc")
	fill.light_energy = 0.25
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
	var floor_visual := block(center + Vector3(0,-0.12,0), Vector3(half * 2,0.25,half * 2), stone)
	var courtyard_wall: StandardMaterial3D
	if index == 0:
		# A plane has an unambiguous 0..1 UV range, unlike the BoxMesh atlas.
		# This changes only the non-colliding skin above the original foundation.
		var floor_mesh := PlaneMesh.new()
		floor_mesh.size = Vector2(half * 2, half * 2)
		floor_visual.mesh = floor_mesh
		floor_visual.position = center + Vector3.UP * 0.005
		floor_visual.name = "CourtyardFlagstone"
		var floor_material := COURTYARD_FLOOR.duplicate() as StandardMaterial3D
		floor_material.uv1_scale = Vector3.ONE * (half * 2 / 1.8)
		floor_visual.material_override = floor_material
		floor_visual.set_meta("physical_tile_meters", 1.8)
		courtyard_wall = COURTYARD_WALL.duplicate() as StandardMaterial3D
		courtyard_wall.uv1_triplanar = true
		courtyard_wall.uv1_world_triplanar = true
		courtyard_wall.uv1_scale = Vector3.ONE / 2.0
	for radius in [3.2, 4.0, 8.5]:
		ring(center + Vector3.UP * 0.035, radius, trim if radius != 3.2 else glow)
	for side in [-1, 1]:
		for z_offset in [-half + 3, -5, 7, half - 3]:
			# Consume the same height sample even when the first room uses a fixed
			# canonical pillar, preserving all later rooms' seeded decoration.
			column(center + Vector3(side * (half - 2),0,z_offset), 5.5 + rng.randf_range(0,2.5), index == 0)
		block(center + Vector3(side * half,0.65,0), Vector3(0.65,1.3,half * 2), courtyard_wall if index == 0 else dark, true)
		block(center + Vector3(side * half,1.33,0), Vector3(0.8,0.08,half * 2), courtyard_wall if index == 0 else trim)
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
		if index == 0:
			# Keep the original RNG sequence for every later room. The first room's
			# old floating cuboids are replaced by grounded, clustered edge debris.
			slab.hide()
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
	if index == 0:
		_courtyard_gateway(center + Vector3(0,0,-half+2))
		var dressing := COURTYARD_ART.new() as Node3D
		dressing.name = "CourtyardArt"
		dressing.position = center
		add_child(dressing)
	else:
		for side in [-1, 1]:
			column(center + Vector3(side * 7.5,0,-half+2), 8.5 if index == 6 else 7.0)
		block(center + Vector3(0,7,-half+2), Vector3(17,1.1,1.4), dark)
		block(center + Vector3(0,7.65,-half+2), Vector3(17.5,0.18,1.65), trim)

func _column_base(point: Vector3) -> MeshInstance3D:
	return block(point + Vector3.UP * 0.3, Vector3(1.6,0.6,1.6), dark, true)

func column(point: Vector3, height: float, detailed: bool = false) -> void:
	var base := _column_base(point)
	if detailed:
		base.hide() # Visibility does not disable the original base collision.
		_courtyard_pillar(point)
		return
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

func _prop(scene: PackedScene, point: Vector3, prop_name: String) -> Node3D:
	var visual := scene.instantiate() as Node3D
	visual.name = prop_name
	visual.position = point
	add_child(visual)
	return visual

func _prop_body(parent: Node3D, body_name: String) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.name = body_name
	body.collision_layer = 1
	body.collision_mask = 0
	parent.add_child(body)
	return body

func _prop_shape(body: StaticBody3D, shape: Shape3D, point: Vector3) -> void:
	var node := CollisionShape3D.new()
	node.shape = shape
	node.position = point
	body.add_child(node)

func _prop_box(body: StaticBody3D, size: Vector3, point: Vector3) -> void:
	var shape := BoxShape3D.new()
	shape.size = size
	_prop_shape(body, shape, point)

func _courtyard_pillar(point: Vector3) -> void:
	var visual := _prop(COURTYARD_PILLAR_SCENE, point, "CourtyardPillar")
	visual.set_meta("production_asset", "sanctuary_pillar")
	var body := _prop_body(visual, "ColumnCollision")
	# Canonical bounds: 1.6 x 7 x 1.6m. The source's shaft (Y1.2..5.8)
	# has a measured maximum XZ radius .697867m. Collars use small boxes.
	var shaft := CylinderShape3D.new()
	shaft.radius = 0.70
	shaft.height = 4.6
	_prop_shape(body, shaft, Vector3(0,3.5,0))
	_prop_box(body, Vector3(1.5,0.6,1.5), Vector3(0,0.9,0))
	_prop_box(body, Vector3(1.4,1.2,1.4), Vector3(0,6.4,0))

func _courtyard_gateway(point: Vector3) -> void:
	for side in [-1, 1]:
		var base := _column_base(point + Vector3(side * 7.5,0,0))
		base.hide()
	# This frame stays visible independently of the two encounter barriers.
	# Do not put it in gates: their collision child order is gameplay-owned.
	var visual := _prop(COURTYARD_GATEWAY_SCENE, point, "CourtyardGateway")
	visual.set_meta("production_asset", "pilgrim_gateway")
	var body := _prop_body(visual, "FrameCollision")
	for side in [-1, 1]:
		_prop_box(body, Vector3(2.5,6,1.6), Vector3(side * 7.25,3,0))
	_prop_box(body, Vector3(17,1.8,1.6), Vector3(0,6.9,0))

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
