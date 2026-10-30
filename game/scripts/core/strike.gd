class_name CombatStrike
extends RefCounted

# A new ledger for each swing. Swept spheres cover the space between physics ticks.
var data: AttackData
var source: CharacterBody3D
var elapsed: float = 0.0
var hit_ids: Dictionary = {}
var previous_tip: Vector3
var started: bool = false
var multiplier: float = 1.0

func _init(actor: CharacterBody3D, attack: AttackData, power: float = 1.0) -> void:
	source = actor
	data = attack
	multiplier = power
	previous_tip = actor.global_position

func register_target(id: int) -> bool:
	if hit_ids.has(id):
		return false
	hit_ids[id] = true
	return true

func step(delta: float, forward: Vector3, mask: int) -> void:
	var old_time := elapsed
	elapsed += delta
	if elapsed < data.startup or old_time >= data.startup + data.active:
		return
	var fraction := clampf((elapsed - data.startup) / data.active, 0.0, 1.0)
	var angle := deg_to_rad(lerpf(-data.arc * 0.5, data.arc * 0.5, fraction))
	var tip := source.global_position + Vector3.UP * 1.1 + forward.rotated(Vector3.UP, angle) * (data.reach - 0.65)
	if not started:
		previous_tip = source.global_position + Vector3.UP * 1.1 + forward.rotated(Vector3.UP, deg_to_rad(-data.arc * 0.5)) * (data.reach - 0.65)
		started = true
	var sphere := SphereShape3D.new()
	sphere.radius = 0.85
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = sphere
	query.collision_mask = mask
	query.exclude = [source.get_rid()]
	var samples := maxi(1, ceili(previous_tip.distance_to(tip) / 0.35))
	for sample in range(samples + 1):
		query.transform = Transform3D(Basis.IDENTITY, previous_tip.lerp(tip, float(sample) / samples))
		for result in source.get_world_3d().direct_space_state.intersect_shape(query, 16):
			var target: Object = result.collider
			if not target.has_method("receive_hit") or hit_ids.has(target.get_instance_id()):
				continue
			var wall_query := PhysicsRayQueryParameters3D.create(source.global_position + Vector3.UP, target.global_position + Vector3.UP, 1)
			if not source.get_world_3d().direct_space_state.intersect_ray(wall_query).is_empty():
				continue
			if register_target(target.get_instance_id()):
				target.receive_hit(data.damage * multiplier, data.poise * multiplier, source.global_position, data.parryable)
	previous_tip = tip
