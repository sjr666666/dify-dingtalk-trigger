import json

from werkzeug import Request, Response

from dify_plugin.entities.trigger import EventDispatch, Subscription
from dify_plugin.errors.trigger import TriggerDispatchError, TriggerValidationError
from dify_plugin.interfaces.trigger import Trigger

from .dingtalk_crypto import DingTalkCallbackCrypto

# DingTalk event type -> Dify event name (identity.name of the event yaml).
# ``check_url`` is handled inline and never dispatched.
_EVENT_ROUTES = {
    "bpms_instance_change": "bpms_instance_change",
    "bpms_task_change": "bpms_task_change",
    "user_add_org": "user_add_org",
    "user_leave_org": "user_leave_org",
    "user_modify_org": "user_modify_org",
}


class DingTalkTrigger(Trigger):
    def _dispatch_event(self, subscription: Subscription, request: Request) -> EventDispatch:
        """Handle a DingTalk Open Platform HTTP callback request.

        DingTalk POSTs ``{"encrypt": "..."}`` with ``signature`` (or
        ``msg_signature``), ``timestamp`` and ``nonce`` as query parameters.
        Every request — including the initial ``check_url`` handshake — is
        answered with an encrypted ``"success"`` response.
        """
        token = subscription.properties.get("dingtalk_token") or ""
        aes_key = subscription.properties.get("dingtalk_aes_key") or ""
        app_key = subscription.properties.get("dingtalk_app_key") or ""

        try:
            crypto = DingTalkCallbackCrypto(token, aes_key, app_key)
        except ValueError as exc:
            raise TriggerDispatchError(str(exc)) from exc

        params = request.args
        signature = params.get("signature") or params.get("msg_signature") or ""
        timestamp = params.get("timestamp") or ""
        nonce = params.get("nonce") or ""

        body = request.get_json(silent=True) or {}
        encrypt = body.get("encrypt") or ""
        if not isinstance(encrypt, str) or not encrypt:
            raise TriggerValidationError("Missing encrypted payload in request body")

        try:
            data = crypto.verify_and_decrypt(signature, timestamp, nonce, encrypt)
        except ValueError as exc:
            raise TriggerValidationError(str(exc)) from exc

        # DingTalk mixes snake_case (new events) and PascalCase (legacy events).
        event_type = str(data.get("event_type") or data.get("EventType") or "")

        response = Response(
            json.dumps(crypto.success_response()),
            status=200,
            mimetype="application/json",
        )

        event_name = _EVENT_ROUTES.get(event_type)
        if event_name is None:
            # Unknown or handshake events: acknowledge with the encrypted
            # "success" body so DingTalk does not retry, but dispatch nothing.
            return EventDispatch(events=[], payload=data, response=response)

        return EventDispatch(events=[event_name], payload=data, response=response)
