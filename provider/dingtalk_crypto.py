"""DingTalk callback crypto helpers.

Implements the message signature and AES payload scheme used by the DingTalk
Open Platform HTTP callback (旧版HTTP推送) protocol:

- The request signature is ``sha1`` of the lexicographically sorted
  concatenation of ``token``, ``timestamp``, ``nonce`` and the ``encrypt``
  string from the request body.
- The ``encrypt`` string is AES-256-CBC encrypted with a key derived from the
  43-character ``EncodingAESKey`` configured in the DingTalk developer
  console. The plaintext layout is ``random(16 bytes) + msg_len(4 bytes, big
  endian) + msg + receiver_id`` followed by PKCS#7 padding to a 32-byte
  boundary.
- Every callback request — including the initial ``check_url`` handshake —
  must be answered with a JSON object containing an encrypted ``"success"``
  string together with a fresh ``msg_signature`` / ``timeStamp`` / ``nonce``
  triple.

Reference implementation (official): https://github.com/open-dingtalk/DingTalk-Callback-Crypto
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import string
import struct
import time
from typing import Any

from Crypto.Cipher import AES

_SUCCESS = "success"


class DingTalkCallbackCrypto:
    """Encrypt / verify / decrypt DingTalk HTTP callback messages."""

    def __init__(self, token: str, aes_key: str, receiver_id: str) -> None:
        """
        :param token: the ``Token`` configured in the DingTalk developer console
        :param aes_key: the 43-character ``EncodingAESKey`` from the console
        :param receiver_id: the expected receiver id appended to plaintext
            (``appKey`` for org-self-built apps, ``corpId`` for callback
            registration of some app types). When empty the receiver check is
            skipped.
        """
        self.token = token or ""
        self.receiver_id = receiver_id or ""
        try:
            self.aes_key = base64.b64decode((aes_key or "") + "=")
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            raise ValueError(f"Invalid EncodingAESKey: {exc}") from exc
        if len(self.aes_key) != 32:
            raise ValueError("EncodingAESKey must decode to 32 bytes")

    # ------------------------------------------------------------------
    # signature
    # ------------------------------------------------------------------

    @staticmethod
    def _signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
        joined = "".join(sorted([token, str(timestamp), str(nonce), encrypt]))
        return hashlib.sha1(joined.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # AES helpers
    # ------------------------------------------------------------------

    def _encrypt(self, plaintext: str) -> str:
        raw = (
            secrets.token_bytes(16)
            + struct.pack("!I", len(plaintext.encode("utf-8")))
            + plaintext.encode("utf-8")
            + self.receiver_id.encode("utf-8")
        )
        pad = 32 - len(raw) % 32
        raw += bytes([pad]) * pad
        cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
        return base64.b64encode(cipher.encrypt(raw)).decode("utf-8")

    def _decrypt(self, ciphertext: str) -> str:
        try:
            cipher = AES.new(self.aes_key, AES.MODE_CBC, self.aes_key[:16])
            plain = cipher.decrypt(base64.b64decode(ciphertext))
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            raise ValueError(f"Failed to decrypt payload: {exc}") from exc

        pad = plain[-1]
        if not 1 <= pad <= 32:
            raise ValueError("Invalid PKCS#7 padding")
        plain = plain[:-pad]
        if len(plain) < 20:
            raise ValueError("Decrypted payload is too short")

        msg_len = struct.unpack("!I", plain[16:20])[0]
        msg = plain[20 : 20 + msg_len]
        if len(msg) != msg_len:
            raise ValueError("Decrypted message length mismatch")

        receiver = plain[20 + msg_len :].decode("utf-8", errors="replace")
        if self.receiver_id and receiver != self.receiver_id:
            raise ValueError("Receiver id verification failed")

        return msg.decode("utf-8")

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def verify_and_decrypt(
        self, signature: str, timestamp: str, nonce: str, encrypt: str
    ) -> dict[str, Any]:
        """Validate the request signature and return the decrypted JSON object."""
        expected = self._signature(self.token, timestamp, nonce, encrypt)
        if not hmac.compare_digest(expected, signature or ""):
            raise ValueError("Signature verification failed")

        plaintext = self._decrypt(encrypt)
        import json

        try:
            data = json.loads(plaintext)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Decrypted payload is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Decrypted payload is not a JSON object")
        return data

    def success_response(self) -> dict[str, str]:
        """Build the JSON body DingTalk expects for every callback request."""
        timestamp = str(int(time.time()))
        nonce = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        encrypt = self._encrypt(_SUCCESS)
        return {
            "msg_signature": self._signature(self.token, timestamp, nonce, encrypt),
            "timeStamp": timestamp,
            "nonce": nonce,
            "encrypt": encrypt,
        }
