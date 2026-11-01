extends RefCounted

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _floor(stage: Node3D, point: Vector3, size: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.collision_layer = 1
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	stage.add_child(body)
	body.position = point
	return body

static func _actor(stage: Node3D, point: Vector3) -> CharacterBody3D:
	var body := CharacterBody3D.new()
	body.collision_layer = 2
	body.collision_mask = 1
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.height = 1.8
	capsule.radius = .36
	shape.shape = capsule
	shape.position.y = .9
	body.add_child(shape)
	stage.add_child(body)
	body.position = point
	# Exercise the production ActorVisual hook, not a substitute ellipse.
	body.add_child(ActorVisual.new())
	return body

static func _shadow(body: CharacterBody3D) -> GroundingShadow:
	return (body.get_child(1) as ActorVisual).grounding_shadow

static func run(world: Node3D, check: Callable) -> bool:
	var tree := world.get_tree()
	var saved_quality: int = Session.quality
	var viewport := SubViewport.new()
	viewport.own_world_3d = true
	viewport.size = Vector2i(320,240)
	world.add_child(viewport)
	var stage := Node3D.new()
	viewport.add_child(stage)
	var floor_body := _floor(stage,Vector3(0,-.1,0),Vector3(8,.2,8))
	var actor := _actor(stage,Vector3.ZERO)
	var shadow := _shadow(actor)
	var before := actor.global_transform
	Session.quality = 0
	await _tick(tree)
	await _tick(tree)
	check.call(not shadow.patch.visible,"Balanced mode never draws an approximation over the actual light shadow")
	Session.quality = 1
	await _tick(tree)
	await _tick(tree)
	check.call(shadow.patch.visible and absf(shadow.patch.global_position.y-.012)<.0001 and actor.global_transform==before,"Performance grounding lands above an actual layer1 floor without moving its actor")
	check.call(shadow.patch.cast_shadow==GeometryInstance3D.SHADOW_CASTING_SETTING_OFF and shadow.get_child_count()==1 and shadow.get_child(0) is MeshInstance3D,"Grounding adds one finite non-casting mesh and no collision or light node")
	var grounded_opacity: float = shadow.material.get_shader_parameter("opacity")
	actor.position.y = .7
	for index in range(8):
		await _tick(tree)
	var raised_opacity: float = shadow.material.get_shader_parameter("opacity")
	check.call(shadow.patch.visible and raised_opacity>0.0 and raised_opacity<grounded_opacity*.5,"Raising the actual capsule fades the approximation instead of attaching a dark disc to airborne feet")
	actor.position.y = 1.1
	for index in range(8):
		await _tick(tree)
	check.call(not shadow.patch.visible,"Bodies above the finite grounding range do not retain a floating shadow")
	actor.position = Vector3(20,0,0)
	for index in range(4):
		await _tick(tree)
	check.call(not shadow.patch.visible and not shadow.presentation_report().cached_ground,"Moving past the real floor edge invalidates the previous support instead of projecting through empty space")
	actor.position = Vector3.ZERO
	for index in range(8):
		await _tick(tree)
	var before_queries: int = shadow.presentation_report().query_count
	var start_physics_frame := Engine.get_physics_frames()
	for index in range(12):
		await _tick(tree)
	var query_delta: int = shadow.presentation_report().query_count-before_queries
	var sampled_physics_frames := Engine.get_physics_frames()-start_physics_frame
	var maximum_queries := ceili(float(sampled_physics_frames)/Engine.physics_ticks_per_second*10.0)+1
	check.call(query_delta>=1 and query_delta<=maximum_queries,"A stationary actual actor reuses support within the10Hz floor-query budget across actual elapsed physics frames")
	var sibling := _actor(stage,Vector3(1,0,0))
	await _tick(tree)
	await _tick(tree)
	var other := _shadow(sibling)
	check.call(shadow.patch.mesh==other.patch.mesh and shadow.material.shader==other.material.shader and shadow.material!=other.material,"Grounding shares geometry and shader while per-actor fade materials remain independent")
	actor.position.y = .7
	for index in range(8):
		await _tick(tree)
	check.call(float(other.material.get_shader_parameter("opacity"))>float(shadow.material.get_shader_parameter("opacity")),"An airborne actor cannot fade another actor's shared-shader grounding")
	Session.quality = 0
	shadow.refresh_quality()
	other.refresh_quality()
	check.call(not shadow.patch.visible and not other.patch.visible,"The ordinary quality refresh removes both approximation meshes immediately")
	Session.quality = 1
	actor.position = Vector3.ZERO
	var extras: Array[CharacterBody3D] = []
	for index in range(10):
		extras.append(_actor(stage,Vector3(float(index%4)-1.5,0,float(index/4)-1.0)))
	for index in range(8):
		await _tick(tree)
	var visible := int(shadow.patch.visible)+int(other.patch.visible)
	for extra in extras:
		visible += int(_shadow(extra).patch.visible)
	check.call(visible>=1 and visible<=8 and GroundingShadow.visible_budget_used()<=8,"More real actors cannot exceed the finite eight-ellipse visible budget")
	actor.scale = Vector3(1,2,1)
	await _tick(tree)
	check.call(not shadow.patch.visible,"Unsupported nonuniform actor scale fails closed rather than stretching the patch across a floor")
	for extra in extras:
		extra.free()
	sibling.free()
	actor.scale = Vector3.ONE
	actor.position = Vector3.ZERO
	floor_body.free()
	for index in range(8):
		await _tick(tree)
	check.call(not shadow.patch.visible and not shadow.presentation_report().cached_ground,"Removing actual support hides the cached patch instead of retaining it through empty space")
	var steep := _floor(stage,Vector3(0,-.1,0),Vector3(8,.2,8))
	steep.rotation.z = deg_to_rad(65.0)
	for index in range(8):
		await _tick(tree)
	check.call(not shadow.patch.visible and not shadow.presentation_report().cached_ground and shadow.presentation_report().reason=="no_supported_ground","A real steep side surface cannot be mistaken for upward supporting ground")
	steep.rotation.z = deg_to_rad(25.0)
	for index in range(8):
		await _tick(tree)
	check.call(shadow.patch.visible and shadow.patch.global_basis.y.normalized().dot(Vector3.UP.rotated(Vector3.BACK,deg_to_rad(25.0)))>.999,"A supported incline aligns the finite patch to the measured floor normal")
	var report := {"scope":"Native actual floor/ledge/height/quality/resource/budget fixtures; no raster, performance, physical foot shadow or AAA approval",
		"grounded_opacity":grounded_opacity,"raised_opacity":raised_opacity,"stationary_query_delta":query_delta,"sampled_physics_frames":sampled_physics_frames,"visible_fixture_ellipses":visible,
		"grounding_source_sha256":FileAccess.get_sha256("res://scripts/actors/grounding_shadow.gd"),
		"shader_sha256":FileAccess.get_sha256("res://assets/shaders/grounding_shadow.gdshader")}
	var path := ProjectSettings.globalize_path("res://../build/verification/grounding-shadow/native.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report,"\t")+"\n")
		file.close()
	viewport.free()
	Session.quality = saved_quality
	await _tick(tree)
	check.call(GroundingShadow.visible_budget_used()<=8,"Freeing the isolated actor tree releases its grounding budget without retaining actor nodes")
	return true
