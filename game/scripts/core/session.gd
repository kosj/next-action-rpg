extends Node

signal notification(text: String)
signal changed

const SAVE_PATH := "user://runefall_v1.json"
const SAVE_VERSION := 1
const MAX_SAVE_BYTES := 64 * 1024
var completed: Array[int] = []
var checkpoint: int = 0
var shards: int = 0
var upgrades: Array[int] = [0, 0, 0]
var lore_found: Array[int] = []
var shake: bool = true
var volume: float = 0.7
var quality: int = 0
var has_save: bool = false
var journey_started: bool = false
var build_id: String = ""
var save_path: String = SAVE_PATH
var _persistence_notice_sent: bool = false

func _ready() -> void:
	build_id = str(ProjectSettings.get_setting("application/config/version")) + " · development"
	configure_inputs()
	if FileAccess.file_exists("res://build_id.txt"):
		build_id = FileAccess.get_file_as_string("res://build_id.txt").strip_edges()
	load_game()

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

func new_game() -> bool:
	var previous := snapshot()
	var previous_has_save := has_save
	journey_started = true
	completed.clear()
	checkpoint = 0
	shards = 0
	upgrades = [0, 0, 0]
	lore_found.clear()
	if save_game():
		return true
	_apply_state(previous)
	has_save = previous_has_save
	return false

func snapshot() -> Dictionary:
	# A snapshot must not share arrays with mutable live progress (rollback uses it).
	return {"version": SAVE_VERSION, "journey_started": journey_started, "completed": completed.duplicate(), "checkpoint": checkpoint,
		"shards": shards, "upgrades": upgrades.duplicate(), "lore": lore_found.duplicate(),
		"settings": {"shake": shake, "volume": volume, "quality": quality}}

func _valid_integer(value: Variant, minimum: int, maximum: int) -> bool:
	if not (value is int or value is float):
		return false
	var number := float(value)
	return is_finite(number) and number == floor(number) and number >= minimum and number <= maximum

func _normalize_save(data: Dictionary) -> Dictionary:
	if not _valid_integer(data.get("version"), SAVE_VERSION, SAVE_VERSION):
		return {}
	if not data.get("completed") is Array or not data.get("upgrades") is Array:
		return {}
	var incoming_upgrades: Array = data.upgrades
	if incoming_upgrades.size() != 3:
		return {}
	var clean_upgrades: Array[int] = []
	for value: Variant in incoming_upgrades:
		if not _valid_integer(value, 0, 3):
			return {}
		clean_upgrades.append(int(value))
	var clean_completed: Array[int] = []
	for value: Variant in data.completed:
		if not _valid_integer(value, 0, 6):
			return {}
		if int(value) not in clean_completed:
			clean_completed.append(int(value))
	var point: Variant = data.get("checkpoint", 0)
	var money: Variant = data.get("shards", 0)
	if not _valid_integer(point, 0, 2) or not _valid_integer(money, 0, 100000):
		return {}
	var incoming_lore: Variant = data.get("lore", [])
	var settings: Variant = data.get("settings", {})
	if not incoming_lore is Array or not settings is Dictionary:
		return {}
	var clean_lore: Array[int] = []
	for value: Variant in incoming_lore:
		if not _valid_integer(value, 0, 2):
			return {}
		if int(value) not in clean_lore:
			clean_lore.append(int(value))
	# Old v1 files predate this distinction and represent an existing journey.
	var saved_journey: Variant = data.get("journey_started", true)
	if not saved_journey is bool:
		return {}
	var saved_shake: Variant = settings.get("shake", true)
	var saved_volume: Variant = settings.get("volume", 0.7)
	var saved_quality: Variant = settings.get("quality", 0)
	if not saved_shake is bool:
		return {}
	if not (saved_volume is float or saved_volume is int):
		return {}
	if not is_finite(float(saved_volume)) or saved_volume < 0 or saved_volume > 1:
		return {}
	if not _valid_integer(saved_quality, 0, 1):
		return {}
	return {"version": SAVE_VERSION, "journey_started": saved_journey, "completed": clean_completed, "checkpoint": int(point),
		"shards": int(money), "upgrades": clean_upgrades, "lore": clean_lore,
		"settings": {"shake": saved_shake, "volume": float(saved_volume), "quality": int(saved_quality)}}

func _apply_state(data: Dictionary) -> void:
	journey_started = data.journey_started
	completed.assign(data.completed)
	checkpoint = data.checkpoint
	shards = data.shards
	upgrades.assign(data.upgrades)
	lore_found.assign(data.lore)
	shake = data.settings.shake
	volume = data.settings.volume
	quality = data.settings.quality

func apply_save(data: Dictionary) -> bool:
	var normalized := _normalize_save(data)
	if normalized.is_empty():
		return false
	_apply_state(normalized)
	return true

func _read_valid_save(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	if file.get_length() > MAX_SAVE_BYTES:
		file.close()
		return {}
	var text := file.get_as_text()
	file.close()
	var parser := JSON.new()
	if parser.parse(text) != OK or not parser.data is Dictionary:
		return {}
	return _normalize_save(parser.data)

func _write_snapshot(path: String, data: Dictionary) -> bool:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return false
	file.store_string(JSON.stringify(data))
	# close() flushes too, but checking the error after an explicit flush catches
	# a failed write before the verified primary or backup is replaced.
	file.flush()
	var result := file.get_error()
	file.close()
	return result == OK

func _replace_file(source: String, target: String) -> Error:
	return DirAccess.rename_absolute(source, target)

func _save_failed(text: String) -> bool:
	DirAccess.remove_absolute(save_path + ".tmp")
	DirAccess.remove_absolute(save_path + ".bak.tmp")
	notification.emit(text)
	return false

func save_game() -> bool:
	var candidate := _normalize_save(snapshot())
	if candidate.is_empty():
		return _save_failed("진행 데이터가 올바르지 않아 저장하지 못했습니다. 이전 저장은 유지됩니다.")
	if not _write_snapshot(save_path + ".tmp", candidate):
		return _save_failed("저장할 수 없습니다. 저장 공간과 브라우저의 저장 권한을 확인해 주세요.")
	# Never rotate a corrupt primary over the healthy backup used for recovery.
	var previous := _read_valid_save(save_path)
	if not previous.is_empty():
		if not _write_snapshot(save_path + ".bak.tmp", previous):
			return _save_failed("백업을 만들지 못해 저장을 취소했습니다. 이전 저장은 유지됩니다.")
		if _replace_file(save_path + ".bak.tmp", save_path + ".bak") != OK:
			return _save_failed("백업을 교체하지 못해 저장을 취소했습니다. 이전 저장은 유지됩니다.")
	if _replace_file(save_path + ".tmp", save_path) != OK:
		return _save_failed("저장 실패 · 이전 저장은 유지됩니다.")
	has_save = journey_started
	changed.emit()
	if OS.has_feature("web") and not OS.is_userfs_persistent() and not _persistence_notice_sent:
		_persistence_notice_sent = true
		notification.emit("현재 브라우저에서 영구 저장을 사용할 수 없습니다. 탭을 닫으면 진행이 사라질 수 있습니다.")
	return true

func load_game() -> bool:
	for path: String in [save_path, save_path + ".bak"]:
		var data := _read_valid_save(path)
		if data.is_empty():
			continue
		_apply_state(data)
		has_save = journey_started
		if path == save_path + ".bak":
			call_deferred("emit_notice", "백업 저장을 복구했습니다.")
		return true
	has_save = false
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
	if save_game():
		return true
	shards += cost
	upgrades[index] -= 1
	return false
