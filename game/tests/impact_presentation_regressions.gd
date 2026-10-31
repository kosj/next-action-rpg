extends RefCounted

# Exercise the actual presentation owners. Combat acceptance/rejection and
# damage are tested separately by charged_impact_regressions.
static func run(world: Node3D, check: Callable) -> bool:
	var context := {"attack_id":"charged_heavy","attack_instance_id":99123,"source":"player",
		"strength":"charged","amount":69.3,"point":Vector3(240, 11, 240),
		"normal":Vector3.BACK,"direction":Vector3.FORWARD,"contact_source":"hurtbox_proxy",
		"material":"metal","blocked":false,"killed":false,"poise_broken":true,
		"reaction":"heavy_hit","hitstop":0.075,"target_id":0}
	var original_shake := Session.shake
	var rig := RuneCamera.new()
	rig.player = world.player
	world.add_child(rig)
	rig.camera.current = false
	rig.set_physics_process(false)
	rig.cinematic = false
	rig.snap()
	Session.shake = true
	rig.apply_impact(context)
	rig._physics_process(0.04)
	check.call(rig.camera.fov < 56.0 and rig.impact_age < 0.24, "A confirmed charged hit produces a brief bounded camera impulse")
	rig._physics_process(0.30)
	check.call(is_equal_approx(rig.camera.fov, 56.0), "The impact FOV returns to its base after the finite impulse")
	Session.shake = false
	rig.apply_impact(context)
	rig._physics_process(0.04)
	check.call(is_equal_approx(rig.camera.fov, 56.0) and rig.camera.global_position.is_equal_approx(rig._follow_position), "Disabling camera shake also disables impact translation and FOV changes")
	Session.shake = true
	rig.snap()
	var blocked := context.duplicate(true)
	blocked.blocked = true
	rig.apply_impact(blocked)
	rig._physics_process(0.04)
	check.call(is_equal_approx(rig.camera.fov, 56.0) and rig.impact_age > 0.24, "A blocked hit does not use the charged penetrating-hit camera impulse")
	rig.free()
	world.rig.camera.current = true
	Session.shake = original_shake
	# Multiple confirmed hits in one physics tick cannot bypass the active cap
	# just because the previous oldest node is only queued for deletion.
	for index in range(20):
		world._on_impact_confirmed(context)
	var active := 0
	var valid := 0
	for effect in world.get_tree().get_nodes_in_group("impact_effects"):
		if not effect.is_queued_for_deletion():
			active += 1
			var report: Dictionary = effect.presentation_report()
			if bool(report.get("valid", false)) and int(report.get("spark_count", 0)) > 0 and int(report.get("triangles", 0)) > 0:
				valid += 1
	check.call(active == 8 and valid == 8, "Twenty confirmed contacts create eight valid nonempty effects within the same-frame crowd budget")
	# The complete effect must expire without another hit, actor or callback.
	await world.get_tree().create_timer(0.85).timeout
	check.call(world.get_tree().get_nodes_in_group("impact_effects").is_empty(), "All contact particles and meshes release their owning effect after its bounded lifetime")
	check.call(world.impact_history.size() <= 32, "Read-only browser impact history has a bounded lifetime budget")
	return true
