extends Node

var sounds: Dictionary = {}
var music_player: AudioStreamPlayer
var _stopped: bool = false
var _music_requested: bool = false
var _lifecycle_epoch: int = 0
var _playbacks: Array[WeakRef] = []
var last_stop_wait: Dictionary = {}

func _ready() -> void:
	for key: String in ["slash", "hit", "parry", "dodge", "rune", "death", "ambience"]:
		sounds[key] = load("res://assets/audio/%s.wav" % key)
	_ensure_music_player()

func _ensure_music_player() -> void:
	if is_instance_valid(music_player) and not music_player.is_queued_for_deletion():
		return
	music_player = AudioStreamPlayer.new()
	music_player.stream = sounds.ambience
	music_player.volume_db = -20.0
	add_child(music_player)
	music_player.finished.connect(_on_music_finished.bind(_lifecycle_epoch))

func _on_music_finished(epoch: int) -> void:
	# A completion queued before stop_all must never restart a stopped or newly
	# replaced player. Only an explicit start() opens the next playback epoch.
	if _stopped or not _music_requested or epoch != _lifecycle_epoch or not is_instance_valid(music_player) or music_player.is_queued_for_deletion():
		return
	music_player.play()
	_track_playback(music_player)

func start() -> void:
	if _stopped:
		_lifecycle_epoch += 1
	_stopped = false
	_music_requested = true
	_ensure_music_player()
	if not music_player.playing:
		music_player.play()
		_track_playback(music_player)

func stop_all() -> void:
	if not _stopped:
		_lifecycle_epoch += 1
	_stopped = true
	_music_requested = false
	music_player = null
	for child in get_children():
		if child is AudioStreamPlayer:
			_track_playback(child)
			for connection in child.finished.get_connections():
				child.finished.disconnect(connection.callable)
			child.stop()
			child.stream = null
			child.queue_free()

func _prune_playbacks() -> void:
	var live: Array[WeakRef] = []
	for reference in _playbacks:
		if reference.get_ref() != null:
			live.append(reference)
	_playbacks = live

func _track_playback(player: AudioStreamPlayer) -> void:
	_prune_playbacks()
	if not player.has_stream_playback():
		return
	var playback := player.get_stream_playback()
	for reference in _playbacks:
		if reference.get_ref() == playback:
			return
	_playbacks.append(weakref(playback))

func stop_report() -> Dictionary:
	_prune_playbacks()
	var players := 0
	for child in get_children():
		if child is AudioStreamPlayer:
			players += 1
	return {"stopped":_stopped, "pending_playbacks":_playbacks.size(), "players":players, "epoch":_lifecycle_epoch}

func wait_until_stopped(timeout_seconds: float = 8.0) -> bool:
	if not _stopped or not is_finite(timeout_seconds) or timeout_seconds <= 0.0:
		return false
	var epoch := _lifecycle_epoch
	var started := Time.get_ticks_usec()
	var frames := 0
	var initial: Dictionary = stop_report()
	# Player.stop() requests a mixer fade; AudioServer releases that playback
	# only after mixing and main-thread cleanup. A SceneTree timer or playing=
	# false does not prove its final reference is gone. Observe WeakRefs without
	# keeping a strong playback reference alive across an await.
	while _stopped and epoch == _lifecycle_epoch:
		var report := stop_report()
		if report.players == 0 and report.pending_playbacks == 0:
			last_stop_wait = {"seconds":(Time.get_ticks_usec()-started)/1000000.0, "frames":frames, "initial_pending_playbacks":initial.pending_playbacks, "pending_playbacks":0, "players":0}
			return true
		if Time.get_ticks_usec()-started >= timeout_seconds*1000000.0:
			last_stop_wait = {"seconds":(Time.get_ticks_usec()-started)/1000000.0, "frames":frames, "pending_playbacks":report.pending_playbacks, "players":report.players}
			push_error("Audio shutdown did not release its actual players/playbacks: %s" % last_stop_wait)
			return false
		await get_tree().process_frame
		frames += 1
	return false # A caller explicitly resumed audio during this shutdown.

func play_sound(key: String, pitch: float = 1.0) -> void:
	if _stopped or not sounds.has(key):
		return
	var player := AudioStreamPlayer.new()
	player.stream = sounds[key]
	player.pitch_scale = pitch
	player.volume_db = -8.0
	add_child(player)
	player.finished.connect(player.queue_free)
	player.play()
	_track_playback(player)

func _process(_delta: float) -> void:
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(Session.volume, 0.0001)))
