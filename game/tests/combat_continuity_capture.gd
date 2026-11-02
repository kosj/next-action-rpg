extends Node

## Continuous scripted native gameplay; raw MovieWriter carries engine-mixed PCM.
## Logical1x, not wall-clock FPS, direct hearing or a writable gameplay QA API.
## Only Input.parse_input_event drives the normal UI/player. Production Game,
## actors, camera, collision, damage, VFX and save handlers remain authoritative.
const FPS := 60
const STEP := 1.0 / FPS
const KEY_ACTIONS := {"forward":KEY_W,"back":KEY_S,"left":KEY_A,"right":KEY_D,"sprint":KEY_SHIFT,"lock_on":KEY_TAB}

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
var combo_requests := 0
var light_active_samples: Dictionary = {}
var whiff_serial := 0
var whiff_observed := false
var heal_attempts := 0
var observed_heals := 0
var observed_parries := 0
var last_potions := -1
var last_heal_tick := -1000
var locomotion_origin := Vector3.ZERO
var maximum_locomotion_displacement := 0.0
var light_images: Dictionary = {}
var ui_geometry_snapshot: Dictionary = {}
var ui_geometry_history: Array[Dictionary] = []

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
	if int(config.get("fps", 0)) != FPS or int(config.get("frames", 0)) < 840 or int(config.frames) > 3600:
		_fail("Continuity capture requires60Hz and14–60seconds of gameplay")
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
	player.parried.connect(func(): observed_parries += 1)
	var observer := AfterPhysics.new()
	observer.process_mode = Node.PROCESS_MODE_ALWAYS
	observer.process_physics_priority = 1000
	observer.recorder = self
	add_child(observer)
	RenderingServer.frame_post_draw.connect(_after_draw)
	provenance = _provenance()
	print("CONTINUITY_CAPTURE_STAGE title build=", Session.build_id)

func _transition(next: String) -> void:
	stage = next
	stage_start = tick
	events.append({"tick":tick, "type":"stage", "stage":stage})
	ui_geometry_history.append({"tick":tick,"stage":stage,"actual":_ui_geometry()})
	print("CONTINUITY_CAPTURE_STAGE ", stage, " tick=", tick)

func _physics_process(delta: float) -> void:
	if config.is_empty() or finished or finishing or world == null:
		return
	tick += 1
	if absf(delta-STEP) > 0.000001 or Engine.time_scale != 1.0:
		_fail("Fixed native physics delta/time scale changed")
		return
	_drain_releases()
	if bool(config.get("ui_geometry_probe",false)) and tick>=4:
		ui_geometry_snapshot = _ui_geometry()
		pending_images.append("ui-geometry-probe")
		finishing = true
		return
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
				if _click_control(option):
					_transition("quality_popup")
		"quality_popup":
			var option := _find_option(hud.root)
			if option != null and option.get_popup().visible and tick-stage_start > 2:
				var focused := option.get_popup().get_focused_item()
				if focused == int(config.get("quality",1)):
					_tap_key(KEY_ENTER, "quality_confirm")
					_transition("quality_selected")
				elif releases.is_empty():
					_tap_key(KEY_DOWN if focused<int(config.get("quality",1)) else KEY_UP, "quality_next")
		"quality_selected":
			if Session.quality == int(config.get("quality",1)) and tick-stage_start > 2 and _click_button("완료"):
				_transition("new_game")
		"new_game":
			if tick-stage_start > 2 and not is_instance_valid(hud.modal) and _click_button("새로운 서약"):
				_transition("prologue")
		"prologue":
			if tick-stage_start > 2 and _click_button("성역으로 향한다"):
				_transition("input_guard")
		"input_guard":
			if not get_tree().paused and player.active and player.ui_input_guard == 0 and releases.is_empty():
				if Session.quality != int(config.get("quality",1)) or Session.checkpoint != 0 or player.health != player.max_health:
					_fail("Normal fresh journey/quality state is unexpected")
					return
				if bool(config.get("ui_route_probe",false)):
					ui_geometry_snapshot = _ui_geometry()
					pending_images.append("ui-route-ready")
					finishing = true
					return
				gameplay_start = tick
				incoming_health = player.health
				locomotion_origin = player.global_position
				last_potions = player.potions
				pending_images.append("01-normal-gameplay")
				if String(config.get("scenario_name","continuity"))=="contact":
					_begin_approach()
				else:
					_set_key("forward",true)
					_transition("prelude_forward")
		"prelude_forward":
			if tick-stage_start>=24:
				_set_key("forward",false)
				_set_key("left",true)
				_transition("prelude_left")
		"prelude_left":
			if tick-stage_start>=20:
				_set_key("left",false)
				_set_key("right",true)
				_transition("prelude_right")
		"prelude_right":
			if tick-stage_start>=20:
				_set_key("right",false)
				_set_key("forward",true)
				_transition("safe_face_forward")
		"safe_face_forward":
			if tick-stage_start>=6:
				_set_key("forward",false)
				_begin_combo()
		"light_chain":
			if player.strike!=null:
				var attack_label := String(player.strike.presentation_id)
				if combo_requests<3 and attack_label=="light_%d" % combo_requests and player.strike.data.can_cancel(player.strike.elapsed):
					_light_tap()
					combo_requests += 1
			elif combo_requests==3:
				if not whiff_observed:
					_set_mouse(MOUSE_BUTTON_RIGHT,true,"heavy",_center())
					_transition("prelude_charge")
				else:
					_transition("safe_spacing")
			if tick-stage_start>240:
				_fail("Ordinary3-light input chain did not complete within4logical seconds")
		"prelude_charge":
			if player.heavy_held>=0.72 and player.strike==null:
				_set_mouse(MOUSE_BUTTON_RIGHT,false,"heavy",_center())
				pending_images.append("09-safe-charged-whiff-release")
				_transition("prelude_whiff_recovery")
		"prelude_whiff_recovery":
			if player.strike!=null and String(player.strike.presentation_id)=="charged_heavy":
				whiff_serial = player.strike.attack_instance_id
			elif whiff_serial>0:
				whiff_observed = true
				for receipt in receipts:
					if int(receipt.get("attack_instance_id",0))==whiff_serial:
						_fail("Safe-space charged whiff unexpectedly produced contact")
						return
				_attempt_heal("prelude_full_health_heal_attempt")
				_transition("safe_spacing")
			if tick-stage_start>180:
				_fail("Safe-space charged release did not complete within3logical seconds")
		"safe_spacing":
			if tick-gameplay_start>=maxi(0,int(config.frames)-840) and player.strike==null:
				_begin_approach()
			elif player.global_position.z<4.0:
				_set_key("back",true)
			else:
				_set_key("back",false)
				_set_key("forward",true)
				_transition("safe_face_forward")
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
		"normal_recovery":
			# Preserve a stationary recovery sample before ordinary defensive input.
			# Healing/parry success is observed separately, never forced.
			if contact_tick>=0 and tick-contact_tick>96 and player.strike==null:
				if player.health<player.max_health*0.70 and player.potions>0 and tick-last_heal_tick>60:
					_attempt_heal("post_contact_heal_attempt")
				if tick-last_heal_tick>30:
					_set_key("left",tick%240<120)
					_set_key("right",tick%240>=120)
					if tick%60==0:
						_tap_key(KEY_SPACE,"defensive_dodge_attempt")
					if tick%120==30:
						_tap_key(KEY_F,"defensive_parry_attempt")
	if player.dead:
		_fail("Player died during the ordinary gameplay take")
	if gameplay_start>=0 and tick%300==0:
		print("CONTINUITY_PROGRESS gameplay_tick=",tick-gameplay_start," stage=",stage," hp=",player.health)

func _center() -> Vector2:
	return Vector2(get_window().size)*0.5

func _visible_control_rect(control: Control) -> Rect2:
	var clipped := control.get_global_rect().intersection(get_viewport().get_visible_rect())
	var parent := control.get_parent()
	while parent is Control:
		if parent.clip_contents:
			clipped = clipped.intersection(parent.get_global_rect())
		parent = parent.get_parent()
	return clipped

func _ui_geometry() -> Dictionary:
	var controls: Array[Dictionary] = []
	for node in hud.root.find_children("*","Button",true,false):
		var button := node as Button
		var clipped := _visible_control_rect(button)
		controls.append({"text":button.text,"class":button.get_class(),"visible":button.is_visible_in_tree(),
			"global_rect":_json(button.get_global_rect()),"clipped_rect":_json(clipped),"global_transform":_json(button.get_global_transform_with_canvas())})
	var focus := get_viewport().gui_get_focus_owner()
	return {"scope":"Read-only actual native UI geometry; no coordinate transform or route assumed",
		"touch_available":TouchControls.available,"modal_present":is_instance_valid(hud.modal),
		"window_size":_json(Vector2(get_window().size)),"window_position":_json(Vector2(get_window().position)),
		"content_scale_size":_json(Vector2(get_window().content_scale_size)),"content_scale_mode":get_window().content_scale_mode,
		"content_scale_factor":get_window().content_scale_factor,"viewport_rect":_json(get_viewport().get_visible_rect()),
		"viewport_final_transform":_json(get_viewport().get_final_transform()),"viewport_stretch_transform":_json(get_viewport().get_stretch_transform()),
		"root_size":_json(hud.root.size),"focus_path":String(focus.get_path()) if focus!=null else "","buttons":controls}

func _light_tap() -> void:
	_set_mouse(MOUSE_BUTTON_LEFT,true,"light",_center())
	releases.append({"at":tick+1,"kind":"mouse","code":MOUSE_BUTTON_LEFT,"name":"light","point":_center()})

func _begin_combo() -> void:
	combo_requests = 1
	_light_tap()
	_transition("light_chain")

func _begin_approach() -> void:
	for direction: String in ["left","right","back"]:
		_set_key(direction,false)
	_set_key("forward",true)
	_set_key("sprint",true)
	_transition("sprint_to_encounter")

func _attempt_heal(label: String) -> void:
	heal_attempts += 1
	last_heal_tick = tick
	_tap_key(KEY_R,label)

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
	return _click_control(button)

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

func _click_control(control: Control) -> bool:
	var logical_point := control.get_global_rect().get_center()
	var transform := get_viewport().get_final_transform()
	var point := transform*logical_point
	# Do not clamp or randomly retry a target outside the actual viewport.
	if not control.is_visible_in_tree() or not _visible_control_rect(control).has_point(logical_point) or not Rect2(Vector2.ZERO,Vector2(get_window().size)).has_point(point):
		_fail("Native UI target is outside actual logical/physical viewport: "+str(logical_point)+" -> "+str(point))
		return false
	events.append({"tick":tick,"type":"native_ui_target","logical_point":_json(logical_point),"window_point":_json(point),"final_transform":_json(transform)})
	var motion := InputEventMouseMotion.new()
	motion.position = point
	motion.global_position = point
	Input.parse_input_event(motion)
	_set_mouse(MOUSE_BUTTON_LEFT, true, "ui_click", point)
	releases.append({"at":tick+1, "kind":"mouse", "code":MOUSE_BUTTON_LEFT, "name":"ui_click", "point":point})
	return true

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

func _set_mouse(code: MouseButton, pressed: bool, label: String, point := Vector2(-1,-1)) -> void:
	if point.x<0.0:
		point = _center()
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
	var audio_report := _audio_presentation()
	packet["audio_presentation_at_receipt"] = audio_report
	var last_impact: Dictionary = audio_report.get("last_impact",{})
	packet["audio_report_matches_attack_id"] = last_impact.get("attack_id","")==context.get("attack_id","")
	packet["audio_report_matches_point"] = last_impact.get("point",[])==_json(context.get("point",Vector3.ZERO))
	packet["audio_observation_scope"] = "Read after ordinary Game callbacks; Audio report has no serial. Receipt serial remains authoritative; no playback injected or hearing approval."
	receipts.append(packet)
	if String(context.get("source", "")) == "player" and String(context.get("attack_id", "")) == "charged_heavy":
		contact_count += 1
		if contact_tick < 0:
			contact_tick = tick
			pending_images.append("04-actual-confirmed-contact")

func _audio_presentation() -> Dictionary:
	var audio := get_tree().root.get_node_or_null("Audio")
	if audio!=null and audio.has_method("presentation_report"):
		return _json(audio.call("presentation_report"))
	return {"unavailable":true,"scope":"No existing read-only audio presentation API"}

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
	if gameplay_start>=0:
		maximum_locomotion_displacement = maxf(maximum_locomotion_displacement,player.global_position.distance_to(locomotion_origin))
		if player.potions<last_potions:
			observed_heals += last_potions-player.potions
		last_potions = player.potions
		if player.strike!=null:
			var attack_name := String(player.strike.presentation_id)
			if attack_name in ["light_1","light_2","light_3"] and player.strike.elapsed>=player.strike.data.startup and player.strike.elapsed<player.strike.data.startup+player.strike.data.active:
				light_active_samples[attack_name] = int(light_active_samples.get(attack_name,0))+1
				if not light_images.has(attack_name):
					pending_images.append("08-"+attack_name+"-first-active")
					light_images[attack_name] = true
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
		"quality":Session.quality,"render_scale":get_viewport().scaling_3d_scale,"checkpoint":Session.checkpoint,"active_encounter":world.get("active_encounter"),
		"held_inputs":held.duplicate(),"hero":_actor(player),"enemies":enemies,"impact":_json(impact),"audio_presentation":_audio_presentation()})
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
		var original := get_viewport().get_texture().get_image()
		var error := original.save_png(path)
		if error != OK:
			failure = "Could not save original viewport PNG: "+str(error)
			finishing = true
		images.append({"label":label,"path":path,"pixel_size":_json(Vector2(original.get_size())),"tick":tick,"process_frame":Engine.get_process_frames(),
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
		"engine_audio_mix_rate":AudioServer.get_mix_rate(),
		"floor_policy":"Unmodified production CharacterBody/CollisionShape; no fixture position or25mm visual bias"}

func _validate_finish() -> void:
	if String(config.get("scenario_name","continuity"))=="continuity":
		for light: String in ["light_1","light_2","light_3"]:
			if int(light_active_samples.get(light,0))<1:
				_fail("Ordinary input did not produce an active sample of "+light)
				return
		if not whiff_observed or maximum_locomotion_displacement<0.5 or heal_attempts<1:
			_fail("Planned continuity prelude coverage was not actually observed")
			return
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
	push_error("CONTINUITY_CAPTURE_FAIL: "+reason)
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
	var probe_status := "ui_route_probe_captured" if bool(config.get("ui_route_probe",false)) else "ui_geometry_probe_captured"
	var result := {"status":(probe_status if bool(config.get("ui_geometry_probe",false)) or bool(config.get("ui_route_probe",false)) else "scripted_native_gameplay_captured") if failure.is_empty() else "failed", "failure":failure,
		"scope":config.get("scope", "Invalid capture configuration"),"provenance":provenance,"fps":FPS,"logical_speed":1.0,"tick_count":tick,
		"gameplay_start_tick":gameplay_start,"gameplay_frames":tick-gameplay_start+1 if gameplay_start >= 0 else 0,
		"release_tick":release_tick,"contact_tick":contact_tick,"charged_contacts":contact_count,
		"paired_pause_frames":paired_pause_frames,"frames":frames,"input_events":events,"receipts":receipts,"images":images,
		"scenario_name":config.get("scenario_name","continuity"),"ui_geometry":ui_geometry_snapshot,"ui_geometry_history":ui_geometry_history,"observed_coverage":{"light_active_samples":light_active_samples,
			"safe_charged_whiff":whiff_observed,"whiff_attack_instance_id":whiff_serial,"maximum_locomotion_displacement_m":maximum_locomotion_displacement,
			"heal_input_attempts":heal_attempts,"observed_potion_consumptions":observed_heals,"observed_successful_parries":observed_parries,
			"scope":"Actual observed/attempted coverage only. Potion consumption, parry success and contact are not injected; no skin/AV/hearing approval."},
		"ai_variance":"Same input policy; production AI and collision remain active. Actual event timing/positions may differ."}
	var file := FileAccess.open(String(config.snapshot), FileAccess.WRITE)
	if file == null:
		push_error("Could not write capture trace")
		get_tree().quit(2)
		return
	file.store_string(JSON.stringify(result))
	file.close()
	print("CONTINUITY_CAPTURE_RESULT ", result.status, " ticks=", tick, " charged_contacts=", contact_count, " paired_pause_frames=", paired_pause_frames)
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
	if value is Rect2:
		return {"position":_json(value.position),"size":_json(value.size)}
	if value is Transform2D:
		return {"x":_json(value.x),"y":_json(value.y),"origin":_json(value.origin)}
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
