class_name RuneCamera
extends Node3D

const BASE_FOV := 56.0
const FREE_DISTANCE := 4.5
const MAX_LOCK_DISTANCE := 8.6
const FOLLOW_HEIGHT := 2.4
const SHOULDER_OFFSET := 1.2
const IMPACT_DURATION := 0.22
const HERO_HEIGHT := 1.82
const COLLISION_FOCUS_HEIGHT := 0.9
const MAX_COLLISION_LIFT := 1.6
const COLLISION_LIFT_STEPS := 16
const COLLISION_FIT_BISECTIONS := 10
const CAMERA_TRANSPARENT_BARRIER_GROUP := &"camera_transparent_barriers"
const MAX_CAMERA_BARRIER_ALPHA := 0.25
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
var _camera_clearance_shape: SphereShape3D
var _collision_receipts: Array[Dictionary] = []
var _collision_fit_report: Dictionary = {"active":false,"obstructed":false,"fit":true,"lift_m":0.0,"candidate_queries":0}
var _follow_base_sync_queries := 0
var _camera_query_exclusions: Array[RID] = []
var _excluded_barriers: Array[Dictionary] = []

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
	impact_amplitude = 0.13 if strength == "charged" else 0.075

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
	_camera_clearance_shape = SphereShape3D.new()
	# Candidate endpoints retain a camera-near radius of clearance. This is a
	# camera query only; no actor, wall or gameplay collision shape is changed.
	_camera_clearance_shape.radius = camera.near

func _lock_target() -> RuneEnemy:
	if is_instance_valid(player) and is_instance_valid(player.locked_target) and not player.locked_target.dead:
		return player.locked_target
	return null

func _is_camera_transparent_barrier(body: StaticBody3D) -> bool:
	# Only the explicitly classified, currently 24%-alpha temporary energy
	# gates have this policy. An ordinary glass wall, opaque mistagged body or
	# unknown shader keeps camera collision authority. Gameplay never uses it.
	if not is_instance_valid(body) or not body.is_in_group(CAMERA_TRANSPARENT_BARRIER_GROUP):
		return false
	if body.get_world_3d()!=get_world_3d():
		return false
	var visual := body.get_parent() as MeshInstance3D
	if visual==null or visual.mesh==null or visual.mesh.get_surface_count()!=1:
		return false
	var material := visual.get_active_material(0) as StandardMaterial3D
	return material!=null and material.transparency==BaseMaterial3D.TRANSPARENCY_ALPHA and is_finite(material.albedo_color.a) and material.albedo_color.a>=0.0 and material.albedo_color.a<=MAX_CAMERA_BARRIER_ALPHA

func _refresh_camera_exclusions() -> void:
	_camera_query_exclusions.clear()
	_excluded_barriers.clear()
	for node: Node in get_tree().get_nodes_in_group(CAMERA_TRANSPARENT_BARRIER_GROUP):
		var body := node as StaticBody3D
		if _is_camera_transparent_barrier(body):
			_camera_query_exclusions.append(body.get_rid())
			_excluded_barriers.append({"collider_id":str(body.get_instance_id()),"collider_path":String(body.get_path())})

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
	# A higher view separates overlapping combatants and the contact plane.
	# FOV stays fixed; the closer follow balances hero size with the higher,
	# wider shoulder view. Confirmed attacks do not drive the follow distance.
	return Vector3(SHOULDER_OFFSET,FOLLOW_HEIGHT+sin(pitch)*distance,distance*cos(pitch)).rotated(Vector3.UP,yaw)

func _frame_subjects() -> Array[Dictionary]:
	var hero_scale := player.global_basis.get_scale().y*(player.visual.scale.y if is_instance_valid(player.visual) else 1.0)
	var subjects: Array[Dictionary] = [{"base":_hero_base(),"height":HERO_HEIGHT*hero_scale,"radius":0.38*hero_scale}]
	var target := _lock_target()
	if target != null:
		var scale_y := target.global_basis.get_scale().y*(target.visual.scale.y if is_instance_valid(target.visual) else 1.0)
		subjects.append({"base":target.global_position,"height":(3.4 if target.is_boss else 1.95)*scale_y,"radius":(0.78 if target.is_boss else 0.42)*scale_y})
	return subjects

func _fit_ratio(position: Vector3, focus: Vector3, subjects: Array[Dictionary], aspect: float, fov_degrees: float = BASE_FOV) -> float:
	var toward := focus-position
	if not toward.is_finite() or toward.length_squared()<0.00000001 or not is_finite(aspect) or aspect<=0.0:
		return 1000000.0
	var forward := toward.normalized()
	var right := forward.cross(Vector3.UP)
	if right.length_squared()<0.00000001:
		return 1000000.0
	right = right.normalized()
	var up := right.cross(forward).normalized()
	var tangent := tan(deg_to_rad(fov_degrees*0.5))
	if not is_finite(tangent) or tangent<=0.0:
		return 1000000.0
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

func _record_camera_collision(hit: Dictionary, stage: String, endpoint: Vector3 = Vector3.ZERO) -> void:
	var collider := hit.get("collider") as Object
	var path := ""
	if collider is Node and collider.is_inside_tree():
		path = String(collider.get_path())
	_collision_receipts.append({"stage":stage,"collider_id":str(collider.get_instance_id()) if is_instance_valid(collider) else "",
		"collider_path":path,"shape_index":int(hit.get("shape",-1)),
		"point":hit.get("position",endpoint),"normal":hit.get("normal",Vector3.ZERO)})

func _camera_candidate_clear(pivot: Vector3, position: Vector3, candidate: Vector3) -> bool:
	var space := get_world_3d().direct_space_state
	var ray := PhysicsRayQueryParameters3D.create(pivot,candidate,1)
	ray.exclude = _camera_query_exclusions
	_collision_fit_report.candidate_queries = int(_collision_fit_report.candidate_queries)+1
	var hit := space.intersect_ray(ray)
	if not hit.is_empty():
		_record_camera_collision(hit,"fit_ray")
		return false
	if candidate.distance_squared_to(position)>0.00000001:
		# A pivot ray can miss an overhang directly above the old camera. Test
		# both the actual lift segment and a near-radius swept volume; a clear
		# endpoint alone never permits moving through that overhang.
		var lift_ray := PhysicsRayQueryParameters3D.create(position,candidate,1)
		lift_ray.exclude = _camera_query_exclusions
		_collision_fit_report.candidate_queries = int(_collision_fit_report.candidate_queries)+1
		hit = space.intersect_ray(lift_ray)
		if not hit.is_empty():
			_record_camera_collision(hit,"fit_lift_ray")
			return false
		var sweep := PhysicsShapeQueryParameters3D.new()
		sweep.shape = _camera_clearance_shape
		sweep.transform = Transform3D(Basis.IDENTITY,position)
		sweep.motion = candidate-position
		sweep.collision_mask = 1
		sweep.exclude = _camera_query_exclusions
		_collision_fit_report.candidate_queries = int(_collision_fit_report.candidate_queries)+1
		var fractions := space.cast_motion(sweep)
		if fractions.size()!=2 or fractions[0]<0.99999:
			_collision_fit_report.lift_sweep_blocked = true
			return false
	var endpoint := PhysicsShapeQueryParameters3D.new()
	endpoint.shape = _camera_clearance_shape
	endpoint.transform = Transform3D(Basis.IDENTITY,candidate)
	endpoint.collision_mask = 1
	endpoint.exclude = _camera_query_exclusions
	_collision_fit_report.candidate_queries = int(_collision_fit_report.candidate_queries)+1
	var overlaps := space.intersect_shape(endpoint,1)
	if not overlaps.is_empty():
		_record_camera_collision(overlaps[0],"fit_endpoint",candidate)
		return false
	return true

func _repair_collision_framing(pivot: Vector3, position: Vector3, focus: Vector3, obstructed: bool) -> Dictionary:
	var was_active := bool(_collision_fit_report.get("active",false))
	_collision_fit_report = {"scope":"Bounded nominal hero framing after camera obstruction; not evaluated skin or terrain approval",
		"active":false,"obstructed":obstructed,"fit":true,"lift_m":0.0,"maximum_lift_m":MAX_COLLISION_LIFT,
		"candidate_queries":0,"endpoint_clearance_radius_m":camera.near,"reason":"unobstructed",
		"unadjusted_position":position,"presented_focus":focus}
	var result := {"position":position,"focus":focus,"lift_m":0.0}
	if not obstructed:
		return result
	var size := get_viewport().get_visible_rect().size
	if size.x<=0.0 or size.y<=0.0:
		_collision_fit_report.fit = false
		_collision_fit_report.reason = "invalid_viewport"
		return result
	var aspect := maxf(0.25,size.x/size.y)
	var hero_subjects: Array[Dictionary] = [_frame_subjects()[0]]
	var original_ratio := _fit_ratio(position,focus,hero_subjects,aspect,camera.fov)
	_collision_fit_report.original_fit_ratio = original_ratio
	if original_ratio<=1.00001 and not was_active:
		_collision_fit_report.reason = "obstructed_hero_already_fits"
		return result
	# A short collision boom cannot safely use a lagging free/lock focus. Keep
	# input yaw and orbit pitch intact; only the emergency look point follows
	# the current hero. Continue it until the obstruction clears to avoid a
	# frame-by-frame switch back to the distant lock point.
	var hero_focus := _hero_base()+Vector3.UP*COLLISION_FOCUS_HEIGHT
	var fresh_ratio := _fit_ratio(position,hero_focus,hero_subjects,aspect,camera.fov)
	var required_lift := 0.0
	var found_fit := fresh_ratio<=1.00001
	var lower := 0.0
	if not found_fit:
		# These bounded evaluations are projection math, not physics queries.
		# Locate the first fitting height, then refine within that small bracket.
		for index in range(1,COLLISION_LIFT_STEPS+1):
			var upper := MAX_COLLISION_LIFT*float(index)/COLLISION_LIFT_STEPS
			if _fit_ratio(position+Vector3.UP*upper,hero_focus,hero_subjects,aspect,camera.fov)<=1.00001:
				for iteration in range(COLLISION_FIT_BISECTIONS):
					var middle := (lower+upper)*0.5
					if _fit_ratio(position+Vector3.UP*middle,hero_focus,hero_subjects,aspect,camera.fov)<=1.00001:
						upper = middle
					else:
						lower = middle
				found_fit = true
				required_lift = upper
				break
			lower = upper
	var candidate := position+Vector3.UP*required_lift
	_collision_fit_report.required_lift_m = required_lift
	_collision_fit_report.candidate_position = candidate
	if found_fit and _camera_candidate_clear(pivot,position,candidate):
		result = {"position":candidate,"focus":hero_focus,"lift_m":required_lift}
		_collision_fit_report.active = true
		_collision_fit_report.lift_m = required_lift
		_collision_fit_report.reason = "hero_fit_restored"
		_collision_fit_report.final_fit_ratio = _fit_ratio(candidate,hero_focus,hero_subjects,aspect,camera.fov)
		_collision_fit_report.presented_focus = hero_focus
		_look_position = hero_focus
		_look_initialized = true
		return result
	# A low ceiling or another wall has authority over framing. Do not jump
	# through it to reach a higher solution. A safer look direction may still
	# reduce the crop without changing the already resolved camera position.
	_collision_fit_report.fit = false
	_collision_fit_report.reason = "no_clear_bounded_fit" if found_fit else "lift_bound_cannot_fit"
	_collision_fit_report.final_fit_ratio = minf(original_ratio,fresh_ratio)
	if fresh_ratio<original_ratio:
		result.focus = hero_focus
		_collision_fit_report.active = true
		_collision_fit_report.presented_focus = hero_focus
		_look_position = hero_focus
		_look_initialized = true
	return result

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
		"follow_height_bias":FOLLOW_HEIGHT,"shoulder_offset":SHOULDER_OFFSET,
		"maximum_lock_distance":MAX_LOCK_DISTANCE,"locked":_lock_target()!=null,
		"viewport":[size.x,size.y],"subjects":bounds,
		"collision_fit":_collision_fit_report.duplicate(true),"collision_receipts":_collision_receipts.duplicate(true),
		"follow_base_sync_queries":_follow_base_sync_queries,
		"camera_transparent_barriers":_excluded_barriers.duplicate(true),"camera_barrier_maximum_alpha":MAX_CAMERA_BARRIER_ALPHA}
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
	_collision_receipts.clear()
	_follow_base_sync_queries = 0
	var target := _hero_base()+Vector3.UP*1.4
	if cinematic:
		var offset := Vector3(8.0 + sin(time * 0.07) * 1.0, 4.2, 9.0)
		camera.global_position = target + offset
		camera.look_at(target + Vector3(1, 0.2, -2))
		camera.fov = BASE_FOV
		_follow_initialized = false
		_look_initialized = false
		return
	_refresh_camera_exclusions()
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
	query.exclude = _camera_query_exclusions
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	var obstructed := not hit.is_empty()
	if not hit.is_empty():
		_record_camera_collision(hit,"follow")
		desired = hit.position + hit.normal * 0.3
	if not _follow_initialized:
		_follow_position = desired
		_follow_initialized = true
	_follow_position = _follow_position.lerp(desired, 1.0 - exp(-delta * 12.0))
	camera.global_position = _follow_position
	shake_strength = maxf(0.0, shake_strength - delta * 1.6)
	camera.fov = BASE_FOV
	if Session.shake and impact_age<IMPACT_DURATION:
		# A short, directional attack followed by a smooth release gives the
		# confirmed cut a distinct punctuation without extending random shake.
		var release := 1.0-clampf(impact_age/IMPACT_DURATION,0.0,1.0)
		var envelope := smoothstep(0.0,0.025,impact_age)*release*release*release
		camera.global_position += (impact_direction+Vector3.UP*0.2)*impact_amplitude*envelope
		camera.fov -= impact_amplitude * 34.0 * envelope
	if Session.shake and shake_strength > 0:
		camera.global_position += Vector3(_noise_rng.randf_range(-1,1),_noise_rng.randf_range(-1,1),0)*shake_strength*0.045
	# Recheck the final kicked position, so feedback cannot push the camera through a wall.
	var feedback_delta := camera.global_position-_follow_position
	query.to = camera.global_position
	hit = get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		obstructed = true
		_record_camera_collision(hit,"post_feedback")
		camera.global_position = hit.position + hit.normal * 0.3
		# Synchronize the latent follow base to the resolved side of this wall.
		# Leaving it outside would shorten every later lifted pose again, even
		# at zero delta. Remove feedback first so a contact kick is not integrated
		# into following, and retain the same normal clearance for that base.
		var resolved_base := camera.global_position-feedback_delta
		var plane_distance: float = hit.normal.dot(resolved_base-hit.position)
		resolved_base += hit.normal*maxf(0.0,0.3-plane_distance)
		if feedback_delta.length_squared()>0.00000001:
			# Subtracting a lateral kick can move the base toward an adjacent
			# corner wall. Reuse the real layer-1 authority for that candidate;
			# this single extra ray is absent when feedback is zero/unobstructed.
			var base_query := PhysicsRayQueryParameters3D.create(target,resolved_base,1)
			base_query.exclude = _camera_query_exclusions
			_follow_base_sync_queries = 1
			var base_hit := get_world_3d().direct_space_state.intersect_ray(base_query)
			if not base_hit.is_empty():
				_record_camera_collision(base_hit,"follow_base")
				resolved_base = base_hit.position+base_hit.normal*0.3
		_follow_position = resolved_base
	var repaired := _repair_collision_framing(target,camera.global_position,look_at_point,obstructed)
	camera.global_position = repaired.position
	look_at_point = repaired.focus
	# Add only the newly required vertical correction. Copying the final kicked
	# camera into the follow base would accumulate attack feedback every frame.
	_follow_position += Vector3.UP*float(repaired.lift_m)
	if camera.global_position.distance_to(look_at_point) > 0.1:
		camera.look_at(look_at_point)

func snap() -> void:
	if not is_instance_valid(player):
		return
	_collision_receipts.clear()
	_follow_base_sync_queries = 0
	_refresh_camera_exclusions()
	camera.fov = BASE_FOV
	var target := _hero_base()+Vector3.UP*1.4
	var focus := _focus_point()
	_look_position = focus
	_look_initialized = true
	_wanted_distance = _required_distance(target,focus)
	_framing_distance = _wanted_distance
	camera.global_position = target+_offset(_framing_distance)
	var query := PhysicsRayQueryParameters3D.create(target,camera.global_position,1)
	query.exclude = _camera_query_exclusions
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		_record_camera_collision(hit,"snap")
		camera.global_position = hit.position+hit.normal*0.3
	var repaired := _repair_collision_framing(target,camera.global_position,focus,not hit.is_empty())
	camera.global_position = repaired.position
	focus = repaired.focus
	if camera.global_position.distance_to(focus)>0.1:
		camera.look_at(focus)
	_follow_position = camera.global_position
	_follow_initialized = true
	impact_age = 1.0
	impact_amplitude = 0.0
	shake_strength = 0.0
	_last_impact_accepted = false
	camera.fov = BASE_FOV
