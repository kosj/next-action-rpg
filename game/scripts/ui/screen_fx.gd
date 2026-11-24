class_name RuneScreenFX
extends CanvasLayer

## Full-screen combat presentation drawn between the 3D view and the HUD.
## It reads the player and world each frame and never writes gameplay state.
## The screen-reading grade is hidden unless Rune Haste or an impact pulse is
## active, so ordinary frames pay for at most the cheap vignette gradient.

const VIGNETTE_SHADER: Shader = preload("res://assets/shaders/screen_vignette.gdshader")
const GRADE_SHADER: Shader = preload("res://assets/shaders/screen_grade.gdshader")
const LOW_HEALTH_RATIO := 0.35
const HURT_DURATION := 0.38
const IMPACT_DURATION := 0.2

var world: Node3D
var grade: ColorRect
var vignette: ColorRect
var _vignette_material: ShaderMaterial
var _grade_material: ShaderMaterial
var hurt := 0.0
var impact := 0.0
var impact_center := Vector2(0.5, 0.5)
var haste := 0.0
var low_health := 0.0
var pulse := 0.0
var heartbeat_phase := 0.0
var impact_count := 0
var hurt_count := 0

func _ready() -> void:
	name = "ScreenFX"
	# Above the 3D view and below RuneHUD (layer 1) and touch controls.
	layer = 0
	_grade_material = ShaderMaterial.new()
	_grade_material.shader = GRADE_SHADER
	grade = _full_rect("HasteImpactGrade", _grade_material)
	_vignette_material = ShaderMaterial.new()
	_vignette_material.shader = VIGNETTE_SHADER
	vignette = _full_rect("CombatVignette", _vignette_material)

func _full_rect(label: String, material: ShaderMaterial) -> ColorRect:
	var rect := ColorRect.new()
	rect.name = label
	rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rect.color = Color.WHITE
	rect.material = material
	rect.visible = false
	add_child(rect)
	return rect

func trigger_hurt() -> void:
	hurt = 1.0
	hurt_count += 1

func trigger_impact(context: Dictionary, camera: Camera3D) -> bool:
	# Radial blur is camera-like motion: it follows the comfort setting.
	if not Session.shake or not is_instance_valid(camera):
		return false
	var strength := String(context.get("strength", ""))
	var attack_id := String(context.get("attack_id", ""))
	var amount := 0.0
	if bool(context.get("blocked", false)):
		return false
	if strength == "charged" or attack_id == "skill_3":
		amount = 1.0
	elif strength == "heavy" and bool(context.get("killed", false)):
		amount = 0.7
	elif bool(context.get("poise_broken", false)) and strength in ["heavy", "skill"]:
		amount = 0.6
	if amount <= 0.0:
		return false
	var point: Variant = context.get("point")
	if not point is Vector3 or not point.is_finite() or camera.is_position_behind(point):
		return false
	var size := camera.get_viewport().get_visible_rect().size
	if size.x <= 0.0 or size.y <= 0.0:
		return false
	var screen := camera.unproject_position(point)
	impact_center = Vector2(clampf(screen.x / size.x, 0.0, 1.0), clampf(screen.y / size.y, 0.0, 1.0))
	impact = maxf(impact, amount)
	impact_count += 1
	return true

func reset() -> void:
	hurt = 0.0
	impact = 0.0
	haste = 0.0
	low_health = 0.0
	pulse = 0.0
	heartbeat_phase = 0.0
	_push()

func _process(delta: float) -> void:
	var player: RunePlayer = world.get("player") if is_instance_valid(world) else null
	if not is_instance_valid(player) or not bool(world.get("started")):
		if grade.visible or vignette.visible:
			reset()
		return
	hurt = maxf(0.0, hurt - delta / HURT_DURATION)
	impact = maxf(0.0, impact - delta / IMPACT_DURATION)
	var haste_target: float = world.call("haste_intensity") if world.has_method("haste_intensity") else 0.0
	haste = move_toward(haste, haste_target, delta * 7.0)
	var ratio := player.health / maxf(player.max_health, 1.0)
	var low_target := 0.0 if player.dead or ratio >= LOW_HEALTH_RATIO else 1.0 - ratio / LOW_HEALTH_RATIO
	low_health = move_toward(low_health, clampf(low_target, 0.0, 1.0), delta * 2.0)
	if low_health > 0.0:
		# Lub-dub heartbeat that quickens as health falls.
		heartbeat_phase = fmod(heartbeat_phase + delta * lerpf(1.05, 2.1, low_health), 1.0)
		var t := heartbeat_phase
		pulse = clampf(exp(-pow((t - 0.08) / 0.055, 2.0)) + 0.6 * exp(-pow((t - 0.27) / 0.055, 2.0)), 0.0, 1.0)
	else:
		pulse = 0.0
	_push()

func _push() -> void:
	var size := get_viewport().get_visible_rect().size if is_inside_tree() else Vector2(16, 10)
	var aspect := Vector2(size.x / maxf(size.y, 1.0), 1.0)
	_vignette_material.set_shader_parameter("aspect", aspect)
	_vignette_material.set_shader_parameter("low_health", low_health)
	_vignette_material.set_shader_parameter("pulse", pulse)
	_vignette_material.set_shader_parameter("hurt", hurt)
	_vignette_material.set_shader_parameter("haste", haste)
	vignette.visible = low_health > 0.001 or hurt > 0.001 or haste > 0.001
	_grade_material.set_shader_parameter("haste", haste)
	_grade_material.set_shader_parameter("impact", impact)
	_grade_material.set_shader_parameter("impact_center", impact_center)
	_grade_material.set_shader_parameter("detail", 1.0 if Session.quality == 0 else 0.0)
	grade.visible = haste > 0.001 or (impact > 0.001 and Session.quality == 0)

func presentation_report() -> Dictionary:
	return {"hurt":hurt, "impact":impact, "impact_center":[impact_center.x, impact_center.y],
		"haste":haste, "low_health":low_health, "pulse":pulse,
		"grade_visible":grade.visible, "vignette_visible":vignette.visible,
		"impact_count":impact_count, "hurt_count":hurt_count}
