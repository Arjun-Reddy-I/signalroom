from app.core.exceptions import BadRequestException
from app.models.enums import ActionItemStatusEnum, MeetingStatusEnum

ALLOWED_MEETING_TRANSITIONS: dict[MeetingStatusEnum, set[MeetingStatusEnum]] = {
    MeetingStatusEnum.SCHEDULED: {MeetingStatusEnum.PREPARING, MeetingStatusEnum.RECORDING, MeetingStatusEnum.UPLOADED, MeetingStatusEnum.ARCHIVED, MeetingStatusEnum.FAILED},
    MeetingStatusEnum.PREPARING: {MeetingStatusEnum.RECORDING, MeetingStatusEnum.UPLOADED, MeetingStatusEnum.SCHEDULED, MeetingStatusEnum.FAILED},
    MeetingStatusEnum.RECORDING: {MeetingStatusEnum.UPLOADED, MeetingStatusEnum.FAILED},
    MeetingStatusEnum.UPLOADED: {MeetingStatusEnum.TRANSCRIBING, MeetingStatusEnum.FAILED},
    MeetingStatusEnum.TRANSCRIBING: {MeetingStatusEnum.ANALYZING, MeetingStatusEnum.FAILED},
    MeetingStatusEnum.ANALYZING: {MeetingStatusEnum.COMPLETED, MeetingStatusEnum.FAILED},
    MeetingStatusEnum.COMPLETED: {MeetingStatusEnum.ARCHIVED, MeetingStatusEnum.FAILED, MeetingStatusEnum.ANALYZING},
    MeetingStatusEnum.FAILED: {MeetingStatusEnum.UPLOADED, MeetingStatusEnum.PREPARING, MeetingStatusEnum.TRANSCRIBING, MeetingStatusEnum.ARCHIVED},
    MeetingStatusEnum.ARCHIVED: {MeetingStatusEnum.COMPLETED, MeetingStatusEnum.SCHEDULED},
}

ALLOWED_ACTION_TRANSITIONS: dict[ActionItemStatusEnum, set[ActionItemStatusEnum]] = {
    ActionItemStatusEnum.OPEN: {ActionItemStatusEnum.IN_PROGRESS, ActionItemStatusEnum.COMPLETED, ActionItemStatusEnum.CANCELLED},
    ActionItemStatusEnum.IN_PROGRESS: {ActionItemStatusEnum.OPEN, ActionItemStatusEnum.COMPLETED, ActionItemStatusEnum.CANCELLED},
    ActionItemStatusEnum.COMPLETED: {ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS},
    ActionItemStatusEnum.CANCELLED: {ActionItemStatusEnum.OPEN, ActionItemStatusEnum.IN_PROGRESS},
}


def validate_meeting_transition(current: MeetingStatusEnum, new_status: MeetingStatusEnum) -> None:
    if current == new_status:
        return
    allowed = ALLOWED_MEETING_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise BadRequestException(
            message=f"Illegal meeting status transition from '{current.value}' to '{new_status.value}'. Allowed targets: {[s.value for s in allowed]}"
        )


def validate_action_item_transition(current: ActionItemStatusEnum, new_status: ActionItemStatusEnum) -> None:
    if current == new_status:
        return
    allowed = ALLOWED_ACTION_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise BadRequestException(
            message=f"Illegal action item status transition from '{current.value}' to '{new_status.value}'. Allowed targets: {[s.value for s in allowed]}"
        )
