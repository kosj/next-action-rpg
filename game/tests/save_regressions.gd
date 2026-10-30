extends RefCounted

# I/O seams simulate actual failures without depending on host permissions or disk quotas.
class FaultSession extends "res://scripts/core/session.gd":
	var denied_write: String = ""
	var denied_replace: String = ""

	func _write_snapshot(path: String, data: Dictionary) -> bool:
		if path == denied_write:
			return false
		return super._write_snapshot(path, data)

	func _replace_file(source: String, target: String) -> Error:
		if target == denied_replace:
			return ERR_CANT_CREATE
		return super._replace_file(source, target)

static func run(_session: Node, check: Callable) -> bool:
	var probe := FaultSession.new()
	probe.save_path = "user://save_audit_%d.json" % Time.get_ticks_usec()
	_cleanup(probe.save_path)
	var empty := probe.snapshot()
	var legacy := {"version":1.0, "completed":[0.0, 0.0, 1.0], "upgrades":[1.0, 0.0, 2.0]}
	check.call(probe.apply_save(legacy), "Save audit: v1 JSON numbers and missing optional defaults remain compatible")
	check.call(probe.completed == [0,1] and probe.checkpoint == 0 and probe.lore_found.is_empty(), "Save audit: completed IDs normalize without duplicated progress")
	var detached := probe.snapshot()
	probe.completed.append(2)
	probe.upgrades[0] = 2
	probe.lore_found.append(1)
	check.call(detached.completed == [0,1] and detached.upgrades == [1,0,2] and detached.lore.is_empty(), "Save audit: rollback snapshots own their progress arrays")
	probe.apply_save(empty)
	var bad_values: Array[Dictionary] = [
		{"field":"version", "value":true},
		{"field":"completed", "value":[0.5]},
		{"field":"upgrades", "value":[1.5,0,0]},
		{"field":"checkpoint", "value":1.5},
		{"field":"shards", "value":3.5},
		{"field":"shards", "value":true},
		{"field":"shards", "value":NAN},
		{"field":"lore", "value":[0.5]},
		{"field":"settings", "value":{"shake":"false"}},
		{"field":"settings", "value":{"volume":NAN}},
		{"field":"settings", "value":{"volume":INF}},
		{"field":"settings", "value":{"volume":2.0}},
		{"field":"settings", "value":{"quality":0.5}}
	]
	for entry in bad_values:
		var invalid: Dictionary = empty.duplicate(true)
		invalid[entry.field] = entry.value
		check.call(not probe.apply_save(invalid) and probe.snapshot() == empty, "Save audit: reject malformed %s without partial application" % entry.field)
	var duplicate_lore: Dictionary = empty.duplicate(true)
	duplicate_lore.lore = [2.0,2.0,0.0]
	check.call(probe.apply_save(duplicate_lore) and probe.lore_found == [2,0], "Save audit: lore IDs normalize without inflated discovery count")
	probe.apply_save(empty)
	check.call(probe.new_game(), "Save audit: initial save succeeds")
	probe.shards = 120
	probe.completed = [0,1]
	probe.checkpoint = 1
	check.call(probe.save_game(), "Save audit: persisted progress baseline")
	var original := probe.snapshot()
	var original_primary := FileAccess.get_file_as_string(probe.save_path)
	var original_backup := FileAccess.get_file_as_string(probe.save_path + ".bak")
	var changes: Array[int] = [0]
	probe.changed.connect(func(): changes[0] += 1)
	probe.denied_write = probe.save_path + ".tmp"
	check.call(not probe.buy_upgrade(0) and probe.shards == 120 and probe.upgrades[0] == 0, "Save audit: failed purchase restores currency and upgrade level")
	check.call(changes[0] == 0, "Save audit: failed purchase never emits saved-success signal")
	check.call(not probe.new_game() and probe.snapshot() == original and probe.has_save, "Save audit: failed new journey restores previous progress and continue availability")
	check.call(FileAccess.get_file_as_string(probe.save_path) == original_primary, "Save audit: temp write failure preserves the primary")
	probe.denied_write = probe.save_path + ".bak.tmp"
	probe.shards = 130
	check.call(not probe.save_game(), "Save audit: backup write failure cancels replacement")
	check.call(FileAccess.get_file_as_string(probe.save_path) == original_primary and FileAccess.get_file_as_string(probe.save_path + ".bak") == original_backup, "Save audit: failed backup write preserves both verified files")
	probe.denied_write = ""
	probe.denied_replace = probe.save_path + ".bak"
	check.call(not probe.save_game(), "Save audit: backup rename failure is reported")
	check.call(FileAccess.get_file_as_string(probe.save_path) == original_primary and FileAccess.get_file_as_string(probe.save_path + ".bak") == original_backup, "Save audit: failed backup replacement leaves the old backup intact")
	probe.denied_replace = probe.save_path
	check.call(not probe.save_game() and FileAccess.get_file_as_string(probe.save_path) == original_primary, "Save audit: primary rename failure preserves the last saved progress")
	check.call(not FileAccess.file_exists(probe.save_path + ".tmp") and not FileAccess.file_exists(probe.save_path + ".bak.tmp"), "Save audit: failed saves remove incomplete temporary files")
	probe.denied_replace = ""
	probe.load_game()
	check.call(probe.buy_upgrade(0) and probe.shards == 85 and probe.upgrades[0] == 1 and changes[0] == 1, "Save audit: successful purchase commits exactly once")
	probe.new_game()
	probe.shards = 41
	probe.save_game()
	probe.shards = 52
	probe.save_game()
	_write_raw(probe.save_path, "{broken")
	check.call(probe.load_game() and probe.shards == 41, "Save audit: corrupt primary recovers the verified backup")
	probe.shards = 60
	check.call(probe.save_game(), "Save audit: saving after backup recovery succeeds")
	var backup: Variant = JSON.parse_string(FileAccess.get_file_as_string(probe.save_path + ".bak"))
	check.call(backup is Dictionary and backup.shards == 41, "Save audit: corrupt primary never overwrites a healthy recovery backup")
	_write_raw(probe.save_path, "{broken again")
	check.call(probe.load_game() and probe.shards == 41, "Save audit: a second primary corruption still recovers progress")
	_write_raw(probe.save_path, JSON.stringify({"version":99}))
	probe.load_game()
	probe.shards = 70
	check.call(probe.save_game(), "Save audit: unknown primary version does not prevent a fresh valid save")
	backup = JSON.parse_string(FileAccess.get_file_as_string(probe.save_path + ".bak"))
	check.call(backup is Dictionary and backup.shards == 41, "Save audit: unknown-version primary also cannot poison the backup")
	_cleanup(probe.save_path)
	probe.has_save = false
	probe.denied_write = probe.save_path + ".tmp"
	check.call(not probe.new_game() and not probe.has_save, "Save audit: first-save failure does not create a phantom continue slot")
	probe.denied_write = ""
	_cleanup(probe.save_path)
	probe.free()
	return true

static func _write_raw(path: String, text: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()

static func _cleanup(path: String) -> void:
	for suffix in ["", ".bak", ".tmp", ".bak.tmp"]:
		DirAccess.remove_absolute(path + suffix)
