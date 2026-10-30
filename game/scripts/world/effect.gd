class_name RuneEffect
extends Node3D

var duration: float = 0.5
var elapsed: float = 0.0
var radius: float = 3.0
var color: Color = Color("79d8cc")
var warning: bool = false
var ring: MeshInstance3D

func _ready() -> void:
	ring = MeshInstance3D.new()
	var mesh := TorusMesh.new()
	mesh.inner_radius = 0.92
	mesh.outer_radius = 1.0
	mesh.rings = 32
	mesh.ring_segments = 6
	ring.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.albedo_color = color
	ring.material_override = mat
	add_child(ring)
	if warning:
		ring.scale = Vector3(radius, 0.35, radius)

func _process(delta: float) -> void:
	elapsed += delta
	var progress := clampf(elapsed / duration, 0, 1)
	if warning:
		ring.scale = Vector3.ONE * radius * (0.85 + progress * 0.15)
	else:
		ring.scale = Vector3.ONE * radius * (0.2 + progress * 0.8)
	var mat: StandardMaterial3D = ring.material_override
	mat.albedo_color.a = (0.4 + progress * 0.5) if warning else 1.0 - progress
	if elapsed >= duration:
		queue_free()
