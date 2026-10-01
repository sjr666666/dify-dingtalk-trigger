from typing import Any, Mapping

from werkzeug import Request

from dify_plugin.entities.trigger import Variables
from dify_plugin.interfaces.trigger import Event

from .._shared import as_str, pick


class BpmsTaskChangeEvent(Event):
    def _on_event(
        self, request: Request, parameters: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> Variables:
        """
        Handle the DingTalk ``bpms_task_change`` event.

        Fired when a task (审批任务) inside an OA approval flow is created,
        completed, or redirected.
        """
        return Variables(
            variables={
                "process_instance_id": as_str(
                    pick(payload, "process_instance_id", "ProcessInstanceId")
                ),
                "task_id": as_str(pick(payload, "task_id", "TaskId")),
                "activity_id": as_str(pick(payload, "activity_id", "ActivityId")),
                "staff_id": as_str(pick(payload, "staff_id", "StaffId")),
                "result": as_str(pick(payload, "result", "Result")),
                "corp_id": as_str(pick(payload, "corp_id", "CorpId")),
                "timestamp": as_str(pick(payload, "timeStamp", "timestamp")),
            }
        )
