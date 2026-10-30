class_name RunePlayer
extends CharacterBody3D

signal hurt
signal died
signal landed_hit(amount: float, position: Vector3)
signal parried
signal skill_effect(position: Vector3, radius: float, color: Color)

const LIGHTS: Array[AttackData] = [preload("res://data/light_1.tres"), preload("res://data/light_2.tres"), preload("res://data/light_3.tres")]
const HEAVY: AttackData = preload("res://data/heavy.tres")
var visual: ActorVisual
var max_health: float = 120.0
var health: float = 120.0
var rune: float = 35.0
var max_rune: float = 100.0
var potions: int = 3
var active: bool = false
var dead: bool = false
var facing: Vector3 = Vector3.FORWARD
var camera_yaw: float = 0.0
var locked_target: Node3D
var strike: CombatStrike
var combo: int = 0
var combo_hits: int = 0
var combo_timeout: float = 0.0
var input_buffer: float = 0.0
var buffered_heavy: bool = false
var heavy_held: float = 0.0
var dodge_time: float = 0.0
var dodge_cooldown: float = 0.0
var dodge_direction: Vector3
var parry_time: float = 0.0
var parry_cooldown: float = 0.0
var invulnerability: float = 0.0
var hit_pause: float = 0.0
var stagger: float = 0.0
var world: Node3D

func _ready() -> void:
	name = "Player"
	collision_layer = 2
	collision_mask = 1 | 4
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.36
	capsule.height = 1.85
	shape.shape = capsule
	shape.position.y = 0.95
	add_child(shape)
	visual = ActorVisual.new()
	add_child(visual)
	visual.setup("hero")
	refresh_stats()
	health = max_health
	floor_snap_length = 0.5
	add_to_group("player")

func refresh_stats() -> void:
	max_health = 120.0 + Session.upgrades[1] * 25.0
	max_rune = 100.0 + Session.upgrades[2] * 20.0
	health = minf(health, max_health)

func restore(point: Vector3) -> void:
	global_position = point
	refresh_stats()
	health = max_health
	rune = maxf(rune, 35.0)
	potions = 3
	dead = false
	strike = null
	combo = 0
	dodge_time = 0.0
	invulnerability = 1.0
	velocity = Vector3.ZERO

func _physics_process(delta: float) -> void:
	if not active:
		visual.pose(delta, 0)
		return
	if dead:
		visual.pose(delta, 0, -1, false, false, true)
		return
	dodge_time = maxf(0.0, dodge_time - delta)
	dodge_cooldown = maxf(0.0, dodge_cooldown - delta)
	parry_time = maxf(0.0, parry_time - delta)
	parry_cooldown = maxf(0.0, parry_cooldown - delta)
	invulnerability = maxf(0.0, invulnerability - delta)
	stagger = maxf(0.0, stagger - delta)
	combo_timeout = maxf(0.0, combo_timeout - delta)
	if combo_timeout == 0.0:
		combo_hits = 0
	if Input.is_action_just_pressed("light"):
		input_buffer = 0.2
		buffered_heavy = false
	if Input.is_action_just_pressed("heavy"):
		heavy_held = 0.0
	if Input.is_action_pressed("heavy"):
		heavy_held += delta
	if Input.is_action_just_released("heavy"):
		input_buffer = 0.2
		buffered_heavy = true
	if Input.is_action_just_pressed("heal") and potions > 0 and health < max_health and strike == null:
		potions -= 1
		health = minf(max_health, health + max_health * 0.55)
		Audio.play_sound("rune")
		skill_effect.emit(global_position, 1.6, Color("8deac2"))
	var axes := Input.get_vector("left", "right", "forward", "back")
	var direction := Vector3(axes.x, 0, axes.y).rotated(Vector3.UP, camera_yaw)
	if Input.is_action_just_pressed("dodge") and dodge_cooldown <= 0.0 and stagger <= 0.0 and (strike == null or strike.data.can_cancel(strike.elapsed)):
		strike = null
		dodge_time = 0.32
		dodge_cooldown = 0.48
		invulnerability = 0.29
		dodge_direction = direction.normalized() if direction.length() > 0.1 else facing
		Audio.play_sound("dodge")
	if Input.is_action_just_pressed("parry") and parry_cooldown <= 0.0 and strike == null and dodge_time <= 0.0:
		parry_time = 0.22
		parry_cooldown = 0.65
	for index in range(3):
		if Input.is_action_just_pressed("skill_%d" % (index + 1)):
			use_skill(index)
	if hit_pause > 0.0:
		hit_pause -= delta
		return
	if strike != null:
		strike.step(delta, facing, 4)
		if input_buffer > 0.0 and strike.data.can_cancel(strike.elapsed):
			begin_attack(buffered_heavy, (combo + 1) % 3)
		elif strike.elapsed >= strike.data.duration():
			strike = null
	elif input_buffer > 0.0 and dodge_time <= 0.0 and parry_time <= 0.0 and stagger <= 0.0:
		begin_attack(buffered_heavy, 0)
	input_buffer = maxf(0.0, input_buffer - delta)
	var speed := 8.5 if Input.is_action_pressed("sprint") else 6.4
	if direction.length() > 0.1 and strike == null and dodge_time <= 0.0:
		facing = direction.normalized()
	if is_instance_valid(locked_target) and not locked_target.dead and strike == null:
		var to_target := locked_target.global_position - global_position
		to_target.y = 0
		if to_target.length() > 0.1:
			facing = to_target.normalized()
	var desired := direction * speed
	if strike != null:
		desired = facing * strike.data.lunge * (1.0 if strike.elapsed < strike.data.startup + strike.data.active else 0.15)
	if dodge_time > 0.0:
		desired = dodge_direction * 17.0
	if stagger > 0.0 or parry_time > 0.0:
		desired *= 0.1
	velocity.x = desired.x
	velocity.z = desired.z
	velocity.y -= 24.0 * delta
	if is_on_floor():
		velocity.y = -0.1
	move_and_slide()
	visual.rotation.y = lerp_angle(visual.rotation.y, atan2(-facing.x, -facing.z), minf(1.0, delta * 18.0))
	var swing := clampf((strike.elapsed - strike.data.startup + 0.15) / (strike.data.active + 0.15), 0.0, 1.0) if strike != null else -1.0
	visual.pose(delta, Vector2(velocity.x, velocity.z).length(), swing, dodge_time > 0.0, parry_time > 0.0)
	if global_position.y < -8:
		world.recover_from_fall()

func begin_attack(heavy: bool, chain: int) -> void:
	combo = chain
	var data: AttackData = HEAVY if heavy else LIGHTS[chain]
	var power := 1.0 + Session.upgrades[0] * 0.15
	if heavy and heavy_held >= 0.65:
		power *= 1.65
	strike = CombatStrike.new(self, data, power)
	input_buffer = 0.0
	heavy_held = 0.0
	if is_instance_valid(locked_target) and not locked_target.dead:
		var to_target := locked_target.global_position - global_position
		to_target.y = 0
		if to_target.length() < 12:
			facing = to_target.normalized()
	else:
		var nearest: Node3D = world.nearest_enemy(global_position, 4.5)
		if nearest != null:
			facing = (nearest.global_position - global_position).normalized()
			facing.y = 0
	Audio.play_sound("slash", 1.0 + chain * 0.12)

func on_hit(amount: float, point: Vector3) -> void:
	rune = minf(max_rune, rune + 7.0 + Session.upgrades[2] * 1.5)
	combo_hits += 1
	combo_timeout = 3.0
	hit_pause = 0.035
	landed_hit.emit(amount, point)
	Audio.play_sound("hit", randf_range(0.9, 1.15))

func receive_hit(amount: float, _poise: float, origin: Vector3, parryable: bool = true) -> void:
	if dead or invulnerability > 0.0 or not active:
		return
	var incoming := origin - global_position
	incoming.y = 0
	if parry_time > 0.0 and parryable and incoming.normalized().dot(facing) > -0.1:
		rune = minf(max_rune, rune + 22.0)
		parry_time = 0.0
		invulnerability = 0.4
		Audio.play_sound("parry")
		parried.emit()
		for enemy in get_tree().get_nodes_in_group("enemies"):
			if not enemy.dead and enemy.global_position.distance_to(global_position) < 5:
				enemy.stagger = 1.4
		return
	health = maxf(0, health - amount)
	invulnerability = 0.7
	stagger = 0.15
	strike = null
	hurt.emit()
	Audio.play_sound("hit", 0.7)
	if health <= 0:
		dead = true
		Audio.play_sound("death")
		died.emit()

func use_skill(index: int) -> bool:
	var costs: Array[float] = [25.0, 45.0, 80.0]
	if dead or rune < costs[index] or stagger > 0 or dodge_time > 0 or strike != null:
		return false
	rune -= costs[index]
	var data: AttackData = HEAVY.duplicate()
	data.title = ["섬광 돌진", "룬 폭풍", "성역의 심판"][index]
	data.damage = [65.0, 55.0, 150.0][index]
	data.poise = [65.0, 65.0, 160.0][index]
	data.arc = 160.0 if index == 0 else 360.0
	data.reach = [4.5, 5.5, 7.0][index]
	data.lunge = 13.0 if index == 0 else 0.0
	data.startup = 0.16
	data.active = 0.35
	data.recovery = 0.28
	strike = CombatStrike.new(self, data, 1.0 + Session.upgrades[0] * 0.15)
	invulnerability = 0.3 if index < 2 else 0.65
	skill_effect.emit(global_position, data.reach, Color("b8f7e3") if index == 2 else Color("53d5d0"))
	Audio.play_sound("rune", 0.85 + index * 0.15)
	return true
