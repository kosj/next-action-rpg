class_name SkeletalVisualBridge
extends Node3D

# AnimationTree owns playback; elapsed action time comes only from gameplay.
const REQUIRED_STATES: Array[StringName] = [&"idle", &"walk", &"run", &"dodge", &"light_1", &"light_2", &"light_3", &"parry", &"hit"]
const LOOP_STATES: Array[StringName] = [&"idle", &"walk", &"run"]
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
	rig.rotation.y += facing_correction # Humanoid +Z -> gameplay -Z, once in this wrapper.
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
	blend.connect_node(&"output", 0, &"Clock")
	animation_tree.tree_root = blend
	animation_tree.active = true
	last_error = ""
	return {"ok":true, "reason":"", "bones":skeleton.get_bone_count(), "states":clips.keys()}

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
	var speed: float = maxf(0.0, float(snapshot.get("speed", 0.0)))
	var state: StringName = &"idle"
	var elapsed: float = 0.0
	var duration: float = 0.0
	if snapshot.get("dead", false):
		state = &"death"
		elapsed = float(snapshot.get("death_elapsed", 0.0))
		duration = float(snapshot.get("death_duration", 0.0))
	elif float(snapshot.get("stagger", 0.0)) > 0.0:
		state = &"hit"
		elapsed = float(snapshot.get("hit_elapsed", 0.0))
		duration = float(snapshot.get("hit_duration", 0.15))
	elif float(snapshot.get("dodge_remaining", 0.0)) > 0.0:
		state = &"dodge"
		elapsed = float(snapshot.get("dodge_elapsed", 0.0))
		duration = float(snapshot.get("dodge_duration", 0.32))
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
	if not clips.has(state):
		last_error = "No authored clip for state: %s" % state
		return false # Caller shows the original visual instead of faking a clip.
	selected_state = state
	selected_clip = clips[state]
	var length := animation_player.get_animation(selected_clip).length
	if state in LOOP_STATES:
		var reference_speed := 8.5 if state == &"run" else 6.4
		locomotion_clock += maxf(delta, 0.0) * (1.0 if state == &"idle" else speed / reference_speed)
		sampled_time = fposmod(locomotion_clock, length)
	else:
		if state == &"death" and duration <= 0.0:
			duration = length
		if not is_finite(elapsed) or not is_finite(duration) or duration <= 0.0:
			last_error = "Action requires finite gameplay elapsed and duration: %s" % state
			return false
		sampled_time = clampf(elapsed / duration, 0.0, 1.0) * length
	_clip_node.animation = selected_clip
	animation_tree.set("parameters/Clock/seek_request", sampled_time)
	animation_tree.advance(0.0)
	last_error = ""
	return true
