from typing import Any, Mapping

from werkzeug import Request

from dify_plugin.entities.trigger import Variables
from dify_plugin.interfaces.trigger import Event

from .._shared import as_str, pick


class BpmsInstanceChangeEvent(Event):
    def _on_event(
        self, request: Request, parameters: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> Variables:
        """
        Handle the DingTalk ``bpms_instance_change`` event.

        Fired when an OA approval (审批) instance is created, completes, or is
        terminated. The decrypted payload has already been verified by the
        trigger provider and is delivered through ``payload``.
        """
        return Variables(
            variables={
                "process_instance_id": as_str(
                    pick(payload, "process_instance_id", "ProcessInstanceId")
                ),
                "result": as_str(pick(payload, "result", "Result")),
                "staff_id": as_str(pick(payload, "staff_id", "StaffId")),
                "corp_id": as_str(pick(payload, "corp_id", "CorpId")),
                "timestamp": as_str(pick(payload, "timeStamp", "timestamp")),
                "biz_category": as_str(
                    pick(payload, "biz_catagory", "bizCategory", "BizCategory")
                ),
                "form": pick(payload, "dic_form", "DicForm", default=""),
            }
        )
