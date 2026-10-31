extends RefCounted

# Real engine ScreenTouch/Drag/Key/Joypad events and the real world controller.
# No button helper invokes gameplay actions. Run late, before Audio's drain.
const ACTIONS: Array[StringName] = [&"left",&"right",&"forward",&"back",&"light",&"heavy",&"dodge",&"parry",&"heal",&"skill_1",&"skill_2",&"skill_3",&"interact",&"lock_on",&"target_next",&"pause",&"sprint"]
const PLAYER_FIELDS: Array[String] = ["max_health","health","rune","max_rune","potions","active","dead","facing","camera_yaw","locked_target","strike","combo","combo_hits","combo_timeout","input_buffer","buffered_heavy","heavy_held","ui_input_guard","dodge_time","dodge_cooldown","dodge_direction","parry_time","parry_cooldown","invulnerability","hit_pause","stagger","presentation_death_elapsed","presentation_heal_remaining","presentation_epoch","velocity","collision_layer","collision_mask"]
const WORLD_FIELDS: Array[String] = ["started","active_encounter","interaction_kind","interaction_index","last_region","lock_cooldown","play_seconds"]
const CAMERA_FIELDS: Array[String] = ["yaw","pitch","cinematic","time","shake_strength"]
const MODAL_FIELDS: Array[String] = ["modal","modal_panel","modal_column","modal_scroll","modal_body"]
const CONTROL_FIELDS: Array[String] = ["anchor_left","anchor_top","anchor_right","anchor_bottom","offset_left","offset_top","offset_right","offset_bottom","custom_minimum_size","size_flags_horizontal","size_flags_vertical","visible"]

static func _ticks(tree: SceneTree, count: int = 1) -> void:
	for index in range(count):
		await tree.physics_frame
		await tree.process_frame

static func _point(value: Array) -> Vector2:
	return Vector2(value[0],value[1])

static func _margins(value: Array) -> Vector4:
	return Vector4(value[0],value[1],value[2],value[3])

static func _rect(value: Array) -> Rect2:
	return Rect2(Vector2(value[0],value[1]),Vector2(value[2],value[3]))

static func _button(name: String) -> Vector2:
	return _rect(TouchControls.presentation_report().action_rects[name]).get_center()

static func _touch(context: Dictionary, index: int, pressed: bool, position: Vector2, canceled: bool = false) -> void:
	var event := InputEventScreenTouch.new()
	event.index = index
	event.pressed = pressed
	event.position = position
	event.canceled = canceled
	if pressed and not canceled:
		context.fingers[index] = position
	else:
		context.fingers.erase(index)
	Input.parse_input_event(event)
	Input.flush_buffered_events()

static func _drag(context: Dictionary, index: int, position: Vector2) -> void:
	var event := InputEventScreenDrag.new()
	event.index = index
	event.position = position
	event.relative = position-Vector2(context.fingers.get(index,position))
	context.fingers[index] = position
	Input.parse_input_event(event)
	Input.flush_buffered_events()

static func _key(pressed: bool) -> void:
	var event := InputEventKey.new()
	event.physical_keycode = KEY_W
	event.keycode = KEY_W
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()

static func _joy(pressed: bool) -> void:
	var event := InputEventJoypadButton.new()
	event.device = 0
	event.button_index = JOY_BUTTON_X
	event.pressed = pressed
	Input.parse_input_event(event)
	Input.flush_buffered_events()

static func _release_fingers(context: Dictionary) -> void:
	for index: int in context.fingers.keys():
		_touch(context,index,false,context.fingers[index])

static func _owner(index: int) -> String:
	for pointer in TouchControls.presentation_report().active_pointers:
		if int(pointer.index) == index:
			return pointer.owner
	return ""

static func _look_point(report: Dictionary) -> Vector2:
	var rect := _rect(report.look_rect)
	for fraction in [Vector2(.25,.25),Vector2(.5,.5),Vector2(.75,.25)]:
		var point: Vector2 = rect.position+rect.size*fraction
		var free := not _rect(report.joystick_rect).has_point(point)
		for value in report.action_rects.values():
			free = free and not _rect(value).has_point(point)
		if free:
			return point
	return rect.get_center()

static func _layout_valid(report: Dictionary) -> bool:
	var size := _point(report.viewport)
	var margins := _margins(report.safe_margins)
	var safe := Rect2(Vector2(margins.x,margins.y),size-Vector2(margins.x+margins.z,margins.y+margins.w))
	var rects: Array[Rect2] = []
	for action: StringName in ACTIONS:
		if action in [&"left",&"right",&"forward",&"back"]:
			continue
		if not report.action_rects.has(String(action)):
			return false
		var rect := _rect(report.action_rects[String(action)])
		if not rect.position.is_finite() or not rect.size.is_finite() or rect.size.x < 44 or rect.size.y < 44 or not safe.encloses(rect):
			return false
		for previous in rects:
			if previous.intersects(rect):
				return false
		rects.append(rect)
	var stick := _rect(report.joystick_rect)
	if not safe.encloses(stick):
		return false
	for rect in rects:
		if rect.intersects(stick):
			return false
	return safe.encloses(_rect(report.look_rect))

static func _input_map() -> Dictionary:
	var result: Dictionary = {}
	for action: StringName in ACTIONS:
		var events: Array[String] = []
		for event in InputMap.action_get_events(action):
			events.append(event.as_text())
		result[action] = events
	return result

static func _controls(node: Node) -> Array[Control]:
	var result: Array[Control] = []
	if node is Control:
		result.append(node)
	for child in node.get_children():
		result.append_array(_controls(child))
	return result

static func _snapshot(world: Node3D) -> Dictionary:
	var player := world.get("player") as RunePlayer
	var rig := world.get("rig") as RuneCamera
	var ui := world.get("ui") as RuneHUD
	var window := world.get_window()
	var context := {"fingers":{},"player":{},"world":{},"camera":{},"modal":{},"controls":[],"actions":{},
		"player_transform":player.global_transform,"camera_transform":rig.camera.global_transform,
		"world_physics":world.is_physics_processing(),"player_physics":player.is_physics_processing(),"camera_physics":rig.is_physics_processing(),
		"paused":world.get_tree().paused,"touch":TouchControls.presentation_report().duplicate(true),"input_map":_input_map(),
		"window_size":window.size,"content_scale_size":window.content_scale_size,"content_scale_mode":window.content_scale_mode,"content_scale_aspect":window.content_scale_aspect,
		"mouse_mode":Input.mouse_mode,"emulate_mouse":Input.emulate_mouse_from_touch,"emulate_touch":Input.emulate_touch_from_mouse,
		"physical_w":Input.is_physical_key_pressed(KEY_W),"joy_x":Input.is_joy_button_pressed(0,JOY_BUTTON_X),
		"session":Session.snapshot(),"save_sha":FileAccess.get_sha256(Session.save_path) if FileAccess.file_exists(Session.save_path) else "",
		"focus":world.get_viewport().gui_get_focus_owner(),"fixture_origin":Vector3(240,.15,240),"metrics":{}}
	for property in PLAYER_FIELDS:
		context.player[property] = player.get(property)
	for property in WORLD_FIELDS:
		context.world[property] = world.get(property)
	for property in CAMERA_FIELDS:
		context.camera[property] = rig.get(property)
	for property in MODAL_FIELDS:
		context.modal[property] = ui.get(property)
	for control in _controls(ui.root):
		var state: Dictionary = {"node":control,"properties":{},"font_override":control.has_theme_font_size_override("font_size"),"font_size":control.get_theme_font_size("font_size"),"separation_override":control.has_theme_constant_override("separation"),"separation":control.get_theme_constant("separation")}
		for property in CONTROL_FIELDS:
			state.properties[property] = control.get(property)
		if control is Label:
			state.properties["autowrap_mode"] = control.autowrap_mode
			state.properties["text"] = control.text
		context.controls.append(state)
	for action in InputMap.get_actions():
		context.actions[action] = Input.get_action_strength(action)
	if is_instance_valid(ui.modal):
		context["modal_parent"] = ui.modal.get_parent()
		context["modal_index"] = ui.modal.get_index()
		ui.modal.get_parent().remove_child(ui.modal)
		for property in MODAL_FIELDS:
			ui.set(property,null)
	return context

static func _arrange(world: Node3D, context: Dictionary) -> void:
	var player := world.get("player") as RunePlayer
	var rig := world.get("rig") as RuneCamera
	var ui := world.get("ui") as RuneHUD
	_release_fingers(context)
	if is_instance_valid(ui.modal):
		ui.close_modal(false)
	world.set("started",true)
	world.set("active_encounter",-1)
	ui.menu.hide()
	ui.hud.show()
	player.restore(context.fixture_origin)
	player.active = true
	player.collision_mask = 1
	rig.cinematic = false
	rig.yaw = 0.0
	rig.pitch = -.18
	player.camera_yaw = 0.0
	player.facing = Vector3.FORWARD
	world.call("set_paused",false)
	TouchControls.set_gameplay_active(true)
	await _ticks(world.get_tree(),3)

static func _resume(world: Node3D, context: Dictionary) -> void:
	var ui := world.get("ui") as RuneHUD
	_release_fingers(context)
	if is_instance_valid(ui.modal):
		ui.close_modal()
	else:
		world.call("set_paused",false)
	await _ticks(world.get_tree(),3)

static func _exercise(world: Node3D, context: Dictionary, check: Callable) -> bool:
	var tree := world.get_tree()
	var player := world.get("player") as RunePlayer
	var rig := world.get("rig") as RuneCamera
	var ui := world.get("ui") as RuneHUD
	var floor := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(40,1,40)
	shape.shape = box
	floor.add_child(shape)
	world.add_child(floor)
	floor.global_position = Vector3(240,-.5,240)
	context["floor"] = floor
	Session.shake = false
	world.set_physics_process(true)
	player.set_physics_process(true)
	rig.set_physics_process(true)
	for action: StringName in ACTIONS:
		Input.action_release(action)
	TouchControls.available = false
	await _arrange(world,context)
	await tree.process_frame
	_key(true)
	await _ticks(tree,2)
	check.call(player.velocity.z < -6.0 and TouchControls.action_pressed(&"forward"), "Desktop physical W still drives the real player through the shared input helper")
	_key(false)
	await _ticks(tree,2)
	await tree.process_frame
	_joy(true)
	await _ticks(tree,1)
	check.call(player.strike != null and player.strike.data == RunePlayer.LIGHTS[0], "Desktop joypad X still begins the actual canonical light strike before mobile mode")
	_joy(false)
	TouchControls.set_gameplay_active(false)
	TouchControls.available = true
	TouchControls.set_viewport_override(Vector2(960,540),Vector4(12,8,12,12))
	await _arrange(world,context)
	check.call(_input_map() == context.input_map, "Mobile aliases leave all canonical keyboard and gamepad action bindings untouched")
	var landscape: Dictionary = TouchControls.presentation_report()
	check.call(_layout_valid(landscape) and _point(landscape.viewport) == Vector2(960,540), "Landscape touch targets remain at least 44 CSS pixels, inside safe margins and separate from each other and the joystick")
	context.metrics["landscape"] = landscape
	var stick := _point(landscape.joystick_center)
	var look := _look_point(landscape)
	var position_before := player.global_position
	var yaw_before := rig.yaw
	await tree.process_frame
	_touch(context,17,true,stick)
	_drag(context,17,stick+Vector2(0,-float(landscape.joystick_radius)*.9))
	_touch(context,59,true,look)
	_drag(context,59,look+Vector2(24,-10))
	await _ticks(tree,2)
	check.call(player.global_position.distance_to(position_before) > .02 and Vector2(player.velocity.x,player.velocity.z).length() > 4 and absf(rig.yaw-yaw_before) > .05, "Two real nonsequential touch pointers move the actual controller and rotate the actual camera together")
	_touch(context,83,true,_button("light"))
	_drag(context,59,look+Vector2(42,-10))
	await _ticks(tree,1)
	check.call(_owner(17) == "stick" and _owner(59) == "look" and _owner(83) == "action" and player.strike != null and player.strike.data == RunePlayer.LIGHTS[0], "Move, look and light attack coexist through actual ScreenTouch IDs 17, 59 and 83")
	_touch(context,83,false,_button("light"))
	await _ticks(tree,1)
	check.call(_owner(17) == "stick" and _owner(59) == "look" and _owner(83).is_empty() and not Input.is_action_pressed(&"touch_light"), "Lifting the attack finger releases only its alias and preserves movement and camera ownership")
	_touch(context,17,false,stick)
	var look_yaw := rig.yaw
	_drag(context,59,look+Vector2(60,-10))
	await _ticks(tree,1)
	check.call(TouchControls.move_vector().is_zero_approx() and _owner(59) == "look" and absf(rig.yaw-look_yaw) > .03, "Lifting the joystick independently stops its vector while the look finger still controls the camera")
	_touch(context,59,false,look+Vector2(60,-10))
	await _ticks(tree,1)
	var stopped_yaw := rig.yaw
	await _ticks(tree,2)
	check.call(absf(rig.yaw-stopped_yaw) < .00001 and TouchControls.presentation_report().active_pointers.is_empty(), "Lifting the last look pointer leaves no camera drift or captured pointer")
	await _arrange(world,context)
	await tree.process_frame
	_touch(context,83,true,_button("light"))
	_touch(context,83,false,_button("light"))
	await _ticks(tree,1)
	check.call(player.strike != null and player.strike.data == RunePlayer.LIGHTS[0], "A real touch press and release within one render frame still reaches the next physics tick as one light attack")
	await _arrange(world,context)
	await tree.process_frame
	_touch(context,83,true,_button("heavy"))
	await _ticks(tree,ceili(.70*Engine.physics_ticks_per_second))
	check.call(player.heavy_held >= .65 and player.strike == null and bool(player.presentation_snapshot().charge_active), "Holding a real heavy touch advances the real player's charged-heavy clock without releasing an attack")
	_touch(context,83,false,_button("heavy"))
	await _ticks(tree,1)
	check.call(player.strike != null and player.strike.data == RunePlayer.HEAVY and player.heavy_held == 0.0, "Normal heavy-finger release starts the actual heavy strike and consumes its held clock")
	await _arrange(world,context)
	await tree.process_frame
	_key(true)
	_touch(context,17,true,stick)
	_drag(context,17,stick+Vector2(0,float(landscape.joystick_radius)))
	await _ticks(tree,1)
	_touch(context,17,false,stick)
	await _ticks(tree,2)
	check.call(Input.is_physical_key_pressed(KEY_W) and Input.is_action_pressed(&"forward") and TouchControls.move_vector().y < -.9 and player.velocity.z < -6.0, "Releasing a competing backward touch never releases the independently held physical W action")
	_key(false)
	await _arrange(world,context)
	player.health = player.max_health*.25
	player.potions = 3
	var health_before := player.health
	_touch(context,17,true,stick)
	_drag(context,17,stick+Vector2(0,-float(landscape.joystick_radius)))
	_touch(context,83,true,_button("heal"))
	await _ticks(tree,1)
	check.call(player.health > health_before and player.potions == 2 and player.strike == null and Vector2(player.velocity.x,player.velocity.z).length() > 4, "A real heal touch applies the existing instant potion effect while joystick movement remains active")
	await _arrange(world,context)
	var target := RuneEnemy.new()
	target.world = world
	target.player = player
	world.add_child(target)
	target.global_position = player.global_position+Vector3.FORWARD*3
	target.set_physics_process(false)
	context["target"] = target
	world.set("lock_cooldown",0.0)
	_touch(context,83,true,_button("lock_on"))
	await _ticks(tree,1)
	check.call(player.locked_target == target, "A touch lock alias reaches the real world's unhandled-input target selection")
	_release_fingers(context)
	player.locked_target = null
	target.free()
	context.erase("target")
	await _arrange(world,context)
	player.global_position = (world.get("sanctuary") as Sanctuary).npc_positions[0]+Vector3(0,.15,1)
	player.velocity = Vector3.ZERO
	await _ticks(tree,2)
	var npc_ready: bool = world.get("interaction_kind") == "npc" and world.get("interaction_index") == 0
	_touch(context,83,true,_button("interact"))
	await tree.process_frame
	check.call(npc_ready and tree.paused and is_instance_valid(ui.modal) and ui.modal_body.text.contains("아스테르"), "A touch interaction alias opens the real archivist dialog without a synthetic gameplay callback")
	await _resume(world,context)
	await _arrange(world,context)
	world.set("started",false)
	player.active = false
	ui.hud.hide()
	ui.menu.show()
	TouchControls.set_gameplay_active(false)
	await tree.process_frame
	_touch(context,17,true,stick)
	_drag(context,17,stick+Vector2(0,-40))
	await _ticks(tree,2)
	check.call(player.strike == null and TouchControls.presentation_report().pressed_actions.is_empty() and not Input.is_action_pressed(&"touch_light"), "A menu finger in the joystick area does not become a gameplay attack or touch alias")
	world.set("started",true)
	player.active = true
	ui.menu.hide()
	ui.hud.show()
	world.call("set_paused",false)
	await _ticks(tree,3)
	check.call(TouchControls.presentation_report().waiting_release and not TouchControls.gameplay_active and player.strike == null, "Resuming with an old GUI finger waits for its release instead of promoting it to gameplay")
	_touch(context,17,false,stick)
	await _ticks(tree,3)
	_touch(context,83,true,_button("light"))
	await _ticks(tree,1)
	check.call(TouchControls.gameplay_active and player.strike != null, "A fresh touch attack works after the menu finger lifts and the existing UI guard expires")
	await _arrange(world,context)
	_touch(context,83,true,_button("heavy"))
	await _ticks(tree,5)
	_touch(context,83,false,_button("heavy"),true)
	await tree.process_frame
	var canceled_paused := tree.paused
	await _resume(world,context)
	check.call(canceled_paused and player.strike == null and player.heavy_held == 0.0 and TouchControls.presentation_report().pressed_actions.is_empty(), "Canceled heavy touches request a safe pause and resume with no phantom heavy release")
	await _arrange(world,context)
	_touch(context,83,true,_button("heavy"))
	await _ticks(tree,5)
	_touch(context,17,true,_button("pause"))
	await tree.process_frame
	var pause_opened := tree.paused and is_instance_valid(ui.modal)
	ui.close_modal()
	await _ticks(tree,3)
	var safe_resume := player.strike == null and player.heavy_held == 0.0
	_release_fingers(context)
	await _ticks(tree,3)
	check.call(pause_opened and safe_resume and player.strike == null, "The real touch pause button cancels a held heavy safely through pause, resume and old-finger release")
	await _arrange(world,context)
	_touch(context,83,true,_button("heavy"))
	await _ticks(tree,4)
	var cancel_before: int = TouchControls.presentation_report().cancel_count
	TouchControls.set_viewport_override(Vector2(390,844),Vector4(6,28,6,20))
	await tree.process_frame
	var portrait: Dictionary = TouchControls.presentation_report()
	var orientation_cleared: bool = portrait.cancel_count > cancel_before and portrait.active_pointers.is_empty() and portrait.pressed_actions.is_empty()
	await _resume(world,context)
	check.call(orientation_cleared and _layout_valid(portrait) and player.strike == null and player.heavy_held == 0.0, "Orientation changes clear ownership and charge safely while rebuilding usable portrait safe-area targets")
	context.metrics["portrait"] = portrait
	await _arrange(world,context)
	var current: Dictionary = TouchControls.presentation_report()
	var portrait_stick := _point(current.joystick_center)
	var portrait_look := _look_point(current)
	_touch(context,17,true,portrait_stick)
	_drag(context,17,portrait_stick+Vector2(0,-40))
	_touch(context,59,true,portrait_look)
	_drag(context,59,portrait_look+Vector2(12,0))
	_touch(context,83,true,_button("heavy"))
	await _ticks(tree,3)
	TouchControls.notification(Node.NOTIFICATION_APPLICATION_FOCUS_OUT)
	await tree.process_frame
	var focus_report: Dictionary = TouchControls.presentation_report()
	check.call(tree.paused and is_instance_valid(ui.modal) and focus_report.active_pointers.is_empty() and focus_report.pressed_actions.is_empty() and TouchControls.move_vector().is_zero_approx(), "Actual focus-loss notification clears every touch owner and asks the real game to pause")
	await _resume(world,context)
	var resumed_yaw := rig.yaw
	await _ticks(tree,2)
	check.call(player.strike == null and player.heavy_held == 0.0 and TouchControls.move_vector().is_zero_approx() and absf(rig.yaw-resumed_yaw) < .00001, "Focus-loss recovery leaves no sticky movement, camera drift or phantom heavy strike")
	return true

static func _restore(world: Node3D, context: Dictionary) -> void:
	var tree := world.get_tree()
	var player := world.get("player") as RunePlayer
	var rig := world.get("rig") as RuneCamera
	var ui := world.get("ui") as RuneHUD
	world.set_physics_process(false)
	player.set_physics_process(false)
	rig.set_physics_process(false)
	player.active = false
	world.set("started",false)
	tree.paused = false
	TouchControls.set_gameplay_active(false)
	_release_fingers(context)
	TouchControls.cancel_all("native_fixture_cleanup")
	if is_instance_valid(ui.modal):
		ui.close_modal(false)
	if context.has("target") and is_instance_valid(context.target):
		context.target.free()
	if context.has("floor") and is_instance_valid(context.floor):
		context.floor.free()
	await tree.process_frame
	TouchControls.available = bool(context.touch.available)
	TouchControls.set_viewport_override(_point(context.touch.viewport_override),_margins(context.touch.safe_margins_override))
	var window := world.get_window()
	window.size = context.window_size
	window.content_scale_size = context.content_scale_size
	window.content_scale_mode = context.content_scale_mode
	window.content_scale_aspect = context.content_scale_aspect
	for property in WORLD_FIELDS:
		world.set(property,context.world[property])
	for property in PLAYER_FIELDS:
		player.set(property,context.player[property])
	player.active = false
	player.global_transform = context.player_transform
	for property in CAMERA_FIELDS:
		rig.set(property,context.camera[property])
	rig.camera.global_transform = context.camera_transform
	Session.shake = bool(context.session.settings.shake)
	if context.has("modal_parent") and is_instance_valid(context.modal.modal):
		var parent: Node = context.modal_parent
		parent.add_child(context.modal.modal)
		parent.move_child(context.modal.modal,mini(int(context.modal_index),parent.get_child_count()-1))
	for property in MODAL_FIELDS:
		ui.set(property,context.modal[property])
	for state in context.controls:
		# Timed HUD labels may expire while real physics/input is exercised.
		# Casting a freed Object raises before a post-cast validity check runs.
		if not is_instance_valid(state.node):
			continue
		var control := state.node as Control
		if not is_instance_valid(control):
			continue
		for property in state.properties:
			control.set(property,state.properties[property])
		if state.font_override:
			control.add_theme_font_size_override("font_size",state.font_size)
		else:
			control.remove_theme_font_size_override("font_size")
		if state.separation_override:
			control.add_theme_constant_override("separation",state.separation)
		else:
			control.remove_theme_constant_override("separation")
	TouchControls.set_gameplay_active(bool(context.touch.desired_gameplay_active))
	_key(bool(context.physical_w))
	_joy(bool(context.joy_x))
	for action in context.actions:
		if float(context.actions[action]) > 0:
			Input.action_press(action,context.actions[action])
		else:
			Input.action_release(action)
	await _ticks(tree,2)
	Input.emulate_mouse_from_touch = bool(context.emulate_mouse)
	Input.emulate_touch_from_mouse = bool(context.emulate_touch)
	Input.mouse_mode = context.mouse_mode
	player.active = bool(context.player.active)
	player.set_physics_process(bool(context.player_physics))
	rig.set_physics_process(bool(context.camera_physics))
	world.set_physics_process(bool(context.world_physics))
	tree.paused = bool(context.paused)
	if is_instance_valid(context.focus) and context.focus.is_inside_tree():
		context.focus.grab_focus()
	player.visual.pose(0.0,Vector2(player.velocity.x,player.velocity.z).length(),-1.0,false,false,player.dead,player.presentation_snapshot())

static func run(world: Node3D, check: Callable) -> bool:
	var before: Dictionary = TouchControls.presentation_report()
	var neutral: bool = before.active_pointers.is_empty() and before.observed_touch_indices.is_empty()
	check.call(neutral, "Native mobile fixture starts without taking over an existing real touch gesture")
	if not neutral:
		return false
	# Deterministic coverage for a transient HUD control expiring after the
	# snapshot, rather than depending on CI timing of a floating damage label.
	var transient := Control.new()
	transient.name = "NativeFixtureTransientUI"
	transient.mouse_filter = Control.MOUSE_FILTER_IGNORE
	(world.get("ui") as RuneHUD).root.add_child(transient)
	var context := _snapshot(world)
	transient.free()
	var completed: bool = await _exercise(world,context,check)
	# Even a runtime error in the inner exercise returns its default false here;
	# restore shared input/window/autoload/UI state before reporting completion.
	await _restore(world,context)
	var after: Dictionary = TouchControls.presentation_report()
	var actions_restored := true
	for action in context.actions:
		actions_restored = actions_restored and is_equal_approx(Input.get_action_strength(action),float(context.actions[action]))
	check.call(actions_restored and Input.is_physical_key_pressed(KEY_W) == context.physical_w and Input.is_joy_button_pressed(0,JOY_BUTTON_X) == context.joy_x and _input_map() == context.input_map, "Native mobile fixture restores original keyboard/gamepad/action state and canonical bindings")
	check.call(after.available == context.touch.available and after.desired_gameplay_active == context.touch.desired_gameplay_active and after.active_pointers.is_empty() and after.observed_touch_indices.is_empty() and world.get_window().size == context.window_size and world.get_window().content_scale_size == context.content_scale_size and world.get_window().content_scale_mode == context.content_scale_mode and Input.mouse_mode == context.mouse_mode and Input.emulate_mouse_from_touch == context.emulate_mouse, "Native mobile fixture restores window, pointer emulation and TouchControls context")
	var player := world.get("player") as RunePlayer
	var rig := world.get("rig") as RuneCamera
	check.call(world.is_physics_processing() == context.world_physics and player.is_physics_processing() == context.player_physics and rig.is_physics_processing() == context.camera_physics and world.get_tree().paused == context.paused and player.active == context.player.active, "Restoration continues past expired HUD controls and restores controller processing and pause state")
	var saved_sha := FileAccess.get_sha256(Session.save_path) if FileAccess.file_exists(Session.save_path) else ""
	check.call(Session.snapshot() == context.session and saved_sha == context.save_sha, "Native touch tests leave progress, settings and the existing save file unchanged")
	print("RUNEFALL_MOBILE_INPUT: ",JSON.stringify({"completed":completed,"pointer_ids":[17,59,83],"landscape_viewport":context.metrics.get("landscape",{}).get("viewport",[]),"portrait_viewport":context.metrics.get("portrait",{}).get("viewport",[]),"source_sha256":FileAccess.get_sha256("res://scripts/ui/touch_controls.gd"),"scope":"Native event/controller/pointer/lifecycle regression, not browser CSS/touch-hardware or mobile performance approval."}))
	return completed
