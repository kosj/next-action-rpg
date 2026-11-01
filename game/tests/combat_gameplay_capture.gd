extends Node

## Scripted native gameplay, not a pose theater or a writable gameplay QA API.
## Only Input.parse_input_event drives the normal UI/player. Production Game,
## actors, camera, collision, damage, VFX and save handlers remain authoritative.
const FPS := 60
const STEP := 1.0 / FPS
const KEY_ACTIONS := {"forward":KEY_W, "sprint":KEY_SHIFT, "lock_on":KEY_TAB}

class AfterPhysics:
	extends Node
	var recorder: Node
	func _physics_process(delta: float) -> void:
		recorder.record_after_physics(delta)

var config: Dictionary = {}
var world: Node3D
var player: RunePlayer
var hud: RuneHUD
var rig: RuneCamera
var frames: Array[Dictionary] = []
var events: Array[Dictionary] = []
var receipts: Array[Dictionary] = []
var images: Array[Dictionary] = []
var held: Dictionary = {}
var releases: Array[Dictionary] = []
var pending_images: Array[String] = []
var provenance: Dictionary = {}
var stage := "title"
var stage_start := 0
var tick := 0
var gameplay_start := -1
var first_process_frame := -1
var recorded_tick := -1
var incoming_health := -1.0
var release_tick := -1
var contact_tick := -1
var contact_count := 0
var paired_pause_frames := 0
var charge_seen := false
var finished := false
var finishing := false
var failure := ""

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	process_physics_priority = -1000
	process_priority = 1000
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		push_error("Expected one absolute capture configuration path after --")
		get_tree().quit(2)
		return
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not document is Dictionary:
		push_error("Capture configuration is not an object")
		get_tree().quit(2)
		return
	config = document
	if int(config.get("fps", 0)) != FPS or int(config.get("frames", 0)) < 600 or int(config.frames) > 960:
		_fail("Capture requires 60Hz and 10–16 seconds of gameplay")
		return
	if Engine.time_scale != 1.0 or Engine.physics_ticks_per_second != FPS:
		_fail("Production clock must remain logical 1x / 60Hz")
		return
	if Session.has_save or Session.journey_started:
		_fail("Fresh private user-data directory unexpectedly contains a journey")
		return
	world = load("res://scenes/main.tscn").instantiate() as Node3D
	# The observer must run while menus pause. Game must retain its ordinary
	# pausable mode rather than inheriting this fixture's ALWAYS mode.
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	player = world.get("player") as RunePlayer
	hud = world.get("ui") as RuneHUD
	rig = world.get("rig") as RuneCamera
	if player == null or hud == null or rig == null:
		_fail("Actual main scene did not expose its production actors/UI/camera")
		return
	player.impact_confirmed.connect(_on_impact)
	var observer := AfterPhysics.new()
	observer.process_mode = Node.PROCESS_MODE_ALWAYS
	observer.process_physics_priority = 1000
	observer.recorder = self
	add_child(observer)
	RenderingServer.frame_post_draw.connect(_after_draw)
	provenance = _provenance()
	print("COMBAT_CAPTURE_STAGE title build=", Session.build_id)

func _transition(next: String) -> void:
	stage = next
	stage_start = tick
	events.append({"tick":tick, "type":"stage", "stage":stage})
	print("COMBAT_CAPTURE_STAGE ", stage, " tick=", tick)

func _physics_process(delta: float) -> void:
	if config.is_empty() or finished or finishing or world == null:
		return
	tick += 1
	if absf(delta-STEP) > 0.000001 or Engine.time_scale != 1.0:
		_fail("Fixed native physics delta/time scale changed")
		return
	_drain_releases()
	if gameplay_start < 0 and tick > 240:
		_fail("Normal Settings/New Game/prologue UI did not finish within four logical seconds")
		return
	match stage:
		"title":
			if tick > 3 and _click_button("환경 설정"):
				_transition("settings")
		"settings":
			var option := _find_option(hud.root)
			if tick-stage_start > 2 and option != null:
				_click_control(option)
				_transition("quality_popup")
		"quality_popup":
			var option := _find_option(hud.root)
			if option != null and option.get_popup().visible and tick-stage_start > 2:
				var focused := option.get_popup().get_focused_item()
				if focused == 1:
					_tap_key(KEY_ENTER, "quality_confirm")
					_transition("quality_selected")
				elif releases.is_empty():
					_tap_key(KEY_DOWN, "quality_next")
		"quality_selected":
			if Session.quality == 1 and tick-stage_start > 2 and _click_button("완료"):
				_transition("new_game")
		"new_game":
			if tick-stage_start > 2 and not is_instance_valid(hud.modal) and _click_button("새로운 서약"):
				_transition("prologue")
		"prologue":
			if tick-stage_start > 2 and _click_button("성역으로 향한다"):
				_transition("input_guard")
		"input_guard":
			if not get_tree().paused and player.active and player.ui_input_guard == 0 and releases.is_empty():
				if Session.quality != 1 or Session.checkpoint != 0 or player.health != player.max_health:
					_fail("Normal fresh journey/quality state is unexpected")
					return
				gameplay_start = tick
				incoming_health = player.health
				_set_key("forward", true)
				_set_key("sprint", true)
				pending_images.append("01-normal-gameplay")
				_transition("sprint_to_encounter")
		"sprint_to_encounter":
			if int(world.get("active_encounter")) == 0:
				_tap_key(KEY_TAB, "lock_on")
				_set_mouse(MOUSE_BUTTON_RIGHT, true, "heavy")
				_transition("approach_while_charging")
		"approach_while_charging":
			var target := _target()
			if target != null and _horizontal_distance(player.global_position, target.global_position) <= 2.0:
				_set_key("forward", false)
				_set_key("sprint", false)
				pending_images.append("02-charge-near-real-enemy")
				_transition("incoming_hit_recovery")
		"incoming_hit_recovery":
			# Real AI damage gives the ordinary recovery/invulnerability window.
			# No actor timer, health, position or attack state is assigned here.
			if player.health < incoming_health and player.stagger <= 0.0 and player.hit_pause <= 0.0 and player.heavy_held >= 0.65 and player.strike == null:
				charge_seen = true
				release_tick = tick
				_set_mouse(MOUSE_BUTTON_RIGHT, false, "heavy")
				pending_images.append("03-native-heavy-release")
				_transition("released")
		"released":
			if contact_count > 0:
				_transition("normal_recovery")
			elif tick-release_tick > 180:
				_fail("Released charged strike produced no real confirmed contact within three seconds")
	if player.dead:
		_fail("Player died during the ordinary gameplay take")

func _target() -> RuneEnemy:
	if is_instance_valid(player.locked_target) and player.locked_target is RuneEnemy and not player.locked_target.dead:
		return player.locked_target as RuneEnemy
	return null

func _horizontal_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x-b.x, a.z-b.z).length()

func _click_button(prefix: String) -> bool:
	var button := _find_button(hud.root, prefix)
	if button == null:
		return false
	_click_control(button)
	return true

func _find_button(node: Node, prefix: String) -> Button:
	if node is Button and not node is OptionButton and node.is_visible_in_tree() and not node.disabled and node.text.begins_with(prefix):
		return node as Button
	for child in node.get_children():
		var found := _find_button(child, prefix)
		if found != null:
			return found
	return null

func _find_option(node: Node) -> OptionButton:
	if node is OptionButton and node.is_visible_in_tree():
		return node as OptionButton
	for child in node.get_children():
		var found := _find_option(child)
		if found != null:
			return found
	return null

func _click_control(control: Control) -> void:
	var point := control.get_global_rect().get_center()
	var motion := InputEventMouseMotion.new()
	motion.position = point
	motion.global_position = point
	Input.parse_input_event(motion)
	_set_mouse(MOUSE_BUTTON_LEFT, true, "ui_click", point)
	releases.append({"at":tick+1, "kind":"mouse", "code":MOUSE_BUTTON_LEFT, "name":"ui_click", "point":point})

func _tap_key(code: Key, label: String) -> void:
	_native_key(code, true, label)
	releases.append({"at":tick+1, "kind":"key", "code":code, "name":label})

func _set_key(action: String, pressed: bool) -> void:
	if bool(held.get(action, false)) == pressed:
		return
	held[action] = pressed
	_native_key(KEY_ACTIONS[action], pressed, action)

func _native_key(code: Key, pressed: bool, label: String) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = code
	event.keycode = code
	event.pressed = pressed
	Input.parse_input_event(event)
	events.append({"tick":tick,"type":"native_key","action":label,"code":code,"pressed":pressed})

func _set_mouse(code: MouseButton, pressed: bool, label: String, point := Vector2(640,360)) -> void:
	if label == "heavy":
		held[label] = pressed
	var event := InputEventMouseButton.new()
	event.button_index = code
	event.pressed = pressed
	event.position = point
	event.global_position = point
	Input.parse_input_event(event)
	events.append({"tick":tick,"type":"native_mouse_button","action":label,"code":code,"pressed":pressed,"point":_json(point)})

func _drain_releases() -> void:
	for index in range(releases.size()-1, -1, -1):
		var release := releases[index]
		if int(release.at) > tick:
			continue
		if String(release.kind) == "key":
			_native_key(release.code, false, release.name)
		else:
			_set_mouse(release.code, false, release.name, release.point)
		releases.remove_at(index)

func _on_impact(context: Dictionary) -> void:
	var packet: Dictionary = _json(context)
	packet["observed_tick"] = tick
	packet["physics_frame"] = Engine.get_physics_frames()
	receipts.append(packet)
	if String(context.get("source", "")) == "player" and String(context.get("attack_id", "")) == "charged_heavy":
		contact_count += 1
		if contact_tick < 0:
			contact_tick = tick
			pending_images.append("04-actual-confirmed-contact")

func _art(visual: ActorVisual) -> Dictionary:
	var report := visual.presentation_report()
	report["ground_offset_y"] = visual.ground_offset_y
	report["visual_global_position"] = _json(visual.global_position)
	if is_instance_valid(visual.rig_weapon):
		for marker_name: String in ["GripOrigin", "BladeTip"]:
			var marker := visual.rig_weapon.find_child(marker_name, true, false) as Node3D
			if marker != null:
				report["blade_grip_world" if marker_name == "GripOrigin" else "blade_tip_world"] = _json(marker.global_position)
	if is_instance_valid(visual.skeletal_bridge):
		report["sampled_time"] = visual.skeletal_bridge.sampled_time
		var skeleton := visual.skeletal_bridge.get_skeleton()
		if skeleton != null:
			var points := {}
			for name: String in ["LeftFoot","RightFoot","LeftToeBase","RightToeBase","LeftHand","RightHand"]:
				var bone := skeleton.find_bone(name)
				if bone >= 0:
					points[name] = _json((skeleton.global_transform*skeleton.get_bone_global_pose(bone)).origin)
			report["bone_world_positions"] = points
	return report

func _actor(actor: CharacterBody3D) -> Dictionary:
	var result := {"id":actor.get_instance_id(),"position":_json(actor.global_position),"velocity":_json(actor.velocity),
		"on_floor":actor.is_on_floor(),"health":actor.get("health"),"dead":actor.get("dead"),
		"hit_pause":actor.get("hit_pause"),"stagger":actor.get("stagger"),
		"presentation":_json(actor.call("presentation_snapshot")),"art":_art(actor.get("visual"))}
	var shape: CollisionShape3D
	for child in actor.get_children():
		if child is CollisionShape3D:
			shape = child as CollisionShape3D
			break
	if shape != null and shape.shape is CapsuleShape3D:
		result["capsule_bottom_world_y"] = shape.global_position.y-(shape.shape as CapsuleShape3D).height*0.5
	if actor is RuneEnemy:
		var enemy := actor as RuneEnemy
		result.merge({"kind":enemy.kind,"elite":enemy.elite,"boss":enemy.is_boss,"hit_reaction":enemy.hit_reaction,
			"recoil_requested_m":enemy.recoil_requested_m,"recoil_displacement":_json(enemy.recoil_displacement)})
	else:
		result["invulnerability"] = actor.get("invulnerability")
		result["locked_target_id"] = player.locked_target.get_instance_id() if is_instance_valid(player.locked_target) else 0
	return result

func record_after_physics(delta: float) -> void:
	if world == null or finished or tick == recorded_tick:
		return
	recorded_tick = tick
	var enemies: Array[Dictionary] = []
	var victim_paused := false
	for enemy: RuneEnemy in world.get("active_enemies"):
		if is_instance_valid(enemy):
			enemies.append(_actor(enemy))
			victim_paused = victim_paused or (enemy.hit_pause > 0.0 and enemy.hit_reaction == "heavy_hit")
	if player.hit_pause > 0.0 and victim_paused:
		paired_pause_frames += 1
	var impact: Dictionary = world.call("impact_presentation_report")
	impact.erase("history")
	frames.append({"tick":tick,"physics_frame":Engine.get_physics_frames(),"delta":delta,"stage":stage,
		"gameplay_frame":tick-gameplay_start if gameplay_start >= 0 else -1,"paused":get_tree().paused,
		"quality":Session.quality,"checkpoint":Session.checkpoint,"active_encounter":world.get("active_encounter"),
		"held_inputs":held.duplicate(),"hero":_actor(player),"enemies":enemies,"impact":_json(impact)})
	if not finishing and gameplay_start >= 0 and tick-gameplay_start+1 >= int(config.frames):
		_validate_finish()

func _process(_delta: float) -> void:
	if first_process_frame < 0:
		first_process_frame = Engine.get_process_frames()
	if not frames.is_empty() and rig != null:
		var row: Dictionary = frames.back()
		row["process_frame"] = Engine.get_process_frames()
		row["movie_frame"] = Engine.get_process_frames()-first_process_frame
		row["camera"] = {"position":_json(rig.camera.global_position),"basis":_json(rig.camera.global_basis),
			"fov":rig.camera.fov,"yaw":rig.yaw,"pitch":rig.pitch,"impact":_json(rig.impact_report())}

func _after_draw() -> void:
	if finished or config.is_empty():
		return
	for label: String in pending_images:
		var path := String(config.image_directory).path_join(label+".png")
		var error := get_viewport().get_texture().get_image().save_png(path)
		if error != OK:
			failure = "Could not save original viewport PNG: "+str(error)
			finishing = true
		images.append({"label":label,"path":path,"tick":tick,"process_frame":Engine.get_process_frames(),
			"movie_frame":Engine.get_process_frames()-first_process_frame,"sha256":FileAccess.get_sha256(path)})
	pending_images.clear()
	if finishing:
		_write_result()

func _provenance() -> Dictionary:
	var models := {}
	for profile: String in ["hero","sentinel_melee"]:
		var definition := ProductionCharacterArt.definition(profile)
		var path := String(definition.get("path", ""))
		models[profile] = {"path":path,"sha256":FileAccess.get_sha256(path)}
	var attack := load("res://data/charged_heavy.tres") as Resource
	var curve := {"mode":"baseline_analytic_blade","resource_sha256":FileAccess.get_sha256("res://data/charged_heavy.tres")}
	if attack.has_method("blade_curve_report"):
		curve = attack.call("blade_curve_report")
		curve["resource_sha256"] = FileAccess.get_sha256("res://data/charged_heavy.tres")
	return {"build_id":Session.build_id,"engine":Engine.get_version_info(),"models":models,"curve":curve,
		"scope":config.scope,"source_context":config.source_context,"engine_time_scale":Engine.time_scale,
		"physics_ticks_per_second":Engine.physics_ticks_per_second,"user_data_dir":OS.get_user_data_dir(),
		"initial_has_save":Session.has_save,"renderer":RenderingServer.get_current_rendering_method(),
		"floor_policy":"Unmodified production CharacterBody/CollisionShape; no fixture position or25mm visual bias"}

func _validate_finish() -> void:
	if not charge_seen or release_tick < 0 or contact_count < 1:
		_fail("Bounded normal gameplay did not produce its required charged contact")
		return
	if paired_pause_frames < 1:
		_fail("No actual post-physics frame observed both attacker and heavy-hit victim paused")
		return
	pending_images.append("05-normal-recovery-end")
	finishing = true

func _fail(reason: String) -> void:
	if finishing or finished:
		return
	failure = reason
	push_error("COMBAT_CAPTURE_FAIL: "+reason)
	pending_images.append("failure")
	finishing = true
	if not RenderingServer.frame_post_draw.is_connected(_after_draw):
		_write_result()

func _write_result() -> void:
	finished = true
	# Cleanup only physical input owned by this script; never rewrite game state.
	for action: String in KEY_ACTIONS:
		_set_key(action, false)
	if bool(held.get("heavy", false)):
		_set_mouse(MOUSE_BUTTON_RIGHT, false, "heavy")
	for release in releases:
		if release.kind == "key":
			_native_key(release.code, false, release.name)
		else:
			_set_mouse(release.code, false, release.name, release.point)
	var result := {"status":"scripted_native_gameplay_captured" if failure.is_empty() else "failed", "failure":failure,
		"scope":config.get("scope", "Invalid capture configuration"),"provenance":provenance,"fps":FPS,"logical_speed":1.0,"tick_count":tick,
		"gameplay_start_tick":gameplay_start,"gameplay_frames":tick-gameplay_start+1 if gameplay_start >= 0 else 0,
		"release_tick":release_tick,"contact_tick":contact_tick,"charged_contacts":contact_count,
		"paired_pause_frames":paired_pause_frames,"frames":frames,"input_events":events,"receipts":receipts,"images":images,
		"ai_variance":"Same input policy; production AI and collision remain active. Actual event timing/positions may differ."}
	var file := FileAccess.open(String(config.snapshot), FileAccess.WRITE)
	if file == null:
		push_error("Could not write capture trace")
		get_tree().quit(2)
		return
	file.store_string(JSON.stringify(result))
	file.close()
	print("COMBAT_CAPTURE_RESULT ", result.status, " ticks=", tick, " charged_contacts=", contact_count, " paired_pause_frames=", paired_pause_frames)
	# End the production scene/audio after the final recorded draw, then allow
	# queued node/resource releases to drain. These cleanup frames are retained
	# in the raw movie and excluded from the prescribed delivery frame count.
	set_process(false)
	set_physics_process(false)
	if RenderingServer.frame_post_draw.is_connected(_after_draw):
		RenderingServer.frame_post_draw.disconnect(_after_draw)
	var audio := get_tree().root.get_node_or_null("Audio")
	if audio != null:
		audio.call("stop_all")
	if is_instance_valid(world):
		world.queue_free()
	world = null
	player = null
	hud = null
	rig = null
	var audio_released := true
	if audio != null:
		audio_released = bool(await audio.call("wait_until_stopped"))
	var cleanup := {"actual_audio_weakrefs_released":audio_released,
		"audio_stop_report":audio.call("stop_report") if audio != null else {},
		"scope":"Post-record resource release only; not audio-hearing approval"}
	var cleanup_file := FileAccess.open(String(config.snapshot).get_base_dir().path_join("cleanup.json"), FileAccess.WRITE)
	if cleanup_file != null:
		cleanup_file.store_string(JSON.stringify(cleanup))
		cleanup_file.close()
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().quit(0 if failure.is_empty() and audio_released else 1)

func _json(value: Variant) -> Variant:
	if value is Vector3:
		return [value.x,value.y,value.z]
	if value is Vector2:
		return [value.x,value.y]
	if value is Basis:
		return [_json(value.x),_json(value.y),_json(value.z)]
	if value is Color:
		return [value.r,value.g,value.b,value.a]
	if value is Dictionary:
		var copy := {}
		for key in value:
			copy[String(key)] = _json(value[key])
		return copy
	if value is Array:
		var copy := []
		for item in value:
			copy.append(_json(item))
		return copy
	if value is Object:
		return "[omitted object]"
	return value
