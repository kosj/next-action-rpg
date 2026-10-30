class_name CombatStrike
extends RefCounted

# A new ledger for each swing. Blade volumes cover the arc between physics ticks.
var data: AttackData
var source: CharacterBody3D
var elapsed: float = 0.0
var hit_ids: Dictionary = {}
var previous_origin: Vector3
var started: bool = false
var multiplier: float = 1.0
var presentation_id: StringName

func _init(actor: CharacterBody3D, attack: AttackData, power: float = 1.0, visual_id: StringName = &"") -> void:
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
	var first_fraction := clampf((old_time - data.startup) / data.active, 0.0, 1.0)
	var last_fraction := clampf((elapsed - data.startup) / data.active, 0.0, 1.0)
	var start_origin := old_origin.lerp(source.global_position, clampf((data.startup-old_time) / delta, 0.0, 1.0))
	var end_origin := old_origin.lerp(source.global_position, clampf((data.startup+data.active-old_time) / delta, 0.0, 1.0))
	var first_angle := deg_to_rad(lerpf(-data.arc * 0.5, data.arc * 0.5, first_fraction))
	var last_angle := deg_to_rad(lerpf(-data.arc * 0.5, data.arc * 0.5, last_fraction))
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
		for result in source.get_world_3d().direct_space_state.intersect_shape(query, 16):
			var target: Object = result.collider
			if not target.has_method("receive_hit") or hit_ids.has(target.get_instance_id()):
				continue
			var wall_query := PhysicsRayQueryParameters3D.create(source.global_position + Vector3.UP, target.global_position + Vector3.UP, 1)
			if not source.get_world_3d().direct_space_state.intersect_ray(wall_query).is_empty():
				continue
			if register_target(target.get_instance_id()):
				target.receive_hit(data.damage * multiplier, data.poise * multiplier, source.global_position, data.parryable)
