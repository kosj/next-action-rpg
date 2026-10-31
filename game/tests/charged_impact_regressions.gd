extends RefCounted

# Actual physics queries, controllers, skeletons and CharacterBody wall response.
# Hook: check(await load("res://tests/charged_impact_regressions.gd").run(world, check), "Charged impact suite completes")
const PLAYER_FIELDS: Array[String] = ["active","dead","health","rune","potions","facing","camera_yaw","locked_target","strike","combo","combo_hits","combo_timeout","input_buffer","buffered_heavy","heavy_held","ui_input_guard","dodge_time","dodge_cooldown","dodge_direction","parry_time","parry_cooldown","invulnerability","hit_pause","hit_pause_started_frame","stagger","presentation_death_elapsed","presentation_heal_remaining","presentation_epoch","velocity"]
const ACTIONS: Array[StringName] = [&"light",&"heavy",&"dodge",&"parry",&"heal",&"skill_1",&"skill_2",&"skill_3",&"left",&"right",&"forward",&"back",&"sprint"]

static func _xyz(value: Vector3) -> Array[float]:
	return [value.x,value.y,value.z]

static func _write_contact_proof(report: Dictionary) -> void:
	report["schema_version"] = 1
	report["scope"] = "Actual native charged contact clocks, final displayed weapon markers and frozen trail; no normal-speed art, audio or target-hardware approval."
	report["engine"] = Engine.get_version_info().string
	report["source_hashes"] = {
		"fixture":FileAccess.get_sha256("res://tests/charged_impact_regressions.gd"),
		"charged_attack":FileAccess.get_sha256("res://data/charged_heavy.tres"),
		"hero_body":FileAccess.get_sha256("res://assets/models/production/lyra_gameplay.glb"),
	}
	var path := ProjectSettings.globalize_path("res://").path_join("../build/verification/charged-impact/contact.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file == null:
		push_error("Cannot write actual charged contact proof: %s" % path)
		return
	file.store_string(JSON.stringify(report,"\t")+"\n")
	file.close()

class BladeProbe:
	extends StaticBody3D
	var hits: int = 0
	func receive_hit(_amount: float, _poise: float, _origin: Vector3, _parryable: bool = true, _context: Dictionary = {}) -> void:
		hits += 1

static func _probe(parent: Node3D, point: Vector3) -> BladeProbe:
	var probe := BladeProbe.new()
	probe.collision_layer = 4
	probe.collision_mask = 0
	var collider := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = .08
	collider.shape = sphere
	probe.add_child(collider)
	parent.add_child(probe)
	probe.global_position = point
	return probe

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _body(parent: Node3D, position: Vector3, size: Vector3) -> StaticBody3D:
	var body := StaticBody3D.new()
	body.collision_layer = 1
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	parent.add_child(body)
	body.position = position
	return body

static func _enemy(parent: Node3D, world: Node3D, point: Vector3, kind: String = "melee", boss: bool = false) -> RuneEnemy:
	var enemy := RuneEnemy.new()
	enemy.kind = kind
	enemy.is_boss = boss
	enemy.world = world
	enemy.player = world.player
	parent.add_child(enemy)
	enemy.position = point
	enemy.set_physics_process(false)
	return enemy

static func _bones(visual: ActorVisual) -> Array[Transform3D]:
	var result: Array[Transform3D] = []
	if not is_instance_valid(visual.skeletal_bridge):
		return result
	var skeleton := visual.skeletal_bridge.get_skeleton()
	if not is_instance_valid(skeleton):
		return result
	for index in range(skeleton.get_bone_count()):
		result.append(skeleton.get_bone_pose(index))
	return result

static func _same_bones(first: Array[Transform3D], second: Array[Transform3D]) -> bool:
	if first.is_empty() or first.size() != second.size():
		return false
	for index in range(first.size()):
		if not first[index].is_equal_approx(second[index]):
			return false
	return true

static func _ready_player(player: RunePlayer, point: Vector3) -> void:
	player.set_physics_process(false)
	player.global_position = point
	player.velocity = Vector3.ZERO
	player.active = true
	player.dead = false
	player.strike = null
	player.locked_target = null
	player.facing = Vector3.FORWARD
	player.camera_yaw = 0.0
	player.input_buffer = 0.0
	player.heavy_held = 0.0
	player.ui_input_guard = 0
	player.hit_pause = 0.0
	player.dodge_time = 0.0
	player.parry_time = 0.0
	player.stagger = 0.0
	player.rune = 100.0
	player.presentation_epoch += 1

static func _finish_attack(player: RunePlayer, tree: SceneTree) -> bool:
	player.set_physics_process(true)
	for index in range(100):
		await _tick(tree)
		if player.strike == null:
			player.set_physics_process(false)
			return true
	player.set_physics_process(false)
	return false

static func run(world: Node3D, check: Callable) -> bool:
	var tree := world.get_tree()
	var player: RunePlayer = world.player
	var saved: Dictionary = {}
	for field in PLAYER_FIELDS:
		saved[field] = player.get(field)
	var saved_transform := player.global_transform
	var saved_player_physics := player.is_physics_processing()
	var saved_world_physics := world.is_physics_processing()
	var saved_shards: int = Session.shards
	var saved_upgrades: Array = Session.upgrades.duplicate()
	var saved_actions: Dictionary = {}
	for action in ACTIONS:
		saved_actions[action] = Input.get_action_strength(action)
		Input.action_release(action)
	var old_enemies: Array[Dictionary] = []
	for node in tree.get_nodes_in_group("enemies"):
		old_enemies.append({"node":node,"physics":node.is_physics_processing()})
		node.set_physics_process(false)
	world.set_physics_process(false)
	Session.upgrades[0] = 0
	var fixture := Node3D.new()
	world.add_child(fixture)
	fixture.global_position = Vector3(240, 8, 240)
	_body(fixture, Vector3(0,-0.5,0), Vector3(30,1,30))
	var events: Array[Dictionary] = []
	var amounts: Array[float] = []
	var contact_proof: Dictionary = {"contact_observed":false}
	var on_impact := func(context: Dictionary) -> void: events.append(context.duplicate(true))
	var on_damage := func(amount: float, _point: Vector3) -> void: amounts.append(amount)
	player.impact_confirmed.connect(on_impact)
	player.landed_hit.connect(on_damage)
	await _tick(tree)
	await _tick(tree)
	var start := fixture.global_position + Vector3(0,0.02,2)
	_ready_player(player, start)
	player.heavy_held = 0.649
	player.begin_attack(true, 0)
	check.call(player.strike.data == RunePlayer.HEAVY and is_equal_approx(player.strike.multiplier,1.0), "A sub-threshold heavy retains its original resource and damage")
	var ordinary_attack_serial := player.strike.attack_instance_id
	player.heavy_held = 0.65
	player.begin_attack(true, 0)
	check.call(player.strike.data == RunePlayer.CHARGED_HEAVY and player.strike.presentation_id == &"charged_heavy" and player.strike.attack_instance_id > ordinary_attack_serial, "A completed charge selects a distinct gameplay, presentation and attack-event identity")
	check.call(is_equal_approx(player.strike.data.duration(),1.06) and is_equal_approx(player.strike.multiplier,1.65), "Charged timing is 1.06 seconds while damage and poise retain their 1.65 multiplier")
	var miss_start := player.global_position
	check.call(await _finish_attack(player,tree), "A missed charged attack completes within its bounded physics timeline")
	var miss_travel := Vector2(player.global_position.x-miss_start.x,player.global_position.z-miss_start.z).length()
	check.call(absf(miss_travel-0.576) < 0.008, "A charged miss resolves nominal 0.576m active-only travel through the real player motor")
	check.call(events.is_empty() and amounts.is_empty(), "A charged miss emits neither confirmed impact nor damage events")
	_ready_player(player,start)
	var swept_probe := _probe(fixture,start+Vector3(-.1,1.26,-1.05))
	var distant_probe := _probe(fixture,start+Vector3(0,1.1,-2.8))
	var overhead_probe := _probe(fixture,start+Vector3(0,3,-.5))
	var rear_probe := _probe(fixture,start+Vector3(0,1.2,.8))
	await _tick(tree)
	await _tick(tree)
	var full_step := CombatStrike.new(player,RunePlayer.CHARGED_HEAVY,1.65)
	full_step.step(.33,Vector3.FORWARD,4)
	check.call(swept_probe.hits == 0, "The raised charged preparation creates no speculative blade contact")
	full_step.step(.73,Vector3.FORWARD,4)
	full_step.step(.1,Vector3.FORWARD,4)
	check.call(swept_probe.hits == 1, "One large physics step sweeps the complete nonlinear 3D blade path once")
	check.call(distant_probe.hits == 0 and overhead_probe.hits == 0 and rear_probe.hits == 0, "Charged contact excludes the old extended proxy range, overhead and rear volumes")
	for probe in [swept_probe,distant_probe,overhead_probe,rear_probe]:
		probe.queue_free()
	var enemy := _enemy(fixture,world,Vector3(0,0,0))
	enemy.cooldown = 999.0
	enemy.set_physics_process(true)
	await _tick(tree)
	await _tick(tree)
	_ready_player(player,start)
	player.heavy_held = 0.65
	player.begin_attack(true,0)
	player.set_physics_process(true)
	for index in range(50):
		await _tick(tree)
		if not events.is_empty():
			break
	player.set_physics_process(false)
	enemy.set_physics_process(false)
	check.call(events.size() == 1 and amounts.size() == 1 and absf(enemy.health-25.7) < 0.001, "A charged sweep confirms exactly one 69.3 damage hit against the 95HP melee target")
	if not events.is_empty():
		var impact: Dictionary = events[0]
		check.call(impact.attack_id == "charged_heavy" and impact.strength == "charged" and impact.source == "player" and int(impact.attack_instance_id) > 0 and int(impact.attack_instance_id) <= CombatStrike.MAX_SAFE_ATTACK_SERIAL and int(impact.attack_instance_id) == player.strike.attack_instance_id, "Confirmed context identifies the real charged strike with a positive JS-safe serial and no object references")
		var blade_nearest := Geometry3D.get_closest_point_to_segment(impact.point,impact.contact_blade_grip,impact.contact_blade_tip)
		check.call(impact.contact_source == "hurtbox_ray" and absf(Vector3(impact.normal).length()-1.0) < .001 and Vector3(impact.point).distance_to(blade_nearest) <= .121 and float(impact.contact_phase) > 0.0, "Confirmed surface point is within the physical blade radius rather than an invented chest-height impact")
		var grip_marker := player.visual.rig_weapon.find_child("GripOrigin",true,false) as Node3D
		var tip_marker := player.visual.rig_weapon.find_child("BladeTip",true,false) as Node3D
		var drawn_nearest := Geometry3D.get_closest_point_to_segment(impact.point,grip_marker.global_position,tip_marker.global_position)
		var contact_time := .34+.18*float(impact.contact_phase)
		contact_proof = {
			"contact_observed":true, "attack_id":String(impact.attack_id), "attack_instance_id":int(impact.attack_instance_id),
			"contact_source":String(impact.contact_source), "contact_phase":float(impact.contact_phase),
			"query_contact_time":contact_time, "event_attack_elapsed":float(impact.attack_elapsed),
			"final_authoritative_elapsed":player.strike.elapsed, "final_drawn_sampled_time":player.visual.skeletal_bridge.sampled_time,
			"point_world":_xyz(impact.point), "normal_world":_xyz(impact.normal),
			"query_blade_grip_world":_xyz(impact.contact_blade_grip), "query_blade_tip_world":_xyz(impact.contact_blade_tip),
			"final_drawn_grip_world":_xyz(grip_marker.global_position), "final_drawn_tip_world":_xyz(tip_marker.global_position),
			"query_point_to_segment_m":Vector3(impact.point).distance_to(blade_nearest),
			"final_drawn_point_to_segment_m":Vector3(impact.point).distance_to(drawn_nearest), "drawn_contact_limit_m":.125,
		}
		check.call(absf(float(impact.attack_elapsed)-contact_time) < .0001 and absf(player.strike.elapsed-contact_time) < .0001 and absf(player.visual.skeletal_bridge.sampled_time-contact_time) < .001, "Confirmed event, authoritative attack and final drawn pose freeze at the first contact sample")
		check.call(Vector3(impact.point).distance_to(drawn_nearest) <= .125, "The final displayed GripOrigin-to-BladeTip segment actually touches the confirmed surface point within 0.125m")
		check.call(not impact.blocked and not impact.killed and impact.poise_broken and impact.reaction == "heavy_hit" and is_equal_approx(float(impact.reaction_duration),0.48), "The surviving charged target resolves its poise break and separate 0.48s strong reaction")
		check.call(is_equal_approx(float(impact.health_before),95) and is_equal_approx(float(impact.health_after),25.7) and is_equal_approx(float(impact.victim_pause),.075) and is_equal_approx(player.hit_pause,.075), "Confirmed outcome records real health and symmetric 75ms hitstop")
	var held_strike := player.strike
	var attack_clock := held_strike.elapsed if held_strike != null else -1.0
	var hit_clock := float(enemy.presentation_snapshot().hit_elapsed)
	var attacker_position := player.global_position
	var victim_position := enemy.global_position
	var attacker_bones := _bones(player.visual)
	var victim_bones := _bones(enemy.visual)
	var frozen_trail := player.visual.blade_trail
	var frozen_trail_mesh := frozen_trail.mesh
	var frozen_trail_samples: Array = frozen_trail._samples.duplicate(true)
	var trail_ages_before: Array[float] = []
	for sample in frozen_trail_samples:
		trail_ages_before.append(float(sample.age))
	contact_proof["trail_before_stop"] = {"samples":frozen_trail_samples.size(), "visible":frozen_trail.visible,
		"triangles":int(frozen_trail.presentation_report().triangles), "ages_s":trail_ages_before}
	check.call(frozen_trail_samples.size() >= 2 and frozen_trail.visible and frozen_trail.mesh != null, "The live confirmed active sample preserves a visible nonempty blade trail before hitstop")
	player.invulnerability = .25
	player.dodge_cooldown = .4
	player.parry_cooldown = .3
	var frozen_invulnerability := player.invulnerability
	Input.action_press("light")
	Input.action_release("light")
	player.set_physics_process(true)
	enemy.set_physics_process(true)
	for index in range(3):
		await _tick(tree)
	player.set_physics_process(false)
	enemy.set_physics_process(false)
	check.call(held_strike != null and player.strike == held_strike and is_equal_approx(held_strike.elapsed,attack_clock) and is_equal_approx(float(enemy.presentation_snapshot().hit_elapsed),hit_clock), "Actual physics frames freeze both attack and victim reaction clocks during hitstop")
	check.call(player.global_position.is_equal_approx(attacker_position) and enemy.global_position.is_equal_approx(victim_position), "Both actual actor roots remain still during hitstop")
	check.call(_same_bones(attacker_bones,_bones(player.visual)) and _same_bones(victim_bones,_bones(enemy.visual)), "Both complete production skeleton poses remain frozen during hitstop")
	check.call(frozen_trail.mesh == frozen_trail_mesh and frozen_trail._samples == frozen_trail_samples and frozen_trail.visible, "Hitstop retains the exact trail vertices and ages instead of clearing the live contact as an editor seek")
	var trail_ages_after: Array[float] = []
	for sample in frozen_trail._samples:
		trail_ages_after.append(float(sample.age))
	contact_proof["after_three_physics_frames"] = {
		"attack_elapsed":held_strike.elapsed if held_strike != null else -1.0,
		"victim_hit_elapsed":float(enemy.presentation_snapshot().hit_elapsed),
		"attack_clock_unchanged":held_strike != null and is_equal_approx(held_strike.elapsed,attack_clock),
		"victim_clock_unchanged":is_equal_approx(float(enemy.presentation_snapshot().hit_elapsed),hit_clock),
		"actor_roots_unchanged":player.global_position.is_equal_approx(attacker_position) and enemy.global_position.is_equal_approx(victim_position),
		"complete_skeletons_unchanged":_same_bones(attacker_bones,_bones(player.visual)) and _same_bones(victim_bones,_bones(enemy.visual)),
		"trail_samples":frozen_trail._samples.size(), "trail_visible":frozen_trail.visible, "trail_ages_s":trail_ages_after,
		"trail_mesh_unchanged":frozen_trail.mesh == frozen_trail_mesh,
		"trail_samples_and_ages_unchanged":frozen_trail._samples == frozen_trail_samples,
	}
	_write_contact_proof(contact_proof)
	frozen_trail_mesh = null
	check.call(is_equal_approx(player.invulnerability,frozen_invulnerability) and is_equal_approx(player.dodge_cooldown,.4) and is_equal_approx(player.parry_cooldown,.3), "Hitstop freezes defensive clocks rather than granting early dodge or parry readiness")
	check.call(player.input_buffer > 0.0 and not player.buffered_heavy, "A short attack tap during hitstop remains buffered without executing an action")
	player.input_buffer = 0.0
	player.set_physics_process(true)
	enemy.set_physics_process(true)
	for index in range(100):
		await _tick(tree)
		if enemy.hit_pause <= 0.0 and enemy.recoil_remaining <= 0.0:
			enemy.set_physics_process(false)
		if player.strike == null:
			break
	player.set_physics_process(false)
	enemy.set_physics_process(false)
	var hit_travel := Vector2(player.global_position.x-start.x,player.global_position.z-start.z).length()
	check.call(absf(hit_travel-miss_travel) < 0.008 and absf(hit_travel-.576) < .008, "Confirmed hitstop preserves active travel instead of dropping a contact tick or jumping after stop")
	check.call(events.size() == 1 and amounts.size() == 1, "Remaining active and recovery frames cannot emit a second confirmed hit")
	check.call(absf(Vector2(enemy.recoil_displacement.x,enemy.recoil_displacement.z).length()-.35) < .008, "A strong reaction resolves approximately 0.35m of actual collision-motor recoil on open floor")
	var shield := _enemy(fixture,world,Vector3(8,0,0),"shield")
	shield.facing = Vector3.BACK
	shield.receive_hit(18,14,shield.global_position+Vector3.BACK*2,true,{"attack_id":"light_1","strength":"light"})
	check.call(absf(shield.health-(shield.max_health-5.4)) < .001 and bool(events[-1].blocked) and events[-1].reaction == "none" and shield.recoil_remaining == 0, "A frontal light still deals 30 percent through a shield without a strong reaction or recoil")
	shield.hit_pause = 0.0
	shield.receive_hit(69.3,79.2,shield.global_position+Vector3.BACK*2,true,{"attack_id":"charged_heavy","strength":"charged"})
	check.call(not events[-1].blocked and events[-1].poise_broken and events[-1].reaction == "heavy_hit", "Charged poise retains the existing shield-bypass rule and reports its actual break")
	var boss := _enemy(fixture,world,Vector3(-8,0,0),"melee",true)
	boss.receive_hit(69.3,79.2,boss.global_position+Vector3.BACK*3,true,{"attack_id":"charged_heavy","strength":"charged"})
	check.call(boss.stagger == 0.0 and boss.recoil_remaining == 0.0 and not events[-1].poise_broken and events[-1].reaction == "none", "A charged hit cannot knock back or interrupt an unbroken boss")
	boss.hit_pause = 0.0
	boss.poise_meter = 150.0
	boss.receive_hit(69.3,79.2,boss.global_position+Vector3.BACK*3,true,{"attack_id":"charged_heavy","strength":"charged"})
	check.call(events[-1].poise_broken and is_equal_approx(boss.stagger,1.4) and boss.recoil_remaining > 0.0, "An actual boss poise break retains its 1.4s opening before allowing strong recoil")
	# A wall is deliberately within the requested recoil budget, but not touching
	# the initial capsule. The actual travel must stop short; no teleport fallback.
	enemy.global_position = fixture.global_position+Vector3(0,0,-6)
	enemy.health = 95
	enemy.hit_pause = 0.0
	enemy.stagger = 0.0
	_body(fixture,Vector3(0,1,-6.7),Vector3(4,2,.2))
	await _tick(tree)
	await _tick(tree)
	enemy.receive_hit(69.3,79.2,enemy.global_position+Vector3.BACK*2,true,{"attack_id":"charged_heavy","strength":"charged"})
	enemy.set_physics_process(true)
	for index in range(35):
		await _tick(tree)
		if enemy.hit_pause <= 0.0 and enemy.recoil_remaining <= 0.0:
			break
	enemy.set_physics_process(false)
	var wall_travel := Vector2(enemy.recoil_displacement.x,enemy.recoil_displacement.z).length()
	check.call(wall_travel > .08 and wall_travel < .24 and enemy.global_position.z >= fixture.global_position.z-6.21, "Real CharacterBody wall collision truncates requested recoil without crossing the wall")
	check.call(is_equal_approx(float(events[-1].requested_recoil_m),.35) and absf(wall_travel-.35) > .05, "Confirmed requested recoil is distinguished from measured resolved travel")
	var kill_before := events.size()
	enemy.hit_pause = 0.0
	enemy.receive_hit(1000,1000,enemy.global_position+Vector3.BACK*2)
	enemy.receive_hit(1000,1000,enemy.global_position+Vector3.BACK*2)
	check.call(events.size() == kill_before+1 and events[-1].killed and float(events[-1].health_after) == 0.0, "Legacy four-argument damage still resolves one kill and dead targets emit no further impact")
	player.impact_confirmed.disconnect(on_impact)
	player.landed_hit.disconnect(on_damage)
	fixture.queue_free()
	await tree.process_frame
	await tree.process_frame
	for field in PLAYER_FIELDS:
		player.set(field,saved[field])
	player.global_transform = saved_transform
	player.set_physics_process(saved_player_physics)
	world.set_physics_process(saved_world_physics)
	Session.shards = saved_shards
	Session.upgrades.assign(saved_upgrades)
	for record in old_enemies:
		if is_instance_valid(record.node):
			record.node.set_physics_process(bool(record.physics))
	for action in ACTIONS:
		if float(saved_actions[action]) > 0.0:
			Input.action_press(action,float(saved_actions[action]))
		else:
			Input.action_release(action)
	player.visual.pose(0.0,0.0,-1.0,false,false,player.dead,player.presentation_snapshot())
	return true
