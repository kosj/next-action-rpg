class_name SkeletalVisualBridge
extends Node3D

# AnimationTree owns playback; elapsed action time comes only from gameplay.
const REQUIRED_STATES: Array[StringName] = [&"idle", &"walk", &"run", &"dodge", &"light_1", &"light_2", &"light_3", &"parry", &"hit"]
const LOOP_STATES: Array[StringName] = [&"idle", &"walk", &"run", &"walk_back", &"walk_left", &"walk_right", &"run_back", &"run_left", &"run_right"]
const TRANSITION_SECONDS := 0.08
var animation_player: AnimationPlayer
var animation_tree: AnimationTree
var rig: Node3D
var clips: Dictionary = {}
var last_error: String = ""
var selected_state: StringName = &""
var selected_clip: StringName = &""
var sampled_time: float = 0.0
var locomotion_clock: float = 0.0
var _clip_node: AnimationNodeAnimation
var _charge_clip_node: AnimationNodeAnimation
var _charge_layer_active: bool = false
var _charge_layer_time: float = 0.0
var _skeleton: Skeleton3D
var _base_rig_yaw: float = 0.0
var _presentation_epoch: int = 0
var _transition_polish_enabled: bool = false
var _has_presented_pose: bool = false
var _gait_phase: float = 0.0
var _idle_clock: float = 0.0
var _blend_elapsed: float = 0.0
var _blend_duration: float = 0.0
var _blend_yaw: float = 0.0
var _blend_positions := PackedVector3Array()
var _blend_rotations: Array[Quaternion] = []
var _blend_scales := PackedVector3Array()
var _blend_upper_only: bool = false

func _is_upper_bone(index: int) -> bool:
	while index >= 0:
		if _skeleton.get_bone_name(index) == "Spine":
			return true
		index = _skeleton.get_bone_parent(index)
	return false

# Facing uses gameplay -Z. Snapshots expose only fresh scalar components,
# never mutable controller/skeleton references.
static func local_direction(direction: Vector3, facing: Vector3) -> Vector2:
	var horizontal := Vector3(direction.x, 0.0, direction.z)
	var forward := Vector3(facing.x, 0.0, facing.z)
	if not horizontal.is_finite() or not forward.is_finite() or horizontal.length_squared() <= 0.000001:
		return Vector2.ZERO
	if forward.length_squared() <= 0.000001:
		forward = Vector3.FORWARD
	var yaw := atan2(-forward.x, -forward.z)
	var local := horizontal.normalized().rotated(Vector3.UP, -yaw)
	return Vector2(local.x, local.z)

func get_skeleton() -> Skeleton3D:
	return _skeleton

func enable_transition_polish(enabled: bool = true) -> Dictionary:
	# An explicit production opt-in. Sparse synthetic/imported clips keep their
	# original immediate-sampling contract; every blended target must overwrite
	# every local bone channel so yesterday's blended pose cannot feed back.
	if enabled:
		var reason := _complete_pose_error()
		if not reason.is_empty():
			return {"ok":false, "reason":reason}
	_transition_polish_enabled = enabled
	reset_presentation(_presentation_epoch)
	return {"ok":true, "reason":""}

func transition_report() -> Dictionary:
	return {"enabled":_transition_polish_enabled, "active":_blend_duration > 0.0,
		"elapsed":_blend_elapsed, "duration":_blend_duration, "gait_phase":_gait_phase,
		"charge_upper_body":_charge_layer_active,"charge_sampled_time":_charge_layer_time}

func _complete_pose_error() -> String:
	if not is_instance_valid(_skeleton) or animation_player == null:
		return "Transition polish requires a mounted skeletal rig"
	var root := animation_player.get_node(animation_player.root_node)
	var animations: Array = clips.values()
	animations.append(&"RESET")
	for clip: StringName in animations:
		var animation := animation_player.get_animation(clip)
		var channels: Dictionary = {}
		for track in range(animation.get_track_count()):
			var path := animation.track_get_path(track)
			var names := path.get_concatenated_names()
			var target := root if names.is_empty() else root.get_node_or_null(NodePath(names))
			var type := animation.track_get_type(track)
			if target != _skeleton or path.get_subname_count() != 1 or not type in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D]:
				return "Transition polish requires complete skeleton-only transform clips: %s" % clip
			var bone := _skeleton.find_bone(path.get_subname(0))
			var bit := 1 if type == Animation.TYPE_POSITION_3D else (2 if type == Animation.TYPE_ROTATION_3D else 4)
			channels[bone] = int(channels.get(bone, 0)) | bit
		for bone in range(_skeleton.get_bone_count()):
			if channels.get(bone, 0) != 7:
				return "Transition polish requires all bone channels in %s: %s" % [clip, _skeleton.get_bone_name(bone)]
	return ""

func bone_report() -> Dictionary:
	var names: Array[StringName] = []
	var roles: Dictionary = {}
	if is_instance_valid(_skeleton):
		for index in range(_skeleton.get_bone_count()):
			names.append(_skeleton.get_bone_name(index))
		# Exact provider bone names only; absence never invents a hand mapping.
		var role_names := {"right_hand":"RightHand", "left_hand":"LeftHand", "hips":"Hips", "head":"Head"}
		for role in role_names:
			var bone_name: String = role_names[role]
			var index := _skeleton.find_bone(bone_name)
			if index >= 0:
				roles[role] = {"name":bone_name, "index":index}
	return {"names":names, "roles":roles}

func mount_scene(scene: PackedScene, aliases: Dictionary = {}, required_states: Array[StringName] = REQUIRED_STATES, facing_correction: float = PI) -> Dictionary:
	if rig != null or required_states.is_empty() or not &"idle" in required_states:
		return _failure("A fresh bridge and a required idle state are needed")
	if scene == null or not scene.can_instantiate():
		return _failure("No rig scene was supplied")
	var instance := scene.instantiate()
	if not instance is Node3D:
		instance.free()
		return _failure("Rig scene root must be Node3D")
	var skeleton: Skeleton3D = _find_type(instance, "Skeleton3D") as Skeleton3D
	var player: AnimationPlayer = _find_type(instance, "AnimationPlayer") as AnimationPlayer
	if skeleton == null or skeleton.get_bone_count() == 0:
		instance.free()
		return _failure("Rig requires a Skeleton3D with bones")
	var skin_report := _skin_report(instance)
	if skin_report.count == 0 or not String(skin_report.error).is_empty():
		instance.free()
		return _failure("Rig requires valid weighted Skin bindings: %s" % skin_report.error)
	if player == null or not player.has_animation(&"RESET"):
		instance.free()
		return _failure("Rig requires an AnimationPlayer and RESET pose")
	var reset_error := _validate_tracks(player, player.get_animation(&"RESET"), instance)
	if not reset_error.is_empty():
		instance.free()
		return _failure("RESET: %s" % reset_error)
	var candidate_clips: Dictionary = {}
	for state: StringName in required_states:
		candidate_clips[state] = state
	for state in aliases:
		if not (state is String or state is StringName) or not (aliases[state] is String or aliases[state] is StringName):
			instance.free()
			return _failure("Clip aliases must map text state names to text clip names")
		candidate_clips[StringName(state)] = StringName(aliases[state])
	for state in candidate_clips:
		var clip: StringName = candidate_clips[state]
		if not player.has_animation(clip):
			instance.free()
			return _failure("Missing clip for %s: %s" % [state, clip])
		var animation := player.get_animation(clip)
		if animation.length <= 0.0:
			instance.free()
			return _failure("Clip must have a positive length: %s" % clip)
		if state in LOOP_STATES and animation.loop_mode == Animation.LOOP_NONE:
			instance.free()
			return _failure("Locomotion clip must loop: %s" % clip)
		if not state in LOOP_STATES and animation.loop_mode != Animation.LOOP_NONE:
			instance.free()
			return _failure("Action clip must not loop: %s" % clip)
		var track_error := _validate_tracks(player, animation, instance)
		if not track_error.is_empty():
			instance.free()
			return _failure("%s: %s" % [clip, track_error])
	# Only attach after validation; a rejected scene never starts its animations.
	rig = instance
	clips = candidate_clips
	animation_player = player
	_skeleton = skeleton
	rig.rotation.y += facing_correction # Humanoid +Z -> gameplay -Z, once in this wrapper.
	_base_rig_yaw = rig.rotation.y
	_disable_automatic_playback(rig)
	add_child(rig)
	animation_tree = AnimationTree.new()
	animation_tree.name = "SkeletalAnimationTree"
	add_child(animation_tree)
	animation_tree.anim_player = animation_tree.get_path_to(animation_player)
	animation_tree.root_node = animation_tree.get_path_to(animation_player.get_node(animation_player.root_node))
	animation_tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	var blend := AnimationNodeBlendTree.new()
	_clip_node = AnimationNodeAnimation.new()
	_clip_node.animation = clips[&"idle"] if clips.has(&"idle") else clips.values()[0]
	var seek := AnimationNodeTimeSeek.new()
	blend.add_node(&"Clip", _clip_node)
	blend.add_node(&"Clock", seek)
	blend.connect_node(&"Clock", 0, &"Clip")
	if clips.has(&"charge") and _skeleton.find_bone("Spine") >= 0:
		# Filter an independent charge clock onto Spine descendants only. Hips,
		# Root and every leg/foot remain the current locomotion sample.
		_charge_clip_node = AnimationNodeAnimation.new()
		_charge_clip_node.animation = clips[&"charge"]
		var charge_clock := AnimationNodeTimeSeek.new()
		var upper := AnimationNodeBlend2.new()
		upper.filter_enabled = true
		var charge_animation := animation_player.get_animation(clips[&"charge"])
		var spine := _skeleton.find_bone("Spine")
		for track in range(charge_animation.get_track_count()):
			var path := charge_animation.track_get_path(track)
			if path.get_subname_count() != 1:
				continue
			var bone := _skeleton.find_bone(path.get_subname(0))
			while bone >= 0:
				if bone == spine:
					upper.set_filter_path(path, true)
					break
				bone = _skeleton.get_bone_parent(bone)
		blend.add_node(&"ChargeClip", _charge_clip_node)
		blend.add_node(&"ChargeClock", charge_clock)
		blend.add_node(&"ChargeUpper", upper)
		blend.connect_node(&"ChargeClock", 0, &"ChargeClip")
		blend.connect_node(&"ChargeUpper", 0, &"Clock")
		blend.connect_node(&"ChargeUpper", 1, &"ChargeClock")
		blend.connect_node(&"output", 0, &"ChargeUpper")
	else:
		blend.connect_node(&"output", 0, &"Clock")
	animation_tree.tree_root = blend
	animation_tree.active = true
	reset_presentation()
	last_error = ""
	return {"ok":true, "reason":"", "bones":skeleton.get_bone_count(), "states":clips.keys(), "bone_mapping":bone_report()}

func reset_presentation(epoch: int = 0) -> void:
	_presentation_epoch = epoch
	locomotion_clock = 0.0
	selected_state = &""
	selected_clip = &""
	sampled_time = 0.0
	_has_presented_pose = false
	_gait_phase = 0.0
	_idle_clock = 0.0
	_clear_transition()
	_charge_layer_active = false
	_charge_layer_time = 0.0
	if _charge_clip_node != null and animation_tree != null:
		animation_tree.set("parameters/ChargeUpper/blend_amount", 0.0)
		animation_tree.set("parameters/ChargeClock/seek_request", 0.0)
	if is_instance_valid(rig):
		rig.rotation.y = _base_rig_yaw
	if animation_tree != null and _clip_node != null:
		_clip_node.animation = &"RESET"
		animation_tree.set("parameters/Clock/seek_request", 0.0)
		animation_tree.advance(0.0)

func _clear_transition() -> void:
	_blend_elapsed = 0.0
	_blend_duration = 0.0
	_blend_positions.clear()
	_blend_rotations.clear()
	_blend_scales.clear()
	_blend_upper_only = false

func _capture_transition(duration: float, upper_only: bool = false) -> void:
	_clear_transition()
	_blend_upper_only = upper_only
	_blend_duration = duration
	_blend_yaw = rig.rotation.y - _base_rig_yaw
	for bone in range(_skeleton.get_bone_count()):
		_blend_positions.append(_skeleton.get_bone_pose_position(bone))
		_blend_rotations.append(_skeleton.get_bone_pose_rotation(bone))
		_blend_scales.append(_skeleton.get_bone_pose_scale(bone))

func _blend_pose(delta: float, visual_yaw: float) -> void:
	if _blend_duration <= 0.0:
		return
	_blend_elapsed = minf(_blend_duration, _blend_elapsed + maxf(delta, 0.0))
	if _blend_elapsed >= _blend_duration:
		_clear_transition()
		return # The exact authored target is already sampled, including yaw.
	var amount := _blend_elapsed / _blend_duration
	amount = amount * amount * (3.0 - 2.0 * amount)
	for bone in range(_skeleton.get_bone_count()):
		if _blend_upper_only and not _is_upper_bone(bone):
			continue
		_skeleton.set_bone_pose_position(bone, _blend_positions[bone].lerp(_skeleton.get_bone_pose_position(bone), amount))
		_skeleton.set_bone_pose_rotation(bone, _blend_rotations[bone].slerp(_skeleton.get_bone_pose_rotation(bone), amount))
		_skeleton.set_bone_pose_scale(bone, _blend_scales[bone].lerp(_skeleton.get_bone_pose_scale(bone), amount))
	if not _blend_upper_only:
		rig.rotation.y = _base_rig_yaw + lerp_angle(_blend_yaw, visual_yaw, amount)

func _failure(reason: String) -> Dictionary:
	last_error = reason
	return {"ok":false, "reason":reason}

func _find_type(node: Node, type: String) -> Node:
	if node.is_class(type):
		return node
	for child in node.get_children():
		var found := _find_type(child, type)
		if found != null:
			return found
	return null

func _skin_report(node: Node) -> Dictionary:
	var count := 0
	if node is MeshInstance3D:
		var mesh := node as MeshInstance3D
		if mesh.skin != null:
			if mesh.mesh == null or mesh.skin.get_bind_count() == 0:
				return {"count":0, "error":"Skin has no mesh or bindings"}
			var skeleton := mesh.get_node_or_null(mesh.skeleton) as Skeleton3D
			if skeleton == null or skeleton.get_bone_count() == 0:
				return {"count":0, "error":"Skin skeleton path does not resolve"}
			for index in range(mesh.skin.get_bind_count()):
				var bone := mesh.skin.get_bind_bone(index)
				var bone_name := mesh.skin.get_bind_name(index)
				if not ((bone_name.is_empty() and bone >= 0 and bone < skeleton.get_bone_count()) or (not bone_name.is_empty() and skeleton.find_bone(bone_name) >= 0)):
					return {"count":0, "error":"Skin binding does not resolve to a bone"}
			if not _weighted_surfaces(mesh.mesh, mesh.skin.get_bind_count()):
				return {"count":0, "error":"Skin mesh requires normalized per-vertex weights and valid bind indices"}
			count = 1
	for child in node.get_children():
		var report := _skin_report(child)
		if not String(report.error).is_empty():
			return report
		count += int(report.count)
	return {"count":count, "error":""}

func _weighted_surfaces(mesh: Mesh, bind_count: int) -> bool:
	if mesh.get_surface_count() == 0:
		return false
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var vertices = arrays[Mesh.ARRAY_VERTEX]
		var bones = arrays[Mesh.ARRAY_BONES]
		var weights = arrays[Mesh.ARRAY_WEIGHTS]
		if vertices == null or vertices.size() == 0 or bones == null or weights == null or bones.size() != weights.size():
			return false
		var influences: int = weights.size() / vertices.size()
		if not influences in [4, 8] or weights.size() != vertices.size() * influences:
			return false
		for vertex in range(vertices.size()):
			var total := 0.0
			for influence in range(influences):
				var index: int = vertex * influences + influence
				var weight: float = weights[index]
				if not is_finite(weight) or weight < 0.0 or (weight > 0.0 and (bones[index] < 0 or bones[index] >= bind_count)):
					return false
				total += weight
			if absf(total-1.0) > 0.01:
				return false
	return true

func _disable_automatic_playback(node: Node) -> void:
	if node is AnimationPlayer:
		node.autoplay = ""
		node.stop()
		node.active = false
	elif node is AnimationTree:
		node.active = false
	for child in node.get_children():
		_disable_automatic_playback(child)

func _validate_tracks(player: AnimationPlayer, animation: Animation, boundary: Node3D) -> String:
	if animation.get_track_count() == 0:
		return "Clip has no authored tracks"
	if player.root_node.is_absolute():
		return "Animation root must remain relative to the rig"
	var root := player.get_node_or_null(player.root_node)
	if root == null or (root != boundary and not boundary.is_ancestor_of(root)):
		return "Animation root does not resolve inside the rig"
	for index in range(animation.get_track_count()):
		var type := animation.track_get_type(index)
		if not type in [Animation.TYPE_POSITION_3D, Animation.TYPE_ROTATION_3D, Animation.TYPE_SCALE_3D, Animation.TYPE_BLEND_SHAPE]:
			return "Only visual transform and blend shape tracks are permitted"
		var path := animation.track_get_path(index)
		if path.is_absolute():
			return "Track target must remain inside the rig: %s" % path
		var names := path.get_concatenated_names()
		var target := root if names.is_empty() else root.get_node_or_null(NodePath(names))
		if target == null:
			return "Track target does not resolve: %s" % path
		if target != boundary and not boundary.is_ancestor_of(target):
			return "Track target escapes the rig: %s" % path
		if target.get_script() != null or target is CollisionObject3D or target is CollisionShape3D:
			return "Tracks may not target gameplay scripts or collision objects: %s" % path
		if type == Animation.TYPE_BLEND_SHAPE:
			if not target is MeshInstance3D or target.mesh == null or path.get_subname_count() != 1:
				return "Blend shape target does not resolve: %s" % path
			var shape_name := String(path.get_subname(0)).trim_prefix("blend_shapes/")
			var shape_found := false
			for shape in range(target.mesh.get_blend_shape_count()):
				shape_found = shape_found or target.mesh.get_blend_shape_name(shape) == shape_name
			if not shape_found:
				return "Blend shape does not exist: %s" % path
		elif target is Skeleton3D:
			if path.get_subname_count() != 1 or target.find_bone(path.get_subname(0)) < 0:
				return "Track bone does not resolve: %s" % path
		elif not target is Node3D or path.get_subname_count() != 0:
			return "Transform tracks must target visual Node3D transforms or skeleton bones: %s" % path
	return ""

func present(delta: float, snapshot: Dictionary) -> bool:
	if animation_tree == null:
		return false
	var speed := float(snapshot.get("speed", 0.0))
	if not is_finite(speed) or not is_finite(delta):
		last_error = "Presentation speed and delta must be finite"
		return false
	speed = maxf(0.0, speed)
	var epoch := int(snapshot.get("presentation_epoch", _presentation_epoch))
	if epoch != _presentation_epoch:
		reset_presentation(epoch)
	var state: StringName = &"idle"
	var elapsed: float = 0.0
	var duration: float = 0.0
	var visual_yaw := 0.0
	if snapshot.get("dead", false):
		state = &"death"
		elapsed = float(snapshot.get("death_elapsed", 0.0))
		duration = float(snapshot.get("death_duration", 0.0))
	elif float(snapshot.get("stagger", 0.0)) > 0.0:
		state = StringName(snapshot.get("hit_reaction", "hit"))
		elapsed = float(snapshot.get("hit_elapsed", 0.0))
		duration = float(snapshot.get("hit_duration", 0.15))
	elif float(snapshot.get("dodge_remaining", 0.0)) > 0.0:
		state = &"dodge"
		elapsed = float(snapshot.get("dodge_elapsed", 0.0))
		duration = float(snapshot.get("dodge_duration", 0.32))
		var direction := Vector2(float(snapshot.get("dodge_local_x", 0.0)), float(snapshot.get("dodge_local_z", -1.0)))
		if not direction.is_finite():
			last_error = "Dodge direction must be finite"
			return false
		if direction.length_squared() > 0.000001:
			visual_yaw = atan2(-direction.x, -direction.y)
	elif float(snapshot.get("parry_remaining", 0.0)) > 0.0:
		state = &"parry"
		elapsed = float(snapshot.get("parry_elapsed", 0.0))
		duration = float(snapshot.get("parry_duration", 0.22))
	elif not String(snapshot.get("attack_id", "")).is_empty():
		state = StringName(snapshot.attack_id)
		elapsed = float(snapshot.get("attack_elapsed", 0.0))
		duration = float(snapshot.get("attack_duration", 0.0))
	elif speed > 0.1:
		state = &"run" if speed >= 7.4 else &"walk"
		var direction := Vector2(float(snapshot.get("move_local_x", 0.0)), float(snapshot.get("move_local_z", -1.0)))
		if not direction.is_finite():
			last_error = "Locomotion direction must be finite"
			return false
		# Nearest cardinal axis, with exact diagonal ties choosing forward/back.
		# Side/back sprint uses the authored directional walk cycle at its actual
		# velocity ratio; it must never silently play the forward sprint cycle.
		if absf(direction.x) > absf(direction.y):
			state = &"walk_right" if direction.x > 0.0 else &"walk_left"
		elif direction.y > 0.0:
			state = &"walk_back"
	elif bool(snapshot.get("charge_active", false)):
		state = &"charge"
		elapsed = float(snapshot.get("charge_elapsed", 0.0))
		duration = float(snapshot.get("charge_duration", 0.65))
	elif float(snapshot.get("heal_remaining", 0.0)) > 0.0:
		# The potion effect is instant and locomotion/actions keep priority. This
		# stationary gesture introduces no gameplay lock or delayed healing.
		state = &"heal"
		elapsed = float(snapshot.get("heal_elapsed", 0.0))
		duration = float(snapshot.get("heal_duration", 0.35))
	if not clips.has(state):
		last_error = "No authored clip for state: %s" % state
		_has_presented_pose = false
		_clear_transition()
		return false # Caller shows the original visual instead of faking a clip.
	var next_clip: StringName = clips[state]
	var length := animation_player.get_animation(next_clip).length
	var previous_time := sampled_time
	var state_changed := state != selected_state or next_clip != selected_clip
	var previous_charge_time := _charge_layer_time
	var charge_layer := _charge_clip_node != null and state in LOOP_STATES and state != &"idle" and bool(snapshot.get("charge_active", false))
	var charge_layer_changed := charge_layer != _charge_layer_active
	if charge_layer:
		var charge_duration := float(snapshot.get("charge_duration", 0.65))
		var charge_elapsed := float(snapshot.get("charge_elapsed", 0.0))
		if not is_finite(charge_duration) or charge_duration <= 0.0 or not is_finite(charge_elapsed):
			last_error = "Moving charge requires finite gameplay elapsed and duration"
			return false
		_charge_layer_time = clampf(charge_elapsed/charge_duration,0.0,1.0)*animation_player.get_animation(clips[&"charge"]).length
	else:
		_charge_layer_time = 0.0
	if state in LOOP_STATES:
		var reference_speed := 8.5 if state == &"run" else 6.4
		reference_speed = float(snapshot.get("locomotion_reference_speed", reference_speed))
		if not is_finite(reference_speed) or reference_speed <= 0.0:
			last_error = "Locomotion reference speed must be finite and positive"
			return false
		var advance := maxf(delta, 0.0) * (1.0 if state == &"idle" else speed / reference_speed)
		locomotion_clock += advance
		if _transition_polish_enabled:
			if state == &"idle":
				_idle_clock += advance
				sampled_time = fposmod(_idle_clock, length)
			else:
				# Keep the same left/right-foot phase when a direction or cycle
				# length changes. Idle breathing has an independent clock.
				_gait_phase = fposmod(_gait_phase + advance / length, 1.0)
				sampled_time = _gait_phase * length
		else:
			sampled_time = fposmod(locomotion_clock, length)
	else:
		if state == &"death" and duration <= 0.0:
			duration = length
		if not is_finite(elapsed) or not is_finite(duration) or duration <= 0.0:
			last_error = "Action requires finite gameplay elapsed and duration: %s" % state
			return false
		sampled_time = clampf(elapsed / duration, 0.0, 1.0) * length
	if _transition_polish_enabled:
		var attack := not String(snapshot.get("attack_id", "")).is_empty() and state == StringName(snapshot.attack_id)
		var startup := float(snapshot.get("attack_startup", 0.0)) if attack else 0.0
		if not is_finite(startup):
			last_error = "Attack startup must be finite"
			return false
		var blend_duration := minf(TRANSITION_SECONDS, maxf(0.0, startup-elapsed)) if attack else TRANSITION_SECONDS
		var restarted := not state in LOOP_STATES and sampled_time < previous_time-0.000001
		# Zero-delta changed samples are explicit audit/editor seeks. An unchanged
		# zero-delta snapshot retains its exact blend weight and gait phase.
		var exact_seek := delta <= 0.0 and (state_changed or absf(sampled_time-previous_time) > 0.000001 or charge_layer_changed or absf(_charge_layer_time-previous_charge_time) > 0.000001)
		if not _has_presented_pose or exact_seek or state in [&"hit", &"heavy_hit", &"dodge", &"parry", &"death"] or (attack and elapsed >= startup):
			_clear_transition()
		elif state_changed or restarted or charge_layer_changed:
			if blend_duration > 0.0:
				_capture_transition(blend_duration, charge_layer_changed and not state_changed and not restarted)
			else:
				_clear_transition()
	selected_state = state
	selected_clip = next_clip
	_charge_layer_active = charge_layer
	rig.rotation.y = _base_rig_yaw + visual_yaw
	_clip_node.animation = selected_clip
	animation_tree.set("parameters/Clock/seek_request", sampled_time)
	if _charge_clip_node != null:
		animation_tree.set("parameters/ChargeUpper/blend_amount", 1.0 if charge_layer else 0.0)
		animation_tree.set("parameters/ChargeClock/seek_request", _charge_layer_time)
	animation_tree.advance(0.0)
	# AnimationTree remains the only playback owner and has sampled the exact
	# gameplay target. This bounded visual blend changes no target clock, actor,
	# collision or hitbox. ActorVisual updates its hand socket after this pose.
	if _transition_polish_enabled:
		_blend_pose(delta, visual_yaw)
	_has_presented_pose = true
	last_error = ""
	return true
