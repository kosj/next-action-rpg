class_name RuneCamera
extends Node3D

const BASE_FOV := 56.0
const FREE_DISTANCE := 5.2
const MAX_LOCK_DISTANCE := 8.6
const IMPACT_DURATION := 0.19
const HERO_HEIGHT := 1.82
var camera: Camera3D
var player: RunePlayer
var yaw: float = 0.0
var pitch: float = -0.18
var shake_strength: float = 0.0
var cinematic: bool = true
var time: float = 0.0
var impact_age: float = 1.0
var impact_direction: Vector3 = Vector3.ZERO
var impact_amplitude: float = 0.0
var _follow_position: Vector3
var _follow_initialized: bool = false
var _framing_distance := FREE_DISTANCE
var _wanted_distance := FREE_DISTANCE
var _look_position := Vector3.ZERO
var _look_initialized := false
var _noise_rng := RandomNumberGenerator.new()
var _last_impact_accepted := false

func apply_impact(context: Dictionary) -> void:
	# Guard the presentation API too: an attack-start/whiff packet cannot kick
	# the camera even if a caller accidentally routes it here.
	_last_impact_accepted = false
	if String(context.get("attack_id", "")).is_empty() or not String(context.get("contact_source", "")) in ["hurtbox_ray","hurtbox_proxy"]:
		return
	for key: String in ["point","normal","direction"]:
		var value: Variant = context.get(key)
		if not value is Vector3 or not value.is_finite():
			return
	var strength := String(context.get("strength", "light"))
	if not strength in ["light","heavy","charged","skill"]:
		return
	_last_impact_accepted = true
	var blocked := bool(context.get("blocked", false))
	shake_strength = maxf(shake_strength,0.16 if blocked else (0.28 if strength=="charged" else 0.20))
	if strength not in ["heavy", "charged"] or blocked:
		return
	impact_age = 0.0
	impact_direction = context.get("direction", Vector3.FORWARD)
	impact_direction.y = 0.0
	impact_direction = impact_direction.normalized()
	var motion: Variant = context.get("contact_blade_motion")
	if motion is Vector3 and motion.is_finite() and motion.length_squared()>0.000001:
		# Follow the accepted cut's direction, never an authored ground-slam kick.
		impact_direction = (impact_direction*0.65+motion.normalized()*0.35).normalized()
	impact_amplitude = 0.085 if strength == "charged" else 0.055

func impact_report() -> Dictionary:
	return {"age":impact_age,"amplitude":impact_amplitude,"duration":IMPACT_DURATION,
		"fov":camera.fov,"enabled":Session.shake,"last_context_accepted":_last_impact_accepted,
		"framing":framing_report()}

func _ready() -> void:
	camera = Camera3D.new()
	camera.keep_aspect = Camera3D.KEEP_HEIGHT
	camera.fov = BASE_FOV
	camera.near = 0.15
	camera.far = 180
	add_child(camera)
	camera.current = true
	_noise_rng.seed = 73020

func _lock_target() -> RuneEnemy:
	if is_instance_valid(player) and is_instance_valid(player.locked_target) and not player.locked_target.dead:
		return player.locked_target
	return null

func _hero_base() -> Vector3:
	var point := player.global_position
	if is_instance_valid(player.visual):
		point += player.global_basis.y*player.visual.ground_offset_y
	return point

func _focus_point() -> Vector3:
	var point := _hero_base()+Vector3.UP*1.35
	var target := _lock_target()
	if target != null:
		point = point.lerp(target.global_position+Vector3.UP*(2.15 if target.is_boss else 1.35),0.45)
	return point

func _offset(distance: float) -> Vector3:
	return Vector3(0.55,1.6+sin(pitch)*distance,distance*cos(pitch)).rotated(Vector3.UP,yaw)

func _frame_subjects() -> Array[Dictionary]:
	var hero_scale := player.global_basis.get_scale().y*(player.visual.scale.y if is_instance_valid(player.visual) else 1.0)
	var subjects: Array[Dictionary] = [{"base":_hero_base(),"height":HERO_HEIGHT*hero_scale,"radius":0.38*hero_scale}]
	var target := _lock_target()
	if target != null:
		var scale_y := target.global_basis.get_scale().y*(target.visual.scale.y if is_instance_valid(target.visual) else 1.0)
		subjects.append({"base":target.global_position,"height":(3.4 if target.is_boss else 1.95)*scale_y,"radius":(0.78 if target.is_boss else 0.42)*scale_y})
	return subjects

func _fit_ratio(position: Vector3, focus: Vector3, subjects: Array[Dictionary], aspect: float) -> float:
	var forward := (focus-position).normalized()
	var right := forward.cross(Vector3.UP).normalized()
	var up := right.cross(forward).normalized()
	var tangent := tan(deg_to_rad(BASE_FOV*0.5))
	var ratio := 1.0
	for subject in subjects:
		var base: Vector3 = subject.base
		var middle := base+Vector3.UP*float(subject.height)*0.5
		for point: Vector3 in [base,base+Vector3.UP*float(subject.height),middle-right*float(subject.radius),middle+right*float(subject.radius)]:
			var relative := point-position
			var depth := relative.dot(forward)
			if depth<=0.1:
				return 1.35
			var x := relative.dot(right)/(depth*tangent*aspect)
			var y := relative.dot(up)/(depth*tangent)
			# Keep nominal feet above the lower20% occupied by portrait actions.
			ratio = maxf(ratio,maxf(absf(x)/0.84,maxf(y/0.86,-y/0.60)))
	return ratio

func _required_distance(target: Vector3, focus: Vector3) -> float:
	var locked := _lock_target()
	if locked == null:
		return FREE_DISTANCE
	var size := get_viewport().get_visible_rect().size
	var aspect := maxf(0.25,size.x/maxf(size.y,1.0))
	var distance := FREE_DISTANCE+clampf((player.global_position.distance_to(locked.global_position)-2.5)*0.16,0.0,2.0)
	var subjects := _frame_subjects()
	for index in range(4):
		var ratio := _fit_ratio(target+_offset(distance),focus,subjects,aspect)
		if ratio<=1.001:
			break
		distance = minf(MAX_LOCK_DISTANCE,distance*minf(ratio,1.3))
	return distance

func framing_report() -> Dictionary:
	if not is_instance_valid(player) or not is_instance_valid(camera):
		return {}
	var size := get_viewport().get_visible_rect().size
	if size.x<=0.0 or size.y<=0.0:
		return {}
	var bounds: Array[Dictionary] = []
	for subject in _frame_subjects():
		var foot: Vector3 = subject.base
		var head := foot+Vector3.UP*float(subject.height)
		var foot_pixel := camera.unproject_position(foot)
		var head_pixel := camera.unproject_position(head)
		bounds.append({"nominal_foot_uv":[foot_pixel.x/size.x,foot_pixel.y/size.y],
			"nominal_head_uv":[head_pixel.x/size.x,head_pixel.y/size.y],
			"height_fraction":absf(foot_pixel.y-head_pixel.y)/size.y,
			"behind_camera":camera.is_position_behind(foot) or camera.is_position_behind(head)})
	var result := {"scope":"Nominal production body/root projection, not evaluated mesh or UI collision approval",
		"free_distance":FREE_DISTANCE,"follow_distance":_framing_distance,"wanted_distance":_wanted_distance,
		"maximum_lock_distance":MAX_LOCK_DISTANCE,"locked":_lock_target()!=null,
		"viewport":[size.x,size.y],"subjects":bounds}
	if is_instance_valid(player.visual) and is_instance_valid(player.visual.rig_weapon):
		for name: String in ["GripOrigin","BladeTip"]:
			var marker := player.visual.rig_weapon.find_child(name,true,false) as Node3D
			if marker != null:
				var pixel := camera.unproject_position(marker.global_position)
				result["actual_"+name+"_uv"] = [pixel.x/size.x,pixel.y/size.y]
	return result

func _unhandled_input(event: InputEvent) -> void:
	if not cinematic and event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * 0.0025
		pitch = clampf(pitch - event.relative.y * 0.002, -0.65, 0.6)

func _physics_process(delta: float) -> void:
	if not is_finite(delta) or delta<0.0:
		return
	time += delta
	impact_age += delta
	if not is_instance_valid(player):
		return
	var target := _hero_base()+Vector3.UP*1.4
	if cinematic:
		var offset := Vector3(8.0 + sin(time * 0.07) * 1.0, 4.2, 9.0)
		camera.global_position = target + offset
		camera.look_at(target + Vector3(1, 0.2, -2))
		camera.fov = BASE_FOV
		_follow_initialized = false
		_look_initialized = false
		return
	var touch_look := TouchControls.take_look_delta()
	yaw -= touch_look.x * 0.004
	pitch = clampf(pitch - touch_look.y * 0.004, -0.65, 0.6)
	var look_axes := Vector2(Input.get_joy_axis(0, JOY_AXIS_RIGHT_X), Input.get_joy_axis(0, JOY_AXIS_RIGHT_Y))
	if look_axes.length() > 0.18:
		yaw -= look_axes.x * delta * 2.3
		pitch = clampf(pitch - look_axes.y * delta * 1.7, -0.65, 0.6)
	var wanted_focus := _focus_point()
	if not _look_initialized:
		_look_position = wanted_focus
		_look_initialized = true
	_look_position = _look_position.lerp(wanted_focus,1.0-exp(-delta*10.0))
	var look_at_point := _look_position
	if is_instance_valid(player.locked_target) and not player.locked_target.dead:
		var toward := player.locked_target.global_position - player.global_position
		yaw = lerp_angle(yaw, atan2(-toward.x, -toward.z), minf(1, delta * 3.0))
	player.camera_yaw = yaw
	_wanted_distance = _required_distance(target,look_at_point)
	# This is a bounded lock-on dolly, not an attack-driven FOV zoom. Its speed
	# is limited so acquiring/releasing a far target cannot pop the composition.
	_framing_distance = move_toward(_framing_distance,_wanted_distance,delta*2.8)
	var offset := _offset(_framing_distance)
	var desired := target + offset
	var query := PhysicsRayQueryParameters3D.create(target, desired, 1)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		desired = hit.position + hit.normal * 0.3
	if not _follow_initialized:
		_follow_position = desired
		_follow_initialized = true
	_follow_position = _follow_position.lerp(desired, 1.0 - exp(-delta * 12.0))
	camera.global_position = _follow_position
	shake_strength = maxf(0.0, shake_strength - delta * 1.6)
	camera.fov = BASE_FOV
	if Session.shake and impact_age<IMPACT_DURATION:
		var envelope := sin(PI*impact_age/IMPACT_DURATION)*exp(-impact_age*12.0)
		camera.global_position += (impact_direction+Vector3.UP*0.2)*impact_amplitude*envelope
		camera.fov -= impact_amplitude * 34.0 * envelope
	if Session.shake and shake_strength > 0:
		camera.global_position += Vector3(_noise_rng.randf_range(-1,1),_noise_rng.randf_range(-1,1),0)*shake_strength*0.045
	# Recheck the final kicked position, so feedback cannot push the camera through a wall.
	query.to = camera.global_position
	hit = get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		camera.global_position = hit.position + hit.normal * 0.3
	if camera.global_position.distance_to(look_at_point) > 0.1:
		camera.look_at(look_at_point)

func snap() -> void:
	if not is_instance_valid(player):
		return
	var target := _hero_base()+Vector3.UP*1.4
	var focus := _focus_point()
	_look_position = focus
	_look_initialized = true
	_wanted_distance = _required_distance(target,focus)
	_framing_distance = _wanted_distance
	camera.global_position = target+_offset(_framing_distance)
	var query := PhysicsRayQueryParameters3D.create(target,camera.global_position,1)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		camera.global_position = hit.position+hit.normal*0.3
	if camera.global_position.distance_to(focus)>0.1:
		camera.look_at(focus)
	_follow_position = camera.global_position
	_follow_initialized = true
	impact_age = 1.0
	impact_amplitude = 0.0
	shake_strength = 0.0
	_last_impact_accepted = false
	camera.fov = BASE_FOV
