extends "res://tests/combat_continuity_capture.gd"

## Two explicitly different evidence modes. `normal` earns rune with real
## native-input parries and can progress through real encounters. `technical`
## funds three skill casts at the ordinary hub to inspect their presentation;
## it is never evidence of earned resources or combat success.
const SKILL_KEYS := [KEY_1, KEY_2, KEY_3]
const SKILL_COSTS := [25.0, 45.0, 80.0]
const NORMAL_ORDER := [2, 1, 0]
const TECHNICAL_ORDER := [0, 1, 2]
var skill_mode := "normal"
var skill_cursor := 0
var requested_skill := -1
var last_skill_attempt := -1000
var last_lock_attempt := -1000
var last_defensive_input := -1000
var skill_casts: Dictionary = {}
var skill_active_samples: Dictionary = {}
var skill_effect_samples: Dictionary = {}
var skill_phase_images: Dictionary = {}
var skill_contacts: Dictionary = {}
var technical_resource_writes: Array[Dictionary] = []
var observed_skill_serials: Dictionary = {}
var next_technical_cast_tick := 0
var completed_skill_casts: Dictionary = {}
var requested_cast: CombatStrike
var last_accepted_skill_tick := -1
var completion_reason := ""

func _ready() -> void:
	super._ready()
	if config.is_empty() or finishing:
		return
	skill_mode = String(config.get("skill_mode", "normal"))
	if not skill_mode in ["normal", "technical"]:
		_fail("Skill capture mode must be normal or technical")
		return
	if int(config.frames) > 2700:
		_fail("Skill capture is bounded to45logical seconds")
		return
	provenance["capture_script"] = {"path":"res://tests/skill_vfx_capture.gd", "sha256":FileAccess.get_sha256("res://tests/skill_vfx_capture.gd")}
	provenance["skill_capture_mode"] = skill_mode
	provenance["capture_completion_policy"] = {"frame_budget":int(config.frames),
		"stop_when_complete":bool(config.get("stop_when_complete", false)),
		"quiet_after_last_accept_ticks":90, "software_threads":int(config.get("software_threads", 1)),
		"scope":"Frame budget remains unchanged. Either explicitly enabled mode may end on observed full skill recovery, expired effects and90quiet ticks. Technical mode still requires3recorded rune-funding writes. Software thread count is not measured hardware FPS.",
		"comparison_scope":"A shorter completed take is compared at matching actual ticks/skill phases, not as an equal-duration full movie to an older exact-budget take."}
	provenance["input_policy"] = "Normal UI and native skill keys. Normal mode earns resources through actual parries and traverses ordinary encounters. Technical mode explicitly assigns rune100 before each safe-hub cast. No damage, health, actor position or camera writes."
	provenance["not_established"] = ["human play", "direct continuous watching/hearing", "actual target-device FPS", "AAA approval"]

func _physics_process(delta: float) -> void:
	if gameplay_start < 0:
		super._physics_process(delta)
		if gameplay_start >= 0 and not finishing:
			_stop_movement()
			next_technical_cast_tick = tick+24
			_transition("skill_technical" if skill_mode == "technical" else "skill_earn")
		return
	if finished or finishing or world == null:
		return
	tick += 1
	if absf(delta-STEP) > 0.000001 or Engine.time_scale != 1.0:
		_fail("Skill take lost its logical1x/60Hz clock")
		return
	_drain_releases()
	if player.dead:
		_fail("Real AI killed the player during skill capture")
		return
	if skill_cursor >= 3:
		_stop_movement()
		return
	if skill_mode == "technical":
		_drive_technical()
	else:
		_drive_normal()
	if tick%300 == 0:
		print("SKILL_CAPTURE_PROGRESS tick=", tick-gameplay_start, " stage=", stage, " rune=", player.rune, " hp=", player.health)

func _skill_index() -> int:
	return int(TECHNICAL_ORDER[skill_cursor] if skill_mode == "technical" else NORMAL_ORDER[skill_cursor])

func _stop_movement() -> void:
	for action: String in ["forward", "back", "left", "right", "sprint"]:
		_set_key(action, false)

func _drive_technical() -> void:
	_stop_movement()
	if requested_skill >= 0:
		_wait_for_cast_end()
		return
	if tick < next_technical_cast_tick or player.strike != null or player.stagger > 0.0:
		return
	var index := _skill_index()
	# This is the only gameplay write in this fixture. It is isolated behind
	# explicit technical mode and recorded as a resource-funded fixture action.
	var before := player.rune
	player.rune = 100.0
	technical_resource_writes.append({"tick":tick, "field":"player.rune", "before":before, "after":player.rune, "purpose":"technical presentation coverage only"})
	_request_skill(index)

func _drive_normal() -> void:
	if requested_skill >= 0:
		_stop_movement()
		_wait_for_cast_end()
		return
	var index := _skill_index()
	if player.strike == null and player.stagger <= 0.0 and player.dodge_time <= 0.0 and player.rune >= SKILL_COSTS[index] and tick-last_skill_attempt > 30:
		_stop_movement()
		_request_skill(index)
		return
	if player.health < player.max_health*0.65 and player.potions > 0 and player.strike == null and tick-last_heal_tick > 90:
		_stop_movement()
		_attempt_heal("skill_capture_normal_heal")
		return
	var target := _closest_living_enemy()
	if target == null:
		# Ordinary movement follows the next authored room; no encounter or gate
		# is assigned by this fixture. Crossing the normal trigger spawns enemies.
		var next_room := 0
		while next_room < Sanctuary.CENTERS.size() and next_room in Session.completed:
			next_room += 1
		if next_room >= Sanctuary.CENTERS.size():
			_fail("All real encounters completed before every requested skill was observed")
			return
		_steer_to(Sanctuary.CENTERS[next_room], 1.0, true)
		return
	if (not is_instance_valid(player.locked_target) or player.locked_target.dead) and tick-last_lock_attempt > 20:
		_tap_key(KEY_TAB, "skill_capture_lock_on")
		last_lock_attempt = tick
	if _horizontal_distance(player.global_position, target.global_position) > 2.1:
		_steer_to(target.global_position, 2.1, false)
	else:
		_stop_movement()
	# Earn rune through actual parry windows, leaving enemies alive for the
	# expensive ultimate. Reading AI intent does not force a parry or resource.
	if player.strike == null and player.parry_cooldown <= 0.0 and player.stagger <= 0.0 and tick-last_defensive_input > 8:
		for candidate in world.get("active_enemies"):
			if not is_instance_valid(candidate):
				continue
			var enemy := candidate as RuneEnemy
			if enemy == null or enemy.dead or enemy.strike == null:
				continue
			var incoming := enemy.global_position-player.global_position
			incoming.y = 0.0
			var remaining := enemy.strike.data.startup-enemy.strike.elapsed
			if incoming.length() <= enemy.strike.data.reach+0.3 and incoming.normalized().dot(player.facing) > 0.0 and remaining > 0.0 and remaining <= 0.13:
				_tap_key(KEY_F, "skill_capture_earn_parry")
				last_defensive_input = tick
				break

func _steer_to(point: Vector3, stop_distance: float, sprinting: bool) -> void:
	var direction := point-player.global_position
	direction.y = 0.0
	if direction.length() <= stop_distance:
		_stop_movement()
		return
	direction = direction.normalized().rotated(Vector3.UP, -player.camera_yaw)
	_set_key("forward", direction.z < -0.25)
	_set_key("back", direction.z > 0.25)
	_set_key("left", direction.x < -0.25)
	_set_key("right", direction.x > 0.25)
	_set_key("sprint", sprinting)

func _closest_living_enemy() -> RuneEnemy:
	var closest: RuneEnemy
	var distance := INF
	for candidate in world.get("active_enemies"):
		if not is_instance_valid(candidate):
			continue
		var enemy := candidate as RuneEnemy
		if enemy == null or enemy.dead:
			continue
		var current := _horizontal_distance(player.global_position, enemy.global_position)
		if current < distance:
			closest = enemy
			distance = current
	return closest

func _request_skill(index: int) -> void:
	requested_skill = index
	requested_cast = null
	last_skill_attempt = tick
	events.append({"tick":tick, "type":"skill_key_request", "skill_index":index, "rune_before":player.rune, "cost":SKILL_COSTS[index], "technical_resource_funded":skill_mode == "technical"})
	_tap_key(SKILL_KEYS[index], "skill_%d" % (index+1))
	_transition("skill_%d_requested" % (index+1))

func _wait_for_cast_end() -> void:
	var label := "skill_%d" % (requested_skill+1)
	if int(skill_casts.get(label, 0)) == 0:
		if tick-last_skill_attempt > 60:
			_fail("Ordinary skill key did not produce an accepted cast: "+label)
		return
	if player.strike == null:
		var completed := requested_cast != null and requested_cast.elapsed >= requested_cast.data.duration()-0.000001
		if completed:
			completed_skill_casts[label] = int(completed_skill_casts.get(label, 0))+1
		events.append({"tick":tick, "type":"skill_cast_end_observed", "attack_id":label,
			"attack_instance_id":requested_cast.attack_instance_id if requested_cast != null else 0,
			"elapsed":requested_cast.elapsed if requested_cast != null else -1.0,
			"duration":requested_cast.data.duration() if requested_cast != null else -1.0,
			"full_recovery":completed})
		skill_cursor += 1
		requested_skill = -1
		requested_cast = null
		next_technical_cast_tick = tick+90
		_transition("skill_%d_recovered" % skill_cursor)

func record_after_physics(delta: float) -> void:
	var previous_size := frames.size()
	super.record_after_physics(delta)
	if frames.size() == previous_size or player == null:
		return
	var row: Dictionary = frames.back()
	row["rune"] = player.rune
	row["skill_capture_mode"] = skill_mode
	row["legacy_rings"] = _legacy_ring_reports()
	if player.strike != null:
		var attack := player.strike
		var label := String(attack.presentation_id)
		if label in ["skill_1", "skill_2", "skill_3"]:
			if requested_skill >= 0 and label == "skill_%d" % (requested_skill+1):
				requested_cast = attack
			if not observed_skill_serials.has(attack.attack_instance_id):
				observed_skill_serials[attack.attack_instance_id] = label
				last_accepted_skill_tick = tick
				skill_casts[label] = int(skill_casts.get(label, 0))+1
				events.append({"tick":tick, "type":"accepted_skill_observed", "attack_id":label, "attack_instance_id":attack.attack_instance_id, "rune_after":player.rune})
			var phase := "preparation" if attack.elapsed < attack.data.startup else ("active" if attack.elapsed < attack.data.startup+attack.data.active else "recovery")
			if phase == "active":
				skill_active_samples[label] = int(skill_active_samples.get(label, 0))+1
			var image_key := label+"-"+phase
			var phase_ready := (phase == "preparation" and attack.elapsed >= 0.075) or (phase == "active" and attack.elapsed >= attack.data.startup+0.06) or (phase == "recovery" and attack.elapsed >= attack.data.startup+attack.data.active+0.15)
			if phase_ready and not skill_phase_images.has(image_key):
				skill_phase_images[image_key] = true
				pending_images.append(image_key)
			var late_key := label+"-active-late"
			if phase == "active" and attack.elapsed >= attack.data.startup+0.28 and not skill_phase_images.has(late_key):
				skill_phase_images[late_key] = true
				pending_images.append(late_key)
	row["skill_effects_after_physics"] = _effect_reports()
	if not finishing and bool(config.get("stop_when_complete", false)) and _capture_completion_ready():
		completion_reason = "all_three_skills_recovered_and_effects_expired"
		_validate_finish()

func _capture_completion_ready() -> bool:
	if player.dead or not player.active or get_tree().paused or skill_cursor < 3 or requested_skill >= 0 or player.strike != null or last_accepted_skill_tick < 0 or tick-last_accepted_skill_tick < 90:
		return false
	if (skill_mode == "normal" and not technical_resource_writes.is_empty()) or (skill_mode == "technical" and technical_resource_writes.size() != 3):
		return false
	for label: String in ["skill_1", "skill_2", "skill_3"]:
		if int(skill_casts.get(label, 0)) < 1 or int(skill_active_samples.get(label, 0)) < 1 or int(completed_skill_casts.get(label, 0)) < 1:
			return false
		if bool(config.get("require_skill_effects", true)) and int(skill_effect_samples.get(label, 0)) < 1:
			return false
	return _effect_reports().is_empty()

func _process(delta: float) -> void:
	super._process(delta)
	if frames.is_empty() or player == null:
		return
	var row: Dictionary = frames.back()
	var reports := _effect_reports()
	row["skill_effects_after_process"] = reports
	if world.has_method("skill_presentation_report"):
		row["game_skill_presentation"] = _json(world.call("skill_presentation_report"))
	for report: Dictionary in reports:
		var label := String(report.get("attack_id", ""))
		if not label.is_empty() and bool(report.get("valid", true)):
			skill_effect_samples[label] = int(skill_effect_samples.get(label, 0))+1

func _effect_reports() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for effect in get_tree().get_nodes_in_group("skill_effects"):
		if not effect.is_queued_for_deletion() and effect.has_method("presentation_report"):
			var report: Dictionary = _json(effect.call("presentation_report"))
			report["position_world"] = _json(effect.global_position)
			result.append(report)
	return result

func _legacy_ring_reports() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for child in world.get_children():
		if child is RuneEffect and not child.is_queued_for_deletion():
			result.append({"radius":child.radius, "elapsed":child.elapsed,
				"duration":child.duration, "warning":child.warning,
				"position_world":_json(child.global_position)})
	return result

func _on_impact(context: Dictionary) -> void:
	super._on_impact(context)
	var label := String(context.get("attack_id", ""))
	if label in ["skill_1", "skill_2", "skill_3"]:
		skill_contacts[label] = int(skill_contacts.get(label, 0))+1
		if int(skill_contacts[label]) == 1:
			pending_images.append(label+"-first-confirmed-contact")

func _validate_finish() -> void:
	for label: String in ["skill_1", "skill_2", "skill_3"]:
		if int(skill_casts.get(label, 0)) < 1 or int(skill_active_samples.get(label, 0)) < 1:
			_fail("Skill take did not observe an accepted active cast: "+label)
			return
		if bool(config.get("require_skill_effects", true)) and int(skill_effect_samples.get(label, 0)) < 1:
			_fail("No live new presentation effect observed for "+label)
			return
	if skill_mode == "normal" and not technical_resource_writes.is_empty():
		_fail("Normal-input mode unexpectedly wrote resources")
		return
	if (skill_mode == "normal" or bool(config.get("stop_when_complete", false))) and not _capture_completion_ready():
		_fail("Take ended before all3skills fully recovered, effects expired and90quiet ticks elapsed")
		return
	if completion_reason.is_empty():
		completion_reason = "exact_frame_budget_complete"
	pending_images.append("skills-final-gameplay")
	finishing = true

func _write_result() -> void:
	provenance["skill_vfx_coverage"] = {"mode":skill_mode, "accepted_casts":skill_casts,
		"active_samples":skill_active_samples, "new_effect_samples":skill_effect_samples,
		"confirmed_contacts":skill_contacts, "technical_resource_writes":technical_resource_writes,
		"completed_skill_casts":completed_skill_casts, "last_accepted_skill_tick":last_accepted_skill_tick,
		"frame_budget":int(config.get("frames", 0)), "actual_gameplay_frames":tick-gameplay_start+1 if gameplay_start >= 0 else 0,
		"stop_when_complete":bool(config.get("stop_when_complete", false)),
		"completion_reason":completion_reason, "quiet_after_last_accept_ticks":tick-last_accepted_skill_tick if last_accepted_skill_tick >= 0 else 0,
		"all_skill_requests_recovered":skill_cursor >= 3 and requested_skill < 0 and requested_cast == null,
		"live_skill_effect_count":_effect_reports().size() if is_instance_valid(world) else -1,
		"comparison_scope":"Compare matching original ticks/skill phases. Optional completed takes may be shorter than an older exact-frame-budget take; no full-movie equal-duration claim.",
		"scope":"Technical mode establishes resource-funded actual Game skill presentation only. Normal mode earns resources with real input. Neither mode establishes direct continuous watching/hearing, hardware or AAA approval."}
	super._write_result()
