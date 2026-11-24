class_name LockReticle
extends Control

## Drawn lock-on reticle: four inward chevrons that snap in on a new target
## and turn slowly. Presentation only; target choice stays in Game/RunePlayer.

const SNAP_DURATION := 0.16
var color := Color("c6ab78")
var age := 0.0
var spin := 0.0
var target_id := 0
var emphasis := false

func _init() -> void:
	name = "LockReticle"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = Vector2(76, 76)
	custom_minimum_size = size
	visible = false

func retarget(id: int, boss_or_elite: bool) -> void:
	if id != target_id:
		target_id = id
		age = 0.0
	emphasis = boss_or_elite
	color = Color("ff8a5c") if boss_or_elite else Color("e3c58a")

func _process(delta: float) -> void:
	if not visible:
		return
	age += delta
	spin = fmod(spin + delta * 0.85, TAU)
	queue_redraw()

func _draw() -> void:
	var center := size * 0.5
	var t := clampf(age / SNAP_DURATION, 0.0, 1.0)
	var eased := 1.0 - pow(1.0 - t, 3.0)
	var radius := lerpf(40.0, 21.0, eased) * (1.12 if emphasis else 1.0)
	var alpha := lerpf(0.0, 1.0, eased)
	var ink := Color(0.03, 0.04, 0.04, 0.55 * alpha)
	var line := Color(color, alpha)
	for index in range(4):
		var direction := Vector2.from_angle(spin + PI * 0.25 + index * TAU / 4.0)
		var side := direction.orthogonal()
		var tip := center + direction * radius
		var points := PackedVector2Array([tip + direction * 9.0 + side * 7.0, tip, tip + direction * 9.0 - side * 7.0])
		draw_polyline(points, ink, 5.0, true)
		draw_polyline(points, line, 2.4, true)
	var d := 5.5
	var diamond := PackedVector2Array([center + Vector2(0, -d), center + Vector2(d, 0), center + Vector2(0, d), center + Vector2(-d, 0), center + Vector2(0, -d)])
	draw_polyline(diamond, ink, 4.0, true)
	draw_polyline(diamond, line, 1.8, true)
	draw_arc(center, radius * 0.7, 0.0, TAU, 40, Color(color, 0.28 * alpha), 1.2, true)
