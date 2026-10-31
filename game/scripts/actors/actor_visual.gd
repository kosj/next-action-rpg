class_name ActorVisual
extends Node3D

const RUNE_SWORD_SCENE: PackedScene = preload("res://assets/models/production/rune_sword_web.glb")

var model: Node3D
var joints: Dictionary = {}
var clock: float = 0.0
var base_scale: Vector3 = Vector3.ONE
var skeletal_bridge: SkeletalVisualBridge
var rig_status: String = "Prototype pivot visual"

func mount_rig(scene: PackedScene, aliases: Dictionary = {}, required_states: Array[StringName] = SkeletalVisualBridge.REQUIRED_STATES, facing_correction: float = PI) -> Dictionary:
	var candidate := SkeletalVisualBridge.new()
	add_child(candidate)
	var result := candidate.mount_scene(scene, aliases, required_states, facing_correction)
	if not result.ok:
		rig_status = result.reason
		candidate.free()
		return result
	clear_rig()
	skeletal_bridge = candidate
	rig_status = "Rig ready; visual quality remains subject to art review"
	return result

func clear_rig() -> void:
	if is_instance_valid(skeletal_bridge):
		skeletal_bridge.free()
	skeletal_bridge = null
	if is_instance_valid(model):
		model.show()
	rig_status = "Prototype pivot visual"

func setup(kind: String) -> void:
	model = load("res://assets/models/%s.glb" % kind).instantiate()
	# Blender faces -Y, which glTF maps to +Z. Face Godot forward (-Z).
	model.rotation.y = PI
	add_child(model)
	_collect(model)
	if kind == "hero":
		_replace_hero_sword()

func _replace_hero_sword() -> void:
	var socket := joints.get("Sword") as Node3D
	if socket == null:
		return
	# Keep the existing grip transform and pivot animation. The replacement lives
	# inside the prototype model so rig visibility and fallback include its weapon.
	for child in socket.get_children():
		if child is MeshInstance3D:
			child.hide()
	var replacement := RUNE_SWORD_SCENE.instantiate() as Node3D
	replacement.name = "RuneSwordPreview"
	# Canonical blade +Y -> prototype blade -Y; keep its broad face normal +Z.
	replacement.rotation.z = PI
	socket.add_child(replacement)

func _collect(node: Node) -> void:
	if node is Node3D:
		joints[String(node.name)] = node
	for child in node.get_children():
		_collect(child)

func pose(delta: float, speed: float, swing: float = -1.0, dodge: bool = false, parry: bool = false, dead: bool = false, snapshot: Dictionary = {}) -> void:
	if is_instance_valid(skeletal_bridge):
		var presented := skeletal_bridge.present(delta, snapshot if not snapshot.is_empty() else {"speed":speed, "dead":dead})
		skeletal_bridge.visible = presented
		if is_instance_valid(model):
			model.visible = not presented
		if presented:
			position.y = 0.0
			rotation.z = 0.0
			return
		rig_status = skeletal_bridge.last_error
	clock += delta * (5.0 + speed * 1.8)
	var stride := minf(speed / 6.0, 1.0)
	_set_joint("LegL", Vector3(sin(clock) * 0.65 * stride, 0, 0))
	_set_joint("LegR", Vector3(-sin(clock) * 0.65 * stride, 0, 0))
	_set_joint("KneeL", Vector3(-maxf(0, -sin(clock)) * 0.7 * stride, 0, 0))
	_set_joint("KneeR", Vector3(-maxf(0, sin(clock)) * 0.7 * stride, 0, 0))
	_set_joint("ArmL", Vector3(-sin(clock) * 0.45 * stride, 0, -0.12))
	_set_joint("ArmR", Vector3(sin(clock) * 0.35 * stride - 0.2, 0, 0.15))
	_set_joint("ElbowR", Vector3(0.15, 0, 0))
	_set_joint("Torso", Vector3(0.07 * stride, 0, 0))
	if swing >= 0.0:
		var motion := sin(swing * PI)
		_set_joint("ArmR", Vector3(-1.1 - motion * 0.6, -1.5 + swing * 3.5, 0.7))
		_set_joint("ElbowR", Vector3(-0.45, 0, 0))
		_set_joint("Torso", Vector3(0.08, -0.55 + swing * 1.1, 0))
		_set_joint("ArmL", Vector3(-0.4, 0, -0.4))
	if parry:
		_set_joint("ArmR", Vector3(-1.35, -0.5, 0.65))
		_set_joint("ArmL", Vector3(-0.9, 0, -0.25))
	if dodge:
		_set_joint("Torso", Vector3(0.5, 0, 0))
	position.y = absf(sin(clock)) * 0.04 * stride
	rotation.z = lerp_angle(rotation.z, -1.45 if dead else 0.0, minf(1.0, delta * 6.0))

func _set_joint(joint: String, angles: Vector3) -> void:
	if joints.has(joint):
		joints[joint].rotation = angles
