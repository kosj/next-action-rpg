extends Node3D

var sanctuary: Sanctuary
var player: RunePlayer
var rig: RuneCamera
var ui: RuneHUD
var boss: RuneEnemy
var started: bool = false
var active_encounter: int = -1
var active_enemies: Array[RuneEnemy] = []
var interaction_kind: String = ""
var interaction_index: int = -1
var last_region: int = -2
var lock_cooldown: float = 0.0
var play_seconds: float = 0.0
var impact_count: int = 0
var impact_spawn_count: int = 0
var impact_history: Array[Dictionary] = []

const LORE: Array[String] = [
	"이 성역의 룬은 빛을 만드는 것이 아니라, 어둠을 가두는 자물쇠였다.\n\n수호자 아스테르는 누구도 기억하지 못하는 서약을 지켰다.\n그의 검이 우리를 향한다면… 그가 지키는 것은 무엇일까?",
	"정원에 남은 이름들\n\n세라, 아린, 벨. 돌아오지 못한 순례자들의 이름이 돌에 새겨져 있다.\n너는 자신의 이름 아래 짧은 약속을 남겼다.\n\"문을 다시 열고, 모두를 집으로.\"",
	"마지막 파수꾼의 기록\n\n봉인을 닫으려면 살아 있는 룬 하나가 필요하다.\n나는 내 심장을 바쳤다.\n\n언젠가 이 검을 멈추러 오는 이여, 부디 망설이지 말기를."
]

func _ready() -> void:
	sanctuary = Sanctuary.new()
	add_child(sanctuary)
	player = RunePlayer.new()
	player.world = self
	add_child(player)
	player.position = Vector3(0,0.1,5)
	player.died.connect(_on_player_died)
	player.hurt.connect(func(): rig.shake_strength = 0.7)
	player.parried.connect(func():
		rig.shake_strength = 1.0
		spawn_ring(player.global_position + Vector3.UP, 3.0, Color("efd39b"))
		ui.toast("완벽한 패링 · 룬 +22"))
	player.landed_hit.connect(func(amount: float, point: Vector3):
		ui.floating_damage(amount, point))
	player.impact_confirmed.connect(_on_impact_confirmed)
	player.skill_effect.connect(spawn_ring)
	rig = RuneCamera.new()
	rig.player = player
	add_child(rig)
	ui = RuneHUD.new()
	ui.world = self
	add_child(ui)
	TouchControls.request_pause.connect(_on_touch_focus_lost)
	TouchControls.layout_changed.connect(apply_quality)
	apply_quality()
	# A complete headless scene load can be exercised without starting gameplay.
	if "--smoke" in OS.get_cmdline_user_args():
		var original_path := Session.save_path
		Session.save_path = "user://smoke_%d.json" % Time.get_ticks_usec()
		if not start_game(true):
			Session.save_path = original_path
			get_tree().quit(1)
			return
		ui.close_modal()
		await get_tree().physics_frame
		print("RUNEFALL_SMOKE_OK rooms=%d player_hp=%d" % [Sanctuary.CENTERS.size(),player.health])
		Audio.stop_all()
		await get_tree().create_timer(0.15).timeout
		await get_tree().process_frame
		await get_tree().process_frame
		for suffix in ["", ".bak", ".tmp", ".bak.tmp"]:
			DirAccess.remove_absolute(Session.save_path + suffix)
		Session.save_path = original_path
		get_tree().quit()

func _on_impact_confirmed(context: Dictionary) -> void:
	rig.apply_impact(context)
	Audio.play_impact(context)
	# A bounded presentation budget also covers radial attacks hitting a crowd.
	var effects: Array[Node] = []
	for active_effect in get_tree().get_nodes_in_group("impact_effects"):
		if not active_effect.is_queued_for_deletion():
			effects.append(active_effect)
	if effects.size() >= 8:
		effects[0].queue_free()
	var effect := RuneImpactEffect.new()
	add_child(effect)
	effect.setup(context, Session.quality)
	impact_spawn_count += 1
	impact_count += 1
	var observation := context.duplicate(true)
	observation["sequence"] = impact_count
	observation["physics_frame"] = Engine.get_physics_frames()
	observation["attacker_pause"] = player.hit_pause
	# Export values, never actor references or a writable command channel.
	for key in observation:
		if observation[key] is Vector3:
			var vector: Vector3 = observation[key]
			observation[key] = [vector.x, vector.y, vector.z]
	impact_history.append(observation)
	if impact_history.size() > 32:
		impact_history.pop_front()

func impact_presentation_report() -> Dictionary:
	var active_effects: Array[Dictionary] = []
	for effect in get_tree().get_nodes_in_group("impact_effects"):
		if not effect.is_queued_for_deletion():
			active_effects.append(effect.presentation_report())
	return {"count":impact_count,"spawn_count":impact_spawn_count,"history":impact_history.duplicate(true),"effects":active_effects,"camera":rig.impact_report()}

func start_game(fresh: bool) -> bool:
	var restored := Session.new_game() if fresh else (Session.load_game() and Session.has_save)
	if not restored:
		ui.toast("저장할 수 없어 새 여정을 시작하지 않았습니다." if fresh else "이어갈 저장을 불러오지 못했습니다.")
		return false
	reset_encounter()
	started = true
	play_seconds = 0
	last_region = -2
	player.locked_target = null
	player.active = true
	if fresh:
		player.rune = 35.0
	player.restore(Sanctuary.CHECKPOINTS[Session.checkpoint] + Vector3.UP * 0.15)
	rig.cinematic = false
	rig.yaw = 0
	rig.snap()
	Audio.start()
	set_paused(false)
	ui.announce("무너진 성역", "CHAPTER I  ·  THE LAST VOW")
	if fresh:
		ui.show_dialog("마지막 서약", "PROLOGUE", "검사 리라, 너는 한때 이 성역의 순례자였다.\n\n사라진 동료들을 찾아 돌아왔지만, 문을 지키는 것은\n타락한 수호자와 꺼지지 않는 룬의 잔향뿐이다.\n\n일곱 봉인을 정화하고 성역의 심장에 도달하라.\n길가의 기록은 이곳에 남은 진실을 알려 줄 것이다.\n\n거점의 기록관과 대장장이에게 상호작용으로 말을 걸 수 있습니다.", [{"text":"성역으로 향한다", "call":ui.close_modal}])
	return true

func set_paused(value: bool) -> void:
	get_tree().paused = value
	TouchControls.set_gameplay_active(started and not value and not player.dead)
	if not value and started and is_instance_valid(player):
		player.discard_ui_actions()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if value or not started or TouchControls.available else Input.MOUSE_MODE_CAPTURED

func _on_touch_focus_lost() -> void:
	if started and not get_tree().paused and not player.dead:
		ui.show_pause()

func return_to_title() -> void:
	TouchControls.set_gameplay_active(false)
	started = false
	player.active = false
	reset_encounter()
	get_tree().paused = false
	rig.cinematic = true
	player.position = Vector3(0,0.1,5)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func reset_encounter() -> void:
	if is_instance_valid(player):
		player.locked_target = null
	for enemy in get_tree().get_nodes_in_group("enemies"):
		enemy.queue_free()
	for index in range(7):
		sanctuary.set_gates(index, false)
	active_enemies.clear()
	active_encounter = -1
	boss = null
	for child in get_children():
		if child is RuneProjectile:
			child.queue_free()
	for effect in get_tree().get_nodes_in_group("impact_effects"):
		effect.queue_free()

func _physics_process(delta: float) -> void:
	TouchControls.set_gameplay_active(started and not player.dead)
	if not started or player.dead:
		return
	play_seconds += delta
	lock_cooldown = maxf(0, lock_cooldown - delta)
	if not is_instance_valid(player.locked_target):
		player.locked_target = null
	else:
		if player.locked_target.dead or player.global_position.distance_to(player.locked_target.global_position) > 28:
			player.locked_target = null
	var closest: int = -1
	var best: float = 30
	for index in range(7):
		var distance := player.global_position.distance_to(Sanctuary.CENTERS[index])
		if distance < best:
			best = distance
			closest = index
		var inside := absf(player.global_position.z-Sanctuary.CENTERS[index].z) < 18.5 and absf(player.global_position.x-Sanctuary.CENTERS[index].x) < 21.0
		if inside and active_encounter < 0 and index not in Session.completed:
			# Encounters are sequential, including after loading an earlier checkpoint.
			var allowed := true
			for previous in range(index):
				if previous not in Session.completed:
					allowed = false
			if allowed:
				begin_encounter(index)
	if closest != last_region:
		last_region = closest
		ui.region_text.text = "순례자의 안식처" if closest < 0 else Sanctuary.TITLES[closest]
	update_interaction()
	if active_encounter >= 0:
		var count := 0
		for enemy in active_enemies:
			if is_instance_valid(enemy) and not enemy.dead:
				count += 1
		ui.objective_text.text = "봉인의 수호자를 물리치세요 · %d" % count
	else:
		ui.objective_text.text = "성역이 다시 빛납니다" if Session.completed.size() == 7 else "다음 봉인으로 향하세요"

func _unhandled_input(event: InputEvent) -> void:
	if not started or get_tree().paused or player.dead:
		return
	if event is InputEventMouseButton and event.pressed and event.device != InputEvent.DEVICE_ID_EMULATION and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		# A physical mouse still works on a touch-capable laptop. Touch-emulated
		# mouse events never request pointer lock on a phone.
		var can_capture: bool = not OS.has_feature("web") or bool(JavaScriptBridge.eval("typeof document.getElementById('canvas').requestPointerLock === 'function'"))
		if can_capture:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
			get_viewport().set_input_as_handled()
	if TouchControls.event_pressed(event, "lock_on") and lock_cooldown <= 0:
		player.locked_target = null if is_instance_valid(player.locked_target) else nearest_enemy(player.global_position, 24)
		lock_cooldown = 0.25
	if TouchControls.event_pressed(event, "target_next"):
		var next := nearest_enemy(player.global_position, 24, player.locked_target)
		if next != null:
			player.locked_target = next
	if TouchControls.event_pressed(event, "interact") and interaction_kind != "":
		interact()

func nearest_enemy(point: Vector3, radius: float, exclude: Node3D = null) -> RuneEnemy:
	var result: RuneEnemy
	var best := radius
	for enemy in get_tree().get_nodes_in_group("enemies"):
		if enemy.dead or enemy.is_queued_for_deletion() or enemy == exclude:
			continue
		var distance: float = point.distance_to(enemy.global_position)
		if distance < best:
			best = distance
			result = enemy
	return result

func can_enemy_attack(candidate: RuneEnemy) -> bool:
	var attackers := 0
	for enemy in active_enemies:
		if is_instance_valid(enemy) and enemy != candidate and not enemy.dead and (enemy.strike != null or enemy.burst_time > 0):
			attackers += 1
	return attackers < 2

func begin_encounter(index: int) -> void:
	active_encounter = index
	active_enemies.clear()
	sanctuary.set_gates(index, true)
	announce(Sanctuary.TITLES[index], "SEAL %02d  /  07" % (index+1))
	var compositions: Array = [
		["melee", "melee", "melee"],
		["melee", "melee", "melee", "ranged"],
		["shield", "shield", "melee", "melee", "ranged"],
		["ranged", "ranged", "melee", "melee", "melee"],
		["shield", "ranged", "ranged", "melee", "elite"],
		["melee", "melee", "melee", "shield", "shield", "ranged", "ranged"],
		["boss"]]
	var list: Array = compositions[index]
	for slot in range(list.size()):
		var enemy := RuneEnemy.new()
		enemy.kind = "melee" if list[slot] in ["boss", "elite"] else list[slot]
		enemy.is_boss = list[slot] == "boss"
		enemy.elite = list[slot] == "elite"
		enemy.player = player
		enemy.world = self
		enemy.position = Sanctuary.CENTERS[index] + Vector3(sin(slot * TAU/list.size()) * 6.0, 0.1, -4.0 + cos(slot * TAU/list.size()) * 4.0)
		add_child(enemy)
		enemy.defeated.connect(_on_enemy_defeated)
		active_enemies.append(enemy)
		if enemy.is_boss:
			boss = enemy
	if index == 0:
		ui.toast("좌클릭을 연결해 콤보 · SPACE 회피 · TAB 적 고정")
	elif index == 2:
		ui.toast("방패는 우클릭 강공격 또는 룬 스킬로 무너뜨리세요.")
	elif index == 6:
		ui.toast("수호자의 원형 충격파는 패링할 수 없습니다. 회피로 피하세요.")

func _on_enemy_defeated(_enemy: RuneEnemy) -> void:
	for enemy in active_enemies:
		if is_instance_valid(enemy) and not enemy.dead:
			return
	var finished := active_encounter
	if finished < 0:
		return
	Session.completed.append(finished)
	Session.shards += 20
	Session.save_game()
	sanctuary.set_gates(finished, false)
	active_encounter = -1
	player.rune = minf(player.max_rune, player.rune + 20)
	announce("봉인 정화", "SEAL RESTORED  ·  룬 조각 +20")
	Audio.play_sound("rune")
	if finished == 6:
		chapter_complete.call_deferred()

func chapter_complete() -> void:
	await get_tree().create_timer(2.0).timeout
	if not started or player.dead:
		return
	ui.show_dialog("서약은 빛으로 남는다", "CHAPTER I · COMPLETE", "아스테르의 검이 멈추고, 성역에 처음으로 새벽이 스며든다.\n\n그가 지키던 것은 어둠이 아니라, 그 안에 갇힌 사람들의 이름이었다.\n리라는 룬검에 새로운 이름을 새긴다.\n\"이제 내가 문을 지킬게.\"\n\n첫 챕터를 완료했습니다. 성역을 자유롭게 탐험할 수 있습니다.\n플레이 시간 %.1f분 · 발견한 기록 %d / 3" % [play_seconds/60.0,Session.lore_found.size()], [{"text":"성역에 머무르기", "call":ui.close_modal}, {"text":"타이틀로", "call":func(): ui.close_modal(); return_to_title(); ui.show_title()}])

func _interaction_hint() -> String:
	return "상호작용" if TouchControls.available else "E"

func update_interaction() -> void:
	interaction_kind = ""
	interaction_index = -1
	ui.interaction.text = ""
	if active_encounter >= 0:
		return
	for index in range(3):
		if player.global_position.distance_to(Sanctuary.CHECKPOINTS[index] + Vector3(2,0,0)) < 3.5:
			if index > 0 and (1 if index == 1 else 4) not in Session.completed:
				continue
			interaction_kind = "checkpoint"
			interaction_index = index
			ui.interaction.text = _interaction_hint() + "  ·  룬의 안식처 — 휴식 / 강화"
	for index in range(2):
		if player.global_position.distance_to(sanctuary.npc_positions[index]) < 3:
			interaction_kind = "npc"
			interaction_index = index
			ui.interaction.text = _interaction_hint() + "  ·  " + ("기록관 에린" if index == 0 else "대장장이 로엔")
	for index in range(3):
		if player.global_position.distance_to(sanctuary.lore_positions[index]) < 2.8:
			interaction_kind = "lore"
			interaction_index = index
			ui.interaction.text = _interaction_hint() + "  ·  성역의 기록" + (" ✓" if index in Session.lore_found else "")

func interact() -> void:
	match interaction_kind:
		"checkpoint":
			var previous_checkpoint := Session.checkpoint
			Session.checkpoint = interaction_index
			if not Session.save_game():
				Session.checkpoint = previous_checkpoint
				return
			player.restore(Sanctuary.CHECKPOINTS[interaction_index] + Vector3.UP * 0.15)
			Audio.play_sound("rune")
			show_upgrades("룬의 안식처", "체력과 회복약이 보충되었습니다.\n룬 조각으로 검에 새로운 힘을 새길 수 있습니다.")
		"npc":
			if interaction_index == 0:
				ui.show_dialog("돌아온 순례자", "ERIN · THE ARCHIVIST", "리라… 정말 너구나.\n\n아스테르는 우리를 알아보지 못해. 그의 서약이 저주가 되어 버렸어.\n일곱 봉인을 되돌리면 성역의 심장에 닿을 수 있을 거야.\n\n거점의 수정과 길 위의 안식처에서 쉬어 가.\n숨겨진 두 기록도 찾아 줘. 우리가 잊은 진실이 있을 테니.", [{"text":"기억할게", "call":ui.close_modal}])
			else:
				show_upgrades("룬을 새기는 대장장이", "검은 주인의 의지를 기억하지.\n가져온 룬 조각을 내게 보여 줘. 쓸 만한 힘으로 바꿔 주지.")
		"lore":
			if interaction_index not in Session.lore_found:
				Session.lore_found.append(interaction_index)
				Session.shards += 25
				Session.save_game()
				Audio.play_sound("rune")
			ui.show_dialog("성역의 기록 %d" % (interaction_index+1), "ECHOES OF THE SANCTUARY", LORE[interaction_index], [{"text":"기록을 간직한다", "call":ui.close_modal}])

func show_upgrades(title: String, description: String) -> void:
	var actions: Array[Dictionary] = []
	var names: Array[String] = ["룬검 · 공격력 +15%", "생명의 서약 · 체력 +25", "룬의 그릇 · 게이지와 회복량 증가"]
	for index in range(3):
		var level := Session.upgrades[index]
		var text := "%s  [%d/3]  ·  %s" % [names[index],level,"완성" if level >= 3 else "%d 조각" % (35+level*25)]
		actions.append({"text":text, "call":func():
			if Session.upgrades[index] >= 3 or Session.shards < 35 + Session.upgrades[index] * 25:
				ui.toast("조각이 부족하거나 이미 완성한 룬입니다.")
			elif Session.buy_upgrade(index):
				player.refresh_stats()
				Audio.play_sound("rune")
			show_upgrades(title, description)})
	actions.append({"text":"여정을 계속한다", "call":ui.close_modal})
	ui.show_dialog(title, "RUNE FORGING  ·  보유 조각 %d" % Session.shards, description, actions)

func recover_from_fall() -> void:
	player.health = maxf(1.0, player.health - 20.0)
	var point := Sanctuary.CENTERS[active_encounter] + Vector3(0,0,12) if active_encounter >= 0 else Sanctuary.CHECKPOINTS[Session.checkpoint]
	player.global_position = point + Vector3.UP * 0.2
	player.velocity = Vector3.ZERO
	rig.snap()
	ui.toast("룬의 힘이 당신을 되돌렸습니다 · 체력 -20")

func _on_player_died() -> void:
	await get_tree().create_timer(1.3).timeout
	if not started:
		return
	ui.show_dialog("아직, 서약은 끝나지 않았다", "VOW UNBROKEN", "가장 최근에 쉬었던 안식처에서 다시 일어납니다.\n정화한 봉인과 강화한 룬은 유지됩니다.", [{"text":"다시 일어난다", "call":func():
		ui.close_modal()
		reset_encounter()
		player.restore(Sanctuary.CHECKPOINTS[Session.checkpoint] + Vector3.UP * 0.2)
		rig.snap()}, {"text":"타이틀로", "call":func(): ui.close_modal(); return_to_title(); ui.show_title()}])

func spawn_ring(point: Vector3, radius: float, color: Color) -> void:
	var effect := RuneEffect.new()
	effect.position = point + Vector3.UP * 0.06
	effect.radius = radius
	effect.color = color
	add_child(effect)

func telegraph(point: Vector3, radius: float, duration: float) -> void:
	var effect := RuneEffect.new()
	effect.position = point + Vector3.UP * 0.07
	effect.radius = radius
	effect.duration = duration
	effect.warning = true
	effect.color = Color("f29372")
	add_child(effect)

func spawn_projectile(point: Vector3, target: Vector3) -> void:
	var projectile := RuneProjectile.new()
	projectile.player = player
	projectile.position = point
	projectile.direction = (target-point).normalized()
	add_child(projectile)

func announce(title: String, subtitle: String) -> void:
	ui.announce(title, subtitle)

func apply_quality() -> void:
	var render_scale: float = (0.8 if OS.has_feature("web") else 1.0) if Session.quality == 0 else 0.65
	if TouchControls.available and OS.has_feature("web"):
		var ratio := float(JavaScriptBridge.eval("Math.max(1, window.devicePixelRatio || 1)"))
		# High-density phones retain sharp UI without rendering the whole 3D
		# scene at two or three times its CSS resolution in each dimension.
		render_scale = maxf(0.25, minf(render_scale, (1.0 if Session.quality == 0 else 0.8) / ratio))
	get_viewport().scaling_3d_scale = render_scale
	if sanctuary != null:
		for node in sanctuary.get_children():
			if node is DirectionalLight3D and node.light_energy > 1:
				node.shadow_enabled = Session.quality == 0
