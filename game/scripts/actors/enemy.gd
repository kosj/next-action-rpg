class_name RuneEnemy
extends CharacterBody3D

signal defeated(enemy: RuneEnemy)
const BASE_ATTACK: AttackData = preload("res://data/enemy_attack.tres")
var kind: String = "melee"
var is_boss: bool = false
var elite: bool = false
var dead: bool = false
var health: float = 85.0
var max_health: float = 85.0
var poise_meter: float = 0.0
var stagger: float = 0.0
var presentation_stagger_duration: float = 0.0
var cooldown: float = 1.0
var strike: CombatStrike
var facing: Vector3 = Vector3.FORWARD
var player: RunePlayer
var world: Node3D
var visual: ActorVisual
var phase: int = 1
var attack_count: int = 0
var burst_time: float = 0.0
var death_time: float = 0.0
var bar: MeshInstance3D
var warning: MeshInstance3D
var home: Vector3

func _ready() -> void:
	collision_layer = 4
	collision_mask = 1 | 2 | 4
	max_health = 1050.0 if is_boss else (180.0 if elite else (70.0 if kind == "ranged" else 95.0))
	if kind == "shield":
		max_health *= 1.25
	health = max_health
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.75 if is_boss else 0.4
	capsule.height = 3.4 if is_boss else 1.95
	shape.shape = capsule
	shape.position.y = capsule.height * 0.5
	add_child(shape)
	visual = ActorVisual.new()
	add_child(visual)
	visual.setup("boss" if is_boss else "sentinel")
	if elite:
		visual.scale *= 1.15
	if kind == "shield":
		var shield := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		mesh.size = Vector3(0.65, 1.2, 0.16)
		shield.mesh = mesh
		shield.position = Vector3(-0.5, 1.0, -0.4)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color("766048")
		mat.metallic = 0.6
		shield.material_override = mat
		visual.add_child(shield)
	bar = _plane(Vector2(1.0, 0.07), Color("da715a"))
	bar.position.y = 2.45 if not is_boss else 4.0
	add_child(bar)
	var bar_mat: StandardMaterial3D = bar.material_override
	bar_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	warning = _plane(Vector2(0.18, 0.65), Color("ffb876"))
	warning.position.y = 2.8 if not is_boss else 4.3
	var warn_mat: StandardMaterial3D = warning.material_override
	warn_mat.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	add_child(warning)
	warning.visible = false
	bar.visible = false
	home = global_position
	add_to_group("enemies")

func _plane(size: Vector2, color: Color) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	var mesh := QuadMesh.new()
	mesh.size = size
	node.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = color
	mat.no_depth_test = true
	node.material_override = mat
	return node

func _physics_process(delta: float) -> void:
	if dead:
		death_time += delta
		visual.pose(delta, 0.0, -1.0, false, false, true, presentation_snapshot())
		if death_time > 3:
			queue_free()
		return
	if not is_instance_valid(player) or not player.active or player.dead:
		visual.pose(delta, 0.0)
		return
	stagger = maxf(0.0, stagger - delta)
	cooldown = maxf(0.0, cooldown - delta)
	poise_meter = maxf(0.0, poise_meter - delta * 4)
	if is_boss and phase == 1 and health <= max_health * 0.5:
		phase = 2
		interrupt_attack(0.8)
		world.announce("봉인이 깨어집니다", "수호자가 두 번째 형상을 드러냅니다.")
		world.spawn_ring(global_position, 6, Color("e89467"))
	var direction := player.global_position - global_position
	direction.y = 0
	var distance := direction.length()
	if distance > 42:
		return
	var desired := Vector3.ZERO
	if strike != null:
		var current_strike := strike
		current_strike.step(delta, facing, 2)
		# A successful parry can cancel this strike during receive_hit().
		if strike == current_strike and current_strike.elapsed >= current_strike.data.duration():
			strike = null
			cooldown = 0.75 if is_boss and phase == 2 else randf_range(1.0, 2.0)
	elif burst_time > 0:
		burst_time -= delta
		if burst_time <= 0:
			world.spawn_ring(global_position, 7.0, Color("ff8c69"))
			if distance < 7.0:
				player.receive_hit(30, 40, global_position, false)
			cooldown = 1.6
	elif stagger <= 0:
		if distance > 0.1:
			facing = direction.normalized()
		var preferred := 10.0 if kind == "ranged" else (3.1 if is_boss else 2.1)
		if distance > preferred:
			desired = facing * (3.9 if is_boss else 3.6)
		elif kind == "ranged" and distance < 6:
			desired = -facing * 2.5
		if cooldown <= 0.0 and distance < preferred + 1.8 and world.can_enemy_attack(self):
			attack_count += 1
			if kind == "ranged":
				world.spawn_projectile(global_position + Vector3.UP * 1.5, player.global_position + Vector3.UP)
				cooldown = 2.8
			elif is_boss and attack_count % 3 == 0:
				burst_time = 1.15
				world.telegraph(global_position, 7.0, 1.15)
			else:
				var data: AttackData = BASE_ATTACK.duplicate()
				if is_boss:
					data.damage = 24.0 if phase == 1 else 29.0
					data.reach = 4.5
					data.arc = 170
					data.startup = 0.68 if phase == 1 else 0.44
				elif elite:
					data.damage = 22.0
				strike = CombatStrike.new(self, data, 1.0, &"enemy_attack")
	if stagger > 0:
		desired = Vector3.ZERO
	if strike != null and strike.elapsed >= strike.data.startup and strike.elapsed < strike.data.startup + strike.data.active:
		desired = facing * (5.5 if is_boss else 3.0)
	# Separation prevents enemies stacking; rooms keep the combat floor unobstructed.
	for other in get_tree().get_nodes_in_group("enemies"):
		if other == self or other.dead:
			continue
		var away: Vector3 = global_position - other.global_position
		away.y = 0
		if away.length() > 0.05 and away.length() < 1.5:
			desired += away.normalized() * 2.0
	velocity.x = desired.x
	velocity.z = desired.z
	velocity.y -= 24 * delta
	if is_on_floor():
		velocity.y = -0.1
	move_and_slide()
	visual.rotation.y = lerp_angle(visual.rotation.y, atan2(-facing.x, -facing.z), minf(1, delta * 9))
	var swing := clampf((strike.elapsed - strike.data.startup + 0.15) / (strike.data.active + 0.15), 0, 1) if strike != null else -1.0
	visual.pose(delta, Vector2(velocity.x, velocity.z).length(), swing, false, false, false, presentation_snapshot())
	warning.visible = strike != null and strike.elapsed < strike.data.startup
	bar.visible = health < max_health and not is_boss
	bar.scale.x = maxf(0.01, health / max_health)

func receive_hit(amount: float, poise: float, origin: Vector3, _parryable: bool = true) -> void:
	if dead:
		return
	var front := (origin - global_position).normalized().dot(facing) > 0.2
	if kind == "shield" and front and poise < 35:
		amount *= 0.3
		world.spawn_ring(global_position + Vector3.UP, 0.6, Color("e5be7b"))
	health = maxf(0.0, health - amount)
	poise_meter += poise
	if (not is_boss and (kind != "shield" or poise >= 35)) or poise_meter >= (180 if is_boss else 65):
		interrupt_attack(1.4 if poise_meter >= 180 else 0.28)
		poise_meter = 0
	player.on_hit(amount, global_position + Vector3.UP * 1.5)
	if health <= 0:
		dead = true
		collision_layer = 0
		collision_mask = 0
		bar.hide()
		warning.hide()
		Session.shards += 80 if is_boss else (20 if elite else 9)
		defeated.emit(self)

func interrupt_attack(duration: float) -> void:
	if duration > stagger:
		presentation_stagger_duration = duration
	stagger = maxf(stagger, duration)
	strike = null
	burst_time = 0.0
	if is_instance_valid(warning):
		warning.hide()

func presentation_snapshot() -> Dictionary:
	return {
		"speed":Vector2(velocity.x, velocity.z).length(), "dead":dead, "death_elapsed":death_time, "stagger":stagger,
		"hit_elapsed":maxf(0.0, maxf(0.28, presentation_stagger_duration)-stagger), "hit_duration":maxf(0.28, presentation_stagger_duration),
		"attack_id":String(strike.presentation_id) if strike != null else ("burst" if burst_time > 0.0 else ""),
		"attack_elapsed":strike.elapsed if strike != null else maxf(0.0, 1.15-burst_time),
		"attack_duration":strike.data.duration() if strike != null else 1.15,
	}
