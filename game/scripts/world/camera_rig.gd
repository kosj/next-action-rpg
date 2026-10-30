class_name RuneCamera
extends Node3D

var camera: Camera3D
var player: RunePlayer
var yaw: float = 0.0
var pitch: float = -0.18
var shake_strength: float = 0.0
var cinematic: bool = true
var time: float = 0.0

func _ready() -> void:
	camera = Camera3D.new()
	camera.fov = 56
	camera.near = 0.15
	camera.far = 180
	add_child(camera)
	camera.current = true

func _unhandled_input(event: InputEvent) -> void:
	if not cinematic and event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * 0.0025
		pitch = clampf(pitch - event.relative.y * 0.002, -0.65, 0.6)

func _physics_process(delta: float) -> void:
	time += delta
	if not is_instance_valid(player):
		return
	var target := player.global_position + Vector3.UP * 1.4
	if cinematic:
		var offset := Vector3(8.0 + sin(time * 0.07) * 1.0, 4.2, 9.0)
		camera.global_position = target + offset
		camera.look_at(target + Vector3(1, 0.2, -2))
		return
	var look_axes := Vector2(Input.get_joy_axis(0, JOY_AXIS_RIGHT_X), Input.get_joy_axis(0, JOY_AXIS_RIGHT_Y))
	if look_axes.length() > 0.18:
		yaw -= look_axes.x * delta * 2.3
		pitch = clampf(pitch - look_axes.y * delta * 1.7, -0.65, 0.6)
	var look_at_point := target + Vector3.UP * 0.2
	if is_instance_valid(player.locked_target) and not player.locked_target.dead:
		var toward := player.locked_target.global_position - player.global_position
		yaw = lerp_angle(yaw, atan2(-toward.x, -toward.z), minf(1, delta * 3.0))
		look_at_point = target.lerp(player.locked_target.global_position + Vector3.UP * 1.6, 0.25)
	player.camera_yaw = yaw
	var offset := Vector3(0.65, 2.1 + sin(pitch) * 6.0, 6.7 * cos(pitch)).rotated(Vector3.UP, yaw)
	var desired := target + offset
	var query := PhysicsRayQueryParameters3D.create(target, desired, 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		desired = hit.position + hit.normal * 0.3
	camera.global_position = camera.global_position.lerp(desired, 1.0 - exp(-delta * 12.0))
	shake_strength = maxf(0.0, shake_strength - delta * 1.6)
	if Session.shake and shake_strength > 0:
		camera.global_position += Vector3(randf_range(-1, 1), randf_range(-1, 1), 0) * shake_strength * 0.1
	if camera.global_position.distance_to(look_at_point) > 0.1:
		camera.look_at(look_at_point)

func snap() -> void:
	camera.global_position = player.global_position + Vector3(0.65, 3.4, 6.7).rotated(Vector3.UP, yaw)
