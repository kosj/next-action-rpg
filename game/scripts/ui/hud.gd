class_name RuneHUD
extends CanvasLayer

const GOLD := Color("c6ab78")
const MINT := Color("87d5c9")
const INK := Color("0d1a22")
const WHITE := Color("eee8d9")
const WEIGHT_AXIS := 0x77676874 # OpenType 'wght', exported font defaults to weight 100.
var world: Node3D
var root: Control
var menu: Control
var hud: Control
var modal: Control
var health_bar: ProgressBar
var rune_bar: ProgressBar
var health_text: Label
var rune_text: Label
var region_text: Label
var objective_text: Label
var counter_text: Label
var potion_text: Label
var combo_text: Label
var boss_box: Control
var boss_bar: ProgressBar
var boss_title: Label
var interaction: Label
var toast_label: Label
var banner_title: Label
var banner_subtitle: Label
var debug_text: Label
var lock_marker: Label
var toast_time: float = 0
var banner_time: float = 0
var damage_numbers: Array[Dictionary] = []
var qa_enabled: bool = false
var qa_clock: float = 0.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	root = Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	var theme := Theme.new()
	var font := FontVariation.new()
	font.base_font = preload("res://assets/fonts/NotoSansKR.ttf")
	font.variation_opentype = {WEIGHT_AXIS: 430.0}
	theme.default_font = font
	theme.default_font_size = 16
	theme.set_color("font_color", "Label", WHITE)
	theme.set_color("font_color", "Button", WHITE)
	theme.set_color("font_hover_color", "Button", MINT)
	theme.set_stylebox("normal", "Button", style(Color(0.045,0.09,0.11,0.88), Color("43534f")))
	theme.set_stylebox("hover", "Button", style(Color("1d393c"), GOLD))
	theme.set_stylebox("focus", "Button", style(Color(0,0,0,0), MINT))
	theme.set_stylebox("pressed", "Button", style(Color("294448"), MINT))
	root.theme = theme
	build_hud()
	show_title()
	Session.notification.connect(toast)
	if OS.has_feature("web"):
		qa_enabled = bool(JavaScriptBridge.eval("new URLSearchParams(window.location.search).has('qa')"))

func style(background: Color, border: Color = Color.TRANSPARENT) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = background
	box.border_color = border
	box.set_border_width_all(1)
	box.content_margin_left = 20
	box.content_margin_right = 20
	box.content_margin_top = 13
	box.content_margin_bottom = 13
	return box

func label(text: String, size: int = 16, color: Color = WHITE) -> Label:
	var node := Label.new()
	node.text = text
	node.add_theme_font_size_override("font_size", size)
	node.add_theme_color_override("font_color", color)
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return node

func place(control: Control, parent: Node, point: Vector2, size: Vector2) -> void:
	parent.add_child(control)
	control.position = point
	control.size = size

func anchored(control: Control, preset: int, point: Vector2, dimensions: Vector2) -> void:
	control.set_anchors_and_offsets_preset(preset)
	control.offset_left = point.x
	control.offset_top = point.y
	control.offset_right = point.x + dimensions.x
	control.offset_bottom = point.y + dimensions.y

func button(text: String, callback: Callable, parent: Node) -> Button:
	var node := Button.new()
	node.text = text
	node.custom_minimum_size = Vector2(0, 48)
	node.pressed.connect(callback)
	parent.add_child(node)
	return node

func bar(color: Color) -> ProgressBar:
	var node := ProgressBar.new()
	node.show_percentage = false
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var background := StyleBoxFlat.new()
	background.bg_color = Color(0.02,0.05,0.06,0.8)
	background.border_color = Color("4e5955")
	background.set_border_width_all(1)
	var fill := StyleBoxFlat.new()
	fill.bg_color = color
	node.add_theme_stylebox_override("background", background)
	node.add_theme_stylebox_override("fill", fill)
	return node

func build_hud() -> void:
	hud = Control.new()
	hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(hud)
	place(label("R U N E F A L L", 18, GOLD), hud, Vector2(42,30), Vector2(300,35))
	region_text = label("순례자의 안식처", 26)
	place(region_text, hud, Vector2(42,65), Vector2(500,45))
	place(label("CHAPTER I  /  무너진 성역", 12, Color("9badae")), hud, Vector2(43,110), Vector2(400,24))
	var stats := Control.new()
	hud.add_child(stats)
	anchored(stats, Control.PRESET_BOTTOM_LEFT, Vector2(42,-160), Vector2(400,160))
	place(label("LYRA  /  리라", 16, GOLD), stats, Vector2.ZERO, Vector2(180,30))
	health_text = label("120 / 120", 13)
	place(health_text, stats, Vector2(225,6), Vector2(150,25))
	health_bar = bar(Color("b88470"))
	place(health_bar, stats, Vector2(0,38), Vector2(340,12))
	rune_bar = bar(MINT)
	place(rune_bar, stats, Vector2(0,60), Vector2(340,6))
	rune_text = label("RUNE  35 / 100", 11, MINT)
	place(rune_text, stats, Vector2(0,76), Vector2(180,25))
	potion_text = label("R  회복  3", 13)
	place(potion_text, stats, Vector2(215,76), Vector2(200,25))
	var mission := VBoxContainer.new()
	hud.add_child(mission)
	anchored(mission, Control.PRESET_TOP_RIGHT, Vector2(-330,38), Vector2(288,100))
	mission.add_child(label("CURRENT OBJECTIVE", 11, GOLD))
	objective_text = label("성역의 봉인을 되찾으세요", 16)
	mission.add_child(objective_text)
	counter_text = label("성역 정화  0 / 7", 12, Color("a2b9b5"))
	mission.add_child(counter_text)
	var skills := HBoxContainer.new()
	hud.add_child(skills)
	anchored(skills, Control.PRESET_BOTTOM_RIGHT, Vector2(-390,-122), Vector2(348,84))
	skills.add_theme_constant_override("separation", 12)
	for index in range(3):
		var box := PanelContainer.new()
		box.add_theme_stylebox_override("panel", style(Color(0.04,0.09,0.11,0.85), Color("5c7067")))
		var column := VBoxContainer.new()
		box.add_child(column)
		var title := label(["1  섬광", "2  폭풍", "3  심판"][index], 15, GOLD)
		column.add_child(title)
		column.add_child(label(["25 RUNE", "45 RUNE", "80 RUNE"][index], 10, MINT))
		skills.add_child(box)
	var hint := label("LMB 공격  ·  RMB 강공격  ·  SPACE 회피  ·  F 패링  ·  TAB 고정", 11, Color("aabdb8"))
	hud.add_child(hint)
	anchored(hint, Control.PRESET_BOTTOM_RIGHT, Vector2(-485,-42), Vector2(450,25))
	combo_text = label("", 42, GOLD)
	place(combo_text, hud, Vector2(44,260), Vector2(250,70))
	boss_box = VBoxContainer.new()
	hud.add_child(boss_box)
	anchored(boss_box, Control.PRESET_CENTER_TOP, Vector2(-265,32), Vector2(530,60))
	boss_title = label("성역의 파수꾼, 아스테르", 17, GOLD)
	boss_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	boss_box.add_child(boss_title)
	boss_bar = bar(Color("b07861"))
	boss_bar.custom_minimum_size = Vector2(530,8)
	boss_box.add_child(boss_bar)
	boss_box.hide()
	interaction = label("", 18, GOLD)
	hud.add_child(interaction)
	anchored(interaction, Control.PRESET_CENTER_BOTTOM, Vector2(-300,-225), Vector2(600,40))
	interaction.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	lock_marker = label("◇", 35, GOLD)
	hud.add_child(lock_marker)
	toast_label = label("", 15, MINT)
	toast_label.z_index = 20
	root.add_child(toast_label)
	anchored(toast_label, Control.PRESET_CENTER_BOTTOM, Vector2(-430,-180), Vector2(860,36))
	toast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner_title = label("", 36, WHITE)
	root.add_child(banner_title)
	anchored(banner_title, Control.PRESET_CENTER_TOP, Vector2(-450,160), Vector2(900,65))
	banner_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner_subtitle = label("", 14, GOLD)
	root.add_child(banner_subtitle)
	anchored(banner_subtitle, Control.PRESET_CENTER_TOP, Vector2(-450,225), Vector2(900,40))
	banner_subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	debug_text = label("", 12, MINT)
	place(debug_text, hud, Vector2(42,155), Vector2(500,70))
	debug_text.hide()

func show_title() -> void:
	hud.hide()
	if is_instance_valid(menu):
		menu.queue_free()
	menu = Control.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(menu)
	var shade := ColorRect.new()
	shade.color = Color(0.02,0.045,0.06,0.65)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu.add_child(shade)
	var column := VBoxContainer.new()
	place(column, menu, Vector2(90,135), Vector2(570,650))
	column.add_theme_constant_override("separation", 14)
	column.add_child(label("A  R U N E B O U N D  C H R O N I C L E", 12, GOLD))
	column.add_child(label("R U N E F A L L", 52, WHITE))
	column.add_child(label("무너진 성역", 24, GOLD))
	var description := label("빛이 사라진 자리, 검에 새겨진 마지막 서약.\n몰락한 성역으로 돌아가 잠든 수호자를 깨우세요.", 17, Color("bac7c1"))
	description.custom_minimum_size.y = 100
	column.add_child(description)
	if Session.has_save:
		button("여정 이어가기     →", func(): start_game(false), column).grab_focus()
	button("새로운 서약     →", func():
		if Session.has_save:
			show_dialog("새로운 서약", "NEW JOURNEY", "기존 진행을 초기화하고 성역 입구에서 시작합니다.", [{"text":"취소", "call":close_modal}, {"text":"새로 시작", "call":func(): close_modal(); start_game(true)}])
		else:
			start_game(true), column)
	button("조작 안내", show_help, column)
	button("환경 설정", show_settings, column)
	column.add_child(label("CHAPTER I · PLAYABLE PROTOTYPE\n" + Session.build_id, 11, Color("91a49d")))
	var footer := label("하나의 검. 일곱 개의 봉인. 끝나지 않은 서약.", 13, GOLD)
	place(footer, menu, Vector2(90,825), Vector2(1000,30))
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func start_game(fresh: bool) -> void:
	if not world.start_game(fresh):
		return
	menu.hide()
	hud.show()

func show_dialog(title: String, subtitle: String, body: String, actions: Array[Dictionary]) -> void:
	close_modal(false)
	world.set_paused(true)
	modal = Control.new()
	modal.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(modal)
	var shade := ColorRect.new()
	shade.color = Color(0.01,0.025,0.03,0.8)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	modal.add_child(shade)
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	modal.add_child(center)
	var panel := PanelContainer.new()
	center.add_child(panel)
	panel.custom_minimum_size = Vector2(700,530)
	panel.add_theme_stylebox_override("panel", style(INK, GOLD))
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	panel.add_child(column)
	column.add_child(label(subtitle, 12, GOLD))
	column.add_child(label(title, 30))
	var text := label(body, 17, Color("bfcac3"))
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.custom_minimum_size = Vector2(630,150)
	text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(text)
	for action in actions:
		button(action.text, action.call, column)
	if actions.size() > 0:
		column.get_child(column.get_child_count()-actions.size()).grab_focus()

func close_modal(resume: bool = true) -> void:
	if is_instance_valid(modal):
		modal.queue_free()
		modal = null
	if resume:
		world.set_paused(false)

func show_help() -> void:
	show_dialog("검에 새긴 서약", "CONTROLS", "WASD 이동 · 마우스 시점 · SHIFT 달리기\n좌클릭 연속 공격 · 우클릭 강공격 (길게 눌러 차지)\nSPACE 회피 · F 패링 · TAB 대상 고정/해제\n1 / 2 / 3 룬 스킬 · R 회복 · E 상호작용 · ESC 일시정지\n\n패드: 왼쪽 스틱 이동 · 오른쪽 스틱 시점 · X 약공격 · Y 강공격\nA 회피 · LB 패링 · B 상호작용 · RS 대상 고정\n방향키 ↑ 회복 · ←/→/↓ 스킬 · START 일시정지\n\n공격을 맞히면 룬 게이지가 회복됩니다.\n방패는 강공격으로 무너뜨리고, 적의 빛나는 공격 예고를 읽으세요.", [{"text":"확인", "call":close_modal}])

func show_pause() -> void:
	show_dialog("잠시 멈춘 여정", "PAUSED", "체크포인트에서 체력과 회복약을 보충할 수 있습니다.\n진행은 체크포인트·강화·전투 완료 시 자동 저장됩니다.", [{"text":"계속하기", "call":close_modal}, {"text":"환경 설정", "call":show_settings}, {"text":"조작 안내", "call":show_help}, {"text":"타이틀로", "call":func(): close_modal(); world.return_to_title(); show_title()}])

func show_settings() -> void:
	show_dialog("환경 설정", "SETTINGS", "", [{"text":"완료", "call":func():
		if Session.save_game():
			close_modal()}])
	var column: VBoxContainer = modal.get_child(1).get_child(0).get_child(0)
	var volume_title := label("전체 음량", 17, GOLD)
	column.add_child(volume_title)
	column.move_child(volume_title, 2)
	var slider := HSlider.new()
	slider.max_value = 1.0
	slider.step = 0.05
	slider.value = Session.volume
	slider.custom_minimum_size.y = 35
	slider.value_changed.connect(func(value: float): Session.volume = value)
	column.add_child(slider)
	column.move_child(slider, 3)
	var shake := CheckButton.new()
	shake.text = "화면 흔들림"
	shake.button_pressed = Session.shake
	shake.toggled.connect(func(value: bool): Session.shake = value)
	column.add_child(shake)
	column.move_child(shake, 4)
	var quality := OptionButton.new()
	quality.add_item("균형 · 기본 해상도 / 그림자")
	quality.add_item("성능 · 낮은 해상도 / 그림자 끄기")
	quality.selected = Session.quality
	quality.item_selected.connect(func(index: int): Session.quality = index; world.apply_quality())
	column.add_child(quality)
	column.move_child(quality, 5)

func toast(text: String) -> void:
	toast_label.text = text
	toast_time = 4.0

func announce(title: String, subtitle: String = "") -> void:
	banner_title.text = title
	banner_subtitle.text = subtitle
	banner_time = 4.5

func floating_damage(amount: float, position_3d: Vector3) -> void:
	var node := label(str(roundi(amount)), 23 if amount < 50 else 31, WHITE if amount < 50 else GOLD)
	root.add_child(node)
	damage_numbers.append({"label":node, "point":position_3d, "time":0.0})

func _process(delta: float) -> void:
	toast_time = maxf(0, toast_time - delta)
	toast_label.modulate.a = minf(1, toast_time)
	banner_time = maxf(0, banner_time - delta)
	banner_title.modulate.a = minf(1, banner_time)
	banner_subtitle.modulate.a = minf(1, banner_time)
	if world == null or world.player == null:
		return
	var player: RunePlayer = world.player
	qa_clock += delta
	if qa_enabled and qa_clock >= 0.25:
		qa_clock = 0
		var rect := Rect2()
		if is_instance_valid(modal):
			rect = modal.get_child(1).get_child(0).get_global_rect()
		var buttons: Array[Dictionary] = []
		for control in root.find_children("*", "Button", true, false):
			if control.is_visible_in_tree() and not control.is_queued_for_deletion():
				var bounds: Rect2 = control.get_global_rect()
				var button_info := {"text":control.text, "kind":control.get_class(),
					"x":bounds.position.x,"y":bounds.position.y,"w":bounds.size.x,"h":bounds.size.y}
				if control is OptionButton:
					button_info["popup_visible"] = control.get_popup().visible
					button_info["popup_focus"] = control.get_popup().get_focused_item()
				buttons.append(button_info)
		var status := {"started":world.started, "paused":get_tree().paused,
			"has_save":Session.has_save, "checkpoint":Session.checkpoint,
			"ui_width":root.size.x,"ui_height":root.size.y,"buttons":buttons,
			"quality":Session.quality,"fps":Engine.get_frames_per_second(),
			"dead":player.dead, "health":player.health, "z":player.global_position.z,
			"encounter":world.active_encounter, "hits":player.combo_hits,
			"modal":is_instance_valid(modal), "modal_x":rect.position.x,"modal_y":rect.position.y,
			"modal_w":rect.size.x,"modal_h":rect.size.y,"hud_y":health_bar.global_position.y}
		JavaScriptBridge.eval("window.__RUNEFALL_STATE = " + JSON.stringify(status))
	health_bar.max_value = player.max_health
	health_bar.value = player.health
	rune_bar.max_value = player.max_rune
	rune_bar.value = player.rune
	health_text.text = "%d / %d" % [player.health,player.max_health]
	rune_text.text = "RUNE  %d / %d" % [player.rune, player.max_rune]
	potion_text.text = "R  회복  %d" % player.potions
	combo_text.text = "%02d  HITS" % player.combo_hits if player.combo_hits >= 2 else ""
	counter_text.text = "성역 정화  %d / 7     룬 조각 %d" % [Session.completed.size(),Session.shards]
	debug_text.text = "FPS %d · HP %.1f · RUNE %.1f\n%s  /  %s" % [Engine.get_frames_per_second(),player.health,player.rune,str(player.global_position),Session.build_id]
	boss_box.visible = is_instance_valid(world.boss) and not world.boss.dead
	if boss_box.visible:
		boss_bar.max_value = world.boss.max_health
		boss_bar.value = world.boss.health
		boss_title.text = "성역의 파수꾼, 아스테르" + ("  ·  해방" if world.boss.phase == 2 else "")
	lock_marker.visible = is_instance_valid(player.locked_target) and not player.locked_target.dead and hud.visible
	if lock_marker.visible:
		var point: Vector3 = player.locked_target.global_position + Vector3.UP * 1.5
		lock_marker.visible = not world.rig.camera.is_position_behind(point)
		lock_marker.position = world.rig.camera.unproject_position(point) - Vector2(16,28)
	for entry in damage_numbers.duplicate():
		entry.time += delta
		entry.point += Vector3.UP * delta * 0.9
		entry.label.position = world.rig.camera.unproject_position(entry.point)
		entry.label.visible = not world.rig.camera.is_position_behind(entry.point)
		entry.label.modulate.a = 1.0 - entry.time / 0.8
		if entry.time >= 0.8:
			entry.label.queue_free()
			damage_numbers.erase(entry)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		if is_instance_valid(modal):
			close_modal()
		elif world.started:
			show_pause()
		get_viewport().set_input_as_handled()
	if event.is_action_pressed("debug_overlay"):
		debug_text.visible = not debug_text.visible
