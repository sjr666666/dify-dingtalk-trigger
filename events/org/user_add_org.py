from typing import Any, Mapping

from werkzeug import Request

from dify_plugin.entities.trigger import Variables
from dify_plugin.interfaces.trigger import Event

from .._shared import as_str, pick


class UserAddOrgEvent(Event):
    def _on_event(
        self, request: Request, parameters: Mapping[str, Any], payload: Mapping[str, Any]
    ) -> Variables:
        """
        Handle the DingTalk ``user_add_org`` event.

        Fired when one or more users join the organization.
        """
        user_ids = pick(payload, "UserId", "user_id", "userId", default=[])
        if isinstance(user_ids, str):
            user_ids = [user_ids]
        if not isinstance(user_ids, list):
            user_ids = []

        return Variables(
            variables={
                "user_ids": [as_str(u) for u in user_ids],
                "corp_id": as_str(pick(payload, "CorpId", "corp_id")),
                "timestamp": as_str(pick(payload, "TimeStamp", "timestamp")),
            }
        )
