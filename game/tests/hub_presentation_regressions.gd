extends RefCounted

const HUB_NPC = preload("res://scripts/world/hub_npc.gd")

static func _tick(tree: SceneTree) -> void:
	await tree.physics_frame
	await tree.process_frame

static func _static_physics(sanctuary: Node3D) -> Array:
	var signature := []
	for node in sanctuary.find_children("*", "CollisionObject3D", true, false):
		var body := node as CollisionObject3D
		signature.append([body.get_instance_id(), body.get_rid().get_id(), body.global_transform, body.collision_layer, body.collision_mask])
	return signature

static func _grounding(world: Node3D, npcs: Array[Node3D], check: Callable) -> void:
	var tree := world.get_tree()
	var saved_paused := tree.paused
	var saved_quality := Session.quality
	var physics_before := _static_physics(world.sanctuary)
	tree.paused = false
	Session.quality = 0
	world.call("apply_quality")
	var before_queries := []
	for npc in npcs:
		check.call(not npc.grounding_shadow.presentation_report().visible, "Balanced hub mode hides its ellipse immediately under actual light shadows")
		before_queries.append(npc.grounding_shadow.presentation_report().query_count)
	Session.quality = 1
	world.call("apply_quality")
	for index in range(3):
		await _tick(tree)
	var query_counts := []
	for npc in npcs:
		var shadow: Node3D = npc.grounding_shadow
		var report: Dictionary = shadow.presentation_report()
		check.call(report.visible and report.cached_ground and report.reason == "static_hub_grounding" and report.query_count > 0 and not report.query_pending, "Performance hub ellipse measures real registered layer1 support once")
		check.call(Vector3(report.ground_normal[0],report.ground_normal[1],report.ground_normal[2]).dot(Vector3.UP) >= 0.65 and shadow.patch.global_basis.y.normalized().dot(Vector3.UP) > 0.999, "Hub ellipse aligns with the actual upward floor normal")
		var ground := Vector3(report.ground_point[0],report.ground_point[1],report.ground_point[2])
		check.call(shadow.patch.global_position.distance_to(ground+Vector3.UP*0.012) < 0.00001 and report.opacity > 0.0 and report.opacity <= 0.210001, "Hub ellipse stays12mm above the measured flat support with bounded softness")
		check.call(report.static_root_only and not report.actor_budget_shared and report.maximum_visible == 2 and not report.gameplay_authority, "Hub grounding has its own two-root static scope, separate from eight actor ellipses")
		check.call(shadow.get_child_count() == 1 and shadow.get_child(0) is MeshInstance3D and shadow.patch.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_OFF, "Hub grounding adds one non-casting mesh without new collision, light or navigation nodes")
		query_counts.append(report.query_count)
	for index in range(npcs.size()):
		check.call(query_counts[index] == before_queries[index] + 1, "Each performance refresh uses exactly one actual support query per authored NPC")
	for index in range(3):
		await _tick(tree)
	for index in range(npcs.size()):
		check.call(npcs[index].grounding_shadow.presentation_report().query_count == query_counts[index], "Stationary hub support does not run continuous floor queries")
	if npcs.size() == 2:
		var first: Node3D = npcs[0].grounding_shadow
		var second: Node3D = npcs[1].grounding_shadow
		check.call(first.patch.mesh == second.patch.mesh and first.material != second.material and first.material.shader == second.material.shader, "Two hub roots share the quad/shader but own their opacity materials")
		var saved_transform := npcs[0].global_transform
		npcs[0].position.x += 0.1
		await tree.process_frame
		check.call(not first.presentation_report().visible and first.presentation_report().query_count == query_counts[0], "Moving outside the static root contract hides the patch without adding tracking queries")
		npcs[0].global_transform = saved_transform
		await tree.process_frame
	Session.quality = 0
	world.call("apply_quality")
	for npc in npcs:
		check.call(not npc.grounding_shadow.presentation_report().visible, "Returning to balanced mode immediately removes the hub approximation")
	check.call(_static_physics(world.sanctuary) == physics_before and GroundingShadow.visible_budget_used() <= 8, "Hub presentation preserves actual static collision RIDs/transforms/layers and the original eight-actor budget")
	Session.quality = saved_quality
	world.call("apply_quality")
	for index in range(3):
		await _tick(tree)
	tree.paused = saved_paused

static func run(world: Node3D, check: Callable) -> bool:
	var sanctuary: Node3D = world.get("sanctuary")
	var npcs: Array[Node3D] = []
	var relics: Array[Node3D] = []
	for node in sanctuary.get_children():
		if node.has_meta("npc"):
			npcs.append(node)
		if node.has_meta("checkpoint"):
			relics.append(node)
	npcs.sort_custom(func(a: Node, b: Node): return a.get_meta("npc") < b.get_meta("npc"))
	check.call(npcs.size() == 2, "Hub retains the two story-role roots")
	for index in range(npcs.size()):
		var npc := npcs[index]
		var role: String = ["erin", "roen"][index]
		var report: Dictionary = npc.presentation_report()
		check.call(report.role == role and report.asset_ready and report.mode == "asset_idle", "Hub " + role + " uses its actual idle asset, without a production fallback claim")
		check.call(report.source_path == HUB_NPC.ROLE_PATHS[role] and report.rigged and report.skinned_meshes > 0, "Hub " + role + " reports actual packed source and skinned rig")
		check.call(report.mesh_nodes > 0 and report.surfaces > 0 and report.vertices > 0 and report.triangles > 0 and not report.materials.is_empty(), "Hub " + role + " reports actual geometry and materials independently of bounds")
		check.call(npc.position.is_equal_approx(sanctuary.npc_positions[index]) and npc.scale.is_equal_approx(Vector3.ONE), "Hub placement and authored metre scale remain outside the presenter")
		var toward_spawn: Vector3 = (Sanctuary.CHECKPOINTS[0] - npc.global_position).normalized()
		check.call((-npc.global_basis.z).normalized().dot(toward_spawn) > 0.9999, "Canonical minus-Z hub model faces the original spawn exactly once")
		check.call(npc.process_mode == Node.PROCESS_MODE_PAUSABLE and not npc.is_in_group("enemies"), "Hub idle stays pausable and outside enemy gameplay")
		var player: AnimationPlayer = npc.get_idle_player()
		if player != null:
			check.call(player.get_animation("idle").loop_mode == Animation.LOOP_LINEAR and player.is_playing(), "Hub idle loops on its independent AnimationPlayer")
	await _grounding(world, npcs, check)
	# A second real instance must own its mutable loop/clock resources.
	if not npcs.is_empty() and npcs[0].get_idle_player() != null:
		var tree := world.get_tree()
		var was_paused := tree.paused
		tree.paused = true
		var duplicate := HUB_NPC.new()
		duplicate.configure("erin")
		world.add_child(duplicate)
		var first: AnimationPlayer = npcs[0].get_idle_player()
		var second: AnimationPlayer = duplicate.get_idle_player()
		check.call(second != null and first != second, "Each hub instance owns its own player")
		if second != null:
			check.call(second.is_playing() and is_zero_approx(second.current_animation_position), "Mounting inside an already-paused tree samples idle at time zero")
			check.call(first.get_animation("idle") != second.get_animation("idle"), "Loop preparation duplicates Animation resources rather than editing shared imports")
			var source := load(HUB_NPC.ROLE_PATHS.erin) as PackedScene
			var source_instance := source.instantiate()
			for source_player in source_instance.find_children("*", "AnimationPlayer", true, false):
				for clip in source_player.get_animation_list():
					if String(clip).get_file() == "idle":
						var source_idle: Animation = source_player.get_animation(clip)
						check.call(source_idle != second.get_animation("idle") and source_idle.loop_mode == int(duplicate.presentation_report().source_idle_loop), "The cached imported idle retains its original resource and loop setting")
			source_instance.free()
			var before := first.current_animation_position
			second.seek(second.get_animation("idle").length * 0.5, true)
			check.call(is_equal_approx(before, first.current_animation_position), "Sampling another idle does not advance the existing NPC clock")
			var paused_clock := first.current_animation_position
			await tree.process_frame
			await tree.process_frame
			check.call(is_equal_approx(first.current_animation_position, paused_clock), "Hub idle freezes when the real scene tree pauses")
		tree.paused = was_paused
		if second != null and not was_paused:
			var resumed_clock := first.current_animation_position
			await tree.process_frame
			await tree.process_frame
			check.call(not is_equal_approx(first.current_animation_position, resumed_clock), "The existing hub idle advances again after the real tree resumes")
		duplicate.queue_free()
		await world.get_tree().process_frame
	var missing := HUB_NPC.new()
	missing.configure("unknown_story_role")
	world.add_child(missing)
	var missing_report: Dictionary = missing.presentation_report()
	check.call(not missing_report.asset_ready and missing_report.mode == "fallback" and missing_report.failure == "unknown_role", "Missing role assets stay explicit fallback presentations")
	missing.queue_free()
	await world.get_tree().process_frame
	check.call(relics.size() == 3 and sanctuary.crystals.size() == 3, "Three original checkpoint roots retain separate crystal pivots")
	for relic in relics:
		var index: int = relic.get_meta("checkpoint")
		var report: Dictionary = relic.presentation_report()
		check.call(relic.position.is_equal_approx(Sanctuary.CHECKPOINTS[index] + Vector3(2,0,0)), "Relic visuals retain the checkpoint's original offset")
		check.call(relic.get_crystal_pivot().position.is_equal_approx(Vector3(0,1.35,0)) and sanctuary.crystals[index] == relic.get_crystal_pivot(), "Sanctuary alone owns the original rotating crystal pivot")
		check.call(report.get("mesh_nodes", 0) == 5 and report.get("triangles", 0) == 2068, "Relic actual mesh payload matches the bounded five-surface design")
		for child in relic.find_children("*", "", true, false):
			check.call(not (child is CollisionObject3D or child is CollisionShape3D or child is Light3D or child is NavigationRegion3D or child is Timer), "Relic descendants have no gameplay, light or timer authority")
	# Preserve the existing NPC-over-checkpoint priority, including the overlap.
	var player: Node3D = world.get("player")
	var saved_position := player.global_position
	var saved_encounter: int = world.get("active_encounter")
	var saved_kind: String = world.get("interaction_kind")
	var saved_index: int = world.get("interaction_index")
	var saved_hint: String = world.ui.interaction.text
	world.set("active_encounter", -1)
	for point in [Vector3(0,0,6), Vector3(1,0,7), Vector3(2,0,6), Vector3(-4,0,5), Vector3(4,0,5)]:
		player.global_position = point
		world.call("update_interaction")
		var expected_kind := "checkpoint" if point.x in [0.0,1.0] else "npc"
		var expected_index := 0 if point.x <= 1.0 else 1
		check.call(world.get("interaction_kind") == expected_kind and world.get("interaction_index") == expected_index, "Hub art preserves existing interaction priority at " + str(point))
	player.global_position = saved_position
	world.set("active_encounter", saved_encounter)
	world.set("interaction_kind", saved_kind)
	world.set("interaction_index", saved_index)
	world.ui.interaction.text = saved_hint
	return true
