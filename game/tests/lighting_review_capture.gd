extends Node

## Deterministic actual-scene lighting comparison, not gameplay/input evidence.
## Actor placement, idle pose, frozen physics and optional HUD are fixture setup.
var world: Node3D
var player: RunePlayer
var rig: RuneCamera
var actors: Array[RuneEnemy] = []
var config: Dictionary = {}
var shots: Array[Dictionary] = []

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var arguments: PackedStringArray = OS.get_cmdline_user_args()
	if arguments.size() != 1:
		push_error("Lighting review requires one configuration path")
		get_tree().quit(2)
		return
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not document is Dictionary:
		push_error("Lighting review configuration must be an object")
		get_tree().quit(2)
		return
	config = document
	_run.call_deferred()

func _run() -> void:
	world = load("res://scenes/main.tscn").instantiate() as Node3D
	add_child(world)
	# Freeze Game/actors/camera, while production presentation children (for
	# example ray-grounded low-cost shadows) can settle normally before draw.
	world.set_process(false)
	world.set_physics_process(false)
	(world.get("sanctuary") as Sanctuary).set_process(false)
	player = world.get("player") as RunePlayer
	rig = world.get("rig") as RuneCamera
	player.active = false
	player.set_physics_process(false)
	player.position = Vector3(0.0,-player.visual.ground_offset_y,-24.0)
	player.facing = Vector3.FORWARD
	player.visual.rotation.y = 0.0
	player.visual.pose(0.0,0.0,-1.0,false,false,false,player.presentation_snapshot(0.0))
	for index in range(3):
		var enemy := RuneEnemy.new()
		enemy.player = player
		enemy.world = world
		world.add_child(enemy)
		enemy.position = Vector3(0,0,-26.5) if index == 0 else Vector3(-4.0 if index == 1 else 4.0,0,-28.0)
		enemy.position.y = -enemy.visual.ground_offset_y
		enemy.facing = (player.position-enemy.position).normalized()
		enemy.visual.rotation.y = atan2(-enemy.facing.x,-enemy.facing.z)
		enemy.visual.pose(0.0,0.0,-1.0,false,false,false,enemy.presentation_snapshot())
		actors.append(enemy)
		enemy.set_physics_process(false)
	world.set("active_enemies",actors)
	world.set("active_encounter",0)
	world.set("started",true)
	var ui := world.get("ui") as RuneHUD
	ui.set_process(false)
	ui.menu.hide()
	ui.hud.show()
	ui.root.visible = bool(config.get("show_ui",false))
	ui.region_text.text = Sanctuary.TITLES[0]
	ui._process(0.0)
	player.locked_target = actors[0]
	rig.cinematic = false
	rig.set_physics_process(false)
	rig.yaw = 0.0
	rig.pitch = -0.18
	Session.shake = false
	for quality: int in config.get("qualities",[0,1]):
		Session.quality = quality
		world.call("apply_quality")
		for view: String in config.get("views",["fight","overview"]):
			rig.snap()
			if view == "overview":
				rig.camera.global_position = Vector3(9.0,7.0,-23.0)
				rig.camera.look_at(Vector3(0,1.0,-38))
			ui._process(0.0)
			for index in range(3):
				await RenderingServer.frame_post_draw
			var output_name := "%s-q%d.png" % [view,quality]
			var path := String(config.output_directory).path_join(output_name)
			var error := get_viewport().get_texture().get_image().save_png(path)
			if error != OK:
				push_error("Cannot save original lighting raster")
				get_tree().quit(2)
				return
			shots.append(_report(view,quality,output_name,path))
			print("LIGHTING_REVIEW_SHOT ",output_name)
	var result := {"status":"deterministic_actual_scene_captured","scope":config.scope,
		"engine":Engine.get_version_info(),"source_context":config.source_context,
		"renderer":RenderingServer.get_current_rendering_method(),"video_adapter":RenderingServer.get_video_adapter_name(),
		"viewport":_json(get_viewport().get_visible_rect().size),"show_ui":bool(config.get("show_ui",false)),
		"fixture_controls":["prescribed actor locations","idle pose seek","frozen Game and actor processing","fixed camera views","direct actual quality setting"],
		"shapes":"Actual unchanged production Hero/Sentinel, floor/walls/props and production camera in fight view",
		"shots":shots}
	var file := FileAccess.open(String(config.result_path),FileAccess.WRITE)
	if file == null:
		push_error("Cannot write lighting review report")
		get_tree().quit(2)
		return
	file.store_string(JSON.stringify(result,"\t")+"\n")
	file.close()
	var audio := get_tree().root.get_node_or_null("Audio")
	if audio != null:
		audio.call("stop_all")
	world.queue_free()
	world = null
	player = null
	rig = null
	actors.clear()
	var released := true
	if audio != null:
		released = bool(await audio.call("wait_until_stopped"))
	await get_tree().process_frame
	await get_tree().process_frame
	print("LIGHTING_REVIEW_COMPLETE shots=",shots.size()," audio_released=",released)
	get_tree().quit(0 if released else 1)

func _actor_report(profile: String,actor: CharacterBody3D,visual: ActorVisual) -> Dictionary:
	var report := {"profile":profile,"position":_json(actor.position),"art":_json(visual.presentation_report())}
	var grounding := visual.get_node_or_null("PerformanceGrounding")
	if grounding != null and grounding.has_method("presentation_report"):
		report["grounding"] = _json(grounding.call("presentation_report"))
	return report

func _report(view: String,quality: int,output_name: String,path: String) -> Dictionary:
	var lights: Array[Dictionary] = []
	var environment: Dictionary = {}
	var sanctuary := world.get("sanctuary") as Sanctuary
	for node in sanctuary.get_children():
		if node is DirectionalLight3D:
			lights.append({"name":node.name,"rotation_degrees":_json(node.rotation_degrees),"color":_json(node.light_color),
				"energy":node.light_energy,"shadows":node.shadow_enabled,"shadow_max_distance":node.directional_shadow_max_distance})
		if node is WorldEnvironment:
			var e: Environment = node.environment
			environment = {"background_mode":e.background_mode,"ambient_source":e.ambient_light_source,
				"ambient_energy":e.ambient_light_energy,"reflections":e.reflected_light_source,"tonemap":e.tonemap_mode,
				"fog_enabled":e.fog_enabled,"fog_density":e.fog_density,"fog_color":_json(e.fog_light_color)}
	var actor_records: Array[Dictionary] = [_actor_report("hero",player,player.visual)]
	for actor in actors:
		actor_records.append(_actor_report("sentinel_melee",actor,actor.visual))
	return {"view":view,"quality":quality,"quality_label":"balanced" if quality == 0 else "performance",
		"render_scale":get_viewport().scaling_3d_scale,"native_scale_note":"Actual native apply_quality: balanced1.0/performance.65; web balanced starts.8 and DPR is a separate browser check",
		"file":output_name,"sha256":FileAccess.get_sha256(path),"camera":{"position":_json(rig.camera.global_position),"basis":_json(rig.camera.global_basis),"fov":rig.camera.fov},
		"lights":lights,"environment":environment,"actors":actor_records}

func _json(value: Variant) -> Variant:
	if value is Vector3:
		return [value.x,value.y,value.z]
	if value is Vector2:
		return [value.x,value.y]
	if value is Color:
		return [value.r,value.g,value.b,value.a]
	if value is Basis:
		return [_json(value.x),_json(value.y),_json(value.z)]
	if value is Dictionary:
		var result := {}
		for key in value:
			result[str(key)] = _json(value[key])
		return result
	if value is Array:
		var result: Array = []
		for item in value:
			result.append(_json(item))
		return result
	return value
