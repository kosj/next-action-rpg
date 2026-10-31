extends RefCounted

# Exercise real WAV playbacks and the driver's deferred release. WeakRefs in
# the service observe actual lifetime; no playback is held across an await.
static func run(world: Node3D, check: Callable) -> bool:
	var audio := world.get_tree().root.get_node("Audio")
	audio.stop_all()
	var initial_drained: bool = await audio.wait_until_stopped()
	check.call(initial_drained, "Audio lifecycle fixture first drains existing real gameplay audio before testing restart")
	if not initial_drained:
		return false
	var initial_wait: Dictionary = audio.last_stop_wait.duplicate()
	audio.start()
	audio.play_sound("rune")
	var old_music_id: int = audio.music_player.get_instance_id()
	var pending_finished: Callable = audio.music_player.finished.get_connections()[0].callable
	var before: Dictionary = audio.stop_report()
	check.call(audio.music_player.playing and before.players == 2 and before.pending_playbacks >= 2, "Explicit start and a real rune sound allocate observable music and effect playbacks")
	# Reproduce work already queued before permanent stop. Disconnection alone
	# does not cancel a callable already in the message queue.
	pending_finished.call_deferred()
	audio.play_sound.call_deferred("rune")
	audio.stop_all()
	var stopped_epoch: int = audio.stop_report().epoch
	audio.stop_all()
	check.call(audio.stop_report().epoch == stopped_epoch, "Repeated permanent stop is idempotent and does not invalidate another stop waiter")
	var drained: bool = await audio.wait_until_stopped()
	check.call(drained and audio.stop_report().players == 0 and audio.stop_report().pending_playbacks == 0, "Stop drains actual mixer-held references and queued players while stale loop/sound callbacks remain blocked")
	if not drained:
		return false
	var stopped_wait: Dictionary = audio.last_stop_wait.duplicate()
	audio.start()
	check.call(is_instance_valid(audio.music_player) and audio.music_player.get_instance_id() != old_music_id and audio.music_player.playing, "A later explicit start creates a working music player instead of accessing the freed stopped player")
	audio.music_player.stop()
	pending_finished.call()
	check.call(not audio.music_player.playing, "A completion captured in the old epoch cannot restart the replacement music player")
	audio.music_player.finished.emit()
	check.call(audio.music_player.playing, "The current epoch still loops music normally after an explicit restart")
	audio.play_sound("rune")
	audio.stop_all()
	var final_drained: bool = await audio.wait_until_stopped()
	check.call(final_drained and audio.stop_report().players == 0 and audio.stop_report().pending_playbacks == 0, "Restarted music and effects also release every actual playback before final shutdown")
	var report := {
		"scope":"Actual WAV playback lifetime, permanent stop, stale callbacks, idempotence and explicit restart; no fixed delay or muted audio substitute.",
		"audio_script_sha256":FileAccess.get_sha256("res://scripts/core/audio.gd"),
		"initial_gameplay_drain":initial_wait,
		"queued_callback_drain":stopped_wait,
		"restarted_drain":audio.last_stop_wait.duplicate(),
		"driver_mix_rate_hz":AudioServer.get_mix_rate(),
		"engine_sources":[
			"https://github.com/godotengine/godot/blob/4.7.2-stable/scene/audio/audio_stream_player_internal.cpp",
			"https://github.com/godotengine/godot/blob/4.7.2-stable/servers/audio/audio_server.cpp",
		],
		"engine_lifetime":"stop_basic clears player refs after requesting stop; server marks FADE_OUT_TO_DELETION, the mixer removes it, and AudioServer.update/maybe_cleanup performs the final unref on the main thread.",
	}
	var path := ProjectSettings.globalize_path("res://").path_join("../build/verification/character-integration/audio-lifecycle.json").simplify_path()
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report, "\t") + "\n")
	return final_drained
