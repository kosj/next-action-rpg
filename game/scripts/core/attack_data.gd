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
	var progress := normalized_sweep_progress(fraction)
	var azimuth := deg_to_rad(lerpf(-arc * 0.5, arc * 0.5, progress))
	var pitch := deg_to_rad(lerpf(blade_pitch_start, blade_pitch_end, progress))
	var grip := blade_grip_start.lerp(blade_grip_end, progress)
	var direction := Vector3(-sin(azimuth)*cos(pitch), sin(pitch), -cos(azimuth)*cos(pitch))
	return [grip, grip + direction * blade_length]
