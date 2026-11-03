extends Node3D

## A technical Compatibility raster witness, not normal gameplay or art approval.
## Deliberately placed fixture/camera isolates shader visibility before full takes.
func _ready() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() != 1:
		get_tree().quit(2)
		return
	var camera := Camera3D.new()
	add_child(camera)
	camera.position = Vector3(3.2, 3.0, 4.5)
	camera.look_at(Vector3(0, 1.0, -1.5))
	camera.current = true
	var environment := WorldEnvironment.new()
	var sky := Environment.new()
	sky.background_mode = Environment.BG_COLOR
	sky.background_color = Color(0.12, 0.13, 0.15)
	environment.environment = sky
	add_child(environment)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(14, 14)
	floor_mesh.mesh = plane
	var ground := StandardMaterial3D.new()
	ground.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ground.albedo_color = Color(0.24, 0.20, 0.17)
	floor_mesh.material_override = ground
	add_child(floor_mesh)
	var owner := CharacterBody3D.new()
	owner.collision_layer = 2
	add_child(owner)
	var data := AttackData.new()
	var strike := CombatStrike.new(owner, data, 1.0, &"heavy")
	var wave := RuneSwordWave.new()
	add_child(wave)
	wave.setup(owner, strike, Vector3.FORWARD, 4.5, 2.4, 16.0, 0.7)
	wave.set_physics_process(false)
	# One real sweep advances the displayed source; no synthetic shader pixels.
	await get_tree().physics_frame
	await get_tree().physics_frame
	wave._physics_process(0.08)
	await RenderingServer.frame_post_draw
	var result := get_viewport().get_texture().get_image().save_png(arguments[0])
	print("SWORD_WAVE_RASTER ", JSON.stringify({"saved":result == OK, "wave":wave.presentation_report(), "scope":"Technical fixture only; not normal input gameplay or visual acceptance"}))
	get_tree().quit(0 if result == OK else 1)
