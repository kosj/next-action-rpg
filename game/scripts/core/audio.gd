extends Node

var sounds: Dictionary = {}
var music_player: AudioStreamPlayer
var _stopped: bool = false
var _music_requested: bool = false
var _lifecycle_epoch: int = 0
var _playbacks: Array[WeakRef] = []
var last_stop_wait: Dictionary = {}
const MAX_EFFECT_PLAYERS := 32
const IMPACT_KEYS: Array[String] = ["contact_tick", "metal_light", "metal_heavy", "body_thump", "charge_sub", "debris_tail", "metal_block", "swing_heavy", "swing_charged"]
var _last_attack: Dictionary = {}
var _last_impact: Dictionary = {}

func _ready() -> void:
	for key: String in ["slash", "hit", "parry", "dodge", "rune", "death", "ambience"]:
		sounds[key] = load("res://assets/audio/%s.wav" % key)
	for key: String in IMPACT_KEYS:
		sounds["impact_"+key] = load("res://assets/audio/impact/%s.wav" % key)
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
	_play_clip(key, pitch, -8.0)

func _effect_player_count() -> int:
	var count := 0
	for child in get_children():
		if child is AudioStreamPlayer and child != music_player and not child.is_queued_for_deletion():
			count += 1
	return count

func _play_clip(key: String, pitch: float, volume_db: float) -> bool:
	if _stopped or not sounds.has(key) or not is_finite(pitch) or pitch <= 0.0 or not is_finite(volume_db):
		return false
	if _effect_player_count() >= MAX_EFFECT_PLAYERS:
		return false
	var player := AudioStreamPlayer.new()
	player.stream = sounds[key]
	player.pitch_scale = clampf(pitch, 0.25, 4.0)
	player.volume_db = volume_db
	player.set_meta("sound_key", key)
	add_child(player)
	player.finished.connect(player.queue_free)
	player.play()
	_track_playback(player)
	return true

func play_attack(attack_id: String, pitch: float = 1.0) -> void:
	# This is an attack-start swing, including whiffs. No contact/low-end layer.
	var key := "slash"
	if attack_id == "charged_heavy":
		key = "impact_swing_charged"
	elif attack_id == "heavy":
		key = "impact_swing_heavy"
	if attack_id.is_empty():
		_last_attack = {"accepted":false, "reason":"empty_attack"}
		return
	var gain := -11.0 if key == "impact_swing_charged" else (-12.0 if key == "impact_swing_heavy" else -8.0)
	var played := _play_clip(key, pitch, gain)
	_last_attack = {"accepted":played, "attack_id":attack_id, "pitch":pitch,
		"phase":"attack_start_swing_only", "sound_key":key, "impact_layers":0}

func _impact_profile(context: Dictionary) -> Dictionary:
	var strength := String(context.get("strength", "light"))
	if bool(context.get("blocked", false)):
		return {"style":"blocked_metal", "layers":[{"key":"contact_tick", "db":-22.0}, {"key":"metal_block", "db":-13.0}, {"key":"debris_tail", "db":-28.0}]}
	if strength == "charged":
		return {"style":"charged", "layers":[{"key":"contact_tick", "db":-17.0}, {"key":"metal_heavy", "db":-13.0}, {"key":"body_thump", "db":-15.0}, {"key":"charge_sub", "db":-18.0}, {"key":"debris_tail", "db":-23.0}]}
	if strength in ["heavy", "skill"]:
		return {"style":strength, "layers":[{"key":"contact_tick", "db":-17.0}, {"key":"metal_heavy", "db":-15.0}, {"key":"body_thump", "db":-14.0}, {"key":"debris_tail", "db":-25.0}]}
	return {"style":"light", "layers":[{"key":"contact_tick", "db":-18.0}, {"key":"metal_light", "db":-18.0}]}

func play_impact(context: Dictionary) -> void:
	# Only the confirmed impact dispatcher calls this API. The context is copied
	# as scalar/value diagnostics; it cannot grant damage or delayed effects.
	_last_impact = {"accepted":false, "reason":"invalid_confirmed_context"}
	if _stopped or String(context.get("attack_id", "")).is_empty():
		return
	if not String(context.get("contact_source", "")) in ["hurtbox_ray", "hurtbox_proxy"]:
		return
	if not String(context.get("strength", "")) in ["light", "heavy", "charged", "skill"]:
		return
	for key: String in ["point", "normal", "direction"]:
		var value: Variant = context.get(key)
		if not value is Vector3 or not value.is_finite():
			return
	var profile := _impact_profile(context)
	var played: Array[Dictionary] = []
	# A dense same-frame crowd must not simply sum full-level transients. Start
	# every layer now (no timer callback), using the current live voice density.
	var density_db := -linear_to_db(1.0+float(_effect_player_count())/4.0)-1.5
	for layer: Dictionary in profile.layers:
		var gain := float(layer.db)+density_db
		if _play_clip("impact_"+String(layer.key), 1.0, gain):
			played.append({"key":String(layer.key), "volume_db":gain})
	_last_impact = {"accepted":not played.is_empty(), "style":String(profile.style),
		"attack_id":String(context.attack_id), "strength":String(context.strength),
		"blocked":bool(context.get("blocked", false)), "killed":bool(context.get("killed", false)),
		"poise_broken":bool(context.get("poise_broken", false)), "contact_source":String(context.contact_source),
		"point":context.point, "layers":played, "density_headroom_db":density_db, "epoch":_lifecycle_epoch}

func presentation_report() -> Dictionary:
	return {"last_attack":_last_attack.duplicate(true), "last_impact":_last_impact.duplicate(true),
		"effect_players":_effect_player_count(), "effect_player_budget":MAX_EFFECT_PLAYERS,
		"stopped":_stopped, "epoch":_lifecycle_epoch}

func _process(_delta: float) -> void:
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(Session.volume, 0.0001)))
