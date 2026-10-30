extends Node

var sounds: Dictionary = {}
var music_player: AudioStreamPlayer

func _ready() -> void:
	for key: String in ["slash", "hit", "parry", "dodge", "rune", "death", "ambience"]:
		sounds[key] = load("res://assets/audio/%s.wav" % key)
	music_player = AudioStreamPlayer.new()
	music_player.stream = sounds.ambience
	music_player.volume_db = -20.0
	add_child(music_player)
	music_player.finished.connect(music_player.play)

func start() -> void:
	if not music_player.playing:
		music_player.play()

func stop_all() -> void:
	for child in get_children():
		if child is AudioStreamPlayer:
			child.stop()
			child.stream = null
			child.queue_free()

func play_sound(key: String, pitch: float = 1.0) -> void:
	if not sounds.has(key):
		return
	var player := AudioStreamPlayer.new()
	player.stream = sounds[key]
	player.pitch_scale = pitch
	player.volume_db = -8.0
	add_child(player)
	player.finished.connect(player.queue_free)
	player.play()

func _process(_delta: float) -> void:
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(Session.volume, 0.0001)))
