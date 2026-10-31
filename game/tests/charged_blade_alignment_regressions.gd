extends RefCounted

# Compare independently imported, posed world markers with the gameplay path.
# This catches exporter axes, rig scale, socket offsets and curve disagreement.
static func _pose(visual: ActorVisual, snapshot: Dictionary, delta: float = 0.0) -> void:
	visual.pose(delta, float(snapshot.get("speed", 0.0)), -1.0, false, false, false, snapshot)

static func _attack(time: float) -> Dictionary:
	var data := RunePlayer.CHARGED_HEAVY
	return {"attack_id":"charged_heavy","attack_elapsed":time,"attack_duration":data.duration(),
		"attack_startup":data.startup,"attack_active":data.active,"speed":0.0}

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
	check.call(original_max_keys == 53, "An unchanged 0.52s light action retains its original 100Hz samples instead of the scene-wide 500Hz expansion")
	var max_grip_error := 0.0
	var max_tip_error := 0.0
	var samples: Array[Dictionary] = []
	for scale_m in [1.0, 1.25]:
		actor.scale = Vector3.ONE * scale_m
		actor.rotation.y = 0.7
		for fraction in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
			var data := RunePlayer.CHARGED_HEAVY
			_pose(visual, _attack(data.startup + data.active * fraction))
			var expected := data.blade_points(fraction)
			var into_actor := actor.global_transform.affine_inverse()
			max_grip_error = maxf(max_grip_error, (into_actor * grip.global_position).distance_to(expected[0]))
			max_tip_error = maxf(max_tip_error, (into_actor * tip.global_position).distance_to(expected[1]))
			samples.append({"phase":fraction,"scale":scale_m,"sampled_time":visual.skeletal_bridge.sampled_time,
				"grip_error_m":(into_actor * grip.global_position).distance_to(expected[0]),
				"tip_error_m":(into_actor * tip.global_position).distance_to(expected[1])})
	check.call(max_grip_error < 0.003 and max_tip_error < 0.003, "Actual Grip/Tip match the accelerated 3D physical blade within 3mm at seven active phases and two actor scales")
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
		"max_grip_error_m":max_grip_error,"max_tip_error_m":max_tip_error,"nominal_support_foot_drift_m":foot_drift,
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
