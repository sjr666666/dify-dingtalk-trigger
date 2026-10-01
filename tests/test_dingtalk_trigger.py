"""Tests for the dingtalk_trigger plugin.

Includes an interop test against the official DingTalk test vector from
https://github.com/open-dingtalk/DingTalk-Callback-Crypto (DingCallbackCrypto3).
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from werkzeug.test import EnvironBuilder

from provider.dingtalk import DingTalkTrigger
from provider.dingtalk_crypto import DingTalkCallbackCrypto

TOKEN = "test-token"
AES_KEY = "Yue0EfdN5900c1ce5cf6A152c63DDe1808a60c5ecd7"  # 43 chars
APP_KEY = "ding6ccabc44d2c8d38b"


# ----------------------------------------------------------------------
# fixtures / helpers
# ----------------------------------------------------------------------


def make_crypto() -> DingTalkCallbackCrypto:
    return DingTalkCallbackCrypto(TOKEN, AES_KEY, APP_KEY)


def sign(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    joined = "".join(sorted([token, timestamp, nonce, encrypt]))
    return hashlib.sha1(joined.encode()).hexdigest()


def make_request(crypto: DingTalkCallbackCrypto, payload: dict, *, tamper: bool = False):
    """Build a werkzeug Request that mimics a DingTalk callback POST."""
    encrypt = crypto._encrypt(json.dumps(payload))
    timestamp = "1700000000000"
    nonce = "nonce12345678"
    signature = sign(TOKEN, timestamp, nonce, encrypt)
    if tamper:
        signature = "0" * 40
    builder = EnvironBuilder(
        method="POST",
        query_string={"signature": signature, "timestamp": timestamp, "nonce": nonce},
        json={"encrypt": encrypt},
    )
    return builder.get_request()


def make_trigger() -> DingTalkTrigger:
    return DingTalkTrigger(runtime=MagicMock())


def make_subscription() -> SimpleNamespace:
    return SimpleNamespace(
        properties={"dingtalk_token": TOKEN, "dingtalk_aes_key": AES_KEY, "dingtalk_app_key": APP_KEY}
    )


def decrypt_response(crypto: DingTalkCallbackCrypto, response) -> str:
    if hasattr(response, "get_data"):
        response = response.get_data()
    data = json.loads(response)
    return crypto._decrypt(data["encrypt"])


# ----------------------------------------------------------------------
# crypto
# ----------------------------------------------------------------------


def test_official_test_vector_roundtrip():
    """Interop: the official DingTalk demo vector decrypts correctly."""
    crypto = DingTalkCallbackCrypto("mryue", AES_KEY, "ding6ccabc44d2c8d38b")
    plaintext = crypto.verify_and_decrypt(
        signature="03044561471240d4a14bb09372dfcfd4fd0e40cb",
        timestamp="1608001896814",
        nonce="WL4PK6yA",
        encrypt=(
            "0vJiX6vliEpwG3U45CtXqi+m8PXbQRARJ8p8BbDuD1EMTDf0jKpQ79QS93qEk7XHpP6u"
            "+oTTrd15NRPvNvmBKyDCYxxOK+HZeKju4yhELOFchzNukR+t8SB/qk4ROMu3"
        ),
    )
    assert plaintext == {"EventType": "check_url"}


def test_success_response_roundtrip():
    crypto = make_crypto()
    response = crypto.success_response()
    assert crypto._decrypt(response["encrypt"]) == "success"
    # response signature is self-consistent
    expected = sign(TOKEN, response["timeStamp"], response["nonce"], response["encrypt"])
    assert expected == response["msg_signature"]


def test_invalid_signature_rejected():
    crypto = make_crypto()
    with pytest.raises(ValueError, match="Signature"):
        crypto.verify_and_decrypt("bad" * 13 + "x", "123", "n", crypto._encrypt("{}"))


def test_invalid_receiver_rejected():
    encrypt = make_crypto()._encrypt("{}")  # encrypted with the correct receiver id
    wrong_receiver = DingTalkCallbackCrypto(TOKEN, AES_KEY, "other-app-key")
    with pytest.raises(ValueError, match="Receiver"):
        wrong_receiver._decrypt(encrypt)


def test_invalid_aes_key_rejected():
    with pytest.raises(ValueError, match="32 bytes"):
        DingTalkCallbackCrypto(TOKEN, "tooshort", APP_KEY)


def test_encrypted_format_matches_official_layout():
    """plaintext = random(16) + len(4, BE) + msg + receiver, PKCS#7 padded."""
    crypto = make_crypto()
    encrypt = crypto._encrypt("hi")
    raw = base64.b64decode(encrypt)
    aes = crypto.aes_key
    from Crypto.Cipher import AES as _AES

    plain = _AES.new(aes, _AES.MODE_CBC, aes[:16]).decrypt(raw)
    pad = plain[-1]
    plain = plain[:-pad]
    assert plain[16:16] == b""  # random prefix present
    msg_len = struct.unpack("!I", plain[16:20])[0]
    assert plain[20 : 20 + msg_len] == b"hi"
    assert plain[20 + msg_len :].decode() == APP_KEY


# ----------------------------------------------------------------------
# trigger dispatch
# ----------------------------------------------------------------------


def test_dispatch_check_url_acknowledges_without_events():
    crypto = make_crypto()
    trigger = make_trigger()
    result = trigger._dispatch_event(
        make_subscription(), make_request(crypto, {"event_type": "check_url", "random": "abc"})
    )
    assert result.events == []
    assert json.loads(result.response.get_data())  # valid encrypted JSON body
    assert decrypt_response(crypto, result.response.get_data()) == "success"


def test_dispatch_bpms_instance_change():
    crypto = make_crypto()
    trigger = make_trigger()
    payload = {
        "event_type": "bpms_instance_change",
        "process_instance_id": "pi-1",
        "result": "agree",
        "staff_id": "u1",
        "corp_id": APP_KEY,
        "timeStamp": 1700000000000,
        "biz_catagory": "start",
    }
    result = trigger._dispatch_event(make_subscription(), make_request(crypto, payload))
    assert result.events == ["bpms_instance_change"]
    assert result.payload["process_instance_id"] == "pi-1"
    assert result.payload["result"] == "agree"
    assert decrypt_response(crypto, result.response.get_data()) == "success"


def test_dispatch_legacy_pascal_case_event():
    crypto = make_crypto()
    trigger = make_trigger()
    payload = {"EventType": "user_add_org", "UserId": ["u1", "u2"], "TimeStamp": 1700000000000, "CorpId": APP_KEY}
    result = trigger._dispatch_event(make_subscription(), make_request(crypto, payload))
    assert result.events == ["user_add_org"]
    assert result.payload["UserId"] == ["u1", "u2"]


def test_dispatch_unknown_event_is_acknowledged_only():
    crypto = make_crypto()
    trigger = make_trigger()
    result = trigger._dispatch_event(
        make_subscription(), make_request(crypto, {"event_type": "some_future_event"})
    )
    assert result.events == []
    assert decrypt_response(crypto, result.response.get_data()) == "success"


def test_dispatch_rejects_tampered_signature():
    crypto = make_crypto()
    trigger = make_trigger()
    from dify_plugin.errors.trigger import TriggerValidationError

    with pytest.raises(TriggerValidationError, match="Signature"):
        trigger._dispatch_event(
            make_subscription(), make_request(crypto, {"event_type": "bpms_instance_change"}, tamper=True)
        )


def test_dispatch_rejects_missing_encrypt_body():
    from dify_plugin.errors.trigger import TriggerValidationError

    trigger = make_trigger()
    builder = EnvironBuilder(
        method="POST", query_string={"signature": "s", "timestamp": "1", "nonce": "n"}, json={}
    )
    with pytest.raises(TriggerValidationError, match="Missing encrypted payload"):
        trigger._dispatch_event(make_subscription(), builder.get_request())


# ----------------------------------------------------------------------
# event handlers
# ----------------------------------------------------------------------


def test_bpms_instance_change_event_variables():
    from events.approval.bpms_instance_change import BpmsInstanceChangeEvent

    event = BpmsInstanceChangeEvent(runtime=MagicMock())
    variables = event._on_event(
        request=None,
        parameters={},
        payload={
            "event_type": "bpms_instance_change",
            "process_instance_id": "pi-9",
            "result": "refuse",
            "staff_id": "u9",
            "corp_id": "corp",
            "timeStamp": 1700000000000,
            "biz_catagory": "start",
        },
    )
    v = variables.variables
    assert v["process_instance_id"] == "pi-9"
    assert v["result"] == "refuse"
    assert v["staff_id"] == "u9"
    assert v["timestamp"] == "1700000000000"
    assert v["biz_category"] == "start"


def test_user_add_org_event_variables():
    from events.org.user_add_org import UserAddOrgEvent

    event = UserAddOrgEvent(runtime=MagicMock())
    variables = event._on_event(
        request=None,
        parameters={},
        payload={"EventType": "user_add_org", "UserId": ["u1", "u2"], "CorpId": "corp", "TimeStamp": 1700000000000},
    )
    v = variables.variables
    assert v["user_ids"] == ["u1", "u2"]
    assert v["corp_id"] == "corp"
    assert v["timestamp"] == "1700000000000"
