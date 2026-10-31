extends Node
# ISOLATED FIXED-ART FIXTURE. Never included in the source game or final exports.
var world: Node3D
var final_time := 0.24
var detail := false
var hidden_ribbon := false
var epoch := 44001

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("configure")

func configure() -> void:
	world = get_parent()
	# Room floor top .005m minus actual capsule sole offset .025m.
	world.player.position = Vector3(0, -0.02, -25)
	world.player.active = false
	world.player.set_physics_process(false)
	world.rig.cinematic = false
	world.rig.yaw = 0
	world.rig.pitch = -0.18
	world.rig.shake_strength = 0
	world.rig.snap()
	Session.quality = 0
	Session.shake = false
	world.apply_quality()
	world.ui.hide()
	await get_tree().physics_frame
	await get_tree().physics_frame
	world.rig._physics_process(1.0)
	world.rig.set_physics_process(false)
	get_tree().paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	set_pose()
	report("ready")

func set_pose() -> void:
	var visual: ActorVisual = world.player.visual
	var data: AttackData = load("res://data/light_1.tres")
	epoch += 1
	visual.blade_trail.reset()
	visual.pose(0.0, 0, -1.0, false, false, false, {"speed":0.0, "presentation_epoch":epoch})
	# Authoritative action scalars, sampled through the real visual path. No
	# synthetic sweep vertices, hitbox/reach inflation, or trail rescaling.
	var time := 0.0
	var previous := 0.0
	while time <= final_time + 0.000001:
		var snapshot := {"speed":0.0, "attack_id":"light_1", "attack_elapsed":time,
			"attack_duration":data.duration(), "attack_startup":data.startup,
			"attack_active":data.active, "attack_reach":data.reach, "presentation_epoch":epoch}
		visual.pose(time - previous if time > 0.0 else 1.0/60.0, 0, -1.0, false, false, false, snapshot)
		previous = time
		if is_equal_approx(time, final_time):
			break
		time = minf(final_time, time + 1.0/60.0)
	visual.blade_trail.visible = not hidden_ribbon and visual.blade_trail.mesh != null

func report(stage: String) -> void:
	var visual: ActorVisual = world.player.visual
	var camera: Camera3D = world.rig.camera
	var data: AttackData = load("res://data/light_1.tres")
	var material := visual.blade_trail.material_override as StandardMaterial3D
	var snapshot := {"stage":stage, "scope":"Fixed-art fixture, not gameplay/timing QA or AAA proof",
		"attack":"light_1", "elapsed":final_time, "startup":data.startup,
		"active":data.active, "duration":data.duration(), "sample_hz":60,
		"detail_reframe":detail, "hidden_ribbon_only":hidden_ribbon,
		"quality":Session.quality, "camera_fov":camera.fov,
		"camera_position":[camera.global_position.x,camera.global_position.y,camera.global_position.z],
		"camera_basis":[camera.global_basis.x.x,camera.global_basis.x.y,camera.global_basis.x.z,camera.global_basis.y.x,camera.global_basis.y.y,camera.global_basis.y.z,camera.global_basis.z.x,camera.global_basis.z.y,camera.global_basis.z.z],
		"hero_position":[world.player.position.x,world.player.position.y,world.player.position.z],
		"hero_art":visual.presentation_report(),
		"trail_tint":visual.blade_trail.tint.to_html(), "depth_test_enabled":not material.no_depth_test,
		"depth_draw_mode":material.depth_draw_mode, "blend_mode":material.blend_mode}
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.__RUNEFALL_TRAIL_ART = " + JSON.stringify(snapshot), true)
	print("RUNEFALL_TRAIL_ART " + JSON.stringify(snapshot))

func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo or world == null:
		return
	match event.physical_keycode:
		KEY_H:
			hidden_ribbon = not hidden_ribbon
			world.player.visual.blade_trail.visible = not hidden_ribbon and world.player.visual.blade_trail.mesh != null
		KEY_V:
			detail = not detail
			if detail:
				# Deliberate closer inspection, distinct from the actual RuneCamera shot.
				world.rig.camera.global_position = world.player.global_position + Vector3(2.5, 1.9, 3.0)
				world.rig.camera.look_at(world.player.global_position + Vector3(0, 1.0, 0))
			else:
				world.rig.snap()
				world.rig._physics_process(1.0)
		KEY_T:
			final_time = 0.18 if final_time > 0.2 else 0.24
			set_pose()
		_:
			return
	report("changed")
