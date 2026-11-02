extends Node
## Isolated matched font controls. No production Game, input or save state.

const WEIGHT_AXIS: int = 0x77676874
const SIZES: Array[int] = [12,16,18,24,36]
const PROFILES: Array[Vector2i] = [Vector2i(390,844),Vector2i(360,800),Vector2i(844,390)]
const CORPUS: Array[String] = [
	"HP 120 / 120 · RUNE 35 / 100",
	"성역 정화 0 / 7 · 룬 조각 35",
	"공격 강공 회피 패링 회복 룬 1 대화 조준",
	"기존 진행을 초기화하고 성역 입구에서 시작합니다.",
	"AV ffi Á 각 각 · 日本語 カナ 中文",
]
const COLORS := {"background":"0b1218", "text":"e6eade", "gold":"d6b87e", "mint":"a2d5c5", "panel":"15242c"}

var config: Dictionary = {}

func _ready() -> void:
	var arguments: PackedStringArray = OS.get_cmdline_user_args()
	if arguments.size() != 1:
		_fail("Font review needs exactly one configuration path")
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(arguments[0]))
	if not parsed is Dictionary:
		_fail("Font review configuration must be a dictionary")
		return
	config = parsed
	_run.call_deferred()

func _fail(message: String) -> void:
	push_error(message)
	get_tree().quit(2)

func _vec(value: Vector2) -> Array:
	return [value.x,value.y]

func _rect(value: Rect2) -> Array:
	return [value.position.x,value.position.y,value.size.x,value.size.y]

func _shape(font: Font, text: String, size: int) -> Dictionary:
	var line := TextLine.new()
	if not line.add_string(text,font,size):
		return {"error":"TextLine.add_string failed"}
	var server := TextServerManager.get_primary_interface()
	var glyphs: Array[Dictionary] = []
	for glyph: Dictionary in server.shaped_text_get_glyphs(line.get_rid()):
		var item: Dictionary = glyph.duplicate()
		# Per-resource RID allocation differs. Keep every other shaped field.
		var rid: RID = item.get("font_rid",RID())
		item["uses_requested_font"] = font.get_rids().has(rid)
		item.erase("font_rid")
		glyphs.append(item)
	return {"size":_vec(line.get_size()),"ascent":line.get_line_ascent(),
		"descent":line.get_line_descent(),"glyphs":glyphs}

func _font_metrics(font: Font, size: int, width: float) -> Dictionary:
	var strings: Array[Dictionary] = []
	for text: String in CORPUS:
		strings.append({"text":text,"string_size":_vec(font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,size)),
			"multiline_size":_vec(font.get_multiline_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,width,size)),
			"shaped":_shape(font,text,size)})
	return {"ascent":font.get_ascent(size),"descent":font.get_descent(size),
		"height":font.get_height(size),"strings":strings}

func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size",size)
	label.add_theme_color_override("font_color",color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label

func _make_controls(viewport: SubViewport, font: Font, size: int) -> VBoxContainer:
	var background := ColorRect.new()
	background.color = Color(COLORS.background)
	background.size = Vector2(viewport.size)
	viewport.add_child(background)
	var column := VBoxContainer.new()
	column.position = Vector2(12,12)
	column.size = Vector2(viewport.size.x-24,viewport.size.y-24)
	column.add_theme_constant_override("separation",8)
	var theme := Theme.new()
	theme.default_font = font
	theme.default_font_size = size
	column.theme = theme
	viewport.add_child(column)
	column.add_child(_label(CORPUS[0],size,Color(COLORS.text)))
	column.add_child(_label(CORPUS[1],size,Color(COLORS.gold)))
	var button := Button.new()
	button.text = "회피  ·  회복 3"
	button.focus_mode = Control.FOCUS_NONE
	button.mouse_filter = Control.MOUSE_FILTER_IGNORE
	button.add_theme_color_override("font_color",Color(COLORS.mint))
	button.add_theme_font_size_override("font_size",size)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(COLORS.panel)
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 8
	style.content_margin_bottom = 8
	button.add_theme_stylebox_override("normal",style)
	column.add_child(button)
	column.add_child(_label(CORPUS[3],size,Color(COLORS.text)))
	column.add_child(_label(CORPUS[4],size,Color(COLORS.mint)))
	return column

func _control_metrics(column: VBoxContainer) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for child: Control in column.get_children():
		var item := {"class":child.get_class(),"text":child.get("text"),"rect":_rect(child.get_rect()),
			"minimum_size":_vec(child.get_minimum_size()),"combined_minimum_size":_vec(child.get_combined_minimum_size())}
		if child is Label:
			var label := child as Label
			var characters: Array[Array] = []
			for index in range(label.text.length()):
				characters.append(_rect(label.get_character_bounds(index)))
			item["line_count"] = label.get_line_count()
			item["visible_line_count"] = label.get_visible_line_count()
			item["character_bounds"] = characters
		result.append(item)
	return result

func _run() -> void:
	var source := load("res://assets/fonts/NotoSansKR.ttf") as FontFile
	var candidate := load("res://assets/fonts/runefall_kr430.ttf") as FontFile
	if source == null or candidate == null:
		_fail("Cannot load review fonts")
		return
	var variable := FontVariation.new()
	variable.base_font = source
	variable.variation_opentype = {WEIGHT_AXIS:430.0}
	var shots: Array[Dictionary] = []
	for take: String in ["variable430","static430"]:
		var font: Font = variable if take == "variable430" else candidate
		for profile: Vector2i in PROFILES:
			for size: int in SIZES:
				var viewport := SubViewport.new()
				viewport.size = profile
				viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
				viewport.transparent_bg = false
				add_child(viewport)
				var column := _make_controls(viewport,font,size)
				for frame in range(4):
					await RenderingServer.frame_post_draw
				var name := "%s-%dx%d-%d.png" % [take,profile.x,profile.y,size]
				var path := String(config.output_directory).path_join(name)
				if FileAccess.file_exists(path):
					_fail("Refusing to overwrite font raster")
					return
				var image := viewport.get_texture().get_image()
				if image.save_png(path) != OK:
					_fail("Cannot save original font raster")
					return
				shots.append({"take":take,"viewport":[profile.x,profile.y],"size":size,"png":name,
					"metrics":_font_metrics(font,size,float(profile.x-24)),"controls":_control_metrics(column),
					"content_bottom":column.get_child(column.get_child_count()-1).get_rect().end.y+column.position.y,
					"image_size":[image.get_width(),image.get_height()]})
				print("UI_FONT_REVIEW_SHOT ",name)
				viewport.queue_free()
				await get_tree().process_frame
	var result := {"status":"isolated_font_raster_captured","engine":Engine.get_version_info(),
		"renderer":RenderingServer.get_current_rendering_method(),"adapter":RenderingServer.get_video_adapter_name(),
		"text_server":TextServerManager.get_primary_interface().get_name(),"palette":COLORS,
		"profiles":[[390,844],[360,800],[844,390]],"font_sizes":SIZES,"corpus":CORPUS,
		"baseline":"Original FontFile wrapped by FontVariation with wght430",
		"candidate":"Static derived FontFile directly; no FontVariation",
		"scope":"Isolated real Godot Control/TextServer comparison, not actual Game/browser UI approval.","shots":shots}
	var result_path := String(config.result_path)
	if FileAccess.file_exists(result_path):
		_fail("Refusing to overwrite font review report")
		return
	var file := FileAccess.open(result_path,FileAccess.WRITE)
	if file == null:
		_fail("Cannot write font review report")
		return
	file.store_string(JSON.stringify(result,"\t")+"\n")
	file.close()
	await get_tree().process_frame
	await get_tree().process_frame
	print("UI_FONT_REVIEW_COMPLETE shots=",shots.size())
	get_tree().quit(0)
