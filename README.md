# DingTalk Trigger

DingTalk (钉钉) trigger plugin for [Dify](https://dify.ai). It subscribes to DingTalk Open Platform events over the HTTP callback protocol and fires Dify workflows when events occur.

Source repository: https://github.com/sjr666666/dify-dingtalk-trigger

## Events

| Event | DingTalk event type | Description |
|---|---|---|
| Approval Instance Changed | `bpms_instance_change` | An OA approval instance is created, completed, or terminated |
| Approval Task Changed | `bpms_task_change` | A task inside an approval flow is created, completed, or redirected |
| User Joined Organization | `user_add_org` | One or more users join the organization |
| User Left Organization | `user_leave_org` | One or more users leave the organization |
| User Profile Updated | `user_modify_org` | One or more user profiles are updated |

## Prerequisites

- A DingTalk organization with [developer console](https://open-dev.dingtalk.com/) access.
- A **self-built org app** (企业内部应用) in the DingTalk developer console.
- Your Dify instance must be reachable from DingTalk servers over HTTPS (a public URL or a tunnel). DingTalk requires a public callback address.

## Setup

1. **Create a self-built app** in the [DingTalk developer console](https://open-dev.dingtalk.com/) and note the `AppKey`.

2. **Configure event subscription**: in the app, open *事件与回调 (Events & Callbacks) → 订阅方式 (Subscription mode)*, select **HTTP 推送 (HTTP push)**, and set:
   - `Token` — any random string (you can generate one yourself);
   - `数据加密密钥 (EncodingAESKey)` — 43 characters (DingTalk can generate one for you).

   Copy these two values, you will need them in Dify.

3. **Create a subscription in Dify**: install the plugin, then add a trigger subscription. Fill in:
   - `AppKey` — from step 1;
   - `Token` — from step 2;
   - `EncodingAESKey` — from step 2.

   Dify generates a webhook endpoint URL for the subscription.

4. **Point DingTalk at the Dify endpoint**: set the 服务器地址 (message callback URL) in the DingTalk event subscription page to the endpoint URL from step 3, then enable the events you want (审批事件 / 通讯录事件).

5. DingTalk sends a `check_url` handshake; the plugin answers it automatically. Once the console shows the callback as verified, events will start flowing.

## Security

- Every callback request is verified with the DingTalk `msg_signature` scheme (SHA-1 over the sorted `token`/`timestamp`/`nonce`/`encrypt` tuple) before any processing.
- The encrypted payload is decrypted with AES-256-CBC using your `EncodingAESKey`, and the receiver id embedded in the plaintext is checked against your `AppKey`.
- Invalid signatures or malformed payloads are rejected without dispatching any workflow.

## Limitations

- Only the HTTP push subscription mode is supported. DingTalk's Stream mode (websocket) and robot chat messages are not part of this plugin.
- The `dic_form` approval form payload is forwarded as-is; its structure depends on your approval template.

## Privacy

See [PRIVACY.md](PRIVACY.md).
