extends "res://tests/lighting_review_capture.gd"

## Actual hub scene with prescribed static cameras and paused production idle.
## No start_game(), save mutation, input, motion or face/finger acceptance claim.
var hub_npcs: Array[Node3D] = []
var hub_checkpoints: Array[Node3D] = []
var animation_controls: Array[Dictionary] = []

func _run() -> void:
	world = load("res://scenes/main.tscn").instantiate() as Node3D
	add_child(world)
	world.set_process(false)
	world.set_physics_process(false)
	var sanctuary := world.get("sanctuary") as Sanctuary
	sanctuary.set_process(false)
	player = world.get("player") as RunePlayer
	rig = world.get("rig") as RuneCamera
	player.active = false
	player.set_physics_process(false)
	player.position = Sanctuary.CHECKPOINTS[0]
	player.position.y = -player.visual.ground_offset_y
	player.facing = Vector3.FORWARD
	player.visual.rotation.y = 0.0
	player.locked_target = null
	player.visual.pose(0.0,0.0,-1.0,false,false,false,player.presentation_snapshot(0.0))
	for child in sanctuary.get_children():
		if child is Node3D and child.has_meta("npc"):
			hub_npcs.append(child as Node3D)
			_freeze_idle(child)
		if child is Node3D and child.has_meta("checkpoint"):
			hub_checkpoints.append(child as Node3D)
	hub_npcs.sort_custom(func(a: Node3D,b: Node3D) -> bool: return int(a.get_meta("npc"))<int(b.get_meta("npc")))
	hub_checkpoints.sort_custom(func(a: Node3D,b: Node3D) -> bool: return int(a.get_meta("checkpoint"))<int(b.get_meta("checkpoint")))
	if hub_npcs.size()!=2 or hub_checkpoints.is_empty():
		push_error("Hub review requires actual NPC0/NPC1 and checkpoint metadata")
		get_tree().quit(2)
		return
	world.set("active_encounter",-1)
	world.set("started",true)
	var ui := world.get("ui") as RuneHUD
	ui.set_process(false)
	ui.menu.hide()
	ui.hud.show()
	ui.root.visible = bool(config.get("show_ui",true))
	ui.region_text.text = "순례자의 안식처"
	rig.cinematic = false
	rig.set_physics_process(false)
	rig.yaw = 0.0
	rig.pitch = -0.18
	Session.shake = false
	for quality: int in config.get("qualities",[0,1]):
		Session.quality = quality
		world.call("apply_quality")
		for view: String in config.get("views",["hubwide","erin","roen","checkpoint"]):
			rig.snap()
			if view=="erin" or view=="roen":
				var npc := hub_npcs[0 if view=="erin" else 1]
				# Camera orientation belongs to the fixed role location, not the
				# presentation root: authorized NPC yaw can differ between sources.
				var toward_spawn := Sanctuary.CHECKPOINTS[0]-npc.global_position
				toward_spawn.y = 0.0
				var role_basis := Basis(Vector3.UP,atan2(-toward_spawn.x,-toward_spawn.z))
				rig.camera.global_position = npc.global_position+role_basis*Vector3(1.45,1.65,-3.9)
				rig.camera.look_at(npc.global_position+Vector3.UP*0.95)
				rig.camera.fov = 38.0
			elif view=="checkpoint":
				rig.camera.global_position = hub_checkpoints[0].global_position+Vector3(3.6,2.9,4.0)
				rig.camera.look_at(hub_checkpoints[0].global_position+Vector3.UP*1.15)
				rig.camera.fov = 38.0
			ui._process(0.0)
			# Allow ordinary presentation rays to settle after the camera change.
			for index in range(3):
				await get_tree().physics_frame
			for index in range(3):
				await RenderingServer.frame_post_draw
			var filename := "%s-q%d.png" % [view,quality]
			var path := String(config.output_directory).path_join(filename)
			if get_viewport().get_texture().get_image().save_png(path)!=OK:
				push_error("Cannot save original hub art viewport raster")
				get_tree().quit(2)
				return
			var shot := _report(view,quality,filename,path)
			shot["camera_control"] = "production_snap_nominal_grounded_checkpoint" if view=="hubwide" else "fixture_closeup_override"
			shot["hub_presentations"] = _npc_reports()
			shot["checkpoint_presentations"] = _checkpoint_reports(sanctuary)
			shots.append(shot)
			print("HUB_ART_REVIEW_SHOT ",filename)
	var result := {"status":"deterministic_actual_scene_captured","scope":config.scope,
		"engine":Engine.get_version_info(),"application_version":ProjectSettings.get_setting("application/config/version"),
		"source_context":config.source_context,"renderer":RenderingServer.get_current_rendering_method(),
		"video_adapter":RenderingServer.get_video_adapter_name(),"viewport":_json(get_viewport().get_visible_rect().size),
		"show_ui":bool(config.get("show_ui",true)),"fixture_controls":["nominal grounded checkpoint Hero","production NPC/checkpoint transforms unchanged by fixture","NPC cameras derive only from role position and checkpoint direction, independent of actual body yaw","production idle paused at zero","Sanctuary cosmetic rotation frozen","production hubwide camera and prescribed closeup cameras","direct actual quality setting"],
		"animation_controls":animation_controls,"sanctuary_static_collision":_static_collision_report(),
		"sanctuary_rng_state":sanctuary.rng.state,"shots":shots}
	var file := FileAccess.open(String(config.result_path),FileAccess.WRITE)
	if file==null:
		push_error("Cannot write hub art report")
		get_tree().quit(2)
		return
	file.store_string(JSON.stringify(result,"\t")+"\n")
	file.close()
	var audio := get_tree().root.get_node_or_null("Audio")
	if audio!=null:
		audio.call("stop_all")
	world.queue_free()
	world = null
	player = null
	rig = null
	hub_npcs.clear()
	hub_checkpoints.clear()
	var released := true
	if audio!=null:
		released = bool(await audio.call("wait_until_stopped"))
	await get_tree().process_frame
	await get_tree().process_frame
	print("HUB_ART_REVIEW_COMPLETE shots=",shots.size()," audio_released=",released)
	get_tree().quit(0 if released else 1)

func _freeze_idle(npc: Node) -> void:
	npc.set_process(false)
	npc.set_physics_process(false)
	for child in npc.find_children("*","AnimationPlayer",true,false):
		var animation := child as AnimationPlayer
		var clip := String(animation.current_animation)
		if clip.is_empty():
			for candidate in animation.get_animation_list():
				if String(candidate).to_lower().ends_with("idle"):
					clip = String(candidate)
					break
		if not clip.is_empty() and animation.has_animation(clip):
			animation.play(clip)
			animation.seek(0.0,true)
			animation.pause()
		animation.active = false
		animation_controls.append({"npc_index":npc.get_meta("npc"),"clip":clip,"seek_seconds":0.0,
			"paused":not animation.is_playing(),"mixer_active":animation.active,"scope":"Fixture idle seek; not observed playback or motion approval"})

func _npc_reports() -> Array[Dictionary]:
	var reports: Array[Dictionary] = []
	for npc in hub_npcs:
		var source := npc.get_script() as Script
		reports.append({"npc_index":int(npc.get_meta("npc")),"global_transform":_json(npc.global_transform),
			"script":source.resource_path if source!=null else "","presentation":_json(npc.call("presentation_report")) if npc.has_method("presentation_report") else {"scope":"Actual baseline prototype; no imported rig/profile report available"}})
	return reports

func _checkpoint_reports(sanctuary: Sanctuary) -> Array[Dictionary]:
	var reports: Array[Dictionary] = []
	for checkpoint in hub_checkpoints:
		var index := int(checkpoint.get_meta("checkpoint"))
		reports.append({"checkpoint_index":index,"global_transform":_json(checkpoint.global_transform),
			"crystal_global_transform":_json(sanctuary.crystals[index].global_transform),
			"presentation":_json(checkpoint.call("presentation_report")) if checkpoint.has_method("presentation_report") else {"scope":"Actual baseline emissive primitive; no relic-module report available"}})
	return reports
