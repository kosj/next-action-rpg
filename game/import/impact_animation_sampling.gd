@tool
extends EditorScenePostImport

# GLTFDocument bakes the whole scene at animation/fps. Only the two newly
# authored impact actions need 500Hz; all other source actions were authored
# on a 100Hz grid. Retain those original samples, endpoints and every channel.
# No geometric/error optimizer touches either set of clips.
const ORIGINAL_SAMPLE_HZ := 100.0
const PRECISE_ACTIONS: Array[StringName] = [&"charge", &"charged_heavy"]

func _post_import(scene: Node) -> Object:
	var removed := 0
	for node in scene.find_children("*", "AnimationPlayer", true, false):
		var player := node as AnimationPlayer
		for name: StringName in player.get_animation_list():
			if name in PRECISE_ACTIONS:
				continue
			var animation := player.get_animation(name)
			for track in range(animation.get_track_count()):
				for key in range(animation.track_get_key_count(track)-2, 0, -1):
					var grid_time := animation.track_get_key_time(track, key) * ORIGINAL_SAMPLE_HZ
					if absf(grid_time - roundf(grid_time)) > 0.0001:
						animation.track_remove_key(track, key)
						removed += 1
	print("RUNEFALL_IMPACT_IMPORT: retained original100Hz actions and new500Hz actions; removed upsampled keys=", removed)
	return scene
