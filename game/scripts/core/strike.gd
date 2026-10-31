class_name CombatStrike
extends RefCounted

# A new ledger for each swing. Blade volumes cover the arc between physics ticks.
const MAX_SAFE_ATTACK_SERIAL: int = 9007199254740991
static var _next_attack_serial: int = 0
var attack_instance_id: int = 0
var data: AttackData
var source: CharacterBody3D
var elapsed: float = 0.0
var hit_ids: Dictionary = {}
var previous_origin: Vector3
var started: bool = false
var multiplier: float = 1.0
var presentation_id: StringName

func _init(actor: CharacterBody3D, attack: AttackData, power: float = 1.0, visual_id: StringName = &"") -> void:
	# RefCounted ObjectIDs carry an engine ownership bit and are not suitable
	# positive/JS-safe event keys. This runtime sequence identifies each swing.
	_next_attack_serial = (_next_attack_serial % MAX_SAFE_ATTACK_SERIAL) + 1
	attack_instance_id = _next_attack_serial
	source = actor
	data = attack
	multiplier = power
	presentation_id = visual_id if not visual_id.is_empty() else StringName(attack.resource_path.get_file().get_basename())
	if presentation_id.is_empty():
		presentation_id = &"unmapped_attack"
	previous_origin = actor.global_position

func register_target(id: int) -> bool:
	if hit_ids.has(id):
		return false
	hit_ids[id] = true
	return true

func step(delta: float, forward: Vector3, mask: int) -> void:
	var old_time := elapsed
	elapsed += delta
	var old_origin := previous_origin
	previous_origin = source.global_position
	if elapsed < data.startup or old_time >= data.startup + data.active:
		return
	if delta <= 0.0 or data.active <= 0.0:
		return
	started = true
	if data.physical_blade_sweep:
		_step_physical_blade(old_time, delta, old_origin, forward, mask)
		return
	var first_fraction := clampf((old_time - data.startup) / data.active, 0.0, 1.0)
	var last_fraction := clampf((elapsed - data.startup) / data.active, 0.0, 1.0)
	var start_origin := old_origin.lerp(source.global_position, clampf((data.startup-old_time) / delta, 0.0, 1.0))
	var end_origin := old_origin.lerp(source.global_position, clampf((data.startup+data.active-old_time) / delta, 0.0, 1.0))
	var first_angle := deg_to_rad(lerpf(-data.arc * 0.5, data.arc * 0.5, data.normalized_sweep_progress(first_fraction)))
	var last_angle := deg_to_rad(lerpf(-data.arc * 0.5, data.arc * 0.5, data.normalized_sweep_progress(last_fraction)))
	var radial_attack := data.arc >= 359.0
	var shape: Shape3D
	if radial_attack:
		var disk := CylinderShape3D.new()
		disk.radius = data.reach
		disk.height = 2.2
		shape = disk
	else:
		# Sweep the whole blade, not only its tip. Angular subdivision follows the
		# actual arc even when one physics step spans the entire active window.
		var blade := CapsuleShape3D.new()
		blade.radius = minf(0.65, data.reach * 0.5)
		blade.height = data.reach
		shape = blade
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = shape
	query.collision_mask = mask
	query.exclude = [source.get_rid()]
	var movement := start_origin.distance_to(end_origin)
	var arc_length := 0.0 if radial_attack else absf(last_angle - first_angle) * data.reach
	var samples := maxi(1, ceili((movement + arc_length) / 0.35))
	for sample in range(samples + 1):
		var fraction := float(sample) / samples
		var origin := start_origin.lerp(end_origin, fraction) + Vector3.UP * 1.1
		var direction := forward.normalized().rotated(Vector3.UP, lerpf(first_angle, last_angle, fraction))
		if radial_attack:
			query.transform = Transform3D(Basis.IDENTITY, origin)
		else:
			query.transform = Transform3D(Basis(Vector3.UP, direction, Vector3.UP.cross(direction)), origin + direction * data.reach * 0.5)
		_confirm_overlaps(query, forward)

func _step_physical_blade(old_time: float, delta: float, old_origin: Vector3, forward: Vector3, mask: int) -> void:
	var first_time := maxf(old_time, data.startup)
	var last_time := minf(elapsed, data.startup + data.active)
	var first := clampf((first_time-data.startup)/data.active, 0.0, 1.0)
	var last := clampf((last_time-data.startup)/data.active, 0.0, 1.0)
	# Bound angular and grip travel at the maximum derivative of smooth(f*f)
	# (2.231); sample spacing remains below the capsule radius, even for a tick
	# that crosses the entire active window. No expanded reach proxy is used.
	var scale_m := source.global_basis.get_scale().abs()
	var max_scale := maxf(scale_m.x, maxf(scale_m.y, scale_m.z))
	var distance_bound := (deg_to_rad(data.arc + absf(data.blade_pitch_end-data.blade_pitch_start))*data.blade_length + data.blade_grip_start.distance_to(data.blade_grip_end))*2.24*(last-first)*max_scale
	distance_bound += old_origin.distance_to(source.global_position)
	var samples := maxi(1, ceili(distance_bound / maxf(0.025, data.blade_radius*0.75)))
	var yaw := atan2(-forward.x, -forward.z)
	var query := PhysicsShapeQueryParameters3D.new()
	query.collision_mask = mask
	query.exclude = [source.get_rid()]
	var blade := CapsuleShape3D.new()
	blade.radius = data.blade_radius * max_scale
	query.shape = blade
	for index in range(samples+1):
		var fraction := float(index)/samples
		var time := lerpf(first_time,last_time,fraction)
		var origin := old_origin.lerp(source.global_position,clampf((time-old_time)/delta,0.0,1.0))
		var points := data.blade_points(lerpf(first,last,fraction))
		var grip := origin + (points[0]*scale_m).rotated(Vector3.UP,yaw)
		var tip := origin + (points[1]*scale_m).rotated(Vector3.UP,yaw)
		var axis := tip-grip
		var direction := axis.normalized()
		var damage_base := grip.lerp(tip,clampf(data.blade_damage_start_fraction,0.0,1.0))
		# Godot capsule height includes both hemispheres. Its outer ends stay
		# inside the authored damage segment; the hilt is not a lethal blunt end.
		blade.height = maxf(damage_base.distance_to(tip),blade.radius*2.0)
		query.transform = Transform3D(Basis(Quaternion(Vector3.UP,direction)),(damage_base+tip)*0.5)
		var damage_axis_base := damage_base+direction*blade.radius
		var damage_axis_tip := tip-direction*blade.radius
		if _confirm_overlaps(query,forward,[grip,tip],lerpf(first,last,fraction),time,[damage_base,tip,damage_axis_base,damage_axis_tip]):
			# Freeze at the first accepted geometric sample. Other targets in this
			# same query share that instant; future arc samples resume after stop.
			return

func _confirm_overlaps(query: PhysicsShapeQueryParameters3D, forward: Vector3, blade_points_world: Array[Vector3] = [], contact_phase: float = -1.0, contact_time: float = -1.0, damage_segment_world: Array[Vector3] = []) -> bool:
	var confirmed := false
	for result in source.get_world_3d().direct_space_state.intersect_shape(query, 16):
		var target: Object = result.collider
		if not target.has_method("receive_hit") or hit_ids.has(target.get_instance_id()):
			continue
		var wall_query := PhysicsRayQueryParameters3D.create(source.global_position + Vector3.UP, target.global_position + Vector3.UP, 1)
		if not source.get_world_3d().direct_space_state.intersect_ray(wall_query).is_empty():
			continue
		if register_target(target.get_instance_id()):
			if contact_time >= 0.0:
				elapsed = contact_time
			confirmed = true
			target.receive_hit(data.damage * multiplier, data.poise * multiplier, source.global_position, data.parryable, _contact_context(target, forward, blade_points_world,contact_phase,damage_segment_world))
	return confirmed

func _contact_context(target: Node3D, forward: Vector3, blade_points_world: Array[Vector3] = [], contact_phase: float = -1.0, damage_segment_world: Array[Vector3] = []) -> Dictionary:
	# The sweep confirms a hurtbox overlap, not a triangle-level sword contact.
	# A ray against that hurtbox supplies an honest surface point/normal. If its
	# origin is inside or another body intercepts it, label the fallback explicitly.
	var incoming := target.global_position - source.global_position
	incoming.y = 0.0
	if incoming.length_squared() < 0.000001:
		incoming = forward
	incoming = incoming.normalized()
	var center := target.global_position + Vector3.UP * 1.1
	var ray_from := source.global_position + Vector3.UP * 1.1
	if blade_points_world.size() == 2:
		var ray_segment: Array[Vector3] = blade_points_world
		if damage_segment_world.size() == 4:
			ray_segment = [damage_segment_world[2],damage_segment_world[3]]
		for child in target.get_children():
			if child is CollisionShape3D and child.shape is CapsuleShape3D and not child.disabled:
				var capsule := child.shape as CapsuleShape3D
				var half_axis := maxf(0.0,capsule.height*0.5-capsule.radius)
				var closest := Geometry3D.get_closest_points_between_segments(ray_segment[0],ray_segment[1],child.to_global(Vector3.DOWN*half_axis),child.to_global(Vector3.UP*half_axis))
				center = closest[1]
				var outward: Vector3 = closest[0]-center
				if outward.length_squared() < 0.000001:
					outward = -incoming
				var shape_scale: Vector3 = child.global_basis.get_scale().abs()
				var radius := capsule.radius*maxf(shape_scale.x,maxf(shape_scale.y,shape_scale.z))
				ray_from = center + outward.normalized()*(radius+0.2)
				break
	var point := center
	var normal := -incoming
	var contact_source := "hurtbox_proxy"
	var ray := PhysicsRayQueryParameters3D.create(ray_from, center)
	ray.exclude = [source.get_rid()]
	ray.hit_from_inside = true
	var surface := source.get_world_3d().direct_space_state.intersect_ray(ray)
	if not surface.is_empty() and surface.collider == target:
		var surface_normal: Vector3 = surface.normal
		if surface_normal.is_finite() and surface_normal.length_squared() > 0.000001:
			point = surface.position
			normal = surface_normal.normalized()
			contact_source = "hurtbox_ray"
	var strength := data.impact_strength
	if strength.is_empty():
		strength = "skill" if String(presentation_id).begins_with("skill_") else ("heavy" if presentation_id == &"heavy" else "light")
	return {
		"attack_id":String(presentation_id), "strength":strength,
		"attack_instance_id":attack_instance_id, "source":"player" if (source.collision_layer & 2) != 0 else "enemy",
		"point":point, "normal":normal, "direction":incoming,
		"source_position":source.global_position, "target_position":target.global_position,
		"contact_source":contact_source, "material":"metal", "target_id":target.get_instance_id(),
		"contact_phase":contact_phase, "attack_elapsed":elapsed,
		"contact_blade_grip":blade_points_world[0] if blade_points_world.size() == 2 else Vector3.ZERO,
		"contact_blade_tip":blade_points_world[1] if blade_points_world.size() == 2 else Vector3.ZERO,
		"damage_start_fraction":data.blade_damage_start_fraction if damage_segment_world.size() == 4 else 0.0,
		"contact_damage_base":damage_segment_world[0] if damage_segment_world.size() == 4 else Vector3.ZERO,
		"contact_damage_tip":damage_segment_world[1] if damage_segment_world.size() == 4 else Vector3.ZERO,
		"contact_damage_axis_base":damage_segment_world[2] if damage_segment_world.size() == 4 else Vector3.ZERO,
		"contact_damage_axis_tip":damage_segment_world[3] if damage_segment_world.size() == 4 else Vector3.ZERO,
	}
