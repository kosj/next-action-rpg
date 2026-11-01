class_name AttackData
extends Resource

@export var title: String = "베기"
@export var damage: float = 18.0
@export var poise: float = 14.0
@export var startup: float = 0.13
@export var active: float = 0.17
@export var recovery: float = 0.22
@export var reach: float = 2.7
@export var arc: float = 130.0
@export var lunge: float = 3.5
@export var parryable: bool = true
@export var phase_lunge: bool = false
@export var startup_lunge: float = 0.0
@export var active_lunge: float = 0.0
@export var recovery_lunge: float = 0.0
@export var impact_strength: String = ""
@export var physical_blade_sweep: bool = false
@export var blade_grip_start: Vector3 = Vector3.ZERO
@export var blade_grip_end: Vector3 = Vector3.ZERO
@export var blade_pitch_start: float = 50.0
@export var blade_pitch_end: float = -45.0
@export var blade_length: float = 1.19
@export var blade_radius: float = 0.12
@export var blade_damage_start_fraction: float = 0.0
@export var blade_curve_path: String = ""
@export var blade_curve_sha256: String = ""
var _curve_cache_key: String = ""
var _curve_report: Dictionary = {}
var _curve_grips: PackedVector3Array = PackedVector3Array()
var _curve_tips: PackedVector3Array = PackedVector3Array()

func blade_curve_report() -> Dictionary:
	_load_blade_curve()
	return _curve_report.duplicate(true)

func _valid_sha(value: String) -> bool:
	if value.length() != 64:
		return false
	for index in range(value.length()):
		if not "0123456789abcdef".contains(value.substr(index,1).to_lower()):
			return false
	return true

func _finite_number(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value))

func _vector_value(value: Variant) -> bool:
	if not value is Array or value.size() != 3:
		return false
	for component in value:
		if not _finite_number(component):
			return false
	return true

func blade_curve_validation_error(document: Variant) -> String:
	if not document is Dictionary:
		return "Blade curve must be an object"
	if document.get("schema_version") != 1 or document.get("coordinate_system") != "actor_y_up_minus_z_forward":
		return "Blade curve schema or coordinate frame is incompatible"
	for key in ["active_start_s","active_duration_s","sample_step_s","blade_length_m","floor_offset_m"]:
		if not _finite_number(document.get(key)):
			return "Blade curve requires finite numeric metadata: %s" % key
	if absf(float(document.active_start_s)-startup) > .000001 or absf(float(document.active_duration_s)-active) > .000001 or absf(float(document.blade_length_m)-blade_length) > .000001:
		return "Blade curve timing or weapon length disagrees with AttackData"
	if absf(float(document.floor_offset_m)-.025) > .000001:
		return "Blade curve must include the canonical capsule-floor offset once"
	var step := float(document.sample_step_s)
	if step <= 0.0 or step > .002001 or active <= 0.0:
		return "Blade curve sampling must be at least 500Hz"
	var intervals := roundi(active/step)
	if absf(intervals*step-active) > .000001:
		return "Blade curve sample grid must span the full active window"
	var metadata: Variant = document.get("source_metadata")
	if not metadata is Dictionary or not metadata.get("asset_path") is String or not _valid_sha(String(metadata.get("sha256",""))):
		return "Blade curve requires a source asset path and SHA256"
	if String(metadata.asset_path).is_empty() or not String(metadata.asset_path).ends_with(".glb"):
		return "Blade curve source must identify its authored GLB"
	var samples: Variant = document.get("samples")
	if not samples is Array or samples.size() != intervals+1:
		return "Blade curve must include every uniform sample and both endpoints"
	var previous_grip := Vector3.ZERO
	var previous_tip := Vector3.ZERO
	for index in range(samples.size()):
		var row: Variant = samples[index]
		if not row is Dictionary or not _finite_number(row.get("time_s")) or not _vector_value(row.get("grip")) or not _vector_value(row.get("tip")):
			return "Blade curve has an invalid sample"
		if absf(float(row.time_s)-(startup+index*step)) > .000001:
			return "Blade curve sample timestamps are missing or out of order"
		var grip := Vector3(row.grip[0],row.grip[1],row.grip[2])
		var tip := Vector3(row.tip[0],row.tip[1],row.tip[2])
		if grip.length() > 5.0 or tip.length() > 5.0 or absf(grip.distance_to(tip)-blade_length) > .0001:
			return "Blade curve sample length or actor-local bounds are invalid"
		if index > 0 and absf(previous_grip.lerp(grip,.5).distance_to(previous_tip.lerp(tip,.5))-blade_length) > .002:
			return "Blade curve interpolation chord exceeds the 2mm length budget"
		previous_grip = grip
		previous_tip = tip
	return ""

func _load_blade_curve() -> bool:
	var key := "%s|%s|%.9f|%.9f|%.9f" % [blade_curve_path,blade_curve_sha256.to_lower(),startup,active,blade_length]
	if key == _curve_cache_key:
		return bool(_curve_report.get("ok",false))
	_curve_cache_key = key
	_curve_grips.clear()
	_curve_tips.clear()
	_curve_report = {"ok":false,"reason":"Blade curve path or SHA256 is missing","path":blade_curve_path}
	if blade_curve_path.is_empty() or not _valid_sha(blade_curve_sha256):
		return false
	if not FileAccess.file_exists(blade_curve_path) or FileAccess.get_sha256(blade_curve_path) != blade_curve_sha256.to_lower():
		_curve_report.reason = "Blade curve is missing or its pinned SHA256 does not match"
		return false
	var document: Variant = JSON.parse_string(FileAccess.get_file_as_string(blade_curve_path))
	var reason := blade_curve_validation_error(document)
	if not reason.is_empty():
		_curve_report.reason = reason
		return false
	for row in document.samples:
		_curve_grips.append(Vector3(row.grip[0],row.grip[1],row.grip[2]))
		_curve_tips.append(Vector3(row.tip[0],row.tip[1],row.tip[2]))
	_curve_report = {"ok":true,"reason":"","path":blade_curve_path,"sha256":blade_curve_sha256.to_lower(),
		"source_asset_path":String(document.source_metadata.asset_path),"source_sha256":String(document.source_metadata.sha256),
		"sample_count":_curve_grips.size(),"sample_step_s":float(document.sample_step_s),"interpolation":"linear_grip_tip"}
	return true

func blade_sweep_phases(first: float, last: float, origin_motion_m: float, scale_m: float) -> PackedFloat64Array:
	var phases := PackedFloat64Array()
	if not _load_blade_curve():
		return phases
	var boundaries := PackedFloat64Array([first])
	for index in range(1,_curve_grips.size()-1):
		var phase := float(index)/(_curve_grips.size()-1)
		if phase > first+.000000001 and phase < last-.000000001:
			boundaries.append(phase)
	if last > first+.000000001:
		boundaries.append(last)
	phases.append(first)
	for index in range(1,boundaries.size()):
		var begin := boundaries[index-1]
		var end := boundaries[index]
		var a := blade_points(begin)
		var b := blade_points(end)
		var travel := maxf(a[0].distance_to(b[0]),a[1].distance_to(b[1]))*scale_m
		travel += origin_motion_m*(end-begin)/maxf(last-first,.000000001)
		var pieces := maxi(1,ceili(travel/maxf(.005,blade_radius*.5)))
		for piece in range(1,pieces+1):
			phases.append(lerpf(begin,end,float(piece)/pieces))
	return phases

func duration() -> float:
	return startup + active + recovery

func is_active(time: float) -> bool:
	return time >= startup and time < startup + active

func can_cancel(time: float) -> bool:
	return time >= startup + active

func lunge_at(time: float) -> float:
	if not phase_lunge:
		return lunge * (1.0 if time < startup + active else 0.15)
	if time < startup:
		return startup_lunge
	if time < startup + active:
		return active_lunge
	return recovery_lunge if time < duration() else 0.0

func lunge_between(from_time: float, to_time: float) -> float:
	# Integrate phase boundaries instead of granting a whole tick of movement
	# when a tick only partially overlaps the short active window.
	if not phase_lunge or to_time <= from_time:
		return lunge_at(to_time)
	var travel := _overlap(from_time, to_time, 0.0, startup) * startup_lunge
	travel += _overlap(from_time, to_time, startup, startup + active) * active_lunge
	travel += _overlap(from_time, to_time, startup + active, duration()) * recovery_lunge
	return travel / (to_time - from_time)

func _overlap(first: float, last: float, begin: float, end: float) -> float:
	return maxf(0.0, minf(last, end) - maxf(first, begin))

func normalized_sweep_progress(fraction: float) -> float:
	var f := clampf(fraction, 0.0, 1.0)
	if not physical_blade_sweep:
		return f
	var squared := f * f
	return squared * squared * (3.0 - 2.0 * squared)

func blade_points(fraction: float) -> Array[Vector3]:
	# Actor-local Y-up/-Z-forward contract, independent of any displayed scene.
	# This authored path already includes the canonical capsule-floor offset.
	if not blade_curve_path.is_empty():
		if not _load_blade_curve():
			return []
		var sample := clampf(fraction,0.0,1.0)*(_curve_grips.size()-1)
		var index := mini(floori(sample),_curve_grips.size()-2)
		var blend := sample-index
		return [_curve_grips[index].lerp(_curve_grips[index+1],blend),_curve_tips[index].lerp(_curve_tips[index+1],blend)]
	var progress := normalized_sweep_progress(fraction)
	var azimuth := deg_to_rad(lerpf(-arc * 0.5, arc * 0.5, progress))
	var pitch := deg_to_rad(lerpf(blade_pitch_start, blade_pitch_end, progress))
	var grip := blade_grip_start.lerp(blade_grip_end, progress)
	var direction := Vector3(-sin(azimuth)*cos(pitch), sin(pitch), -cos(azimuth)*cos(pitch))
	return [grip, grip + direction * blade_length]
