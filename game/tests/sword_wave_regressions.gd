extends RefCounted

# Real collision-server fixtures exercise an independently positioned hurtbox,
# thin blockers and both fixed/large time steps. No gameplay enemy is mutated.
class WaveOwner:
	extends CharacterBody3D
	var dead := false

class HitTarget:
	extends StaticBody3D
	var hits := 0
	var damage := 0.0
	var poise := 0.0
	var context: Dictionary = {}
	func receive_hit(amount: float, force: float, _origin: Vector3, _parryable: bool = true, receipt: Dictionary = {}) -> void:
		hits += 1
		damage += amount
		poise += force
		context = receipt.duplicate(true)

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _owner(parent: Node3D, lane: float) -> WaveOwner:
	var source := WaveOwner.new()
	source.collision_layer = 2
	source.collision_mask = 0
	parent.add_child(source)
	source.position = Vector3(lane,0,0)
	return source

static func _target(parent: Node3D, point: Vector3, radius: float = 0.06) -> HitTarget:
	var target := HitTarget.new()
	target.collision_layer = 4
	target.collision_mask = 0
	var collision := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = radius
	collision.shape = sphere
	collision.position.y = 1.05
	target.add_child(collision)
	parent.add_child(target)
	target.position = point
	return target

static func _wall(parent: Node3D, point: Vector3, size: Vector3) -> StaticBody3D:
	var wall := StaticBody3D.new()
	wall.collision_layer = 1
	wall.collision_mask = 0
	var collision := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	collision.shape = box
	wall.add_child(collision)
	parent.add_child(wall)
	wall.position = point
	return wall

static func _strike(source: CharacterBody3D) -> CombatStrike:
	var data := AttackData.new()
	data.damage = 40.0
	data.poise = 30.0
	data.impact_strength = "heavy"
	return CombatStrike.new(source,data,1.5,&"heavy")

static func _wave(parent: Node3D, source: CharacterBody3D, attack: CombatStrike, reach: float = 4.5, width: float = 2.0, speed: float = 16.0) -> RuneSwordWave:
	var wave := RuneSwordWave.new()
	parent.add_child(wave)
	wave.setup(source,attack,Vector3.FORWARD,reach,width,speed,0.7)
	wave.set_physics_process(false)
	return wave

static func _advance(wave: RuneSwordWave, delta: float, count: int) -> void:
	for index in range(count):
		if not is_instance_valid(wave) or wave.is_queued_for_deletion():
			break
		wave._physics_process(delta)

static func run(world: Node3D, check: Callable) -> bool:
	var tree := world.get_tree()
	var fixture := Node3D.new()
	world.add_child(fixture)
	fixture.global_position = Vector3(460,30,460)
	var saved_quality := Session.quality
	# At 30/60Hz a thin far hurtbox is hit; source-based reach, width,
	# backwards exclusion and per-strike damage are independently observed.
	for hz in [30,60]:
		var lane := 0.0 if hz == 30 else 12.0
		var source := _owner(fixture,lane)
		var far := _target(fixture,Vector3(lane,0,-4.2))
		var outside := _target(fixture,Vector3(lane,0,-4.75))
		var side := _target(fixture,Vector3(lane+1.2,0,-3.0))
		var behind := _target(fixture,Vector3(lane,0,0.5))
		await _tick(tree)
		await _tick(tree)
		var attack := _strike(source)
		var wave := _wave(fixture,source,attack)
		_advance(wave,1.0/hz,hz)
		check.call(far.hits == 1 and outside.hits == 0 and side.hits == 0 and behind.hits == 0,"%dHz sword wave pierces a far hurtbox while respecting its displayed width, source reach and forward direction" % hz)
		check.call(is_equal_approx(far.damage,42.0) and is_equal_approx(far.poise,31.5),"%dHz sword wave uses the originating strike multiplier and configured damage scale once" % hz)
		check.call(bool(far.context.get("sword_wave",false)) and int(far.context.get("attack_instance_id",0)) == attack.attack_instance_id and String(far.context.get("contact_source","")) in ["hurtbox_ray","hurtbox_proxy"] and not far.context.has("curve_sha256"),"Sword-wave receipts retain their originating serial and honest hurtbox provenance without claiming a blade curve")
		await _tick(tree)
	# A full-range delta must cover every intermediate thin target, rather than
	# testing only its final position. The furthest surface remains <=4.5m.
	var source := _owner(fixture,24.0)
	var thin: Array[HitTarget] = []
	for depth in [1.0,2.0,3.0,4.35]:
		thin.append(_target(fixture,Vector3(24,0,-depth),0.025))
	var beyond := _target(fixture,Vector3(24,0,-4.7),0.025)
	await _tick(tree)
	await _tick(tree)
	var attack := _strike(source)
	var wave := _wave(fixture,source,attack)
	wave._physics_process(0.25)
	var every_hit := true
	for target in thin:
		every_hit = every_hit and target.hits == 1
	var report := wave.presentation_report()
	check.call(every_hit and beyond.hits == 0 and absf(float(report.travel_m)-3.9) < 0.00001,"One large delta sweeps every intermediate hurtbox and stops the leading edge at 4.5m from the original source")
	check.call(int(report.triangles) <= 1200 and int(report.collision_segments) <= 8 and report.collision_geometry == "rendered_convex_prisms","The visible solid crescent and swept queries share bounded convex geometry")
	wave.queue_free()
	await _tick(tree)
	# Bidirectional ledger sharing: an existing blade hit is skipped by the
	# wave, and a wave contact prevents the later blade from registering again.
	source = _owner(fixture,36.0)
	var blade_first := _target(fixture,Vector3(36,0,-1.0))
	var wave_first := _target(fixture,Vector3(36,0,-3.0))
	await _tick(tree)
	await _tick(tree)
	attack = _strike(source)
	attack.register_target(blade_first.get_instance_id())
	wave = _wave(fixture,source,attack)
	wave._physics_process(0.20)
	wave._physics_process(0.02)
	check.call(blade_first.hits == 0 and wave_first.hits == 1 and not attack.register_target(wave_first.get_instance_id()),"Melee-first and wave-first contacts share one target ledger in both directions")
	wave.queue_free()
	await _tick(tree)
	# A narrow off-centre wall intersects the crescent edge but misses its
	# centre ray. Full-volume collision must still stop the whole projectile.
	source = _owner(fixture,48.0)
	var before_wall := _target(fixture,Vector3(48,0,-1.2))
	var after_wall := _target(fixture,Vector3(48,0,-3.2))
	_wall(fixture,Vector3(48.84,1.05,-2.2),Vector3(0.12,0.6,0.04))
	await _tick(tree)
	await _tick(tree)
	wave = _wave(fixture,source,_strike(source))
	wave._physics_process(0.25)
	report = wave.presentation_report()
	check.call(before_wall.hits == 1 and after_wall.hits == 0 and String(report.reason) == "wall_stopped" and float(report.travel_m) < 2.0,"A thin off-axis wall stops the actual crescent volume before all targets beyond it even in a large delta")
	wave.queue_free()
	await _tick(tree)
	# Initial overlaps are explicitly covered because cast_motion ignores them.
	source = _owner(fixture,60.0)
	var blocked := _target(fixture,Vector3(60,0,-1.0))
	_wall(fixture,Vector3(60,1.05,-0.5),Vector3(3,0.6,0.3))
	await _tick(tree)
	await _tick(tree)
	wave = _wave(fixture,source,_strike(source))
	wave._physics_process(0.1)
	check.call(blocked.hits == 0 and is_zero_approx(float(wave.presentation_report().travel_m)),"A crescent spawned overlapping a wall cannot escape the initial overlap or damage targets through it")
	wave.queue_free()
	await _tick(tree)
	# The charged configuration reaches its true 7.5m leading-front bound.
	source = _owner(fixture,72.0)
	var charged_far := _target(fixture,Vector3(72,0,-7.3))
	var charged_outside := _target(fixture,Vector3(72,0,-7.7))
	await _tick(tree)
	await _tick(tree)
	wave = _wave(fixture,source,_strike(source),7.5,2.4,18.0)
	wave._physics_process(0.39)
	check.call(charged_far.hits == 1 and charged_outside.hits == 0 and absf(float(wave.presentation_report().travel_m)-6.9) < 0.00001,"The charged wave covers a thin target at 7.3m and never extends its leading front past 7.5m")
	wave.queue_free()
	await _tick(tree)
	# Automatic physics owns finite lifetime; no manual advance or equipped
	# strike is required to clean up. Quality indexes keep their existing roles.
	Session.quality = 1
	source = _owner(fixture,84.0)
	wave = _wave(fixture,source,_strike(source))
	report = wave.presentation_report()
	check.call(int(report.quality) == 1 and int(report.collision_segments) < 8,"Performance quality keeps the same physical crescent with fewer segments")
	var lifetime_ref: WeakRef = weakref(wave)
	wave.set_physics_process(true)
	for index in range(45):
		await _tick(tree)
		if lifetime_ref.get_ref() == null:
			break
	check.call(lifetime_ref.get_ref() == null,"An unattended wave releases itself and its retained originating strike within a finite lifetime")
	# Death and tree exit are distinct ownership terminal paths.
	source = _owner(fixture,96.0)
	wave = _wave(fixture,source,_strike(source))
	var death_ref: WeakRef = weakref(wave)
	source.dead = true
	wave.set_physics_process(true)
	await _tick(tree)
	await _tick(tree)
	check.call(death_ref.get_ref() == null,"Owner death removes a previously launched wave")
	source = _owner(fixture,108.0)
	wave = _wave(fixture,source,_strike(source))
	var exit_ref: WeakRef = weakref(wave)
	source.queue_free()
	await _tick(tree)
	await _tick(tree)
	check.call(exit_ref.get_ref() == null,"Owner tree exit removes a wave without leaving a callback or attack reference")
	# Same-frame cap includes fading live nodes and excludes queued deletions.
	source = _owner(fixture,120.0)
	for index in range(10):
		_wave(fixture,source,_strike(source))
	var active := 0
	for node in tree.get_nodes_in_group("sword_waves"):
		if not node.is_queued_for_deletion():
			active += 1
	check.call(active == RuneSwordWave.MAX_ACTIVE,"Repeated same-frame launches retain at most six live sword waves")
	fixture.queue_free()
	await _tick(tree)
	Session.quality = saved_quality
	check.call(tree.get_nodes_in_group("sword_waves").is_empty(),"Scene teardown removes every wave and its procedural mesh")
	return true
