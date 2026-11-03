extends RefCounted

# Compare independently imported, posed world markers with the gameplay path.
# This catches exporter axes, rig scale, socket offsets and curve disagreement.
static func _pose(visual: ActorVisual, snapshot: Dictionary, delta: float = 0.0) -> void:
	visual.pose(delta, float(snapshot.get("speed", 0.0)), -1.0, false, false, false, snapshot)

static func _attack(time: float) -> Dictionary:
	var data := RunePlayer.CHARGED_HEAVY
	return {"attack_id":"charged_heavy","attack_elapsed":time,"attack_duration":data.duration(),
		"attack_startup":data.startup,"attack_active":data.active,"speed":0.0}

static func _ordinary_heavy_alignment(actor: RunePlayer, visual: ActorVisual, grip: Node3D, tip: Node3D, check: Callable) -> Dictionary:
	# The new ordinary two-handed cut has its own independently imported path.
	# Checking the charged path cannot detect an accidentally retained old arc.
	var data := RunePlayer.HEAVY
	var curve := data.blade_curve_report()
	var source_sha := FileAccess.get_sha256(ProductionCharacterArt.definition("hero").path)
	check.call(data.physical_blade_sweep and data.phase_lunge and curve.ok and String(curve.get("source_sha256",""))==source_sha,
		"Ordinary heavy uses its own source-bound physical blade instead of the former generic horizontal reach")
	if not curve.ok:
		return {"ok":false,"curve":curve}
	var max_grip := 0.0
	var max_tip := 0.0
	var max_chord := 0.0
	for actor_scale in [1.0,1.25]:
		actor.scale = Vector3.ONE*actor_scale
		actor.rotation.y = 0.7
		for index in range((int(curve.sample_count)-1)*2+1):
			var phase := float(index)/((int(curve.sample_count)-1)*2)
			_pose(visual,{"attack_id":"heavy","attack_elapsed":data.startup+data.active*phase,
				"attack_duration":data.duration(),"attack_startup":data.startup,"attack_active":data.active,"speed":0.0})
			var expected := data.blade_points(phase)
			var into_actor := actor.global_transform.affine_inverse()
			max_grip = maxf(max_grip,(into_actor*grip.global_position).distance_to(expected[0]))
			max_tip = maxf(max_tip,(into_actor*tip.global_position).distance_to(expected[1]))
			max_chord = maxf(max_chord,absf(expected[0].distance_to(expected[1])-data.blade_length))
	check.call(max_grip<.003 and max_tip<.003 and max_chord<.002,
		"The independently displayed ordinary heavy matches every LUT key/midpoint within3mm and2mm chord at two scales")
	var phases := data.blade_sweep_phases(0.0,1.0,0.0,1.0)
	var retains_keys := true
	for index in range(int(curve.sample_count)):
		var phase := float(index)/(int(curve.sample_count)-1)
		var found := false
		for queried: float in phases:
			found = found or absf(queried-phase)<.000000001
		retains_keys = retains_keys and found
	check.call(retains_keys,"One large ordinary-heavy physics step retains every authored bend in its own physical path")
	var animation := visual.skeletal_bridge.animation_player.get_animation(&"heavy")
	var maximum_keys := 0
	for track in range(animation.get_track_count()):
		maximum_keys = maxi(maximum_keys,animation.track_get_key_count(track))
	check.call(maximum_keys==87,"Ordinary heavy retains its actual100Hz87-key authored motion without scene-wide500Hz inflation")
	actor.scale = Vector3.ONE
	actor.rotation.y = 0.0
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var foot := skeleton.find_bone("LeftFoot")
	var planted := Vector3.ZERO
	var drift := 0.0
	for time: float in [.28,.32,.34,.40,.48,.54]:
		var travel := data.lunge_between(0.0,time)*time
		actor.position = Vector3.FORWARD*travel
		_pose(visual,{"attack_id":"heavy","attack_elapsed":time,"attack_duration":data.duration(),
			"attack_startup":data.startup,"attack_active":data.active,"speed":0.0})
		var point := (skeleton.global_transform*skeleton.get_bone_global_pose(foot)).origin
		if time==.28:
			planted = point
		drift = maxf(drift,point.distance_to(planted))
	check.call(is_zero_approx(data.lunge_between(0.0,data.startup)) and absf(data.lunge_between(0.0,data.duration())*data.duration()-.704)<.00001 and drift<.005,
		"Ordinary heavy plants its support foot within5mm through0.704m nominal cut travel while preparation stays in place")
	return {"ok":true,"curve":curve,"max_grip_error_m":max_grip,"max_tip_error_m":max_tip,
		"max_chord_error_m":max_chord,"nominal_support_foot_drift_m":drift,"imported_max_keys":maximum_keys,
		"scope":"Actual imported markers and declared nominal plant window only, not terrain IK or visual approval"}

static func run(world: Node3D, check: Callable) -> bool:
	var fixture := Node3D.new()
	world.add_child(fixture)
	fixture.position = Vector3(240, 8, 240)
	var actor := RunePlayer.new()
	actor.world = world
	fixture.add_child(actor)
	actor.set_physics_process(false)
	var visual := actor.visual
	check.call(is_instance_valid(visual.skeletal_bridge), "Blade alignment uses the actual imported player, capsule floor offset and weapon")
	if not is_instance_valid(visual.skeletal_bridge):
		fixture.free()
		return false
	var data := RunePlayer.CHARGED_HEAVY
	var curve := data.blade_curve_report()
	var runtime_sha := FileAccess.get_sha256(ProductionCharacterArt.definition("hero").path)
	check.call(curve.ok and String(curve.get("source_sha256","")) == runtime_sha and String(curve.get("source_asset_path","")).get_file() == String(ProductionCharacterArt.definition("hero").path).get_file(),"The pinned physical curve validates and identifies the exact independently imported hero source")
	if not curve.ok:
		fixture.free()
		return false
	var document: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(data.blade_curve_path))
	var bad_time: Dictionary = document.duplicate(true)
	bad_time.samples[1].time_s = bad_time.samples[0].time_s
	var bad_frame: Dictionary = document.duplicate(true)
	bad_frame.coordinate_system = "blender_z_up"
	var bad_point: Dictionary = document.duplicate(true)
	bad_point.samples[1].tip[0] = NAN
	check.call(not data.blade_curve_validation_error(bad_time).is_empty() and not data.blade_curve_validation_error(bad_frame).is_empty() and not data.blade_curve_validation_error(bad_point).is_empty(),"Physical curves reject duplicate timestamps, the wrong actor frame and non-finite blade geometry")
	var bad_pin := data.duplicate(true) as AttackData
	bad_pin.blade_curve_sha256 = "0".repeat(64)
	check.call(not bad_pin.blade_curve_report().ok,"Changing physical curve bytes or its pinned SHA cannot silently fall back to the old sweep")
	var query_phases := data.blade_sweep_phases(0.0,1.0,0.0,1.0)
	var all_keys_retained := true
	for index in range(int(curve.sample_count)):
		var phase := float(index)/(int(curve.sample_count)-1)
		var found := false
		for queried: float in query_phases:
			found = found or absf(queried-phase) < .000000001
		all_keys_retained = all_keys_retained and found
	var max_query_gap := 0.0
	for index in range(1,query_phases.size()):
		var before := data.blade_points(query_phases[index-1])
		var after := data.blade_points(query_phases[index])
		max_query_gap = maxf(max_query_gap,maxf(before[0].distance_to(after[0]),before[1].distance_to(after[1])))
	check.call(all_keys_retained and max_query_gap <= data.blade_radius*.5+.000001,"A full-window physics sweep retains every baked bend and bounds adjacent blade endpoints to half the collision radius")
	var grip := visual.rig_weapon.find_child("GripOrigin", true, false) as Node3D
	var tip := visual.rig_weapon.find_child("BladeTip", true, false) as Node3D
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var foot := skeleton.find_bone("LeftFoot")
	var animation := visual.skeletal_bridge.animation_player.get_animation(&"charged_heavy")
	var hand_keys := 0
	for track in range(animation.get_track_count()):
		var path := animation.track_get_path(track)
		if animation.track_get_type(track) == Animation.TYPE_ROTATION_3D and path.get_subname_count() == 1 and path.get_subname(0) == "RightHand":
			hand_keys = animation.track_get_key_count(track)
	check.call(hand_keys >= 531, "The actual imported charged hand retains the 500Hz curve instead of silently simplifying its keys")
	var original_animation := visual.skeletal_bridge.animation_player.get_animation(&"light_1")
	var original_max_keys := 0
	for track in range(original_animation.get_track_count()):
		original_max_keys = maxi(original_max_keys, original_animation.track_get_key_count(track))
	check.call(original_max_keys == 53, "The edited0.52s light action follows the explicit100Hz import policy instead of scene-wide500Hz expansion")
	var max_grip_error := 0.0
	var max_tip_error := 0.0
	var max_blade_length_error := 0.0
	var samples: Array[Dictionary] = []
	for scale_m in [1.0, 1.25]:
		actor.scale = Vector3.ONE * scale_m
		actor.rotation.y = 0.7
		# Inspect every baked key and every interpolation midpoint, not merely
		# endpoints of a hard-coded azimuth formula that can hide local bends.
		for index in range((int(curve.sample_count)-1)*2+1):
			var fraction := float(index)/((int(curve.sample_count)-1)*2)
			_pose(visual, _attack(data.startup + data.active * fraction))
			var expected := data.blade_points(fraction)
			max_blade_length_error = maxf(max_blade_length_error,absf(expected[0].distance_to(expected[1])-1.19))
			var into_actor := actor.global_transform.affine_inverse()
			max_grip_error = maxf(max_grip_error, (into_actor * grip.global_position).distance_to(expected[0]))
			max_tip_error = maxf(max_tip_error, (into_actor * tip.global_position).distance_to(expected[1]))
			samples.append({"phase":fraction,"scale":scale_m,"sampled_time":visual.skeletal_bridge.sampled_time,
				"grip_error_m":(into_actor * grip.global_position).distance_to(expected[0]),
				"tip_error_m":(into_actor * tip.global_position).distance_to(expected[1])})
	check.call(max_grip_error < 0.003 and max_tip_error < 0.003 and max_blade_length_error < .002, "Actual Grip/Tip match the baked physical curve within 3mm at every key and midpoint, with bounded 2mm chord error at two actor scales")
	actor.scale = Vector3.ONE
	actor.rotation.y = 0.0
	var planted: Vector3
	var foot_drift := 0.0
	for time: float in [0.30, 0.34, 0.36, 0.43, 0.47, 0.52]:
		# Explicit nominal motor travel; this is not terrain/collision foot IK.
		actor.position = Vector3.FORWARD * (3.2 * clampf(time - 0.34, 0.0, 0.18))
		_pose(visual, _attack(time))
		var actual := (skeleton.global_transform * skeleton.get_bone_global_pose(foot)).origin
		if time == 0.30:
			planted = actual
		foot_drift = maxf(foot_drift, actual.distance_to(planted))
	check.call(foot_drift < 0.005, "The actual imported support foot stays within 5mm through nominal 0.576m attack travel")
	var normal_heavy := _ordinary_heavy_alignment(actor,visual,grip,tip,check)
	actor.position = Vector3.ZERO
	visual.skeletal_bridge.reset_presentation()
	var walking := {"speed":6.4,"move_local_x":0.0,"move_local_z":-1.0}
	_pose(visual, walking, 0.19)
	var before: Array[Transform3D] = []
	for bone in range(skeleton.get_bone_count()):
		before.append(skeleton.get_bone_pose(bone))
	var charged := walking.duplicate(true)
	charged.merge({"charge_active":true,"charge_elapsed":0.65,"charge_duration":0.65})
	_pose(visual, charged)
	var legs_unchanged := true
	for name in ["Root","Hips","LeftUpLeg","LeftLeg","LeftFoot","RightUpLeg","RightLeg","RightFoot"]:
		var index := skeleton.find_bone(name)
		legs_unchanged = legs_unchanged and before[index].is_equal_approx(skeleton.get_bone_pose(index))
	var chest := skeleton.find_bone("Spine2")
	check.call(visual.skeletal_bridge.selected_state == &"walk" and visual.skeletal_bridge.transition_report().charge_upper_body and legs_unchanged and not before[chest].is_equal_approx(skeleton.get_bone_pose(chest)), "Moving charge displays the loaded upper body while preserving the real walking hips and legs")
	var report := {"scope":"Imported actual marker/nominal stance and moving-charge layer alignment only; no terrain IK, normal-speed AV, target-device or AAA approval",
		"ordinary_heavy":normal_heavy,
		"max_grip_error_m":max_grip_error,"max_tip_error_m":max_tip_error,"nominal_support_foot_drift_m":foot_drift,
		"curve":curve,"max_interpolated_blade_length_error_m":max_blade_length_error,
		"full_window_query_samples":query_phases.size(),"max_query_endpoint_step_m":max_query_gap,
		"samples":samples,
		"imported_charged_right_hand_keys":hand_keys,
		"imported_unchanged_light_1_max_keys":original_max_keys,
		"source_body_sha256":FileAccess.get_sha256(ProductionCharacterArt.definition("hero").path)}
	print("RUNEFALL_CHARGED_ALIGNMENT: ", JSON.stringify(report))
	var path := ProjectSettings.globalize_path("res://").path_join("../build/verification/charged-impact/alignment.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report, "\t") + "\n")
	fixture.free()
	return true
