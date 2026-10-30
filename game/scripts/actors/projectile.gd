class_name RuneProjectile
extends Node3D

var direction: Vector3
var player: RunePlayer
var life: float = 5.0

func _ready() -> void:
	var sphere := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.18
	mesh.height = 0.36
	sphere.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color("fa9c70")
	sphere.material_override = mat
	add_child(sphere)

func _physics_process(delta: float) -> void:
	if not is_instance_valid(player) or not player.active or player.dead:
		queue_free()
		return
	var next := global_position + direction * 10.0 * delta
	var query := PhysicsRayQueryParameters3D.create(global_position, next, 1 | 2)
	var result := get_world_3d().direct_space_state.intersect_ray(query)
	if not result.is_empty():
		if result.collider == player:
			player.receive_hit(13, 10, global_position - direction * 2)
		queue_free()
	else:
		global_position = next
	life -= delta
	if life <= 0:
		queue_free()
