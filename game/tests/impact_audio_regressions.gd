extends RefCounted

# Actual imported WAV players and ownership. A profile report alone cannot
# prove that a whiff stayed swing-only or that crowd voices remain bounded.
static func run(world: Node3D, check: Callable) -> bool:
	var audio := world.get_tree().root.get_node("Audio")
	audio.stop_all()
	var initial_drained: bool = await audio.wait_until_stopped()
	check.call(initial_drained, "Impact audio fixture drains existing real playback before its isolated API checks")
	if not initial_drained:
		return false
	var context := {"attack_id":"charged_heavy", "strength":"charged", "point":Vector3(2, 1, -3),
		"normal":Vector3.BACK, "direction":Vector3.FORWARD, "contact_source":"hurtbox_proxy",
		"material":"metal", "blocked":false, "killed":false, "poise_broken":true}
	audio.start()
	audio.play_attack("charged_heavy", 1.24)
	var report: Dictionary = audio.presentation_report()
	var effect_children := 0
	var swing_player: AudioStreamPlayer
	for child in audio.get_children():
		if child is AudioStreamPlayer and child != audio.music_player and not child.is_queued_for_deletion():
			effect_children += 1
			swing_player = child
	check.call(effect_children == 1 and swing_player != null and String(swing_player.get_meta("sound_key", "")) == "impact_swing_charged" and is_equal_approx(swing_player.pitch_scale, 1.24) and report.last_attack.impact_layers == 0,
		"A charged attack start allocates one pitched swing WAV with no confirmed-contact layer")
	var expected := {"light":2, "heavy":4, "charged":5}
	var profiles: Dictionary = {}
	for strength: String in ["light", "heavy", "charged"]:
		context.strength = strength
		var before: int = audio.presentation_report().effect_players
		audio.play_impact(context)
		report = audio.presentation_report()
		profiles[strength] = report.last_impact.duplicate(true)
		check.call(report.last_impact.accepted and report.last_impact.style == strength and report.last_impact.layers.size() == expected[strength] and report.effect_players-before == expected[strength],
			"Confirmed %s contact starts every distinct profile layer synchronously" % strength)
	context.blocked = true
	context.strength = "charged"
	audio.play_impact(context)
	report = audio.presentation_report()
	var blocked_keys: Array[String] = []
	for layer: Dictionary in report.last_impact.layers:
		blocked_keys.append(String(layer.key))
	check.call(report.last_impact.style == "blocked_metal" and blocked_keys == ["contact_tick", "metal_block", "debris_tail"],
		"A blocked charged contact uses metal deflection without penetrating body or charged-sub layers")
	profiles.blocked = report.last_impact.duplicate(true)
	var before_invalid: int = report.effect_players
	var invalid := context.duplicate(true)
	invalid.contact_source = "attack_start"
	audio.play_impact(invalid)
	report = audio.presentation_report()
	check.call(not report.last_impact.accepted and report.effect_players == before_invalid,
		"An unconfirmed attack-start context cannot allocate impact players")
	context.blocked = false
	for index in range(20):
		audio.play_impact(context)
	report = audio.presentation_report()
	check.call(report.effect_players == 32 and report.effect_player_budget == 32,
		"A same-frame confirmed-impact crowd reaches but cannot exceed the actual 32-player effect cap")
	audio.stop_all()
	audio.play_attack("charged_heavy")
	audio.play_impact(context)
	check.call(not audio.presentation_report().last_attack.accepted and not audio.presentation_report().last_impact.accepted,
		"Permanent stop blocks both swing and confirmed-impact entry points")
	var final_drained: bool = await audio.wait_until_stopped()
	check.call(final_drained and audio.stop_report().players == 0 and audio.stop_report().pending_playbacks == 0,
		"All layered crowd WAV players and mixer references release through the existing observed shutdown contract")
	var path := ProjectSettings.globalize_path("res://").path_join("../build/verification/charged-impact/audio.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify({"scope":"Actual WAV API allocation, swing/contact separation, profile ownership, same-frame crowd cap and observed playback shutdown; listening and rendered Web mix remain separate.",
			"audio_script_sha256":FileAccess.get_sha256("res://scripts/core/audio.gd"), "profiles":profiles,
			"crowd_effect_players":report.effect_players, "final_drained":final_drained, "stop":audio.last_stop_wait.duplicate()}, "\t")+"\n")
	return final_drained
