extends Node3D
## Authored, distant sanctuary valley. Mesh presentation only: no collision,
## navigation, lights, process callbacks, or access to Sanctuary's RNG.
## Its silhouette is a candidate for actual-camera review, not AAA approval.

const LIMESTONE: StandardMaterial3D = preload("res://assets/materials/courtyard/wall_limestone.tres")
const FLOOR_STONE: StandardMaterial3D = preload("res://assets/materials/courtyard/floor_stone.tres")
const PROFILE_ID := "sanctuary_atmosphere_v012"
const SIDE_CLEARANCE := 46.0
const FAR_CLEARANCE := -465.0
const TRIANGLE_LIMIT := 24000
const BATCH_LIMIT := 6

# Hand-placed valley sections, with distinct left/right ridge profiles. The
# lower strata connect the floating sanctuary's foundations to a larger valley.
const STATION_Z := [52.0,25.0,2.0,-20.0,-42.0,-66.0,-91.0,-120.0,-154.0,-188.0,-216.0]
const INNER_X := [75.0,66.0,61.0,54.0,49.0,53.0,57.0,50.0,55.0,64.0,73.0]
const LEFT_RIDGE := [22.0,32.0,43.0,37.0,49.0,41.0,54.0,46.0,61.0,50.0,39.0]
const RIGHT_RIDGE := [28.0,41.0,34.0,48.0,40.0,51.0,43.0,58.0,49.0,62.0,44.0]
const LAYER_HEIGHT := [0.0,0.23,0.45,0.64,0.82,1.0]
const LAYER_RECESS := [4.0,0.0,3.0,10.0,22.0,38.0]

var _vertices := PackedVector3Array()
var _normals := PackedVector3Array()
var _uvs := PackedVector2Array()
var _tangents := PackedFloat32Array()

func _ready() -> void:
	name = "SanctuaryBackdrop"
	_cliff_faces()
	_finish("LayeredValleyCliffs", _material(Color("536a78"),6.8,0.60,true))
	_strata_shelves()
	_finish("ErodedStrataShelves", _material(Color("64747a"),6.0,0.52,true))
	_ruined_terraces()
	_finish("RuinedSanctuaryTerraces", _material(Color("b8b3a0"),2.0,0.65))
	_broken_cornices()
	_finish("FracturedTerraceCrowns", _material(Color("a7aa98"),2.0,0.55))
	_far_ridge()
	_finish("FarValleyRidge", _material(Color("566c7c"),9.0,0.35,true))
	set_meta("mesh_only",true)
	set_meta("presentation_profile",PROFILE_ID)
	set_meta("determinism","fixed authored profiles; no RNG")

func _material(tint: Color, tile_meters: float, normal_strength: float, geology: bool = false) -> StandardMaterial3D:
	# Existing irregular flagstone gives geology fractured rock detail; the
	# straight masonry bond is reserved for the constructed sanctuary ruins.
	# Neither CC0 albedo / OpenGL normal / ARM source resource is modified.
	var source: StandardMaterial3D = FLOOR_STONE if geology else LIMESTONE
	var material := source.duplicate() as StandardMaterial3D
	material.albedo_color = tint
	material.uv1_triplanar = true
	material.uv1_world_triplanar = true
	material.uv1_scale = Vector3.ONE / tile_meters
	material.normal_scale = normal_strength
	material.set_meta("backdrop_source_material",source.resource_path)
	return material

func _finish(label: String, material: StandardMaterial3D) -> void:
	if _vertices.is_empty():
		return
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = _vertices
	arrays[Mesh.ARRAY_NORMAL] = _normals
	arrays[Mesh.ARRAY_TANGENT] = _tangents
	arrays[Mesh.ARRAY_TEX_UV] = _uvs
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var node := MeshInstance3D.new()
	node.name = label
	node.mesh = mesh
	node.material_override = material
	# Background geometry must not occupy the near-field cascade or add shadow
	# draws. Both quality modes retain exactly the same authored silhouette.
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	node.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	add_child(node)
	_vertices = PackedVector3Array()
	_normals = PackedVector3Array()
	_uvs = PackedVector2Array()
	_tangents = PackedFloat32Array()

func _triangle(a: Vector3, b: Vector3, c: Vector3, facing: Vector3) -> void:
	var normal := (b-a).cross(c-a).normalized()
	if normal.length_squared() < 0.5:
		return
	if normal.dot(facing) < 0.0:
		normal = -normal
	# Godot uses clockwise front faces. Keep face normals outward, and choose
	# winding independently, including the mirrored side of the valley.
	var points: Array[Vector3] = [a,b,c]
	if (b-a).cross(c-a).dot(normal)>0.0:
		points[1] = c
		points[2] = b
	var tangent := Vector3.UP.cross(normal).normalized()
	if tangent.length_squared()<0.5:
		tangent = Vector3.RIGHT
	for point in points:
		_vertices.append(point)
		_normals.append(normal)
		_uvs.append(Vector2(point.x,point.z)/2.0)
		_tangents.append_array(PackedFloat32Array([tangent.x,tangent.y,tangent.z,1.0]))

func _quad(a: Vector3, b: Vector3, c: Vector3, d: Vector3, facing: Vector3) -> void:
	_triangle(a,b,c,facing)
	_triangle(a,c,d,facing)

func _stratum_point(side: float, station: int, layer: int) -> Vector3:
	var ridge: float = LEFT_RIDGE[station] if side<0.0 else RIGHT_RIDGE[station]
	var x: float = INNER_X[station]+LAYER_RECESS[layer]
	# Small, fixed section variation breaks long straight seams without random
	# rubble noise. The actual innermost vertex remains outside X +/-46m.
	x += sin(station*1.43+layer*0.71+(0.8 if side>0.0 else 0.0))*1.5
	var y: float = -48.0+(ridge+48.0)*LAYER_HEIGHT[layer]
	if layer>0 and layer<LAYER_HEIGHT.size()-1:
		y += sin(station*0.92+layer*1.8)*1.3
	return Vector3(side*maxf(SIDE_CLEARANCE,x),y,STATION_Z[station])

func _cliff_faces() -> void:
	for side: float in [-1.0,1.0]:
		for station in range(STATION_Z.size()-1):
			for layer in range(LAYER_HEIGHT.size()-1):
				_quad(_stratum_point(side,station,layer),_stratum_point(side,station+1,layer),
					_stratum_point(side,station+1,layer+1),_stratum_point(side,station,layer+1),Vector3(-side,0.25,0))
			var top_a := _stratum_point(side,station,5)
			var top_b := _stratum_point(side,station+1,5)
			_quad(top_a,top_b,top_b+Vector3(side*36,-7,0),top_a+Vector3(side*36,-7,0),Vector3.UP)
		# Close each visible end into a broad sloping outcrop, rather than leaving
		# an infinitely thin background card or an uncapped column silhouette.
		for station in [0,STATION_Z.size()-1]:
			var outward := Vector3.BACK if station==0 else Vector3.FORWARD
			for layer in range(LAYER_HEIGHT.size()-1):
				var low := _stratum_point(side,station,layer)
				var high := _stratum_point(side,station,layer+1)
				_quad(low,high,high+Vector3(side*36,-7,0),low+Vector3(side*36,-7,0),outward)

func _strata_shelves() -> void:
	for side: float in [-1.0,1.0]:
		for station in range(1,STATION_Z.size()-2):
			for layer in [2,3,4]:
				# Discontinuous broad ledges follow geological beds. Sloping wedge
				# undersides give these actual depth instead of applied flat stripes.
				if (station+layer+(1 if side>0.0 else 0))%4==0:
					continue
				var a := _stratum_point(side,station,layer)
				var b := _stratum_point(side,station+1,layer)
				var lip := Vector3(-side*(1.5+0.4*sin(station*1.7)),0.5,0)
				var front_a := a+lip
				var front_b := b+lip*0.8
				front_a.x = side*maxf(SIDE_CLEARANCE,absf(front_a.x))
				front_b.x = side*maxf(SIDE_CLEARANCE,absf(front_b.x))
				_quad(a,b,front_b,front_a,Vector3.UP)
				_quad(front_a,front_b,b-Vector3.UP*2.2,a-Vector3.UP*2.2,Vector3(-side,-0.3,0))

func _extrude_x(section: Array[Vector2], x: float, thickness: float) -> void:
	# Convex authored Y/Z profiles: tapered buttresses, chipped wall fragments,
	# and individual radial arch stones. All faces join the same opaque batch.
	var center := Vector2.ZERO
	for point in section:
		center += point
	center /= section.size()
	for side: float in [-1.0,1.0]:
		var face_x := x+side*thickness*0.5
		for index in range(1,section.size()-1):
			_triangle(Vector3(face_x,section[0].y,section[0].x),
				Vector3(face_x,section[index].y,section[index].x),
				Vector3(face_x,section[index+1].y,section[index+1].x),Vector3(side,0,0))
	for index in range(section.size()):
		var a := section[index]
		var b := section[(index+1)%section.size()]
		var outward := (a+b)*0.5-center
		_quad(Vector3(x-thickness*0.5,a.y,a.x),Vector3(x+thickness*0.5,a.y,a.x),
			Vector3(x+thickness*0.5,b.y,b.x),Vector3(x-thickness*0.5,b.y,b.x),Vector3(0,outward.y,outward.x))

func _ruined_terraces() -> void:
	for side: float in [-1.0,1.0]:
		var x: float = side*64.0
		var shift: float = 8.0 if side>0.0 else 0.0
		# A damaged upper ambulatory sits on the rock shoulders behind the
		# existing near arcade. Wide empty bays preserve a permeable silhouette.
		for index in range(5):
			var z := -72.0-index*17.0+shift
			var top := 31.0+(3.5 if index in [1,3] else 0.0)
			if side>0.0 and index==4:
				top = 25.0
			var pier: Array[Vector2] = [Vector2(z-3.4,8),Vector2(z+3.4,8),
				Vector2(z+2.0,top-1),Vector2(z+0.7,top),Vector2(z-1.9,top-0.6)]
			_extrude_x(pier,x,5.5)
			# Tapered transverse buttresses make the lower wall read as weight-
			# bearing architecture, not isolated rectangular skyline spikes.
			var buttress: Array[Vector2] = [Vector2(z-2.7,-1),Vector2(z+2.7,-1),
				Vector2(z+1.5,22),Vector2(z-1.5,22)]
			_extrude_x(buttress,x-side*3.0,6.0)
		for bay in range(4):
			var z := -80.5-bay*17.0+shift
			var segments := 12
			for segment in range(segments):
				# Two partial crowns expose the fracture. They do not all lose the
				# same endpoint or repeat an identical complete semicircle.
				if (side<0.0 and bay==0 and segment>=9) or (side>0.0 and bay==3 and segment<4):
					continue
				var a := PI*(segment+0.025)/segments
				var b := PI*(segment+0.975)/segments
				var section: Array[Vector2] = [Vector2(z+cos(a)*6.5,29+sin(a)*6.5),
					Vector2(z+cos(b)*6.5,29+sin(b)*6.5),
					Vector2(z+cos(b)*8.1,29+sin(b)*8.1),Vector2(z+cos(a)*8.1,29+sin(a)*8.1)]
				_extrude_x(section,x,4.2)

func _broken_cornices() -> void:
	for side: float in [-1.0,1.0]:
		var shift: float = 8.0 if side>0.0 else 0.0
		for index in range(5):
			if side>0.0 and index==4:
				continue
			var z := -72.0-index*17.0+shift
			var y := 31.0+(3.5 if index in [1,3] else 0.0)
			var crown: Array[Vector2] = [Vector2(z-2.8,y-0.7),Vector2(z+2.8,y-0.7),
				Vector2(z+3.2,y+0.5),Vector2(z+1.0,y+0.95),Vector2(z-3.2,y+0.3)]
			_extrude_x(crown,side*64.0,7.2)
		# Fractured retaining-wall tails create a lower horizontal counterpoint
		# to the arch crowns. Each fragment has a deliberately chipped profile.
		for index in range(3):
			var z := -58.0-index*37.0+shift
			var wall: Array[Vector2] = [Vector2(z-13,3),Vector2(z+13,3),Vector2(z+13,13),
				Vector2(z+7,14.5),Vector2(z-3,13.2),Vector2(z-13,16.0)]
			_extrude_x(wall,side*68.0,4.2)

func _far_ridge() -> void:
	# Beyond the final room (Z-375 +/-23), never in an apparent traversable
	# corridor. This supplies a closed valley horizon if the atmosphere reveals
	# it; it must not be pulled forward through playable rooms to defeat fog.
	var heights := [35.0,52.0,67.0,58.0,91.0,77.0,103.0,86.0,68.0,79.0,48.0,32.0]
	for index in range(heights.size()-1):
		var x_a := -220.0+index*40.0
		var x_b := x_a+40.0
		var a := Vector3(x_a,heights[index],-478.0-11.0*sin(index*1.7))
		var b := Vector3(x_b,heights[index+1],-478.0-11.0*sin((index+1)*1.7))
		var mid_a := Vector3(x_a,-8.0,-465.0)
		var mid_b := Vector3(x_b,-8.0,-465.0)
		_quad(mid_a,mid_b,b,a,Vector3(0,0.2,1))
		_quad(a,b,b+Vector3(0,-23,-52),a+Vector3(0,-23,-52),Vector3.UP)
		_quad(mid_a+Vector3(0,-44,0),mid_b+Vector3(0,-44,0),mid_b,mid_a,Vector3.BACK)

func presentation_report() -> Dictionary:
	# Inspect actual runtime mesh arrays and transformed triangle bounds rather
	# than claiming the profile constants prove non-interference or draw cost.
	var meshes: Array[Dictionary] = []
	var triangles := 0
	var vertices := 0
	var surfaces := 0
	var protected_clear := true
	var no_collision_or_lights := true
	for child in find_children("*","",true,false):
		if child is CollisionObject3D or child is CollisionShape3D or child is Light3D or child is NavigationRegion3D or child is NavigationLink3D or child is NavigationObstacle3D:
			no_collision_or_lights = false
		if not child is MeshInstance3D:
			continue
		var node := child as MeshInstance3D
		var mesh := node.mesh
		var item_vertices := 0
		var item_triangles := 0
		var bounds := AABB()
		var started := false
		for surface in range(mesh.get_surface_count()):
			var arrays := mesh.surface_get_arrays(surface)
			var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			# A valid non-indexed ArrayMesh exposes null in ARRAY_INDEX. Keep
			# triangle-soup geometry intact and count its sequential vertices.
			var indices := PackedInt32Array()
			if arrays[Mesh.ARRAY_INDEX] != null:
				indices = arrays[Mesh.ARRAY_INDEX]
			item_vertices += points.size()
			var count := indices.size() if not indices.is_empty() else points.size()
			item_triangles += count/3
			for point in points:
				var world_point: Vector3 = node.global_transform*point
				if not started:
					bounds = AABB(world_point,Vector3.ZERO)
					started = true
				else:
					bounds = bounds.expand(world_point)
			for offset in range(0,count,3):
				var triangle_bounds := AABB()
				for corner in range(3):
					var point_index: int = indices[offset+corner] if not indices.is_empty() else offset+corner
					var point: Vector3 = node.global_transform*points[point_index]
					triangle_bounds = AABB(point,Vector3.ZERO) if corner==0 else triangle_bounds.expand(point)
				var triangle_end := triangle_bounds.end
				if not (triangle_bounds.position.x>=SIDE_CLEARANCE or triangle_end.x<=-SIDE_CLEARANCE or triangle_end.z<=FAR_CLEARANCE):
					protected_clear = false
		triangles += item_triangles
		vertices += item_vertices
		surfaces += mesh.get_surface_count()
		meshes.append({"name":str(node.name),"vertices":item_vertices,"triangles":item_triangles,
			"surfaces":mesh.get_surface_count(),"world_aabb":{"position":bounds.position,"size":bounds.size},
			"source_material":node.material_override.get_meta("backdrop_source_material",""),
			"cast_shadows":node.cast_shadow!=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF})
	return {"profile":PROFILE_ID,"mesh_only":no_collision_or_lights,"no_collision_or_lights":no_collision_or_lights,
		"protected_view_clear":protected_clear,"side_clearance_meters":SIDE_CLEARANCE,"far_z_clearance":FAR_CLEARANCE,
		"mesh_nodes":meshes.size(),"surfaces":surfaces,"vertices":vertices,"triangles":triangles,"meshes":meshes,
		"within_geometry_budget":surfaces<=BATCH_LIMIT and triangles<=TRIANGLE_LIMIT,
		"source_material":"res://assets/materials/courtyard/wall_limestone.tres",
		"geology_source_material":"res://assets/materials/courtyard/floor_stone.tres",
		"determinism":"fixed authored profiles; no RNG","visual_acceptance":"pending actual-camera review"}
