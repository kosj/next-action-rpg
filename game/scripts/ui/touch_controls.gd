extends CanvasLayer
## Touch owns only touch_* InputMap aliases. Physical actions are never released.

signal layout_changed
signal request_pause

const ACTIONS: Array[StringName] = [&"light", &"heavy", &"dodge", &"parry", &"heal", &"skill_1", &"skill_2", &"skill_3", &"interact", &"lock_on", &"target_next", &"pause", &"sprint"]
const MOVEMENT: Array[StringName] = [&"left", &"right", &"forward", &"back"]
const GRID_ACTIONS: Array[StringName] = [&"skill_1", &"skill_2", &"skill_3", &"heal", &"sprint", &"lock_on", &"target_next", &"interact", &"parry", &"dodge", &"heavy", &"light"]
const LABELS := {&"light":"공격", &"heavy":"강공", &"dodge":"회피", &"parry":"패링", &"heal":"회복", &"skill_1":"룬 1", &"skill_2":"룬 2", &"skill_3":"룬 3", &"interact":"대화", &"lock_on":"조준", &"target_next":"전환", &"sprint":"질주"}
const ACTION_FONT_SIZE: int = 14
const HELPER_FONT_SIZE: int = 10
const BASE_FONT: Font = preload("res://assets/fonts/NotoSansKR.ttf")
const WEB_METRICS := """(function(){
 const c=document.getElementById('canvas')||document.querySelector('canvas');
 if(!window.__touchControlsBridge){
  window.__touchControlsBridge={cancelSerial:0};
  document.addEventListener('touchcancel',function(e){
   if(c&&(e.target===c||c.contains(e.target)))window.__touchControlsBridge.cancelSerial++;
  },{capture:true,passive:true});
 }
 const s=document.getElementById('safe-area');const p=s?getComputedStyle(s):null;
 return JSON.stringify({touch:(navigator.maxTouchPoints||0)>0||matchMedia('(any-pointer: coarse)').matches,
 width:c?c.clientWidth:0,height:c?c.clientHeight:0,
 safe:p?[parseFloat(p.paddingLeft)||0,parseFloat(p.paddingTop)||0,parseFloat(p.paddingRight)||0,parseFloat(p.paddingBottom)||0]:[0,0,0,0],
 cancelSerial:window.__touchControlsBridge.cancelSerial});
})()"""

class TouchSurface extends Control:

	var controls: CanvasLayer

	func _draw() -> void:
		if is_instance_valid(controls):
			controls.call("draw_surface", self)

var available: bool = false:
	set(value):
		if available == value:
			return
		available = value
		if is_inside_tree():
			_availability_changed()
var gameplay_active: bool = false
var safe_margins: Vector4 = Vector4.ZERO

var _wanted_active: bool = false
var _activation_scheduled: bool = false
var _waiting_release: bool = false
var _surface: TouchSurface
var _button_rects: Dictionary = {}
var _joystick_rect := Rect2()
var _look_rect := Rect2()
var _joystick_center := Vector2.ZERO
var _joystick_radius: float = 48.0
var _viewport_css := Vector2.ZERO
var _viewport_override := Vector2.ZERO
var _safe_override := Vector4.ZERO
var _override_restore_window_size := Vector2i.ZERO
var _base_content_size := Vector2i.ZERO
var _base_content_mode: int = 0
var _applying_metrics: bool = false
var _viewport_sync_pending: bool = false
var _layout_generation: int = 0
var _poll_time: float = 0.0
var _web_cancel_serial: int = 0
var _pointers: Dictionary = {}
var _observed: Dictionary = {}
var _suppressed_ids: Dictionary = {}
var _refs: Dictionary = {}
var _stick_id: int = -1
var _look_id: int = -1
var _stick := Vector2.ZERO
var _look_delta := Vector2.ZERO
var _canceling: bool = false
var _cancel_count: int = 0
var _last_cancel_reason: String = ""
var _merged: Dictionary = {}
var _edges: Dictionary = {}
var _blocked_physics: Dictionary = {}
var _blocked_process: Dictionary = {}
var _normal_style: StyleBoxFlat
var _pressed_style: StyleBoxFlat
var _font: FontVariation

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 25
	Input.emulate_mouse_from_touch = true
	_base_content_size = get_window().content_scale_size
	_base_content_mode = get_window().content_scale_mode
	for action: StringName in ACTIONS + MOVEMENT:
		var alias := _alias(action)
		if not InputMap.has_action(alias):
			InputMap.add_action(alias, 0.2)
		_merged[action] = _raw_pressed(action)
	_surface = TouchSurface.new()
	_surface.name = "TouchSurface"
	_surface.controls = self
	_surface.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_surface.focus_mode = Control.FOCUS_NONE
	add_child(_surface)
	_surface.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_normal_style = _style(Color(0.025, 0.045, 0.065, 0.66), Color(0.72, 0.79, 0.79, 0.5))
	_pressed_style = _style(Color(0.35, 0.29, 0.13, 0.82), Color(1.0, 0.84, 0.46, 0.95))
	_font = FontVariation.new()
	_font.base_font = BASE_FONT
	_font.variation_opentype = {0x77676874:430.0}
	get_viewport().size_changed.connect(_on_viewport_resized)
	get_window().focus_exited.connect(_on_focus_lost)
	var detected: bool = OS.has_feature("android") or OS.has_feature("ios")
	if DisplayServer.has_method("is_touchscreen_available"):
		detected = detected or bool(DisplayServer.call("is_touchscreen_available"))
	var metrics := _web_metrics()
	detected = detected or bool(metrics.get("touch", false))
	available = detected
	_sync_viewport(metrics)
	_update_visibility()

func _style(background: Color, border: Color) -> StyleBoxFlat:
	var result := StyleBoxFlat.new()
	result.bg_color = background
	result.border_color = border
	result.set_border_width_all(1)
	result.set_corner_radius_all(12)
	return result

func _alias(action: StringName) -> StringName:
	return StringName("touch_" + String(action))

func _raw_pressed(action: StringName) -> bool:
	return (InputMap.has_action(action) and Input.is_action_pressed(action)) or (InputMap.has_action(_alias(action)) and Input.is_action_pressed(_alias(action)))

func _native_edge(action: StringName, pressed: bool) -> bool:
	var alias := _alias(action)
	if pressed:
		return (InputMap.has_action(action) and Input.is_action_just_pressed(action)) or (InputMap.has_action(alias) and Input.is_action_just_pressed(alias))
	return (InputMap.has_action(action) and Input.is_action_just_released(action)) or (InputMap.has_action(alias) and Input.is_action_just_released(alias))

func _stamp(action: StringName, pressed: bool) -> void:
	var edge: Dictionary = _edges.get(action, {})
	var prefix: String = "p" if pressed else "r"
	# Input 4.7 stamps real events physics+1 / current process. A direct
	# Input.action_press can first be observed in its already-due physics tick.
	var physics_frame: int = Engine.get_physics_frames() + 1
	if Engine.is_in_physics_frame() and _native_edge(action, pressed):
		physics_frame = Engine.get_physics_frames()
	edge[prefix + "_physics"] = physics_frame
	edge[prefix + "_process"] = Engine.get_process_frames()
	_edges[action] = edge

func _observe_action(action: StringName) -> void:
	var down := _raw_pressed(action)
	var previous: bool = bool(_merged.get(action, false))
	if down != previous:
		_merged[action] = down
		if not _canceling:
			_stamp(action, down)
	elif not down and not previous and not _canceling and _native_edge(action, true) and _native_edge(action, false):
		# Direct API press+release can happen without an _input callback. Keep
		# both edges for that clock domain; querying never consumes them.
		var frame: int = Engine.get_physics_frames() if Engine.is_in_physics_frame() else Engine.get_process_frames()
		var suffix: String = "_physics" if Engine.is_in_physics_frame() else "_process"
		var edge: Dictionary = _edges.get(action, {})
		if int(edge.get("p" + suffix, -1)) != frame:
			_stamp(action, true)
			_stamp(action, false)

func action_pressed(action: StringName) -> bool:
	_observe_action(action)
	return _raw_pressed(action)

func _logical_edge(action: StringName, pressed: bool) -> bool:
	_observe_action(action)
	var physics := Engine.is_in_physics_frame()
	var frame: int = Engine.get_physics_frames() if physics else Engine.get_process_frames()
	var blocked: Dictionary = _blocked_physics if physics else _blocked_process
	if frame <= int(blocked.get(action, -1)):
		return false
	if not pressed and _raw_pressed(action):
		return false
	var key: String = ("p" if pressed else "r") + ("_physics" if physics else "_process")
	return int(_edges.get(action, {}).get(key, -1)) == frame and _native_edge(action, pressed)

func action_just_pressed(action: StringName) -> bool:
	return _logical_edge(action, true)

func action_just_released(action: StringName) -> bool:
	return _logical_edge(action, false)

func event_pressed(event: InputEvent, action: StringName) -> bool:
	return (InputMap.has_action(action) and event.is_action_pressed(action)) or (InputMap.has_action(_alias(action)) and event.is_action_pressed(_alias(action)))

func move_vector() -> Vector2:
	return (Input.get_vector("left", "right", "forward", "back") + _stick).limit_length(1.0)

func take_look_delta() -> Vector2:
	var result := _look_delta
	_look_delta = Vector2.ZERO
	return result

func set_gameplay_active(value: bool) -> void:
	if _wanted_active == value:
		return
	_wanted_active = value
	if not value:
		gameplay_active = false
		_waiting_release = false
		cancel_all("gameplay_inactive")
		Input.emulate_mouse_from_touch = true
		_update_visibility()
	else:
		_schedule_activation()

func _schedule_activation() -> void:
	if _activation_scheduled:
		return
	_activation_scheduled = true
	call_deferred("_commit_activation")

func _commit_activation() -> void:
	_activation_scheduled = false
	if not _wanted_active:
		return
	# A menu button can run inside an emulated MouseDown before the original
	# ScreenTouchDown reaches us. Always defer, then wait for all GUI fingers.
	_waiting_release = available and not _observed.is_empty()
	if _waiting_release:
		gameplay_active = false
		Input.emulate_mouse_from_touch = true
	else:
		gameplay_active = true
		Input.emulate_mouse_from_touch = not available
	_update_visibility()

func _availability_changed() -> void:
	if _surface == null:
		return
	if not available:
		cancel_all("touch_unavailable")
		Input.emulate_mouse_from_touch = true
		_applying_metrics = true
		get_window().content_scale_size = _base_content_size
		get_window().content_scale_mode = _base_content_mode
		_applying_metrics = false
	else:
		gameplay_active = false
		_sync_viewport()
		if _wanted_active:
			_schedule_activation()
	_update_visibility()
	layout_changed.emit()

func _update_visibility() -> void:
	if _surface != null:
		_surface.visible = available and gameplay_active
		_surface.queue_redraw()

func _emit_alias(action: StringName, pressed: bool) -> void:
	_observe_action(action)
	var event := InputEventAction.new()
	event.action = _alias(action)
	event.pressed = pressed
	event.strength = 1.0 if pressed else 0.0
	Input.parse_input_event(event)
	_observe_action(action)

func _hold_action(action: StringName) -> void:
	var count: int = int(_refs.get(action, 0))
	_refs[action] = count + 1
	if count == 0:
		_emit_alias(action, true)

func _release_action(action: StringName) -> void:
	var count: int = maxi(0, int(_refs.get(action, 0)) - 1)
	if count == 0:
		_refs.erase(action)
		_emit_alias(action, false)
	else:
		_refs[action] = count

func cancel_all(reason: String = "cancel_all") -> void:
	_cancel_count += 1
	_last_cancel_reason = reason
	_canceling = true
	for action: StringName in ACTIONS + MOVEMENT:
		if int(_refs.get(action, 0)) <= 0 and not Input.is_action_pressed(_alias(action)):
			continue
		_edges.erase(action)
		_blocked_physics[action] = Engine.get_physics_frames() + 1
		_blocked_process[action] = Engine.get_process_frames()
		_emit_alias(action, false)
	_refs.clear()
	for index: int in _observed.keys():
		if String(_observed[index].get("phase", "gui")) == "gameplay":
			_suppressed_ids[index] = true
			_observed.erase(index)
	_pointers.clear()
	_stick_id = -1
	_look_id = -1
	_stick = Vector2.ZERO
	_look_delta = Vector2.ZERO
	_canceling = false
	if _surface != null:
		_surface.queue_redraw()

func _cancel_with_pause(reason: String) -> void:
	var should_pause := available and gameplay_active
	cancel_all(reason)
	if should_pause:
		request_pause.emit()

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_on_focus_lost()

func _on_focus_lost() -> void:
	_cancel_with_pause("focus_lost")
	_observed.clear()
	_suppressed_ids.clear()

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var index: int = event.index
		var terminal: bool = event.canceled or not event.pressed
		if terminal:
			var canceled: bool = event.canceled or _web_touch_was_canceled()
			var owned: bool = _pointers.has(index)
			if canceled:
				_cancel_with_pause("touch_canceled")
			elif owned:
				_end_pointer(index)
			_observed.erase(index)
			_suppressed_ids.erase(index)
			if _wanted_active and not gameplay_active:
				_schedule_activation()
			if owned:
				get_viewport().set_input_as_handled()
			return
		var phase: String = "gameplay" if available and gameplay_active else "gui"
		# A fresh Down starts a new lifecycle even when an interrupted contact
		# never supplied Up; stale drags still cannot acquire a new owner.
		_suppressed_ids.erase(index)
		_observed[index] = {"position":event.position, "phase":phase}
		if not available:
			var was_active := gameplay_active
			available = true
			if was_active:
				# This first fallback touch may already have emitted MouseDown.
				# Pause/guard it and keep mouse emulation until its GUI TouchUp.
				request_pause.emit()
		if not gameplay_active or _suppressed_ids.has(index):
			return
		if _begin_pointer(index, event.position):
			get_viewport().set_input_as_handled()
		return
	if event is InputEventScreenDrag:
		if _observed.has(event.index):
			_observed[event.index]["position"] = event.position
		if not gameplay_active or not _pointers.has(event.index):
			return
		var pointer: Dictionary = _pointers[event.index]
		var previous: Vector2 = pointer.position
		pointer.position = event.position
		_pointers[event.index] = pointer
		if pointer.owner == "stick":
			_update_stick(event.position)
		elif pointer.owner == "look":
			# Web drag.relative can belong to another changedTouches index.
			_look_delta += event.position - previous
		_surface.queue_redraw()
		get_viewport().set_input_as_handled()
		return
	for action: StringName in ACTIONS + MOVEMENT:
		if (InputMap.has_action(action) and event.is_action(action)) or event.is_action(_alias(action)):
			_observe_action(action)

func _begin_pointer(index: int, position: Vector2) -> bool:
	if _pointers.has(index):
		return true
	for action: StringName in ACTIONS:
		var rect: Rect2 = _button_rects.get(action, Rect2())
		if rect.has_point(position):
			_pointers[index] = {"owner":"action", "action":action, "position":position}
			_hold_action(action)
			_surface.queue_redraw()
			return true
	if _stick_id < 0 and _joystick_rect.has_point(position):
		_stick_id = index
		_pointers[index] = {"owner":"stick", "action":&"", "position":position}
		_update_stick(position)
		return true
	if _look_id < 0 and _look_rect.has_point(position):
		_look_id = index
		_pointers[index] = {"owner":"look", "action":&"", "position":position}
		return true
	return false

func _end_pointer(index: int) -> void:
	var pointer: Dictionary = _pointers[index]
	_pointers.erase(index)
	if pointer.owner == "action":
		_release_action(pointer.action)
	elif pointer.owner == "stick":
		_stick_id = -1
		_stick = Vector2.ZERO
	elif pointer.owner == "look":
		_look_id = -1
	_surface.queue_redraw()

func _update_stick(position: Vector2) -> void:
	var vector := ((position - _joystick_center) / _joystick_radius).limit_length(1.0)
	var magnitude := vector.length()
	_stick = vector.normalized() * ((magnitude - 0.14) / 0.86) if magnitude > 0.14 else Vector2.ZERO
	_surface.queue_redraw()

func _process(delta: float) -> void:
	for action: StringName in ACTIONS + MOVEMENT:
		_observe_action(action)
	_poll_time += delta
	if OS.has_feature("web") and _poll_time >= 0.25:
		_poll_time = 0.0
		var metrics := _web_metrics()
		if bool(metrics.get("touch", false)) and not available:
			available = true
		_sync_viewport(metrics)

func _web_metrics() -> Dictionary:
	if not OS.has_feature("web"):
		return {}
	var result: Variant = JavaScriptBridge.eval(WEB_METRICS, true)
	if result is String:
		var parsed: Variant = JSON.parse_string(result)
		if parsed is Dictionary:
			return parsed
	return {}

func _web_touch_was_canceled() -> bool:
	if not OS.has_feature("web"):
		return false
	var serial: int = int(JavaScriptBridge.eval("window.__touchControlsBridge ? window.__touchControlsBridge.cancelSerial : 0", true))
	var changed := serial != _web_cancel_serial
	_web_cancel_serial = serial
	return changed

func set_viewport_override(size_css: Vector2 = Vector2.ZERO, margins_css: Vector4 = Vector4.ZERO) -> void:
	# Native event injection uses window pixels. Keep the emulated CSS viewport
	# and native window identical so report rectangles can drive real input.
	if not OS.has_feature("web"):
		_applying_metrics = true
		if size_css.x > 0 and size_css.y > 0:
			if _override_restore_window_size == Vector2i.ZERO:
				_override_restore_window_size = get_window().size
			get_window().size = Vector2i(roundi(size_css.x), roundi(size_css.y))
		elif _override_restore_window_size != Vector2i.ZERO:
			get_window().size = _override_restore_window_size
			_override_restore_window_size = Vector2i.ZERO
		_applying_metrics = false
	_viewport_override = size_css
	_safe_override = margins_css
	_sync_viewport()

func _on_viewport_resized() -> void:
	if _applying_metrics or _viewport_sync_pending:
		return
	_viewport_sync_pending = true
	_cancel_with_pause("viewport_changed")
	# Window emits size_changed inside _update_viewport_size, before attaching
	# its cached screen rect. A nested content-scale setter would be overwritten
	# by that outer rect. Read the latest CSS metrics after it has returned.
	call_deferred("_apply_deferred_viewport")

func _apply_deferred_viewport() -> void:
	_sync_viewport()
	_viewport_sync_pending = false

func _sync_viewport(metrics: Dictionary = {}) -> void:
	if _surface == null or _applying_metrics:
		return
	var size_css := Vector2(get_window().size)
	var margins := Vector4.ZERO
	if OS.has_feature("web"):
		if metrics.is_empty():
			metrics = _web_metrics()
		var width: float = float(metrics.get("width", 0))
		var height: float = float(metrics.get("height", 0))
		if width > 0 and height > 0:
			size_css = Vector2(width, height)
		var safe: Array = metrics.get("safe", [0, 0, 0, 0])
		if safe.size() == 4:
			margins = Vector4(float(safe[0]), float(safe[1]), float(safe[2]), float(safe[3]))
	if _viewport_override.x > 0 and _viewport_override.y > 0:
		size_css = _viewport_override
		margins = _safe_override
	if size_css.x <= 0 or size_css.y <= 0:
		return
	var changed := not _viewport_css.is_equal_approx(size_css) or not safe_margins.is_equal_approx(margins)
	var target_scale_size := Vector2i(roundi(size_css.x), roundi(size_css.y))
	var needs_scale: bool = available and (get_window().content_scale_size != target_scale_size or get_window().content_scale_mode != Window.CONTENT_SCALE_MODE_CANVAS_ITEMS)
	if not changed and not needs_scale:
		return
	var had_layout := _viewport_css != Vector2.ZERO
	if had_layout and not _viewport_sync_pending:
		_cancel_with_pause("viewport_changed")
	_viewport_css = size_css
	safe_margins = margins
	if available:
		_applying_metrics = true
		get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
		get_window().content_scale_size = target_scale_size
		_applying_metrics = false
	_rebuild_layout()
	layout_changed.emit()

func _rebuild_layout() -> void:
	_layout_generation += 1
	_button_rects.clear()
	var width := _viewport_css.x
	var bottom := _viewport_css.y - safe_margins.w - 12.0
	var usable_width := width - safe_margins.x - safe_margins.z - 24.0
	var button_size: float = 48.0 if usable_width >= 356.0 else 44.0
	var columns: int = 4 if width >= 380.0 else 3
	var rows: int = ceili(float(GRID_ACTIONS.size()) / columns)
	var grid_size := Vector2(columns * button_size + (columns - 1) * 6.0, rows * button_size + (rows - 1) * 6.0)
	var origin := Vector2(width - safe_margins.z - 12.0 - grid_size.x, bottom - grid_size.y)
	for index in range(GRID_ACTIONS.size()):
		var offset := Vector2((index % columns) * (button_size + 6.0), floori(float(index) / columns) * (button_size + 6.0))
		_button_rects[GRID_ACTIONS[index]] = Rect2(origin + offset, Vector2.ONE * button_size)
	_button_rects[&"pause"] = Rect2(Vector2(width - safe_margins.z - 56.0, safe_margins.y + 12.0), Vector2(44, 44))
	_joystick_radius = 56.0 if usable_width >= 356.0 else 48.0
	_joystick_center = Vector2(safe_margins.x + 76.0, bottom - 64.0)
	if usable_width < 296.0:
		_joystick_center.y = origin.y - _joystick_radius - 14.0
	_joystick_rect = Rect2(_joystick_center - Vector2(68, 76), Vector2(136, 152))
	var look_top: float = safe_margins.y + 64.0
	_look_rect = Rect2(Vector2(width * 0.42, look_top), Vector2(maxf(44.0, width * 0.58 - safe_margins.z - 12.0), maxf(44.0, origin.y - look_top - 12.0)))
	_surface.queue_redraw()

func _rect_array(rect: Rect2) -> Array:
	return [rect.position.x, rect.position.y, rect.size.x, rect.size.y]

func presentation_report() -> Dictionary:
	var rects: Dictionary = {}
	for action: StringName in _button_rects:
		rects[String(action)] = _rect_array(_button_rects[action])
	var pointers: Array = []
	for index: int in _pointers:
		var p: Dictionary = _pointers[index]
		pointers.append({"index":index, "owner":p.owner, "action":String(p.action), "position":[p.position.x, p.position.y]})
	var pressed: Array = []
	for action: StringName in _refs:
		if int(_refs[action]) > 0:
			pressed.append(String(action))
	return {"available":available, "gameplay_active":gameplay_active, "visible":available and gameplay_active,
		"waiting_release":_waiting_release, "desired_gameplay_active":_wanted_active,
		"viewport":[_viewport_css.x, _viewport_css.y], "safe_margins":[safe_margins.x, safe_margins.y, safe_margins.z, safe_margins.w],
		"viewport_override":[_viewport_override.x, _viewport_override.y], "safe_margins_override":[_safe_override.x, _safe_override.y, _safe_override.z, _safe_override.w],
		"action_rects":rects, "joystick_rect":_rect_array(_joystick_rect), "joystick_center":[_joystick_center.x, _joystick_center.y],
		"joystick_radius":_joystick_radius, "look_rect":_rect_array(_look_rect), "stick_vector":[_stick.x, _stick.y],
		"look_delta":[_look_delta.x, _look_delta.y], "active_pointers":pointers, "pressed_actions":pressed,
		"observed_touch_indices":_observed.keys().duplicate(), "suppressed_pointer_indices":_suppressed_ids.keys().duplicate(),
		"cancel_count":_cancel_count, "last_cancel_reason":_last_cancel_reason, "layout_generation":_layout_generation,
		"action_font_size":ACTION_FONT_SIZE, "helper_font_size":HELPER_FONT_SIZE, "joystick_label_font_size":0,
		"emulate_mouse_from_touch":Input.emulate_mouse_from_touch}

func draw_surface(canvas: Control) -> void:
	canvas.draw_circle(_joystick_center, _joystick_radius + 7.0, Color(0.025, 0.045, 0.06, 0.38))
	canvas.draw_arc(_joystick_center, _joystick_radius + 7.0, 0, TAU, 48, Color(0.75, 0.82, 0.82, 0.45), 1.5, true)
	canvas.draw_circle(_joystick_center + _stick * _joystick_radius, 22.0, Color(0.84, 0.78, 0.58, 0.65 if _stick_id >= 0 else 0.3))
	var font: Font = _font
	for action: StringName in _button_rects:
		var rect: Rect2 = _button_rects[action]
		var held: bool = int(_refs.get(action, 0)) > 0
		canvas.draw_style_box(_pressed_style if held else _normal_style, rect)
		if action == &"pause":
			canvas.draw_rect(Rect2(rect.position + Vector2(15, 13), Vector2(4, 18)), Color(0.94, 0.92, 0.83, 0.95))
			canvas.draw_rect(Rect2(rect.position + Vector2(25, 13), Vector2(4, 18)), Color(0.94, 0.92, 0.83, 0.95))
		else:
			var text: String = String(LABELS.get(action, String(action)))
			var text_size := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, ACTION_FONT_SIZE)
			var point := rect.get_center() + Vector2(-text_size.x * 0.5, 5.0)
			if action == &"heavy":
				point.y -= 4.0
				canvas.draw_string(font, rect.position + Vector2(11, rect.size.y - 5), "길게", HORIZONTAL_ALIGNMENT_LEFT, -1, HELPER_FONT_SIZE, Color(0.88, 0.82, 0.63, 0.95))
			canvas.draw_string(font, point, text, HORIZONTAL_ALIGNMENT_LEFT, -1, ACTION_FONT_SIZE, Color(0.97, 0.95, 0.86, 0.96))
