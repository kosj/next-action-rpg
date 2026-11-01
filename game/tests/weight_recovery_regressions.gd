extends RefCounted

# Compare imported motion against the immutable v0.1.8 runtime, then exercise
# the real production bridge. This measures changed poses and clock/joins;
# it does not approve normal-speed choreography, terrain contact or AAA art.
const BASELINES := {
	"hero":{"path":"res://assets/models/production/lyra_impact_gameplay.glb","sha256":"0aa78c46c0453f8286785ee937ef9388324dc4312bb076f5179934f08e44d57d"},
	"sentinel_melee":{"path":"res://assets/models/production/sentinel_impact_gameplay.glb","sha256":"6180967f4220651f5a9a343109e07bfab5831252c875170d008d17072d09c576"},
}

static func _pose(visual: ActorVisual, state: String, time: float, delta: float = 0.0) -> void:
	var snapshot: Dictionary = {"speed":0.0}
	if state == "charge":
		snapshot.merge({"charge_active":true,"charge_elapsed":time,"charge_duration":.65})
	elif state == "charged_heavy":
		var data := RunePlayer.CHARGED_HEAVY
		snapshot.merge({"attack_id":state,"attack_elapsed":time,"attack_duration":data.duration(),"attack_startup":data.startup,"attack_active":data.active})
	elif state == "heavy_hit":
		snapshot.merge({"stagger":maxf(.000001,.48-time),"hit_reaction":state,"hit_elapsed":time,"hit_duration":.48})
	visual.pose(delta,0.0,-1.0,false,false,false,snapshot)

static func _sample(bridge: SkeletalVisualBridge, actor: Node3D) -> Dictionary:
	var skeleton := bridge.get_skeleton()
	var positions: Dictionary = {}
	var rotations: Dictionary = {}
	var into_actor := actor.global_transform.affine_inverse()*skeleton.global_transform
	for index in range(skeleton.get_bone_count()):
		var name := String(skeleton.get_bone_name(index))
		positions[name] = (into_actor*skeleton.get_bone_global_pose(index)).origin
		rotations[name] = skeleton.get_bone_pose_rotation(index)
	return {"positions":positions,"rotations":rotations}

static func _difference(first: Dictionary, second: Dictionary) -> Dictionary:
	var distance := 0.0
	var angle := 0.0
	for name in first.positions:
		var a: Vector3 = first.positions[name]
		var b: Vector3 = second.positions[name]
		var qa: Quaternion = first.rotations[name]
		var qb: Quaternion = second.rotations[name]
		distance = maxf(distance,a.distance_to(b))
		angle = maxf(angle,qa.angle_to(qb))
	return {"max_joint_distance_m":distance,"max_local_rotation_rad":angle}

static func _baseline(parent: Node3D, profile: String, height_offset: float) -> Dictionary:
	var scene := load(String(BASELINES[profile].path)) as PackedScene
	if scene == null:
		return {"ok":false,"reason":"Pinned baseline scene could not be loaded"}
	var instance := scene.instantiate()
	var player := ProductionCharacterArt.find_type(instance,"AnimationPlayer") as AnimationPlayer
	if player == null:
		instance.free()
		return {"ok":false,"reason":"Pinned baseline has no AnimationPlayer"}
	# Raw glTF clips carry no authoritative loop flag. Apply the same isolated
	# resource-copy policy as ProductionCharacterArt.prepare(), never mutating
	# cached source clips or redirecting the global production profile mapping.
	var states: Array[StringName] = ProductionCharacterArt.definition(profile).states.duplicate()
	states.append(&"RESET")
	var library := AnimationLibrary.new()
	for state in states:
		if not player.has_animation(state):
			instance.free()
			return {"ok":false,"reason":"Pinned baseline is missing state: %s" % state}
		var animation := player.get_animation(state).duplicate(true) as Animation
		animation.loop_mode = Animation.LOOP_LINEAR if state in ProductionCharacterArt.CYCLES else Animation.LOOP_NONE
		library.add_animation(state,animation)
	for name in player.get_animation_library_list():
		player.remove_animation_library(name)
	player.add_animation_library(&"",library)
	player.autoplay = ""
	var packed := PackedScene.new()
	var packed_result := packed.pack(instance)
	instance.free()
	if packed_result != OK:
		return {"ok":false,"reason":"Pinned baseline runtime copy could not be packed"}
	var bridge := SkeletalVisualBridge.new()
	parent.add_child(bridge)
	bridge.position.y = height_offset
	var result := bridge.mount_scene(packed,{},ProductionCharacterArt.definition(profile).states)
	print("RUNEFALL_WEIGHT_BASELINE_MOUNT: ",JSON.stringify({"profile":profile,"ok":result.ok,"reason":result.reason}))
	result["bridge"] = bridge
	return result

static func _baseline_pose(bridge: SkeletalVisualBridge, state: String, time: float) -> void:
	var snapshot: Dictionary = {"speed":0.0}
	if state == "charged_heavy":
		snapshot.merge({"attack_id":state,"attack_elapsed":time,"attack_duration":1.06,"attack_startup":.34,"attack_active":.18})
	elif state == "heavy_hit":
		snapshot.merge({"stagger":maxf(.000001,.48-time),"hit_reaction":state,"hit_elapsed":time,"hit_duration":.48})
	bridge.present(0.0,snapshot)

static func run(world: Node3D, check: Callable) -> bool:
	var fixture := Node3D.new()
	world.add_child(fixture)
	fixture.position = Vector3(280,8,280)
	var hero := RunePlayer.new()
	hero.world = world
	fixture.add_child(hero)
	hero.set_physics_process(false)
	var sentinel := RuneEnemy.new()
	sentinel.player = hero
	sentinel.world = world
	fixture.add_child(sentinel)
	sentinel.set_physics_process(false)
	var ready := is_instance_valid(hero.visual.skeletal_bridge) and is_instance_valid(sentinel.visual.skeletal_bridge)
	check.call(ready,"Weight recovery checks mount the actual new production controllers and both weighted rigs")
	if not ready:
		fixture.free()
		return false
	var pinned := true
	for profile in BASELINES:
		pinned = pinned and FileAccess.get_sha256(BASELINES[profile].path) == BASELINES[profile].sha256
	check.call(pinned,"Choreography comparisons use the exact immutable v0.1.8 body and motion baselines")
	var hero_baseline := _baseline(hero,"hero",hero.visual.ground_offset_y)
	var sentinel_baseline := _baseline(sentinel,"sentinel_melee",sentinel.visual.ground_offset_y)
	if not hero_baseline.ok or not sentinel_baseline.ok:
		check.call(false,"Both pinned baseline AnimationTrees mount for independent posed comparisons: hero=%s; sentinel=%s" % [hero_baseline.reason,sentinel_baseline.reason])
		fixture.free()
		return false
	var old_hero := hero_baseline.bridge as SkeletalVisualBridge
	var old_sentinel := sentinel_baseline.bridge as SkeletalVisualBridge
	_pose(hero.visual,"charge",.65)
	var loaded := _sample(hero.visual.skeletal_bridge,hero)
	_pose(hero.visual,"charged_heavy",0.0)
	var joined := _sample(hero.visual.skeletal_bridge,hero)
	var join := _difference(loaded,joined)
	check.call(float(join.max_joint_distance_m) < .001 and float(join.max_local_rotation_rad) < deg_to_rad(.1),"Stationary held charge and released attack share all 53 bone poses within 1mm and 0.1 degree")
	var hero_rows: Array[Dictionary] = []
	var new_hips: Array[Vector3] = []
	var old_hips: Array[Vector3] = []
	var startup_hip_shift := 0.0
	var baseline_startup_hip_shift := 0.0
	for time: float in [0.0,.12,.22,.30,.34,.43,.52,.66,.84,1.04]:
		_pose(hero.visual,"charged_heavy",time)
		_baseline_pose(old_hero,"charged_heavy",time)
		var current := _sample(hero.visual.skeletal_bridge,hero)
		var prior := _sample(old_hero,hero)
		var hips: Vector3 = current.positions.Hips
		var old: Vector3 = prior.positions.Hips
		new_hips.append(hips)
		old_hips.append(old)
		if time <= .34:
			startup_hip_shift = maxf(startup_hip_shift,Vector2(hips.x-new_hips[0].x,hips.z-new_hips[0].z).length())
			baseline_startup_hip_shift = maxf(baseline_startup_hip_shift,Vector2(old.x-old_hips[0].x,old.z-old_hips[0].z).length())
		hero_rows.append({"time":time,"body_difference":_difference(current,prior),"hips_y":hips.y,"baseline_hips_y":old.y})
	check.call(startup_hip_shift > baseline_startup_hip_shift+.01,"New charged preparation transfers the pelvis horizontally by at least 1cm more than the pinned v0.1.8 motion")
	_pose(sentinel.visual,"idle",0.0)
	var guard := _sample(sentinel.visual.skeletal_bridge,sentinel)
	var sentinel_rows: Array[Dictionary] = []
	var maximum_body_change := 0.0
	var maximum_foot_change := 0.0
	var preserved_clock := true
	var near_end: Dictionary
	for time: float in [0.0,.075,.16,.24,.32,.40,.4666666667]:
		_pose(sentinel.visual,"heavy_hit",time)
		_baseline_pose(old_sentinel,"heavy_hit",time)
		var current := _sample(sentinel.visual.skeletal_bridge,sentinel)
		var prior := _sample(old_sentinel,sentinel)
		var hips: Vector3 = current.positions.Hips
		var old: Vector3 = prior.positions.Hips
		maximum_body_change = maxf(maximum_body_change,hips.distance_to(old))
		for bone in ["LeftFoot","RightFoot"]:
			var foot: Vector3 = current.positions[bone]
			var old_foot: Vector3 = prior.positions[bone]
			maximum_foot_change = maxf(maximum_foot_change,foot.distance_to(old_foot))
		preserved_clock = preserved_clock and sentinel.visual.skeletal_bridge.selected_state == &"heavy_hit" and absf(sentinel.visual.skeletal_bridge.sampled_time-time) < .001
		near_end = current
		sentinel_rows.append({"time":time,"hips_difference_m":hips.distance_to(old),"guard_difference":_difference(current,guard)})
	check.call(maximum_body_change > .01 and maximum_foot_change > .01,"New strong-hit braking changes actual pelvis and foot paths by more than 1cm from the old reaction")
	check.call(preserved_clock,"The heavy-hit bridge preserves braking and recovery through the normal final 0.4667s physics sample without truncating at motor completion")
	var guard_return := _difference(near_end,guard)
	check.call(float(guard_return.max_joint_distance_m) < .02,"The final half-open reaction sample has recovered all joints within 2cm of guard")
	_pose(sentinel.visual,"idle",0.0,1.0/60.0)
	var idle_join := _difference(near_end,_sample(sentinel.visual.skeletal_bridge,sentinel))
	check.call(sentinel.visual.skeletal_bridge.selected_state == &"idle" and float(idle_join.max_joint_distance_m) < .02,"Returning from the completed reaction to idle keeps a bounded 2cm first-frame pose transition")
	var report: Dictionary = {"scope":"Actual imported choreography changes versus pinned v0.1.8 and final presentation joins. Foot changes are actor-local pose measurements, not world footplant during collision-resolved recoil; no terrain IK, normal-speed AV, target hardware or AAA approval",
		"baselines":BASELINES,"hero_path":ProductionCharacterArt.definition("hero").path,"sentinel_path":ProductionCharacterArt.definition("sentinel_melee").path,
		"hero_sha256":FileAccess.get_sha256(ProductionCharacterArt.definition("hero").path),"sentinel_sha256":FileAccess.get_sha256(ProductionCharacterArt.definition("sentinel_melee").path),
		"stationary_charge_release_join":join,"startup_hip_shift_m":startup_hip_shift,"baseline_startup_hip_shift_m":baseline_startup_hip_shift,
		"hero_samples":hero_rows,"sentinel_samples":sentinel_rows,"max_sentinel_hip_change_m":maximum_body_change,"max_sentinel_foot_change_m":maximum_foot_change,
		"near_end_guard_join":guard_return,"first_idle_join":idle_join,"reaction_clock_preserved":preserved_clock}
	var path := ProjectSettings.globalize_path("res://").path_join("../build/verification/heavy-weight/recovery.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report,"\t")+"\n")
		file.close()
	else:
		push_error("Cannot write native weight recovery proof")
	fixture.free()
	return true
