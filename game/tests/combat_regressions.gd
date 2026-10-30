extends RefCounted

class HitTarget:
	extends StaticBody3D
	var hits: int = 0
	func receive_hit(_amount: float, _poise: float, _origin: Vector3, _parryable: bool = true) -> void:
		hits += 1

static func _target(parent: Node3D, point: Vector3) -> HitTarget:
	var target := HitTarget.new()
	target.collision_layer = 4
	target.collision_mask = 0
	var collider := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.2
	collider.shape = sphere
	collider.position.y = 1.1
	target.add_child(collider)
	parent.add_child(target)
	target.position = point
	return target

static func run(world: Node, check: Callable) -> bool:
	var tree := world.get_tree()
	var fixture := Node3D.new()
	world.add_child(fixture)
	fixture.global_position = Vector3(240, 10, 240)
	var source := CharacterBody3D.new()
	source.collision_layer = 0
	fixture.add_child(source)
	var close := _target(fixture, Vector3(0, 0, -0.8))
	var middle := _target(fixture, Vector3(0, 0, -3.0))
	var side := _target(fixture, Vector3(4.0, 0, 0))
	var behind := _target(fixture, Vector3(0, 0, 3.5))
	var outside := _target(fixture, Vector3(0, 0, -6.5))
	await tree.physics_frame
	await tree.physics_frame
	var data := AttackData.new()
	data.arc = 360.0
	data.reach = 5.5
	# Cross the complete active window in one update, the worst case for a
	# 360-degree swing whose initial and final tip positions are identical.
	var burst := CombatStrike.new(source, data)
	burst.step(data.duration(), Vector3.FORWARD, 4)
	check.call(close.hits == 1 and middle.hits == 1, "Radial skills hit close and mid-range enemies")
	check.call(side.hits == 1 and behind.hits == 1, "A full-window radial update covers every direction")
	check.call(outside.hits == 0, "Radial skills respect their reach")
	burst.step(0.02, Vector3.FORWARD, 4)
	check.call(close.hits == 1 and side.hits == 1, "Radial skills register each target once per cast")
	var wall := StaticBody3D.new()
	var wall_shape := CollisionShape3D.new()
	var wall_box := BoxShape3D.new()
	wall_box.size = Vector3(1.0, 3.0, 0.2)
	wall_shape.shape = wall_box
	wall.add_child(wall_shape)
	fixture.add_child(wall)
	wall.position = Vector3(0, 1.1, -1.8)
	await tree.physics_frame
	await tree.physics_frame
	var blocked := CombatStrike.new(source, data)
	blocked.step(data.duration(), Vector3.FORWARD, 4)
	check.call(middle.hits == 1 and close.hits == 2, "Radial skills cannot damage targets through walls")
	wall.queue_free()
	await tree.physics_frame
	await tree.physics_frame
	# A longer heavy attack must include its inner blade, not leave a safe hole.
	data.arc = 130.0
	data.reach = 4.0
	var before := close.hits
	var behind_before := behind.hits
	var heavy := CombatStrike.new(source, data)
	heavy.step(data.duration(), Vector3.FORWARD, 4)
	check.call(close.hits == before + 1, "Heavy attacks cover the inner blade at close range")
	check.call(behind.hits == behind_before, "Directional attacks do not hit enemies behind the player")
	var player: RunePlayer = world.player
	var origin := player.global_position
	var enemy := RuneEnemy.new()
	enemy.player = player
	enemy.world = world
	fixture.add_child(enemy)
	enemy.global_position = origin + Vector3.FORWARD * 2.0
	enemy.strike = CombatStrike.new(enemy, RuneEnemy.BASE_ATTACK)
	enemy.burst_time = 0.5
	player.active = true
	player.dead = false
	player.invulnerability = 0.0
	player.parry_time = 0.22
	player.facing = Vector3.FORWARD
	player.receive_hit(10.0, 10.0, enemy.global_position)
	check.call(enemy.strike == null and enemy.burst_time == 0.0, "Parry cancels prepared melee and burst attacks")
	check.call(enemy.stagger >= 1.4, "Parry grants its full counterattack opening")
	enemy.receive_hit(1.0, 1.0, origin)
	check.call(enemy.stagger >= 1.4, "Weak follow-up attacks cannot shorten parry stagger")
	player.active = false
	enemy.stagger = 0.0
	enemy.burst_time = 0.0
	enemy.facing = Vector3.BACK
	enemy.strike = CombatStrike.new(enemy, RuneEnemy.BASE_ATTACK)
	enemy.strike.elapsed = RuneEnemy.BASE_ATTACK.startup - 0.001
	await tree.physics_frame
	await tree.physics_frame
	player.active = true
	player.invulnerability = 0.0
	player.parry_time = 0.22
	var health_before := player.health
	enemy._physics_process(0.1)
	check.call(enemy.strike == null and player.health == health_before, "Parry during an enemy physics swing cancels safely")
	player.active = false
	player.input_buffer = 0.2
	player.heavy_held = 3.0
	player.parry_time = 0.2
	player.parry_cooldown = 0.6
	player.dodge_time = 0.3
	player.dodge_cooldown = 0.5
	player.hit_pause = 0.1
	player.stagger = 1.0
	player.combo_hits = 6
	player.combo_timeout = 3.0
	player.rune = 1000.0
	player.locked_target = enemy
	player.restore(origin)
	check.call(player.input_buffer == 0 and player.heavy_held == 0 and player.combo_hits == 0, "Restore clears buffered attacks and old combo state")
	check.call(player.parry_time == 0 and player.parry_cooldown == 0 and player.dodge_cooldown == 0, "Restore clears defensive action state")
	check.call(player.hit_pause == 0 and player.stagger == 0 and player.locked_target == null, "Restore clears interruption state and stale targets")
	check.call(player.rune <= player.max_rune, "Restore clamps rune after a maximum gauge change")
	check.call(not player.use_skill(-1) and not player.use_skill(3), "Invalid skill indices do not access outside the skill table")
	fixture.queue_free()
	await tree.process_frame
	await tree.process_frame
	return true
