extends "res://tests/combat_continuity_capture.gd"

## Bounded real-Game take. Reuses the native UI, observer, actor/foot/weapon
## trace, camera, PNG and orderly audio-cleanup helpers of the continuity take.
## Every gameplay action below is a normal physical input event. No actor state,
## collider, camera, health, target selection or encounter is assigned here.
var chain_requests := 0
var stationary_heavy_seen := false
var charged_seen := false
var wave_images: Dictionary = {}
var movement_active: Dictionary = {}
var wave_contacts := 0
var wave_serials: Dictionary = {}
var next_light_tick := 0
var last_retarget := -1000
var last_heal_input := -1000

func _ready() -> void:
	var arguments: PackedStringArray = OS.get_cmdline_user_args()
	if arguments.size() == 1 and not arguments[0].is_absolute_path():
		push_error("Stride/wave configuration must be an absolute path after --")
		get_tree().quit(2)
		return
	super._ready()
	if not config.is_empty() and not finishing:
		if int(config.frames) < 900 or int(config.frames) > 1200:
			_fail("Stride/wave take requires 15–20 seconds at logical 60Hz")
		provenance["capture_script"] = {"path":"res://tests/stride_wave_capture.gd","sha256":FileAccess.get_sha256("res://tests/stride_wave_capture.gd")}
		provenance["input_policy"] = "Native UI → sprint approach → locked W/A/D three-light chain → stationary right-tap heavy → ordinary backwards charged spacing/release → moving light chains. No gameplay writes."

func _physics_process(delta: float) -> void:
	if gameplay_start < 0:
		super._physics_process(delta)
		if gameplay_start >= 0 and not finishing:
			_set_key("forward",true)
			_set_key("sprint",true)
			_transition("stride_approach")
		return
	if finished or finishing or world == null:
		return
	tick += 1
	if absf(delta-STEP) > 0.000001 or Engine.time_scale != 1.0:
		_fail("Native stride/wave take lost its logical 1x/60Hz clock")
		return
	_drain_releases()
	if player.dead:
		_fail("Real AI killed the player during the ordinary-input take")
		return
	var target := _target()
	if int(world.get("active_encounter")) >= 0 and target == null and tick-last_retarget > 45:
		_tap_key(KEY_TAB,"lock_on")
		last_retarget = tick
	if player.health < player.max_health*0.45 and player.potions > 0 and player.strike == null and tick-last_heal_input > 90:
		_tap_key(KEY_R,"heal")
		last_heal_input = tick
	match stage:
		"stride_approach":
			if target != null and _horizontal_distance(player.global_position,target.global_position) <= 10.0:
				_set_key("sprint",false)
				chain_requests = 1
				_light_tap()
				pending_images.append("stride-01-locked-forward-light")
				_transition("stride_chain")
		"stride_chain":
			if player.strike != null:
				var label := String(player.strike.presentation_id)
				if chain_requests < 3 and label == "light_%d" % chain_requests and player.strike.data.can_cancel(player.strike.elapsed):
					_set_key("forward",false)
					_set_key("left",chain_requests == 1)
					_set_key("right",chain_requests == 2)
					_light_tap()
					chain_requests += 1
			elif chain_requests == 3:
				_stop_directions()
				_set_mouse(MOUSE_BUTTON_RIGHT,true,"heavy",_center())
				releases.append({"at":tick+1,"kind":"mouse","code":MOUSE_BUTTON_RIGHT,"name":"heavy","point":_center()})
				_transition("stride_stationary_heavy")
			elif tick-stage_start > 120:
				_light_tap()
		"stride_stationary_heavy":
			if player.strike != null and String(player.strike.presentation_id) == "heavy":
				stationary_heavy_seen = true
			elif stationary_heavy_seen and player.strike == null:
				_set_key("back",true)
				_set_mouse(MOUSE_BUTTON_RIGHT,true,"heavy",_center())
				_transition("stride_charge_spacing")
		"stride_charge_spacing":
			# The target keeps its real chase/attack motor. Only S creates space.
			var separation := _horizontal_distance(player.global_position,target.global_position) if target != null else 0.0
			if player.heavy_held >= 0.72 and player.strike == null and player.stagger <= 0.0 and (separation >= float(config.get("charged_release_distance",8.4)) or tick-stage_start >= 240):
				_set_key("back",false)
				charge_seen = true
				release_tick = tick
				_set_mouse(MOUSE_BUTTON_RIGHT,false,"heavy",_center())
				pending_images.append("stride-02-charged-release-real-spacing")
				_transition("stride_charged_recovery")
		"stride_charged_recovery":
			if player.strike != null and String(player.strike.presentation_id) == "charged_heavy":
				charged_seen = true
			elif charged_seen and player.strike == null:
				next_light_tick = tick
				_transition("stride_followup")
		"stride_followup":
			var left := floori(float(tick-stage_start)/60.0)%2 == 0
			_set_key("left",left)
			_set_key("right",not left)
			if tick >= next_light_tick:
				_light_tap()
				next_light_tick = tick+10
	# A stalled input policy remains bounded and leaves an honest failure trace.
	if stage != "stride_followup" and tick-stage_start > 300:
		_fail("Ordinary-input stage did not finish within five logical seconds: "+stage)

func _stop_directions() -> void:
	for action: String in ["forward","back","left","right","sprint"]:
		_set_key(action,false)

func record_after_physics(delta: float) -> void:
	var previous_size := frames.size()
	super.record_after_physics(delta)
	if frames.size() == previous_size or player == null:
		return
	var waves: Array[Dictionary] = []
	for wave in get_tree().get_nodes_in_group("sword_waves"):
		if wave is RuneSwordWave and not wave.is_queued_for_deletion():
			var report: Dictionary = wave.presentation_report()
			report["position_world"] = _json(wave.global_position)
			waves.append(report)
			wave_serials[str(report.attack_instance_id)] = true
			var key := str(report.attack_instance_id)
			if not wave_images.has(key) and wave_images.size() < 6:
				wave_images[key] = true
				pending_images.append("stride-wave-%02d-live" % wave_images.size())
	var row: Dictionary = frames.back()
	row["sword_waves"] = _json(waves)
	row["moving_light_observed"] = _moving_light()

func _moving_light() -> bool:
	if player.strike == null or not String(player.strike.presentation_id).begins_with("light_"):
		return false
	if Vector2(player.resolved_velocity.x,player.resolved_velocity.z).length() < 0.25:
		return false
	for action: String in ["forward","left","right"]:
		if bool(held.get(action,false)):
			movement_active[action] = int(movement_active.get(action,0))+1
	return true

func _on_impact(context: Dictionary) -> void:
	super._on_impact(context)
	if bool(context.get("sword_wave",false)):
		wave_contacts += 1
		if wave_contacts <= 3:
			pending_images.append("stride-wave-contact-%02d" % wave_contacts)

func _validate_finish() -> void:
	for label: String in ["light_1","light_2","light_3"]:
		if int(light_active_samples.get(label,0)) < 1:
			_fail("Actual moving-input take did not observe "+label)
			return
	for action: String in ["forward","left","right"]:
		if int(movement_active.get(action,0)) < 1:
			_fail("No real moving-light sample under "+action)
			return
	if not stationary_heavy_seen or not charged_seen or wave_serials.is_empty():
		_fail("Actual take lacks requested normal-heavy/charged/projectile coverage")
		return
	if wave_contacts < 1:
		_fail("Actual take produced no confirmed sword-wave contact")
		return
	pending_images.append("stride-03-final-ordinary-gameplay")
	finishing = true

func _write_result() -> void:
	provenance["stride_wave_coverage"] = {"moving_light_samples_by_held_key":movement_active,
		"normal_heavy_observed":stationary_heavy_seen,"charged_observed":charged_seen,
		"wave_serials_observed":wave_serials.keys(),"confirmed_wave_contacts":wave_contacts,
		"scope":"Real normal-input observations only; no final art, hearing or target-hardware approval"}
	super._write_result()
