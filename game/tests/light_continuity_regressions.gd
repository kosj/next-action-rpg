extends RefCounted
## Native clip continuity and hand/socket contracts, not skin/AV/AAA approval.
## The archived baseline is loaded in memory only; it is not a runtime asset.

const BASELINE_PATH := "res://../art_source/production/candidates/lyra-fury-001/source.glb"
const BASELINE_SHA := "f2edbd3709d2f06ceb2f4c7ec7ddecdbf80cc2e97bee71664044eeac04a74beb"
const ORIGINAL_CURVE_SHA := "601adad7389ae4f22563db2deeb6982651c9776daa05be070a781d44bd322e6e"
const LEFT_TARGET_PATH := "res://../art_source/production/candidates/lyra-continuity-001/source-006-guarded.targets.json"
const LEFT_TARGET_SHA := "0f94df41666376c56ea88df75437454f1c48612700d87de603b2e5b1639f0c7a"
const SPEED_LIMIT_DEG_S := 2700.0 # Existing45deg per1/60s; never relaxed.
const LIGHTS := ["light_1", "light_2", "light_3"]

static func _baseline(parent: Node3D, floor_y: float, check: Callable) -> Dictionary:
	var path := ProjectSettings.globalize_path(BASELINE_PATH).simplify_path()
	if FileAccess.get_sha256(path) != BASELINE_SHA:
		check.call(false, "Light continuity requires the immutable archived f2ed baseline")
		return {}
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	# Explicit in-memory images: never extract PNGs beside the immutable archive.
	var image_mode := &"HANDLE_BINARY_EMBED_AS_UNCOMPRESSED"
	if not ClassDB.class_has_integer_constant(&"GLTFState", image_mode):
		check.call(false, "Pinned GLTFState provides in-memory uncompressed image import")
		return {}
	state.set("handle_binary_image", ClassDB.class_get_integer_constant(&"GLTFState", image_mode))
	var error := document.append_from_file(path, state)
	check.call(error == OK, "Archived Fury baseline is independently imported by native GLTFDocument")
	if error != OK:
		return {}
	# Independent original-light control at its100Hz comparison policy. The
	# production500Hz+posthook importer remains untouched; EditorScenePostImport
	# cannot be instantiated by this ordinary native Node runner.
	var generated := document.generate_scene(state, 100.0, false, false)
	var scene := generated as Node3D
	if scene == null:
		if is_instance_valid(generated):
			generated.free()
		check.call(false, "Archived baseline generates an actual3D rig")
		return {}
	var player := ProductionCharacterArt.find_type(scene, "AnimationPlayer") as AnimationPlayer
	var skeleton := ProductionCharacterArt.find_type(scene, "Skeleton3D") as Skeleton3D
	if player == null or skeleton == null:
		scene.free()
		check.call(false, "Archived baseline exposes actual AnimationPlayer and Skeleton3D")
		return {}
	player.autoplay = ""
	player.stop()
	player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	var wrapper := Node3D.new()
	wrapper.position.y = floor_y
	parent.add_child(wrapper)
	scene.rotation.y += PI # Same single Humanoid+Z→gameplay−Z correction.
	wrapper.add_child(scene)
	return {"root":wrapper,"player":player,"skeleton":skeleton}

static func _pose(visual: ActorVisual, clip: String, time: float, delta: float = 0.0, epoch: int = 0) -> void:
	var data := load("res://data/"+clip+".tres") as AttackData
	var length := visual.skeletal_bridge.animation_player.get_animation(clip).length
	var snapshot := {"speed":0.0,"attack_id":clip,"attack_elapsed":time/length*data.duration(),
		"attack_duration":data.duration(),"attack_startup":data.startup,"attack_active":data.active,
		"presentation_epoch":epoch}
	visual.pose(delta, 0.0, -1.0, false, false, false, snapshot)

static func _baseline_pose(baseline: Dictionary, clip: String, time: float) -> void:
	var player: AnimationPlayer = baseline.player
	player.play(clip)
	player.seek(time, true)

static func _quaternion_finite(q: Quaternion) -> bool:
	return is_finite(q.x) and is_finite(q.y) and is_finite(q.z) and is_finite(q.w) and q.length_squared() > 0.000001

static func _angle(a: Quaternion, b: Quaternion) -> float:
	# Components are promoted to GDScript float64 before norm/dot arithmetic;
	# identical float32 Quaternion values must not acquire a spurious angle.
	var aa: float = float(a.x)*a.x+float(a.y)*a.y+float(a.z)*a.z+float(a.w)*a.w
	var bb: float = float(b.x)*b.x+float(b.y)*b.y+float(b.z)*b.z+float(b.w)*b.w
	var dot: float = float(a.x)*b.x+float(a.y)*b.y+float(a.z)*b.z+float(a.w)*b.w
	return rad_to_deg(2.0*acos(clampf(absf(dot/sqrt(aa*bb)),0.0,1.0)))

static func _sample(skeleton: Skeleton3D) -> Dictionary:
	var local: Array[Quaternion] = []
	var global: Array[Quaternion] = []
	var positions: Array[Vector3] = []
	var scales: Array[Vector3] = []
	var finite := true
	for index in range(skeleton.get_bone_count()):
		var local_q := skeleton.get_bone_pose_rotation(index)
		var world_pose := skeleton.global_transform*skeleton.get_bone_global_pose(index)
		var global_q := world_pose.basis.orthonormalized().get_rotation_quaternion()
		finite = finite and _quaternion_finite(local_q) and _quaternion_finite(global_q) and world_pose.origin.is_finite()
		local.append(local_q)
		global.append(global_q)
		positions.append(skeleton.get_bone_pose_position(index))
		scales.append(skeleton.get_bone_pose_scale(index))
	return {"local":local,"global":global,"positions":positions,"scales":scales,"finite":finite}

static func _same_sample(a: Dictionary, b: Dictionary) -> bool:
	if not a.finite or not b.finite or a.local.size()!=b.local.size():
		return false
	for index in range(a.local.size()):
		if _angle(a.local[index],b.local[index])>0.001 or not a.positions[index].is_equal_approx(b.positions[index]) or not a.scales[index].is_equal_approx(b.scales[index]):
			return false
	return true

static func _dedupe_times(values: Array[float], length: float) -> Array[float]:
	# Collapse only equivalent importer float-time representations, not a rate
	# denominator clamp. Real authored100Hz intervals are ten thousand times larger.
	values.sort()
	var result: Array[float] = []
	for value in values:
		var time := clampf(value,0.0,length)
		if result.is_empty() or time-result[-1]>0.000001:
			result.append(time)
	if not result.is_empty() and absf(result[-1]-length)<=0.000001:
		result[-1]=length
	return result

static func _grid(length: float, hz: float) -> Array[float]:
	var result: Array[float] = []
	for index in range(int(floor(length*hz))+1):
		result.append(float(index)/hz)
	if result.is_empty() or length-result[-1] > 0.0000001:
		result.append(length)
	return result

static func _keys(animation: Animation) -> Array[float]:
	var unique := {0.0:true,animation.length:true}
	for track in range(animation.get_track_count()):
		for index in range(animation.track_get_key_count(track)):
			var time := animation.track_get_key_time(track,index)
			unique[snappedf(time,0.000000001)] = true
	var result: Array[float] = []
	for time in unique:
		result.append(float(time))
	return _dedupe_times(result,animation.length)

static func _with_midpoints(keys: Array[float]) -> Array[float]:
	var result: Array[float] = []
	for index in range(keys.size()):
		if index > 0:
			result.append((keys[index-1]+keys[index])*0.5)
		result.append(keys[index])
	return result

static func _continuity(visual: ActorVisual, baseline: Dictionary, clip: String, times: Array[float], current: bool) -> Dictionary:
	var skeleton: Skeleton3D = visual.skeletal_bridge.get_skeleton() if current else baseline.skeleton
	var previous: Dictionary = {}
	var previous_time := 0.0
	var result := {"samples":times.size(),"bones":skeleton.get_bone_count(),"finite":true,
		"maximum_local_step_deg":0.0,"maximum_global_step_deg":0.0,
		"maximum_local_deg_s":0.0,"maximum_global_deg_s":0.0,"worst_local":{},"worst_global":{},"per_bone":{}}
	for time in times:
		if current:
			_pose(visual,clip,time)
		else:
			_baseline_pose(baseline,clip,time)
		var sample := _sample(skeleton)
		result.finite = result.finite and sample.finite
		if not previous.is_empty() and sample.finite and previous.finite:
			var delta := time-previous_time
			for bone in range(skeleton.get_bone_count()):
				var name := String(skeleton.get_bone_name(bone))
				if not result.per_bone.has(name):
					result.per_bone[name] = {"local_deg_s":0.0,"global_deg_s":0.0}
				for space in ["local","global"]:
					var degrees := _angle(previous[space][bone],sample[space][bone])
					var speed := degrees/delta
					result["maximum_"+space+"_step_deg"] = maxf(result["maximum_"+space+"_step_deg"],degrees)
					result.per_bone[name][space+"_deg_s"] = maxf(result.per_bone[name][space+"_deg_s"],speed)
					if speed > result["maximum_"+space+"_deg_s"]:
						result["maximum_"+space+"_deg_s"] = speed
						result["worst_"+space] = {"bone":name,"from_s":previous_time,"to_s":time,"step_deg":degrees}
		previous = sample
		previous_time = time
	return result

static func _hand(skeleton: Skeleton3D, name: String) -> Transform3D:
	return skeleton.global_transform*skeleton.get_bone_global_pose(skeleton.find_bone(name))

static func _left_targets(runtime_sha: String, floor_y: float, check: Callable) -> Dictionary:
	var path := ProjectSettings.globalize_path(LEFT_TARGET_PATH).simplify_path()
	if FileAccess.get_sha256(path) != LEFT_TARGET_SHA:
		check.call(false,"Authored free-left targets retain their explicit source-sidecar SHA")
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		check.call(false,"Authored free-left target sidecar parses as a dictionary")
		return {}
	var targets: Dictionary = parsed
	var metadata: Dictionary = targets.get("source_metadata",{})
	var conversion: Dictionary = targets.get("conversion",{})
	var valid: bool = targets.get("schema_version")==1 and targets.get("coordinate_system")=="actor_y_up_minus_z_forward" and targets.get("time_units")=="source_clip_seconds"
	valid = valid and conversion.get("offset_already_in_actor_coordinates",false) and absf(float(targets.get("floor_offset_m",-1.0))-floor_y)<0.000001
	valid = valid and metadata.get("sha256","")==runtime_sha and metadata.get("parent_sha256","")==BASELINE_SHA and targets.get("clips",{}) is Dictionary
	check.call(valid,"Authored free-left oracle binds the actual candidate and archived parent with PI/floor conversion already applied")
	return targets if valid else {}

static func _authored_left(visual: ActorVisual, actor: Node3D, clip: String, target_clip: Dictionary) -> Dictionary:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var animation := visual.skeletal_bridge.animation_player.get_animation(clip)
	var samples: Array = target_clip.get("samples",[])
	var expected_times := _with_midpoints(_keys(animation))
	var result := {"samples":samples.size(),"source_key_samples":0,"midpoint_samples":0,"finite":true,"schedule_matches":samples.size()==expected_times.size(),
		"maximum_target_error_m":0.0,"maximum_key_error_m":0.0,"maximum_midpoint_error_m":0.0,"maximum_orientation_error_deg":0.0,"worst":{}}
	result.schedule_matches = result.schedule_matches and target_clip.get("key_hz")==100 and target_clip.get("midpoint_targets_included",false) and absf(float(target_clip.get("duration_s",-1.0))-animation.length)<0.000001
	for index in range(samples.size()):
		var sample: Dictionary = samples[index]
		var position: Array = sample.get("actor_hand_position_m",[])
		var rotation: Array = sample.get("actor_hand_rotation_xyzw",[])
		if position.size()!=3 or rotation.size()!=4:
			result.finite = false
			continue
		var time := float(sample.get("time_s",-1.0))
		var target := Vector3(position[0],position[1],position[2])
		var target_rotation := Quaternion(rotation[0],rotation[1],rotation[2],rotation[3])
		var source_key: bool = sample.get("is_source_key",false)
		result.schedule_matches = result.schedule_matches and index<expected_times.size()
		if index<expected_times.size():
			result.schedule_matches = result.schedule_matches and absf(time-expected_times[index])<0.000001 and source_key==(index%2==0)
		_pose(visual,clip,time)
		# Sidecar is already actor-space, including the25mm floor offset and PI.
		# Remove only the fixture actor world transform; never apply either twice.
		var hand := actor.global_transform.affine_inverse()*_hand(skeleton,"LeftHand")
		var actual_rotation := hand.basis.orthonormalized().get_rotation_quaternion()
		result.finite = result.finite and is_finite(time) and target.is_finite() and hand.origin.is_finite() and _quaternion_finite(target_rotation) and _quaternion_finite(actual_rotation)
		if not result.finite:
			continue
		var error := hand.origin.distance_to(target)
		var kind := "key" if source_key else "midpoint"
		result["source_key_samples" if source_key else "midpoint_samples"] += 1
		result["maximum_"+kind+"_error_m"] = maxf(result["maximum_"+kind+"_error_m"],error)
		result.maximum_orientation_error_deg = maxf(result.maximum_orientation_error_deg,_angle(actual_rotation,target_rotation))
		if error>result.maximum_target_error_m:
			result.maximum_target_error_m = error
			result.worst = {"time_s":time,"is_source_key":source_key,"target_m":[target.x,target.y,target.z],"actual_m":[hand.origin.x,hand.origin.y,hand.origin.z]}
	return result

static func _hand_keys(visual: ActorVisual, baseline: Dictionary, clip: String, keys: Array[float], local_grip: Vector3, local_tip: Vector3) -> Dictionary:
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var grip := visual.rig_weapon.find_child("GripOrigin",true,false) as Node3D
	var tip := visual.rig_weapon.find_child("BladeTip",true,false) as Node3D
	var result := {"samples":keys.size(),"right_hand_m":0.0,"left_hand_m":0.0,"grip_m":0.0,"tip_m":0.0,
		"right_hand_orientation_deg":0.0,"left_hand_orientation_deg":0.0}
	for time in keys:
		_pose(visual,clip,time)
		_baseline_pose(baseline,clip,time)
		var old_right := _hand(baseline.skeleton,"RightHand")
		var right := _hand(skeleton,"RightHand")
		var old_left := _hand(baseline.skeleton,"LeftHand")
		var left := _hand(skeleton,"LeftHand")
		result.right_hand_m = maxf(result.right_hand_m,right.origin.distance_to(old_right.origin))
		result.left_hand_m = maxf(result.left_hand_m,left.origin.distance_to(old_left.origin))
		result.grip_m = maxf(result.grip_m,grip.global_position.distance_to(old_right*local_grip))
		result.tip_m = maxf(result.tip_m,tip.global_position.distance_to(old_right*local_tip))
		result.right_hand_orientation_deg = maxf(result.right_hand_orientation_deg,_angle(right.basis.orthonormalized().get_rotation_quaternion(),old_right.basis.orthonormalized().get_rotation_quaternion()))
		result.left_hand_orientation_deg = maxf(result.left_hand_orientation_deg,_angle(left.basis.orthonormalized().get_rotation_quaternion(),old_left.basis.orthonormalized().get_rotation_quaternion()))
	return result

static func _joins(visual: ActorVisual, clip: String, previous_clip: String, epoch: int, check: Callable) -> Dictionary:
	var bridge := visual.skeletal_bridge
	bridge.enable_transition_polish()
	bridge.reset_presentation(epoch)
	visual.pose(0.0,0.0,-1.0,false,false,false,{"speed":0.0,"presentation_epoch":epoch})
	if not previous_clip.is_empty():
		var length := bridge.animation_player.get_animation(previous_clip).length
		_pose(visual,previous_clip,length-0.000001,0.0,epoch)
	_pose(visual,clip,0.0,1.0/60.0,epoch)
	var entry := bridge.transition_report()
	check.call(bridge.selected_state == StringName(clip) and is_zero_approx(bridge.sampled_time) and entry.duration <= 0.080001,"Actual light join retains target time zero and the existing80ms maximum blend")
	var data := load("res://data/"+clip+".tres") as AttackData
	var length := bridge.animation_player.get_animation(clip).length
	var active_time := data.startup/data.duration()*length
	# Supply the exact gameplay boundary rather than round-tripping it through
	# clip time and introducing a float value infinitesimally before startup.
	var active_snapshot := {"speed":0.0,"attack_id":clip,"attack_elapsed":data.startup,
		"attack_duration":data.duration(),"attack_startup":data.startup,"attack_active":data.active,"presentation_epoch":epoch}
	visual.pose(1.0/60.0,0.0,-1.0,false,false,false,active_snapshot)
	check.call(not bridge.transition_report().active and absf(bridge.sampled_time-active_time)<0.000001,"The light active boundary reaches the unblended authoritative clip clock")
	var active_bones := _sample(bridge.get_skeleton())
	var active_weapon := visual.weapon_grip.global_transform
	bridge.enable_transition_polish(false)
	visual.pose(0.0,0.0,-1.0,false,false,false,active_snapshot)
	check.call(_same_sample(active_bones,_sample(bridge.get_skeleton())) and visual.weapon_grip.global_transform.is_equal_approx(active_weapon),"Each light active boundary matches the actual raw authored skeleton and same-frame weapon")
	bridge.enable_transition_polish()
	visual.pose(0.0,0.0,-1.0,false,false,false,active_snapshot)
	var frozen := _sample(bridge.get_skeleton())
	var frozen_weapon := visual.weapon_grip.global_transform
	var frozen_transition := bridge.transition_report()
	for index in range(3):
		visual.pose(0.0,0.0,-1.0,false,false,false,active_snapshot)
	check.call(_same_sample(_sample(bridge.get_skeleton()),frozen) and visual.weapon_grip.global_transform.is_equal_approx(frozen_weapon) and bridge.transition_report()==frozen_transition,"Zero-delta light hitstop samples freeze actual bones, weapon and blend state")
	bridge.reset_presentation(epoch+1)
	visual.pose(0.0,0.0,-1.0,false,false,false,{"speed":0.0,"presentation_epoch":epoch+1})
	check.call(bridge.selected_state==&"idle" and not bridge.transition_report().active and is_zero_approx(bridge.sampled_time),"A new presentation epoch returns directly to authored idle without retaining a light blend")
	# Also exercise the ordinary return, separately from the epoch reset path.
	_pose(visual,clip,length-0.000001,0.0,epoch+1)
	visual.pose(1.0/60.0,0.0,-1.0,false,false,false,{"speed":0.0,"presentation_epoch":epoch+1})
	var idle_entry := bridge.transition_report()
	check.call(bridge.selected_state==&"idle" and idle_entry.active and idle_entry.duration<=0.080001,"Each actual light recovery enters ordinary idle through the existing bounded blend")
	for index in range(5):
		visual.pose(1.0/60.0,0.0,-1.0,false,false,false,{"speed":0.0,"presentation_epoch":epoch+1})
	check.call(not bridge.transition_report().active and _sample(bridge.get_skeleton()).finite,"Ordinary light-to-idle recovery finishes its finite blend without an epoch shortcut")
	bridge.enable_transition_polish(false)
	return {"entry":entry,"active_clip_time":active_time,"epoch_reset":epoch+1,"ordinary_idle_return":idle_entry}

static func run(world: Node3D, check: Callable) -> bool:
	var fixture := Node3D.new()
	world.add_child(fixture)
	fixture.position = Vector3(340,8,340)
	var actor := RunePlayer.new()
	actor.world = world
	fixture.add_child(actor)
	actor.set_physics_process(false)
	var visual := actor.visual
	if not is_instance_valid(visual.skeletal_bridge):
		check.call(false,"Light continuity mounts the actual production Hero and weapon")
		fixture.free()
		return false
	var baseline := _baseline(fixture,visual.ground_offset_y,check)
	if baseline.is_empty():
		fixture.free()
		return false
	var skeleton := visual.skeletal_bridge.get_skeleton()
	var old_skeleton: Skeleton3D = baseline.skeleton
	var names_match := skeleton.get_bone_count()==53 and old_skeleton.get_bone_count()==53
	for bone in range(mini(skeleton.get_bone_count(),old_skeleton.get_bone_count())):
		names_match = names_match and skeleton.get_bone_name(bone)==old_skeleton.get_bone_name(bone)
	check.call(names_match,"Candidate and independent archived control expose the same53 actual bones")
	if not names_match:
		fixture.free()
		return false
	visual.skeletal_bridge.enable_transition_polish(false)
	_pose(visual,"light_1",0.0)
	var hand := _hand(skeleton,"RightHand")
	var local_grip: Vector3 = hand.affine_inverse()*(visual.rig_weapon.find_child("GripOrigin",true,false) as Node3D).global_position
	var local_tip: Vector3 = hand.affine_inverse()*(visual.rig_weapon.find_child("BladeTip",true,false) as Node3D).global_position
	var runtime_sha := FileAccess.get_sha256(ProductionCharacterArt.definition("hero").path)
	var targets := _left_targets(runtime_sha,visual.ground_offset_y,check)
	if targets.is_empty():
		fixture.free()
		return false
	var report := {"scope":"Actual native all53bone light continuity, authored free-left key/mid targets and original right-hand/socket contracts; no fullskin, naturalness, AV, hardware or AAA approval",
		"baseline_sha256":BASELINE_SHA,"runtime_sha256":FileAccess.get_sha256(ProductionCharacterArt.definition("hero").path),
		"authored_left_target_path":LEFT_TARGET_PATH,"authored_left_target_sha256":LEFT_TARGET_SHA,"authored_left_metadata":targets.source_metadata,
		"baseline_loader":"Independent in-memory GLTF100Hz/removeImmutablefalse for original three light controls only; actual Skeleton/AnimationPlayer. Current production500Hz+100Hz posthook unchanged.",
		"angular_method":"Normalized abs(dot) shortest quaternion, local and actual world bone bases; velocity bound2700deg/s (45deg/60Hz)",
		"left_target_policy":"Intentional free-left reauthor: explicit source-sidecar actor-space key AND midpoint targets within3mm; old left positions/orientations reported only. No second PI/floor offset.",
		"clips":{}}
	for index in range(LIGHTS.size()):
		var clip: String = LIGHTS[index]
		var animation := visual.skeletal_bridge.animation_player.get_animation(clip)
		var old_animation: Animation = baseline.player.get_animation(clip)
		check.call(absf(animation.length-old_animation.length)<0.000001,"Edited light clip preserves its actual source duration: "+clip)
		var keys := _grid(animation.length,100.0)
		var schedules := {"60Hz":_grid(animation.length,60.0),"120Hz":_grid(animation.length,120.0),"all_keys_and_midpoints":_with_midpoints(_keys(animation))}
		var metrics := {}
		var all_times: Array[float] = []
		for name in schedules:
			var times: Array[float] = schedules[name]
			all_times.append_array(times)
			var current := _continuity(visual,baseline,clip,times,true)
			var old := _continuity(visual,baseline,clip,times,false)
			check.call(current.finite and current.maximum_local_deg_s<=SPEED_LIMIT_DEG_S and current.maximum_global_deg_s<=SPEED_LIMIT_DEG_S,"All53 native bones stay below the unchanged45deg/60Hz angular-speed bound: "+clip+" "+name)
			metrics[name] = {"candidate":current,"baseline":old}
		check.call(metrics["60Hz"].baseline.finite and maxf(metrics["60Hz"].baseline.maximum_local_step_deg,metrics["60Hz"].baseline.maximum_global_step_deg)>45.0,"Independent native old-source positive control exposes the real light flip: "+clip)
		var hands := _hand_keys(visual,baseline,clip,keys,local_grip,local_tip)
		check.call(hands.right_hand_m<0.003 and hands.grip_m<0.003 and hands.tip_m<0.003,"Edited light preserves original100Hz right-hand and actual Grip/Tip targets within3mm: "+clip)
		var authored_left := _authored_left(visual,actor,clip,targets.clips.get(clip,{}))
		check.call(authored_left.finite and authored_left.schedule_matches and authored_left.maximum_target_error_m<0.003,"Reauthored free-left hand matches explicit source targets at every key and independent midpoint within3mm: "+clip)
		var all_hands := _hand_keys(visual,baseline,clip,_dedupe_times(all_times,animation.length),local_grip,local_tip)
		check.call(all_hands.right_hand_m<0.003 and all_hands.grip_m<0.003 and all_hands.tip_m<0.003,"Structurally untouched right branch preserves hand/Grip/Tip at60/120Hz and every key/midpoint within3mm: "+clip)
		var previous: String = LIGHTS[index-1] if index>0 else ""
		report.clips[clip] = {"continuity":metrics,"original_right_key_identity_old_left_diagnostic":hands,"authored_free_left_targets":authored_left,"all_schedule_right_identity_old_left_diagnostic":all_hands,"joins":_joins(visual,clip,previous,14000+index*10,check)}
	var curve := RunePlayer.CHARGED_HEAVY.blade_curve_report()
	var text := FileAccess.get_file_as_string(RunePlayer.CHARGED_HEAVY.blade_curve_path)
	var source_sha := String(curve.get("source_sha256",""))
	check.call(curve.ok and source_sha==String(report.runtime_sha256) and source_sha!=BASELINE_SHA and text.count(source_sha)==1 and text.replace(source_sha,BASELINE_SHA).sha256_text()==ORIGINAL_CURVE_SHA,"Only curve source-SHA metadata changes; inverse substitution preserves every original91-sample curve byte")
	var path := ProjectSettings.globalize_path("res://../build/verification/light-continuity/native.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report,"\t")+"\n")
		file.close()
	fixture.free()
	return true
