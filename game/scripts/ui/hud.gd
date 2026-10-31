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
var brand_text: Label
var chapter_text: Label
var stats_box: Control
var stats_title: Label
var mission_box: VBoxContainer
var mission_title: Label
var skills_box: HBoxContainer
var keyboard_hint: Label
var title_column: VBoxContainer
var title_scroll: ScrollContainer
var title_footer: Label
var title_logo: Label
var title_description: Label
var modal_panel: PanelContainer
var modal_column: VBoxContainer
var modal_scroll: ScrollContainer
var modal_body: Label

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
	get_viewport().size_changed.connect(_apply_layout)
	TouchControls.layout_changed.connect(_apply_layout)
	_apply_layout.call_deferred()
	Session.notification.connect(toast)
	if OS.has_feature("web"):
		qa_enabled = bool(JavaScriptBridge.eval("new URLSearchParams(window.location.search).has('qa')"))

func style(background: Color, border: Color = Color.TRANSPARENT) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = background
	box.border_color = border
	box.set_border_width_all(1)
	box.content_margin_left = 12 if TouchControls.available else 20
	box.content_margin_right = 12 if TouchControls.available else 20
	box.content_margin_top = 8 if TouchControls.available else 13
	box.content_margin_bottom = 8 if TouchControls.available else 13
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
	if TouchControls.available:
		node.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		# Let ScrollContainer see button-start drags. SCROLL_BEGIN cancels
		# BaseButton's pending click once the gesture becomes a scroll.
		node.mouse_filter = Control.MOUSE_FILTER_PASS
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
	brand_text = label("R U N E F A L L", 18, GOLD)
	place(brand_text, hud, Vector2(42,30), Vector2(300,35))
	region_text = label("순례자의 안식처", 26)
	place(region_text, hud, Vector2(42,65), Vector2(500,45))
	chapter_text = label("CHAPTER I  /  무너진 성역", 12, Color("9badae"))
	place(chapter_text, hud, Vector2(43,110), Vector2(400,24))
	stats_box = Control.new()
	var stats := stats_box
	hud.add_child(stats)
	anchored(stats, Control.PRESET_BOTTOM_LEFT, Vector2(42,-160), Vector2(400,160))
	stats_title = label("LYRA  /  리라", 16, GOLD)
	place(stats_title, stats, Vector2.ZERO, Vector2(180,30))
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
	mission_box = VBoxContainer.new()
	var mission := mission_box
	hud.add_child(mission)
	anchored(mission, Control.PRESET_TOP_RIGHT, Vector2(-330,38), Vector2(288,100))
	mission_title = label("CURRENT OBJECTIVE", 11, GOLD)
	mission.add_child(mission_title)
	objective_text = label("성역의 봉인을 되찾으세요", 16)
	mission.add_child(objective_text)
	counter_text = label("성역 정화  0 / 7", 12, Color("a2b9b5"))
	mission.add_child(counter_text)
	skills_box = HBoxContainer.new()
	var skills := skills_box
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
	keyboard_hint = label("LMB 공격  ·  RMB 강공격  ·  SPACE 회피  ·  F 패링  ·  TAB 고정", 11, Color("aabdb8"))
	var hint := keyboard_hint
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

func _scroll_container() -> ScrollContainer:
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	scroll.follow_focus = true
	scroll.scroll_deadzone = 10
	return scroll

func _safe_rect() -> Rect2:
	var margins: Vector4 = TouchControls.safe_margins
	return Rect2(Vector2(margins.x+12, margins.y+12), Vector2(
		maxf(1, root.size.x-margins.x-margins.z-24),
		maxf(1, root.size.y-margins.y-margins.w-24)))

func _apply_layout() -> void:
	if not TouchControls.available or not is_instance_valid(root):
		return
	var safe := _safe_rect()
	var portrait := safe.size.x < 600
	# Reserve the thumb controls' lower zone, including the narrow four-row grid.
	brand_text.hide()
	chapter_text.hide()
	region_text.hide()
	stats_title.hide()
	mission_title.hide()
	skills_box.hide()
	keyboard_hint.hide()
	var stats_width := minf(286, safe.size.x-68)
	anchored(stats_box, Control.PRESET_TOP_LEFT, safe.position, Vector2(stats_width,78))
	anchored(health_text, Control.PRESET_TOP_LEFT, Vector2.ZERO, Vector2(stats_width-84,24))
	anchored(potion_text, Control.PRESET_TOP_LEFT, Vector2(stats_width-84,0), Vector2(84,24))
	anchored(health_bar, Control.PRESET_TOP_LEFT, Vector2(0,28), Vector2(stats_width,10))
	anchored(rune_bar, Control.PRESET_TOP_LEFT, Vector2(0,46), Vector2(stats_width,6))
	anchored(rune_text, Control.PRESET_TOP_LEFT, Vector2(0,56), Vector2(stats_width,24))
	for text in [health_text, rune_text, potion_text, objective_text, counter_text]:
		text.add_theme_font_size_override("font_size", 16)
	var mission_position := safe.position+Vector2(0,90) if portrait else safe.position+Vector2(stats_width+20,0)
	var mission_width := safe.size.x if portrait else maxf(1,safe.size.x-stats_width-88)
	anchored(mission_box, Control.PRESET_TOP_LEFT, mission_position, Vector2(mission_width,64))
	objective_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	counter_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	combo_text.add_theme_font_size_override("font_size", 22)
	anchored(combo_text, Control.PRESET_TOP_LEFT, safe.position+Vector2(0,148 if portrait else 82), Vector2(180,32))
	boss_title.add_theme_font_size_override("font_size", 16)
	boss_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	boss_bar.custom_minimum_size.x = 0
	var boss_width := minf(530,safe.size.x)
	anchored(boss_box, Control.PRESET_TOP_LEFT, Vector2(safe.get_center().x-boss_width/2,safe.position.y+(166 if portrait else 86)), Vector2(boss_width,42))
	var prompt_y := maxf(safe.position.y,safe.end.y-(252 if root.size.x < 380 else 236))
	interaction.add_theme_font_size_override("font_size", 16)
	interaction.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	anchored(interaction, Control.PRESET_TOP_LEFT, Vector2(safe.position.x,prompt_y), Vector2(safe.size.x,36))
	toast_label.add_theme_font_size_override("font_size", 16)
	toast_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	anchored(toast_label, Control.PRESET_TOP_LEFT, Vector2(safe.position.x,prompt_y-42), Vector2(safe.size.x,40))
	var banner_y := safe.position.y+(164 if portrait else 84)
	banner_title.add_theme_font_size_override("font_size", 22)
	banner_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	anchored(banner_title, Control.PRESET_TOP_LEFT, Vector2(safe.position.x,banner_y), Vector2(safe.size.x,32))
	banner_subtitle.add_theme_font_size_override("font_size", 16)
	banner_subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	anchored(banner_subtitle, Control.PRESET_TOP_LEFT, Vector2(safe.position.x,banner_y+32), Vector2(safe.size.x,28))
	anchored(debug_text, Control.PRESET_TOP_LEFT, safe.position+Vector2(0,190), Vector2(safe.size.x,60))
	if is_instance_valid(title_scroll):
		anchored(title_scroll, Control.PRESET_TOP_LEFT, safe.position, safe.size)
		title_column.add_theme_constant_override("separation", 10)
		title_column.custom_minimum_size = Vector2.ZERO
		title_description.custom_minimum_size.y = 64
		title_logo.add_theme_font_size_override("font_size", 32)
		title_footer.hide()
		for child in title_column.get_children():
			if child is Label:
				child.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
				if child != title_logo and child != title_description:
					child.add_theme_font_size_override("font_size", 16)
	if is_instance_valid(modal_panel):
		var center := modal.get_child(1) as CenterContainer
		center.offset_left = safe.position.x
		center.offset_top = safe.position.y
		center.offset_right = -TouchControls.safe_margins.z-12
		center.offset_bottom = -TouchControls.safe_margins.w-12
		modal_panel.custom_minimum_size = Vector2(minf(640,safe.size.x),minf(620,safe.size.y))
		modal_column.add_theme_constant_override("separation", 12)
		for child in modal_column.get_children():
			if child is Label:
				child.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
				child.custom_minimum_size.x = 0
				child.add_theme_font_size_override("font_size", 22 if child == modal_column.get_child(1) else 16)
		modal_body.custom_minimum_size = Vector2.ZERO
		modal_body.size_flags_vertical = Control.SIZE_FILL
		modal_body.visible = not modal_body.text.is_empty()

func _touch_copy(text: String) -> String:
	if not TouchControls.available:
		return text
	return text.replace("E  ·  ", "상호작용 버튼 · ").replace("E로", "상호작용 버튼으로").replace("좌클릭", "공격 버튼").replace("우클릭", "강공격 버튼").replace("SPACE", "회피 버튼").replace("TAB", "고정 버튼")

func _sync_touch_state() -> void:
	var active: bool = is_instance_valid(world) and world.started and hud.visible and not get_tree().paused and not is_instance_valid(modal)
	if active and is_instance_valid(world.player):
		active = not world.player.dead
	if TouchControls.gameplay_active != active:
		TouchControls.set_gameplay_active(active)

func show_title() -> void:
	hud.hide()
	TouchControls.set_gameplay_active(false)
	if is_instance_valid(menu):
		menu.queue_free()
	menu = Control.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(menu)
	var shade := ColorRect.new()
	shade.color = Color(0.02,0.045,0.06,0.65)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	menu.add_child(shade)
	title_column = VBoxContainer.new()
	var column := title_column
	title_scroll = null
	if TouchControls.available:
		title_scroll = _scroll_container()
		title_scroll.name = "TitleScroll"
		menu.add_child(title_scroll)
		title_scroll.add_child(column)
		column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	else:
		place(column, menu, Vector2(90,135), Vector2(570,650))
	column.add_theme_constant_override("separation", 14)
	column.add_child(label("A  R U N E B O U N D  C H R O N I C L E", 12, GOLD))
	title_logo = label("R U N E F A L L", 52, WHITE)
	column.add_child(title_logo)
	column.add_child(label("무너진 성역", 24, GOLD))
	title_description = label("빛이 사라진 자리, 검에 새겨진 마지막 서약.\n몰락한 성역으로 돌아가 잠든 수호자를 깨우세요.", 17, Color("bac7c1"))
	var description := title_description
	description.custom_minimum_size.y = 100
	column.add_child(description)
	if Session.has_save:
		var continue_button := button("여정 이어가기     →", func(): start_game(false), column)
		if not TouchControls.available:
			continue_button.grab_focus()
	button("새로운 서약     →", func():
		if Session.has_save:
			show_dialog("새로운 서약", "NEW JOURNEY", "기존 진행을 초기화하고 성역 입구에서 시작합니다.", [{"text":"취소", "call":close_modal}, {"text":"새로 시작", "call":func(): close_modal(); start_game(true)}])
		else:
			start_game(true), column)
	button("조작 안내", show_help, column)
	button("환경 설정", show_settings, column)
	column.add_child(label("CHAPTER I · PLAYABLE PROTOTYPE\n" + Session.build_id, 11, Color("91a49d")))
	title_footer = label("하나의 검. 일곱 개의 봉인. 끝나지 않은 서약.", 13, GOLD)
	var footer := title_footer
	place(footer, menu, Vector2(90,825), Vector2(1000,30))
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_apply_layout()

func start_game(fresh: bool) -> void:
	if not world.start_game(fresh):
		return
	menu.hide()
	hud.show()
	_sync_touch_state()

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
	modal_panel = PanelContainer.new()
	var panel := modal_panel
	center.add_child(panel)
	panel.custom_minimum_size = Vector2(700,530)
	panel.add_theme_stylebox_override("panel", style(INK, GOLD))
	modal_column = VBoxContainer.new()
	var column := modal_column
	column.add_theme_constant_override("separation", 16)
	modal_scroll = null
	if TouchControls.available:
		modal_scroll = _scroll_container()
		modal_scroll.name = "ModalScroll"
		panel.add_child(modal_scroll)
		modal_scroll.add_child(column)
		column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	else:
		panel.add_child(column)
	column.add_child(label(subtitle, 12, GOLD))
	column.add_child(label(title, 30))
	modal_body = label(_touch_copy(body), 17, Color("bfcac3"))
	var text := modal_body
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.custom_minimum_size = Vector2(630,150)
	text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(text)
	for action in actions:
		button(action.text, action.call, column)
	if actions.size() > 0 and not TouchControls.available:
		column.get_child(column.get_child_count()-actions.size()).grab_focus()
	_sync_touch_state()
	_apply_layout()

func close_modal(resume: bool = true) -> void:
	if is_instance_valid(modal):
		modal.queue_free()
		modal = null
		modal_panel = null
		modal_column = null
		modal_scroll = null
		modal_body = null
	if resume:
		world.set_paused(false)
	_sync_touch_state()

func show_help() -> void:
	if TouchControls.available:
		show_dialog("검에 새긴 서약", "CONTROLS", "왼쪽 스틱을 밀어 이동하고 달리기 버튼을 누르세요.\n화면 오른쪽의 빈 곳을 드래그하면 시점이 돌아갑니다.\n\n공격 버튼을 연결해 연속 공격을 펼치세요.\n강공격 버튼은 길게 눌러 힘을 모을 수 있습니다.\n회피 · 패링 · 고정 · 회복과 세 룬 스킬은 화면 버튼으로 사용합니다.\n\n사람이나 안식처 가까이에서 상호작용 버튼을 누르세요.\n상단의 일시정지 버튼으로 설정과 조작 안내를 열 수 있습니다.\n\n공격을 맞히면 룬 게이지가 회복됩니다.\n방패는 강공격으로 무너뜨리고 적의 공격 예고를 읽으세요.", [{"text":"확인", "call":close_modal}])
		return
	show_dialog("검에 새긴 서약", "CONTROLS", "WASD 이동 · 마우스 시점 · SHIFT 달리기\n좌클릭 연속 공격 · 우클릭 강공격 (길게 눌러 차지)\nSPACE 회피 · F 패링 · TAB 대상 고정/해제\n1 / 2 / 3 룬 스킬 · R 회복 · E 상호작용 · ESC 일시정지\n\n패드: 왼쪽 스틱 이동 · 오른쪽 스틱 시점 · X 약공격 · Y 강공격\nA 회피 · LB 패링 · B 상호작용 · RS 대상 고정\n방향키 ↑ 회복 · ←/→/↓ 스킬 · START 일시정지\n\n공격을 맞히면 룬 게이지가 회복됩니다.\n방패는 강공격으로 무너뜨리고, 적의 빛나는 공격 예고를 읽으세요.", [{"text":"확인", "call":close_modal}])

func show_pause() -> void:
	show_dialog("잠시 멈춘 여정", "PAUSED", "체크포인트에서 체력과 회복약을 보충할 수 있습니다.\n진행은 체크포인트·강화·전투 완료 시 자동 저장됩니다.", [{"text":"계속하기", "call":close_modal}, {"text":"환경 설정", "call":show_settings}, {"text":"조작 안내", "call":show_help}, {"text":"타이틀로", "call":func(): close_modal(); world.return_to_title(); show_title()}])

func show_settings() -> void:
	show_dialog("환경 설정", "SETTINGS", "", [{"text":"완료", "call":func():
		if Session.save_game():
			close_modal()}])
	var column := modal_column
	var volume_title := label("전체 음량", 17, GOLD)
	column.add_child(volume_title)
	column.move_child(volume_title, 2)
	var slider := HSlider.new()
	slider.max_value = 1.0
	slider.step = 0.05
	slider.value = Session.volume
	slider.custom_minimum_size.y = 48 if TouchControls.available else 35
	slider.value_changed.connect(func(value: float): Session.volume = value)
	column.add_child(slider)
	column.move_child(slider, 3)
	var shake := CheckButton.new()
	shake.text = "화면 흔들림"
	shake.button_pressed = Session.shake
	if TouchControls.available:
		shake.custom_minimum_size.y = 48
		shake.mouse_filter = Control.MOUSE_FILTER_PASS
	shake.toggled.connect(func(value: bool): Session.shake = value)
	column.add_child(shake)
	column.move_child(shake, 4)
	if TouchControls.available:
		var quality_title := label("화면 품질", 17, GOLD)
		column.add_child(quality_title)
		column.move_child(quality_title, 5)
		for index in range(2):
			var choice := button(["균형 · 기본 해상도 / 그림자", "성능 · 낮은 해상도 / 그림자 끄기"][index], func():
				Session.quality = index
				world.apply_quality()
				for child in column.get_children():
					if child is Button and child.has_meta("quality_index"):
						child.set_pressed_no_signal(int(child.get_meta("quality_index")) == index), column)
			choice.toggle_mode = true
			choice.set_meta("quality_index", index)
			choice.set_pressed_no_signal(Session.quality == index)
			column.move_child(choice, 6+index)
		_apply_layout()
		return
	var quality := OptionButton.new()
	quality.add_item("균형 · 기본 해상도 / 그림자")
	quality.add_item("성능 · 낮은 해상도 / 그림자 끄기")
	quality.selected = Session.quality
	quality.item_selected.connect(func(index: int): Session.quality = index; world.apply_quality())
	column.add_child(quality)
	column.move_child(quality, 5)

func toast(text: String) -> void:
	toast_label.text = _touch_copy(text)
	toast_time = 4.0

func announce(title: String, subtitle: String = "") -> void:
	banner_title.text = title
	banner_subtitle.text = subtitle
	banner_time = 4.5

func floating_damage(amount: float, position_3d: Vector3) -> void:
	var node := label(str(roundi(amount)), 23 if amount < 50 else 31, WHITE if amount < 50 else GOLD)
	root.add_child(node)
	damage_numbers.append({"label":node, "point":position_3d, "time":0.0})

func _qa_character_art(visual: ActorVisual) -> Dictionary:
	# Export values only. Browser QA cannot use this snapshot to drive a rig.
	var report := visual.presentation_report()
	if is_instance_valid(visual.skeletal_bridge):
		var bridge := visual.skeletal_bridge
		report["sampled_time"] = bridge.sampled_time
		var skeleton := bridge.get_skeleton()
		if is_instance_valid(skeleton):
			var hand := skeleton.find_bone("RightHand")
			if hand >= 0:
				var pose := skeleton.get_bone_global_pose(hand)
				var hand_rotation := pose.basis.orthonormalized().get_rotation_quaternion()
				report["right_hand_pose"] = [pose.origin.x,pose.origin.y,pose.origin.z,
					hand_rotation.x,hand_rotation.y,hand_rotation.z,hand_rotation.w]
	return report

func _qa_visible_rect(control: Control) -> Rect2:
	var visible_rect := control.get_global_rect().intersection(Rect2(Vector2.ZERO,root.size))
	var parent := control.get_parent()
	while parent is Control:
		if parent.clip_contents:
			visible_rect = visible_rect.intersection(parent.get_global_rect())
		parent = parent.get_parent()
	return visible_rect

func _qa_ui_report() -> Dictionary:
	var scrolls: Array[Dictionary] = []
	for scroll in [title_scroll,modal_scroll]:
		if is_instance_valid(scroll) and scroll.is_visible_in_tree():
			var bounds: Rect2 = scroll.get_global_rect()
			var vertical: VScrollBar = scroll.get_v_scroll_bar()
			scrolls.append({"name":scroll.name,"x":bounds.position.x,"y":bounds.position.y,
				"w":bounds.size.x,"h":bounds.size.y,"value":vertical.value,
				"max":vertical.max_value,"page":vertical.page})
	var texts: Array[Dictionary] = []
	for control in root.find_children("*", "Label", true, false):
		if control.is_visible_in_tree() and not control.is_queued_for_deletion() and not control.text.is_empty():
			var bounds: Rect2 = control.get_global_rect()
			var visible_rect := _qa_visible_rect(control)
			texts.append({"text":control.text,"font_size":control.get_theme_font_size("font_size"),"alpha":control.modulate.a,
				"x":bounds.position.x,"y":bounds.position.y,"w":bounds.size.x,"h":bounds.size.y,
				"visible_x":visible_rect.position.x,"visible_y":visible_rect.position.y,
				"visible_w":visible_rect.size.x,"visible_h":visible_rect.size.y,
				"line_count":control.get_line_count(),"visible_line_count":control.get_visible_line_count(),
				"minimum_h":control.get_minimum_size().y})
	var sliders: Array[Dictionary] = []
	for control in root.find_children("*", "HSlider", true, false):
		if control.is_visible_in_tree() and not control.is_queued_for_deletion():
			var bounds: Rect2 = control.get_global_rect()
			sliders.append({"x":bounds.position.x,"y":bounds.position.y,"w":bounds.size.x,"h":bounds.size.y,
				"value":control.value,"min":control.min_value,"max":control.max_value,"step":control.step})
	return {"scrolls":scrolls,"texts":texts,"sliders":sliders}

func _qa_interaction_targets() -> Array[Dictionary]:
	var targets: Array[Dictionary] = []
	for index in range(Sanctuary.CHECKPOINTS.size()):
		var point: Vector3 = Sanctuary.CHECKPOINTS[index]+Vector3(2,0,0)
		targets.append({"kind":"checkpoint","index":index,"x":point.x,"z":point.z})
	for index in range(world.sanctuary.npc_positions.size()):
		var point: Vector3 = world.sanctuary.npc_positions[index]
		targets.append({"kind":"npc","index":index,"x":point.x,"z":point.z})
	for index in range(world.sanctuary.lore_positions.size()):
		var point: Vector3 = world.sanctuary.lore_positions[index]
		targets.append({"kind":"lore","index":index,"x":point.x,"z":point.z})
	return targets

func _qa_viewport_geometry() -> Dictionary:
	var window := get_window()
	var viewport := get_viewport()
	var texture := viewport.get_texture()
	var texture_size := texture.get_size() if texture != null else Vector2.ZERO
	var final := viewport.get_final_transform()
	var stretch := viewport.get_stretch_transform()
	var visible := viewport.get_visible_rect()
	var display_size := DisplayServer.window_get_size()
	return {"window_size":[window.size.x,window.size.y],
		"display_size":[display_size.x,display_size.y],
		"content_scale_size":[window.content_scale_size.x,window.content_scale_size.y],
		"content_scale_mode":window.content_scale_mode,"content_scale_aspect":window.content_scale_aspect,
		"content_scale_factor":window.content_scale_factor,
		"texture_size":[texture_size.x,texture_size.y],
		"visible_rect":[visible.position.x,visible.position.y,visible.size.x,visible.size.y],
		"final_transform":[final.x.x,final.x.y,final.y.x,final.y.y,final.origin.x,final.origin.y],
		"stretch_transform":[stretch.x.x,stretch.x.y,stretch.y.x,stretch.y.y,stretch.origin.x,stretch.origin.y]}

func _process(delta: float) -> void:
	toast_time = maxf(0, toast_time - delta)
	toast_label.modulate.a = minf(1, toast_time)
	banner_time = maxf(0, banner_time - delta)
	banner_title.modulate.a = minf(1, banner_time)
	banner_subtitle.modulate.a = minf(1, banner_time)
	_sync_touch_state()
	if world == null or world.player == null:
		return
	var player: RunePlayer = world.player
	qa_clock += delta
	if qa_enabled and qa_clock >= 0.25:
		qa_clock = 0
		var rect := Rect2()
		if is_instance_valid(modal_panel):
			rect = modal_panel.get_global_rect()
		var buttons: Array[Dictionary] = []
		for control in root.find_children("*", "Button", true, false):
			if control.is_visible_in_tree() and not control.is_queued_for_deletion():
				var bounds: Rect2 = control.get_global_rect()
				var visible_rect := _qa_visible_rect(control)
				var button_info := {"text":control.text, "kind":control.get_class(),
					"x":bounds.position.x,"y":bounds.position.y,"w":bounds.size.x,"h":bounds.size.y,
					"disabled":control.disabled,"font_size":control.get_theme_font_size("font_size"),
					"on_screen":visible_rect.has_area(),"visible_x":visible_rect.position.x,
					"visible_y":visible_rect.position.y,"visible_w":visible_rect.size.x,"visible_h":visible_rect.size.y}
				if control is OptionButton:
					button_info["popup_visible"] = control.get_popup().visible
					button_info["popup_focus"] = control.get_popup().get_focused_item()
				buttons.append(button_info)
		var enemy_art: Array[Dictionary] = []
		for actor in get_tree().get_nodes_in_group("enemies"):
			var enemy := actor as RuneEnemy
			if enemy != null and is_instance_valid(enemy.visual) and not enemy.is_queued_for_deletion():
				var art := _qa_character_art(enemy.visual)
				art.merge({"kind":enemy.kind,"elite":enemy.elite,"boss":enemy.is_boss,"dead":enemy.dead}, true)
				enemy_art.append(art)
		var status := {"build_id":Session.build_id, "started":world.started, "paused":get_tree().paused,
			"viewport_geometry":_qa_viewport_geometry(),
			"save_primary":Session._read_valid_save(Session.save_path),
			"save_primary_mtime":FileAccess.get_modified_time(Session.save_path),
			"fs_persistent":OS.is_userfs_persistent(),
			"physics_frame":Engine.get_physics_frames(), "dpr":float(JavaScriptBridge.eval("window.devicePixelRatio || 1")),
			"has_save":Session.has_save, "checkpoint":Session.checkpoint,
			"ui_width":root.size.x,"ui_height":root.size.y,"buttons":buttons,
			"quality":Session.quality,"fps":Engine.get_frames_per_second(),
			"render_scale":get_viewport().scaling_3d_scale,
			"dead":player.dead, "health":player.health, "max_health":player.max_health,
			"rune":player.rune,"potions":player.potions,"x":player.global_position.x,"z":player.global_position.z,
			"camera_yaw":world.rig.yaw,"camera_pitch":world.rig.pitch,
			"charge_elapsed":player.heavy_held,"heavy_held":player.heavy_held,
			"dodge_remaining":player.dodge_time,"parry_remaining":player.parry_time,"stagger":player.stagger,
			"dodge_cooldown":player.dodge_cooldown,"parry_cooldown":player.parry_cooldown,
			"locked":is_instance_valid(player.locked_target),
			"locked_target":is_instance_valid(player.locked_target),
			"locked_target_id":player.locked_target.get_instance_id() if is_instance_valid(player.locked_target) else 0,
			"interaction_kind":world.interaction_kind,"interaction_index":world.interaction_index,
			"interaction_targets":_qa_interaction_targets(),
			"touch":TouchControls.presentation_report(),"ui":_qa_ui_report(),
			"encounter":world.active_encounter, "hits":player.combo_hits,
			"input_ready":player.active and not player.dead and not get_tree().paused and player.ui_input_guard == 0,
			"hero_art":_qa_character_art(player.visual), "enemy_art":enemy_art,
			"modal":is_instance_valid(modal), "modal_x":rect.position.x,"modal_y":rect.position.y,
			"modal_w":rect.size.x,"modal_h":rect.size.y,"hud_y":health_bar.global_position.y}
		JavaScriptBridge.eval("window.__RUNEFALL_STATE = " + JSON.stringify(status))
	health_bar.max_value = player.max_health
	health_bar.value = player.health
	rune_bar.max_value = player.max_rune
	rune_bar.value = player.rune
	health_text.text = ("HP %d / %d" if TouchControls.available else "%d / %d") % [player.health,player.max_health]
	rune_text.text = "RUNE  %d / %d" % [player.rune, player.max_rune]
	potion_text.text = ("회복 %d" if TouchControls.available else "R  회복  %d") % player.potions
	if TouchControls.available:
		interaction.text = _touch_copy(interaction.text)
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
	if TouchControls.event_pressed(event, "pause"):
		if is_instance_valid(modal):
			close_modal()
		elif world.started:
			show_pause()
		get_viewport().set_input_as_handled()
	if event.is_action_pressed("debug_overlay"):
		debug_text.visible = not debug_text.visible
