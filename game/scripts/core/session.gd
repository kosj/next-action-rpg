extends Node

signal notification(text: String)
signal changed

const SAVE_PATH := "user://runefall_v1.json"
const SAVE_VERSION := 1
var completed: Array[int] = []
var checkpoint: int = 0
var shards: int = 0
var upgrades: Array[int] = [0, 0, 0]
var lore_found: Array[int] = []
var shake: bool = true
var volume: float = 0.7
var quality: int = 0
var has_save: bool = false
var build_id: String = "0.1.0 · development"
var save_path: String = SAVE_PATH

func _ready() -> void:
	configure_inputs()
	if FileAccess.file_exists("res://build_id.txt"):
		build_id = FileAccess.get_file_as_string("res://build_id.txt").strip_edges()
	has_save = load_game()

func configure_inputs() -> void:
	var keys := {"forward": KEY_W, "back": KEY_S, "left": KEY_A, "right": KEY_D,
		"dodge": KEY_SPACE, "parry": KEY_F, "interact": KEY_E, "heal": KEY_R,
		"skill_1": KEY_1, "skill_2": KEY_2, "skill_3": KEY_3, "pause": KEY_ESCAPE,
		"lock_on": KEY_TAB, "target_next": KEY_Q, "sprint": KEY_SHIFT, "debug_overlay": KEY_F3}
	for action: String in keys:
		InputMap.add_action(action, 0.2)
		var event := InputEventKey.new()
		event.physical_keycode = keys[action]
		InputMap.action_add_event(action, event)
	for action: String in ["light", "heavy"]:
		InputMap.add_action(action)
		var mouse := InputEventMouseButton.new()
		mouse.button_index = MOUSE_BUTTON_LEFT if action == "light" else MOUSE_BUTTON_RIGHT
		InputMap.action_add_event(action, mouse)
	var buttons := {"light": JOY_BUTTON_X, "heavy": JOY_BUTTON_Y, "dodge": JOY_BUTTON_A,
		"interact": JOY_BUTTON_B, "parry": JOY_BUTTON_LEFT_SHOULDER, "lock_on": JOY_BUTTON_RIGHT_STICK,
		"heal": JOY_BUTTON_DPAD_UP, "pause": JOY_BUTTON_START, "target_next": JOY_BUTTON_RIGHT_SHOULDER, "sprint": JOY_BUTTON_LEFT_STICK,
		"skill_1": JOY_BUTTON_DPAD_LEFT, "skill_2": JOY_BUTTON_DPAD_RIGHT, "skill_3": JOY_BUTTON_DPAD_DOWN}
	for action: String in buttons:
		var button := InputEventJoypadButton.new()
		button.button_index = buttons[action]
		InputMap.action_add_event(action, button)
	for spec: Array in [["left", JOY_AXIS_LEFT_X, -1.0], ["right", JOY_AXIS_LEFT_X, 1.0], ["forward", JOY_AXIS_LEFT_Y, -1.0], ["back", JOY_AXIS_LEFT_Y, 1.0]]:
		var axis := InputEventJoypadMotion.new()
		axis.axis = spec[1]
		axis.axis_value = spec[2]
		InputMap.action_add_event(spec[0], axis)

func new_game() -> void:
	completed.clear()
	checkpoint = 0
	shards = 0
	upgrades = [0, 0, 0]
	lore_found.clear()
	save_game()

func snapshot() -> Dictionary:
	return {"version": SAVE_VERSION, "completed": completed, "checkpoint": checkpoint,
		"shards": shards, "upgrades": upgrades, "lore": lore_found,
		"settings": {"shake": shake, "volume": volume, "quality": quality}}

func apply_save(data: Dictionary) -> bool:
	if data.get("version") != SAVE_VERSION:
		return false
	if not data.get("completed") is Array or not data.get("upgrades") is Array:
		return false
	var incoming_upgrades: Array = data.upgrades
	if incoming_upgrades.size() != 3:
		return false
	for value: Variant in incoming_upgrades:
		if not (value is float or value is int) or value < 0 or value > 3:
			return false
	var incoming_completed: Array[int] = []
	for value: Variant in data.completed:
		if not (value is float or value is int) or value < 0 or value > 6:
			return false
		if int(value) not in incoming_completed:
			incoming_completed.append(int(value))
	var point: Variant = data.get("checkpoint", 0)
	var money: Variant = data.get("shards", 0)
	if not (point is float or point is int) or point < 0 or point > 2:
		return false
	if not (money is float or money is int) or money < 0 or money > 100000:
		return false
	var incoming_lore: Variant = data.get("lore", [])
	var settings: Variant = data.get("settings", {})
	if not incoming_lore is Array or not settings is Dictionary:
		return false
	for value: Variant in incoming_lore:
		if not (value is float or value is int) or value < 0 or value > 2:
			return false
	completed.assign(incoming_completed)
	checkpoint = int(point)
	shards = int(money)
	upgrades.assign(incoming_upgrades)
	lore_found.assign(incoming_lore)
	shake = bool(settings.get("shake", true))
	var saved_volume: Variant = settings.get("volume", 0.7)
	volume = clampf(float(saved_volume), 0.0, 1.0) if saved_volume is float or saved_volume is int else 0.7
	quality = clampi(int(settings.get("quality", 0)), 0, 1) if settings.get("quality", 0) is float or settings.get("quality", 0) is int else 0
	return true

func save_game() -> bool:
	var file := FileAccess.open(save_path + ".tmp", FileAccess.WRITE)
	if file == null:
		notification.emit("저장할 수 없습니다. 브라우저의 저장 권한을 확인해 주세요.")
		return false
	file.store_string(JSON.stringify(snapshot()))
	file.close()
	if FileAccess.file_exists(save_path):
		DirAccess.copy_absolute(save_path, save_path + ".bak")
	var error := DirAccess.rename_absolute(save_path + ".tmp", save_path)
	if error != OK:
		notification.emit("저장 실패 · 이전 저장은 유지됩니다.")
		return false
	has_save = true
	changed.emit()
	return true

func load_game() -> bool:
	for path: String in [save_path, save_path + ".bak"]:
		if not FileAccess.file_exists(path):
			continue
		var parser := JSON.new()
		if parser.parse(FileAccess.get_file_as_string(path)) != OK:
			continue
		var parsed: Variant = parser.data
		if parsed is Dictionary and apply_save(parsed):
			if path.ends_with(".bak"):
				call_deferred("emit_notice", "백업 저장을 복구했습니다.")
			return true
	return false

func emit_notice(text: String) -> void:
	notification.emit(text)

func buy_upgrade(index: int) -> bool:
	if index < 0 or index >= 3 or upgrades[index] >= 3:
		return false
	var cost := 35 + upgrades[index] * 25
	if shards < cost:
		return false
	shards -= cost
	upgrades[index] += 1
	save_game()
	return true
