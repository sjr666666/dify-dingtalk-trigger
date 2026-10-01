# Privacy Policy

The DingTalk Trigger plugin processes data on behalf of the Dify instance operator who installs it.

## What data is processed

- Incoming DingTalk callback payloads (event metadata such as approval instance ids, results, user ids, corporation ids, and timestamps) are received, signature-verified, decrypted, and passed to the Dify workflows configured by the operator.
- No message content, documents, or media are fetched by this plugin.

## What is stored

- Nothing is stored by the plugin itself. The credentials entered by the operator (AppKey, Token, EncodingAESKey) are stored by the Dify platform in its own credential storage.
- Event payloads are held in memory only for the duration of a callback request.

## Third parties

- The plugin communicates exclusively with the DingTalk Open Platform callback endpoint, which calls the Dify instance — the plugin does not make outbound requests to any third party.
- It does not send analytics or telemetry anywhere.

## Contact

For questions about this policy, open an issue at https://github.com/sjr666666/dify-dingtalk-trigger/issues
