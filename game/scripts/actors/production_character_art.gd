class_name ProductionCharacterArt
extends RefCounted

# Source GLBs stay immutable. Loop flags belong to isolated runtime copies of
# clips whose seam/pose review is recorded with the authored source candidate.
const HERO_STATES: Array[StringName] = [
	&"idle", &"walk", &"run", &"walk_back", &"walk_left", &"walk_right",
	&"dodge", &"light_1", &"light_2", &"light_3", &"parry", &"hit",
	&"heavy", &"charge", &"charged_heavy", &"skill_1", &"skill_2", &"skill_3", &"death", &"heal",
]
const SENTINEL_STATES: Array[StringName] = [
	&"idle", &"walk", &"run", &"walk_back", &"walk_left", &"walk_right", &"enemy_attack", &"hit", &"heavy_hit", &"death",
]
const CYCLES: Array[StringName] = [&"idle", &"walk", &"run", &"walk_back", &"walk_left", &"walk_right"]
const SEMANTIC_BONES := {
	"Root":"Root", "Hips":"Hips", "Spine":"Spine", "Chest":"Spine1", "UpperChest":"Spine2",
	"Neck":"Neck", "Head":"Head", "LeftShoulder":"LeftShoulder", "RightShoulder":"RightShoulder",
	"LeftUpperArm":"LeftArm", "RightUpperArm":"RightArm", "LeftLowerArm":"LeftForeArm", "RightLowerArm":"RightForeArm",
	"LeftHand":"LeftHand", "RightHand":"RightHand", "LeftUpperLeg":"LeftUpLeg", "RightUpperLeg":"RightUpLeg",
	"LeftLowerLeg":"LeftLeg", "RightLowerLeg":"RightLeg", "LeftFoot":"LeftFoot", "RightFoot":"RightFoot",
	"LeftToes":"LeftToeBase", "RightToes":"RightToeBase",
}
static var _prepared: Dictionary = {}

static func definition(profile: String) -> Dictionary:
	if profile == "hero":
		return {"path":"res://assets/models/production/lyra_fury_gameplay.glb", "states":HERO_STATES,
			"height":1.82, "grip_profile":"lyra", "walk_speed":6.4,
			"eye_path":"res://assets/models/production/lyra_eyes.glb"}
	if profile == "sentinel_melee":
		return {"path":"res://assets/models/production/sentinel_weight_gameplay.glb", "states":SENTINEL_STATES,
			"height":1.95, "grip_profile":"sentinel", "walk_speed":3.6}
	return {}

static func prepare(profile: String) -> Dictionary:
	if _prepared.has(profile):
		return _prepared[profile]
	var config := definition(profile)
	if config.is_empty():
		return {"ok":false, "reason":"Unknown character art profile: " + profile}
	if not ResourceLoader.exists(config.path, "PackedScene"):
		return {"ok":false, "reason":"Character art is not installed: " + profile}
	var source := load(config.path) as PackedScene
	if source == null or not source.can_instantiate():
		return {"ok":false, "reason":"Character art cannot be instantiated: " + profile}
	var eyes: PackedScene
	if config.has("eye_path"):
		if not ResourceLoader.exists(config.eye_path, "PackedScene"):
			return {"ok":false, "reason":"Character eye geometry is not installed: " + profile}
		eyes = load(config.eye_path) as PackedScene
		if eyes == null or not eyes.can_instantiate():
			return {"ok":false, "reason":"Character eye geometry cannot be instantiated: " + profile}
	var instance := source.instantiate() as Node3D
	if instance == null:
		return {"ok":false, "reason":"Character art root must be spatial: " + profile}
	var skeleton := find_type(instance, "Skeleton3D") as Skeleton3D
	var player := find_type(instance, "AnimationPlayer") as AnimationPlayer
	var reason := ""
	if skeleton == null or player == null:
		reason = "Character art requires a skeleton and animation player"
	else:
		for bone in SEMANTIC_BONES.values():
			if skeleton.find_bone(bone) < 0:
				reason = "Character art is missing semantic bone: " + String(bone)
				break
	var library := AnimationLibrary.new()
	if reason.is_empty():
		var states: Array[StringName] = config.states.duplicate()
		states.append(&"RESET")
		for state: StringName in states:
			if not player.has_animation(state):
				reason = "Character art is missing authored state: " + String(state)
				break
			var animation := player.get_animation(state).duplicate(true) as Animation
			animation.loop_mode = Animation.LOOP_LINEAR if state in CYCLES else Animation.LOOP_NONE
			library.add_animation(state, animation)
	if not reason.is_empty():
		instance.free()
		return {"ok":false, "reason":reason}
	for library_name in player.get_animation_library_list():
		player.remove_animation_library(library_name)
	player.add_animation_library(&"", library)
	player.autoplay = ""
	var map := BoneMap.new()
	map.profile = SkeletonProfileHumanoid.new()
	for semantic in SEMANTIC_BONES:
		if map.profile.find_bone(semantic) >= 0:
			map.set_skeleton_bone_name(semantic, SEMANTIC_BONES[semantic])
	var fingers := {"Thumb":["Metacarpal", "Proximal", "Distal"],
		"Index":["Proximal", "Intermediate", "Distal"], "Middle":["Proximal", "Intermediate", "Distal"],
		"Ring":["Proximal", "Intermediate", "Distal"], "Little":["Proximal", "Intermediate", "Distal"]}
	for side in ["Left", "Right"]:
		var digit := 0
		for finger in fingers:
			for joint in range(3):
				var semantic: String = String(side) + String(finger) + String(fingers[finger][joint])
				var actual: String = "HandLoRA_Bip01_%s_Finger%d%s" % ["L" if side == "Left" else "R", digit, "" if joint == 0 else str(joint)]
				if map.profile.find_bone(semantic) >= 0 and skeleton.find_bone(actual) >= 0:
					map.set_skeleton_bone_name(semantic, actual)
			digit += 1
	skeleton.set_meta("humanoid_bone_map", map)
	var packed := PackedScene.new()
	var packed_result := packed.pack(instance)
	instance.free()
	if packed_result != OK:
		return {"ok":false, "reason":"Character runtime scene could not be prepared"}
	var result := {"ok":true, "reason":"", "scene":packed, "states":config.states,
		"profile":profile, "bone_map":map, "config":config, "eyes":eyes}
	_prepared[profile] = result
	return result

static func find_type(node: Node, type: String) -> Node:
	if node.is_class(type):
		return node
	for child in node.get_children():
		var found := find_type(child, type)
		if found != null:
			return found
	return null
