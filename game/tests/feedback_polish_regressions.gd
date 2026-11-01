extends RefCounted

# Native presentation fixtures: actual skinned actor/mesh, Camera3D projection
# and PhysicsServer occlusion. No input, damage, animation authoring or AV pass.
static func _contact() -> Dictionary:
	var point: Vector3 = Vector3(0,1.2,-2)
	return {"attack_id":"charged_heavy","strength":"charged","point":point,
		"normal":Vector3.BACK,"direction":Vector3.FORWARD,"contact_source":"hurtbox_ray",
		"contact_blade_grip":point-Vector3.UP*0.4,"contact_blade_tip":point+Vector3.UP*0.79,
		"contact_blade_motion":Vector3.RIGHT*4.0,"blocked":false,"material":"metal"}

static func _wall(parent: Node3D, point: Vector3, size: Vector3) -> StaticBody3D:
	var body: StaticBody3D = StaticBody3D.new()
	body.collision_layer = 1
	var shape: CollisionShape3D = CollisionShape3D.new()
	var box: BoxShape3D = BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.add_child(shape)
	parent.add_child(body)
	body.position = point
	return body

static func run(world: Node3D, check: Callable) -> bool:
	var viewport: SubViewport = SubViewport.new()
	viewport.size = Vector2i(390,844)
	viewport.own_world_3d = true
	world.add_child(viewport)
	var stage: Node3D = Node3D.new()
	viewport.add_child(stage)
	var hero: RunePlayer = RunePlayer.new()
	stage.add_child(hero)
	hero.active = false
	hero.set_physics_process(false)
	hero.position.y = -hero.visual.ground_offset_y
	var enemy: RuneEnemy = RuneEnemy.new()
	enemy.player = hero
	stage.add_child(enemy)
	enemy.set_physics_process(false)
	enemy.position = Vector3(0,0,-7)
	var rig: RuneCamera = RuneCamera.new()
	rig.player = hero
	stage.add_child(rig)
	rig.set_physics_process(false)
	rig.cinematic = false
	var saved_shake: bool = Session.shake
	Session.shake = false
	rig.snap()
	var initial: Transform3D = rig.camera.global_transform
	rig._physics_process(1.0/60.0)
	check.call(rig.camera.global_transform.is_equal_approx(initial),"Free camera snap and first follow frame use the same composition without the old6.7m startup jump")
	var portrait: Dictionary = rig.framing_report()
	var baseline: Camera3D = Camera3D.new()
	stage.add_child(baseline)
	baseline.fov = 56
	baseline.global_position = hero.global_position+Vector3.UP*1.4+Vector3(0.65,2.1+sin(-0.18)*6.0,6.7*cos(-0.18))
	baseline.look_at(hero.global_position+Vector3.UP*1.6)
	var sole: Vector3 = hero.global_position+Vector3.UP*hero.visual.ground_offset_y
	var top: Vector3 = sole+Vector3.UP*1.82
	var old_height: float = absf(baseline.unproject_position(sole).y-baseline.unproject_position(top).y)/844.0
	var ratio: float = float(portrait.subjects[0].height_fraction)/old_height
	check.call(ratio>1.20 and ratio<1.45 and float(portrait.subjects[0].nominal_foot_uv[1])<0.80 and float(portrait.subjects[0].nominal_head_uv[1])>0.05,
		"Actual portrait projection enlarges nominal hero by20–45% while reserving the bottom20% for actions")
	baseline.free()
	hero.locked_target = enemy
	rig.snap()
	for index in range(45):
		rig._physics_process(1.0/60.0)
	var locked: Dictionary = rig.framing_report()
	var both_inside: bool = locked.subjects.size()==2
	for subject: Dictionary in locked.subjects:
		both_inside = both_inside and not subject.behind_camera and float(subject.nominal_foot_uv[1])<0.82 and float(subject.nominal_head_uv[1])>0.03
	check.call(both_inside and locked.follow_distance>=RuneCamera.FREE_DISTANCE and locked.follow_distance<=RuneCamera.MAX_LOCK_DISTANCE,
		"A settled far lock keeps both nominal bodies in the portrait frame with bounded physical camera distance")
	hero.locked_target = null
	rig.snap()
	var contact: Dictionary = _contact()
	var unconfirmed: Dictionary = contact.duplicate(true)
	unconfirmed.contact_source = "attack_start"
	rig.apply_impact(unconfirmed)
	check.call(not rig.impact_report().last_context_accepted and rig.impact_amplitude==0.0,"An attack-start or whiff packet cannot create a camera contact impulse")
	Session.shake = true
	rig.apply_impact(contact)
	rig._physics_process(0.04)
	check.call(rig.camera.fov<56.0 and rig.camera.fov>54.0 and rig.camera.global_position.distance_to(rig._follow_position)<0.09,
		"Confirmed charged feedback has a short limited FOV and positional impulse")
	rig._physics_process(0.30)
	check.call(is_equal_approx(rig.camera.fov,56.0),"The contact FOV returns to56 without altering the follow framing")
	Session.shake = false
	rig.snap()
	rig.apply_impact(contact)
	rig._physics_process(0.04)
	check.call(is_equal_approx(rig.camera.fov,56.0) and rig.camera.global_position.is_equal_approx(rig._follow_position),"Shake off suppresses all new contact camera displacement and FOV emphasis")
	var effect: RuneImpactEffect = RuneImpactEffect.new()
	stage.add_child(effect)
	var original: Dictionary = contact.duplicate(true)
	effect.setup(contact,1)
	check.call(effect.presentation_report().cut_visible and effect.presentation_report().triangles>0,"A first-active confirmed contact already has a core/stroke without inventing earlier trail samples")
	effect._process(0.025)
	var cut_mesh: ImmediateMesh = effect._meshes.cut
	var cut_bounds: Vector3 = cut_mesh.get_aabb().size
	check.call(cut_bounds.x>cut_bounds.y*3.0 and effect.presentation_report().cut_basis_source=="confirmed_blade_motion" and contact==original,
		"Actual contact mesh follows the confirmed horizontal blade-motion plane and leaves the packet immutable")
	var turned: Dictionary = contact.duplicate(true)
	turned.contact_blade_motion = Vector3.UP*4.0
	turned.contact_blade_grip = Vector3(contact.point)-Vector3.RIGHT*0.4
	turned.contact_blade_tip = Vector3(contact.point)+Vector3.RIGHT*0.79
	var rotated: RuneImpactEffect = RuneImpactEffect.new()
	stage.add_child(rotated)
	rotated.setup(turned,0)
	rotated._process(0.025)
	var rotated_mesh: ImmediateMesh = rotated._meshes.cut
	var rotated_bounds: Vector3 = rotated_mesh.get_aabb().size
	check.call(rotated_bounds.y>rotated_bounds.x*3.0 and rotated.presentation_report().spark_count<=10 and rotated.get_child_count()==5,
		"Rotating the real packet rotates the emitted stroke; lower quality retains direction within10sparks/five mesh groups")
	var depth_tested: bool = true
	for child in effect.get_children():
		var instance: MeshInstance3D = child as MeshInstance3D
		var material: StandardMaterial3D = instance.material_override
		depth_tested = depth_tested and not material.no_depth_test and material.depth_draw_mode==BaseMaterial3D.DEPTH_DRAW_DISABLED
	check.call(depth_tested,"Every actual contact material tests depth and avoids writing a transparent screen-covering depth layer")
	var rejected: RuneImpactEffect = RuneImpactEffect.new()
	stage.add_child(rejected)
	rejected.setup(unconfirmed,1)
	check.call(rejected.is_queued_for_deletion() and not rejected.presentation_report().valid,"Unconfirmed contexts cannot allocate a contact presentation")
	var data: AttackData = load("res://data/charged_heavy.tres")
	var snapshot: Dictionary = {"speed":0.0,"presentation_epoch":85201,"attack_id":"charged_heavy","attack_elapsed":data.startup,
		"attack_duration":data.duration(),"attack_startup":data.startup,"attack_active":data.active}
	var visual: ActorVisual = hero.visual
	visual.blade_trail.reset()
	visual.pose(1.0/60.0,0.0,-1.0,false,false,false,snapshot)
	check.call(visual.blade_trail.presentation_report().samples==1 and not visual.blade_trail.visible,"First-active contact may legitimately contain one actual blade sample and no swept area")
	snapshot.attack_elapsed = data.startup+0.02
	visual.pose(0.02,0.0,-1.0,false,false,false,snapshot)
	var trail: BladeTrail = visual.blade_trail
	var layered: bool = trail.mesh!=null and trail.mesh.get_surface_count()==2
	check.call(layered,"Two actual forward charged samples produce the layered trail")
	if not layered:
		Session.shake = saved_shake
		viewport.free()
		return false
	var mesh_id: int = trail.mesh.get_instance_id() if trail.mesh!=null else 0
	var tip: Node3D = visual.rig_weapon.find_child("BladeTip",true,false) as Node3D
	var edge: PackedVector3Array = trail.mesh.surface_get_arrays(1)[Mesh.ARRAY_VERTEX]
	check.call(trail.mesh.get_surface_count()==2 and edge[-1].distance_to(tip.global_position)<0.0001,
		"The actual charged trail adds a separate narrow edge that ends at the displayed physical sword tip")
	snapshot.attack_elapsed = data.startup+0.04
	visual.pose(0.02,0.0,-1.0,false,false,false,snapshot)
	check.call(trail.mesh.get_instance_id()==mesh_id and trail.presentation_report().triangles<=44,"Charged emission reuses its mesh resource and bounds two-layer geometry")
	var frozen: Array = trail.mesh.surface_get_arrays(1)
	visual.pose(0.0,0.0,-1.0,false,false,false,snapshot)
	check.call(trail.mesh.surface_get_arrays(1)==frozen,"Zero-delta hitstop preserves the complete charged edge geometry and colors")
	effect._process(RuneImpactEffect.MAX_LIFETIME)
	rotated._process(RuneImpactEffect.MAX_LIFETIME)
	check.call(effect.is_queued_for_deletion() and rotated.is_queued_for_deletion(),"Both contact quality modes release within the existing bounded lifetime")
	Session.shake = true
	rig.snap()
	# Nominal ray misses this side post, but the positive-X kick enters it.
	# Only the second query can keep the final kicked camera outside the post.
	var post: StaticBody3D = _wall(stage,Vector3(0.585,2.0,5.3),Vector3(0.05,2.0,1.0))
	await world.get_tree().physics_frame
	await world.get_tree().physics_frame
	var side_hit: Dictionary = contact.duplicate(true)
	side_hit.direction = Vector3.RIGHT
	side_hit.normal = Vector3.LEFT
	rig.apply_impact(side_hit)
	rig._physics_process(0.04)
	var post_box: AABB = AABB(post.position-Vector3(0.025,1.0,0.5),Vector3(0.05,2.0,1.0))
	check.call(not post_box.has_point(rig.camera.global_position) and rig.camera.global_position.x<0.50,"Final impact displacement is rechecked against a side obstacle missed by the unshaken follow ray")
	var path: String = ProjectSettings.globalize_path("res://../build/verification/combat-feedback/native.json").simplify_path()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file: FileAccess = FileAccess.open(path,FileAccess.WRITE)
	if file!=null:
		file.store_string(JSON.stringify({"scope":"Native actual projection, skin-marker ribbon, emitted mesh/material, bounded lifecycle and physics-ray presentation fixtures only; no real-input/continuousAV/targetGPU/AAA approval",
			"portrait":portrait,"portrait_height_ratio_vs_v019":ratio,"far_lock":locked,
			"cut_aabb":cut_bounds,"rotated_cut_aabb":rotated_bounds,"charged_trail":trail.presentation_report(),
			"source_sha256":{"effect":FileAccess.get_sha256("res://scripts/world/impact_effect.gd"),"trail":FileAccess.get_sha256("res://scripts/actors/blade_trail.gd"),"camera":FileAccess.get_sha256("res://scripts/world/camera_rig.gd")}},"\t")+"\n")
	Session.shake = saved_shake
	viewport.free()
	return true
