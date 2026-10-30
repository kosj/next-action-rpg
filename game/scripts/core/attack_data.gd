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

func duration() -> float:
	return startup + active + recovery

func is_active(time: float) -> bool:
	return time >= startup and time < startup + active

func can_cancel(time: float) -> bool:
	return time >= startup + active
