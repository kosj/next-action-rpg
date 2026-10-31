extends RefCounted

# Real production Skeleton poses and weapon markers, with a sparse fixture to
# retain the original public bridge contract. No renderer or physics movement.
const DT := 1.0 / 60.0
const REPORT_PATH := "../build/verification/character-integration/transition-polish.json"

static func _pose(visual: ActorVisual, snapshot: Dictionary, delta: float = 0.0) -> void:
	visual.pose(delta, float(snapshot.get("speed", 0.0)), -1.0, false, false, false, snapshot)

static func _idle(visual: ActorVisual, epoch: int) -> void:
	visual.skeletal_bridge.reset_presentation(epoch)
	_pose(visual, {"speed":0.0, "presentation_epoch":epoch})

static func _bones(visual: ActorVisual) -> Array[Transform3D]:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var result: Array[Transform3D] = []
	for bone in range(skeleton.get_bone_count()):
		result.append(skeleton.get_bone_pose(bone))
	return result

static func _same_bones(a: Array[Transform3D], b: Array[Transform3D]) -> bool:
	if a.size() != b.size():
		return false
	for bone in range(a.size()):
		if not a[bone].is_equal_approx(b[bone]):
			return false
	return true

static func _markers(visual: ActorVisual) -> Dictionary:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var into_actor := visual.global_transform.affine_inverse()
	var result: Dictionary = {}
	for name in ["Hips", "LeftFoot", "RightFoot", "RightHand"]:
		var index := skeleton.find_bone(name)
		result[name] = into_actor * (skeleton.global_transform * skeleton.get_bone_global_pose(index)).origin
	result["BladeTip"] = into_actor * (visual.rig_weapon.find_child("BladeTip", true, false) as Node3D).global_position
	return result

static func _jump(a: Dictionary, b: Dictionary) -> float:
	var distance := 0.0
	for name in a:
		distance = maxf(distance, a[name].distance_to(b[name]))
	return distance

static func _socket_matches(visual: ActorVisual) -> bool:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var expected := skeleton.global_transform * skeleton.get_bone_global_pose(skeleton.find_bone("RightHand"))
	return visual.weapon_socket.global_transform.is_equal_approx(expected)

static func _motion(speed: float, x: float = 0.0, z: float = -1.0) -> Dictionary:
	return {"speed":speed, "move_local_x":x, "move_local_z":z}

static func _attack(time: float) -> Dictionary:
	var data: AttackData = load("res://data/light_1.tres")
	return {"speed":0.0, "attack_id":"light_1", "attack_elapsed":time, "attack_duration":data.duration(), "attack_startup":data.startup}

static func _jump_case(raw: ActorVisual, polished: ActorVisual, before: Dictionary, advance: float, after: Dictionary, epoch: int) -> Dictionary:
	_idle(raw, epoch)
	_idle(polished, epoch)
	if advance > 0.0:
		_pose(raw, before, advance)
		_pose(polished, before, advance)
	var source_raw := _markers(raw)
	var source_polished := _markers(polished)
	_pose(raw, after, DT)
	_pose(polished, after, DT)
	return {"raw_m":_jump(source_raw, _markers(raw)), "polished_m":_jump(source_polished, _markers(polished))}

static func run(world: Node3D, check: Callable) -> bool:
	var sparse := ActorVisual.new()
	sparse.setup("hero")
	world.add_child(sparse)
	var mounted := sparse.mount_rig(load("res://tests/skeletal_regressions.gd")._scene())
	check.call(mounted.ok and not sparse.skeletal_bridge.transition_report().enabled, "Sparse synthetic rigs retain immediate sampling unless production polish is explicitly enabled")
	var unsupported := sparse.skeletal_bridge.enable_transition_polish()
	_pose(sparse, {"attack_id":"light_1", "attack_elapsed":0.13, "attack_duration":0.52})
	check.call(not unsupported.ok and "all bone channels" in unsupported.reason and absf(sparse.skeletal_bridge.get_skeleton().get_bone_pose_position(0).x-0.25) < 0.00001, "Polish rejects incomplete pose channels without changing the existing synthetic action clock")
	sparse.free()
	var visuals: Array[ActorVisual] = []
	for index in range(3):
		var visual := ActorVisual.new()
		visual.setup("hero")
		world.add_child(visual)
		var result := visual.use_production_profile("hero")
		check.call(result.ok, "Transition fixture mounts actual weighted production hero %d: %s" % [index, result.reason])
		if not result.ok:
			visual.free()
			for previous in visuals:
				previous.free()
			return false
		visuals.append(visual)
	var raw := visuals[0]
	var polished := visuals[1]
	var oracle := visuals[2]
	raw.skeletal_bridge.enable_transition_polish(false)
	var enabled := polished.skeletal_bridge.enable_transition_polish()
	oracle.skeletal_bridge.enable_transition_polish()
	check.call(enabled.ok and polished.skeletal_bridge.transition_report().enabled, "Complete actual production bone channels opt in to bounded presentation blending")
	var actor_transform := polished.global_transform
	var metrics: Dictionary = {}
	metrics["start"] = _jump_case(raw, polished, {"speed":0.0}, 0.0, _motion(6.4), 81001)
	metrics["stop"] = _jump_case(raw, polished, _motion(6.4), 0.19, {"speed":0.0}, 81002)
	metrics["direction"] = _jump_case(raw, polished, _motion(6.4), 0.16, _motion(6.4, 1.0, 0.0), 81003)
	metrics["walk_to_run"] = _jump_case(raw, polished, _motion(6.4), 0.12, _motion(8.5), 81004)
	for name in metrics:
		var measured: Dictionary = metrics[name]
		check.call(measured.raw_m > 0.03 and measured.polished_m < measured.raw_m*0.5, "Actual %s transition reduces the first-frame body/foot/hand/blade marker jump by at least half" % name)
	_idle(polished, 81005)
	_pose(polished, _motion(6.4), 0.12)
	var bridge := polished.skeletal_bridge
	var walk_length := bridge.animation_player.get_animation(bridge.clips[&"walk"]).length
	var phase := bridge.sampled_time / walk_length
	_pose(polished, _motion(8.5))
	var run_length := bridge.animation_player.get_animation(bridge.clips[&"run"]).length
	check.call(absf(bridge.sampled_time/run_length-phase) < 0.000001, "Changing between actual walk and run preserves normalized left/right-foot cycle phase despite unequal clip lengths")
	_pose(polished, _motion(6.4, -1.0, 0.0))
	check.call(absf(bridge.sampled_time/walk_length-phase) < 0.000001, "Directional changes preserve the same normalized gait phase instead of restarting a foot cycle")
	_idle(polished, 81006)
	_pose(polished, _motion(6.4), DT)
	var frozen_bones := _bones(polished)
	var frozen_weapon := polished.weapon_grip.global_transform
	var frozen_phase: float = bridge.transition_report().gait_phase
	var frozen_elapsed: float = bridge.transition_report().elapsed
	var frozen_clock := bridge.locomotion_clock
	for index in range(8):
		_pose(polished, _motion(6.4))
	await world.get_tree().process_frame
	await world.get_tree().process_frame
	check.call(_same_bones(frozen_bones, _bones(polished)) and polished.weapon_grip.global_transform.is_equal_approx(frozen_weapon) and bridge.transition_report().gait_phase == frozen_phase and bridge.transition_report().elapsed == frozen_elapsed and bridge.locomotion_clock == frozen_clock, "Hit-paused zero-delta holds freeze all 53 bones, weapon, transition weight and locomotion phase without automatic playback")
	check.call(_socket_matches(polished), "The same-frame hand socket follows the final blended Skeleton pose")
	for spec in [
		{"speed":0.0, "stagger":0.10, "hit_elapsed":0.05, "hit_duration":0.15, "attack_id":"light_1", "attack_elapsed":0.2, "attack_duration":0.52},
		{"speed":0.0, "dodge_remaining":0.16, "dodge_elapsed":0.16, "dodge_duration":0.32, "dodge_local_x":-1.0, "dodge_local_z":0.0},
		{"speed":0.0, "parry_remaining":0.11, "parry_elapsed":0.11, "parry_duration":0.22},
		{"speed":0.0, "dead":true, "death_elapsed":0.2, "death_duration":1.1},
	]:
		_idle(polished, 81007)
		_pose(polished, _motion(6.4), DT)
		_pose(polished, spec, DT)
		_pose(oracle, spec)
		check.call(not bridge.transition_report().active and _same_bones(_bones(polished), _bones(oracle)) and _socket_matches(polished), "%s presentation interrupts a blend immediately at the authoritative action sample" % String(bridge.selected_state))
	_idle(polished, 81008)
	_pose(polished, _motion(6.4), 0.12)
	_pose(polished, _attack(DT), DT)
	check.call(bridge.transition_report().active and bridge.transition_report().duration <= float(_attack(DT).attack_startup)-DT and absf(bridge.sampled_time-DT) < 0.000001, "Attack entry blends only within remaining startup while its sampled target retains gameplay elapsed")
	var last_time := DT
	var active_exact := true
	for time: float in [0.05, 0.09, 0.13, 0.17, 0.30]:
		_pose(polished, _attack(time), time-last_time)
		_pose(oracle, _attack(time))
		if time >= float(_attack(time).attack_startup):
			active_exact = active_exact and not bridge.transition_report().active and _same_bones(_bones(polished), _bones(oracle)) and _jump(_markers(polished), _markers(oracle)) < 0.00001
		last_time = time
	check.call(active_exact, "At active attack start and throughout the strike the real Skeleton and weapon are the exact unblended authored target")
	_idle(polished, 81009)
	_idle(oracle, 81009)
	_pose(polished, {"speed":0.0, "charge_active":true, "charge_elapsed":0.1, "charge_duration":0.65}, 0.02)
	_pose(polished, {"speed":0.0, "charge_active":true, "charge_elapsed":0.15, "charge_duration":0.65}, 0.02)
	_pose(oracle, {"speed":0.0, "charge_active":true, "charge_elapsed":0.15, "charge_duration":0.65}, 0.04)
	check.call(_same_bones(_bones(polished), _bones(oracle)) and _jump(_markers(polished), _markers(oracle)) < 0.00001, "Transition progress depends on accumulated presentation seconds rather than rendered frame count")
	# The same zero-delta seek contract used by art audits must still expose the
	# exact target, including a seek that interrupts a partially blended action.
	_pose(polished, _attack(0.2))
	_pose(oracle, _attack(0.2))
	check.call(not bridge.transition_report().active and _same_bones(_bones(polished), _bones(oracle)), "An explicit changed-time zero-delta audit seek samples the exact target pose")
	_idle(polished, 81012)
	_pose(polished, _motion(6.4), 0.12)
	_pose(polished, _motion(6.4, 1.0, 0.0), DT)
	var interrupted_source := _markers(polished)
	var charge := {"speed":0.0, "charge_active":true, "charge_elapsed":0.1, "charge_duration":0.65}
	_pose(oracle, charge)
	var immediate_interrupt_jump := _jump(interrupted_source, _markers(oracle))
	_pose(polished, charge, DT)
	check.call(bridge.transition_report().active and _jump(interrupted_source, _markers(polished)) < immediate_interrupt_jump*0.5, "Interrupting an unfinished blend starts from its currently displayed pose instead of snapping to an outgoing raw clip")
	_idle(polished, 81013)
	_pose(polished, {"speed":0.0, "dodge_remaining":0.16, "dodge_elapsed":0.16, "dodge_duration":0.32, "dodge_local_x":-1.0, "dodge_local_z":0.0})
	var dodge_yaw := absf(wrapf(bridge.rig.rotation.y-PI, -PI, PI))
	_pose(polished, {"speed":0.0}, DT)
	var returning_yaw := absf(wrapf(bridge.rig.rotation.y-PI, -PI, PI))
	var yaw_blended := returning_yaw > 0.001 and returning_yaw < dodge_yaw and _socket_matches(polished)
	_pose(polished, {"speed":0.0}, 0.08)
	check.call(yaw_blended and absf(bridge.rig.rotation.y-PI) < 0.00001 and _socket_matches(polished), "Leaving a side dodge smoothly restores visual rig yaw and its same-frame weapon, without rotating the actor")
	_idle(polished, 81010)
	_pose(polished, _motion(6.4), DT)
	_pose(polished, {"speed":0.0, "presentation_epoch":81011}, DT)
	_idle(oracle, 81011)
	_pose(oracle, {"speed":0.0, "presentation_epoch":81011}, DT)
	check.call(not bridge.transition_report().active and bridge.transition_report().gait_phase == 0.0 and _same_bones(_bones(polished), _bones(oracle)), "A presentation epoch resets gait/blend history and starts directly on the new authored pose without a T-pose blend")
	check.call(polished.global_transform.is_equal_approx(actor_transform), "Transition polish never translates or rotates the authoritative visual actor wrapper")
	var report := {"scope":"Actual production pose transitions, visual markers and clocks only; no runtime foot IK, velocity continuity, final deformation or AAA approval.",
		"presentation_step_seconds":DT, "blend_max_seconds":SkeletalVisualBridge.TRANSITION_SECONDS,
		"marker_jump_m":metrics, "hero_sha256":FileAccess.get_sha256("res://assets/models/production/lyra_gameplay.glb"),
		"bridge_sha256":FileAccess.get_sha256("res://scripts/actors/skeletal_visual_bridge.gd")}
	var report_file := FileAccess.open(ProjectSettings.globalize_path("res://").path_join(REPORT_PATH).simplify_path(), FileAccess.WRITE)
	if report_file != null:
		report_file.store_string(JSON.stringify(report, "\t") + "\n")
	for visual in visuals:
		visual.free()
	return true
