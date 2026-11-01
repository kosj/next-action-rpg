extends RefCounted

static func run(world: Node3D, check: Callable) -> bool:
	var sanctuary := world.get("sanctuary") as Sanctuary
	var key := sanctuary.get_node("SanctuaryKey") as DirectionalLight3D
	var fill := sanctuary.get_node("SanctuaryFill") as DirectionalLight3D
	var saved_quality := Session.quality
	var saved_key_energy := key.light_energy
	var saved_fill_energy := fill.light_energy
	var saved_fill_shadow := fill.shadow_enabled
	# Art-direction energy must not silently change which light owns shadows.
	key.light_energy = 0.9
	fill.light_energy = 1.1
	Session.quality = 0
	world.call("apply_quality")
	var balanced_scale := world.get_viewport().scaling_3d_scale
	check.call(key.shadow_enabled and not fill.shadow_enabled, "Balanced mode retains the key's real shadow after key/fill energy order changes")
	Session.quality = 1
	world.call("apply_quality")
	var performance_scale := world.get_viewport().scaling_3d_scale
	check.call(not key.shadow_enabled and not fill.shadow_enabled, "Performance mode turns off real directional shadows irrespective of key energy")
	check.call(performance_scale < balanced_scale and performance_scale > 0.0, "Performance mode reduces actual 3D resolution while keeping the balanced profile distinct")
	Session.quality = 0
	world.call("apply_quality")
	check.call(key.shadow_enabled and is_equal_approx(world.get_viewport().scaling_3d_scale, balanced_scale), "Returning from performance restores actual balanced shadow and resolution state")
	key.light_energy = saved_key_energy
	fill.light_energy = saved_fill_energy
	fill.shadow_enabled = saved_fill_shadow
	Session.quality = saved_quality
	world.call("apply_quality")
	return true
