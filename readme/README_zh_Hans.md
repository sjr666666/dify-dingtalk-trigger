# 钉钉触发器（DingTalk Trigger）

[Dify](https://dify.ai) 的钉钉触发器插件。通过钉钉开放平台的 HTTP 回调协议订阅事件，在事件发生时触发 Dify 工作流。

源代码仓库：https://github.com/sjr666666/dify-dingtalk-trigger

## 支持的事件

| 事件 | 钉钉事件类型 | 说明 |
|---|---|---|
| 审批实例状态变更 | `bpms_instance_change` | OA 审批实例创建、结束或终止 |
| 审批任务变更 | `bpms_task_change` | 审批流程中的任务创建、完成或转交 |
| 新员工加入 | `user_add_org` | 有用户加入组织 |
| 员工离职 | `user_leave_org` | 有用户离开组织 |
| 员工信息变更 | `user_modify_org` | 用户资料发生变更 |

## 前置条件

- 一个可以在[钉钉开发者后台](https://open-dev.dingtalk.com/)操作的组织。
- 一个**企业内部应用**。
- Dify 实例必须能被钉钉服务器通过 HTTPS 访问到（公网地址或隧道）。

## 配置步骤

1. **创建企业内部应用**：在钉钉开发者后台创建应用，记录 `AppKey`。

2. **配置事件订阅**：在应用的「事件与回调 → 订阅方式」中选择 **HTTP 推送**，设置：
   - `Token`：任意随机字符串（可自行生成）；
   - `数据加密密钥（EncodingAESKey）`：43 位（可让钉钉自动生成）。

   记下这两个值，稍后在 Dify 中使用。

3. **在 Dify 创建订阅**：安装本插件后添加触发器订阅，填入：
   - `AppKey`（来自第 1 步）；
   - `Token`、`EncodingAESKey`（来自第 2 步）。

   Dify 会为该订阅生成一个 webhook 端点 URL。

4. **把端点地址填回钉钉**：将 Dify 生成的端点 URL 填到钉钉事件订阅页的「服务器地址」，然后勾选需要的事件（审批事件 / 通讯录事件）。

5. 钉钉会发送 `check_url` 校验请求，插件会自动应答。后台显示回调校验通过后，事件即可正常流入。

## 安全性

- 所有回调请求先按钉钉 `msg_signature` 规范（对 `token`/`timestamp`/`nonce`/`encrypt` 排序拼接后取 SHA-1）验签，通过后才处理。
- 加密载荷使用你的 `EncodingAESKey` 以 AES-256-CBC 解密，并校验明文中的接收者 ID 与 `AppKey` 一致。
- 验签失败或载荷非法时直接拒绝，不会触发任何工作流。

## 已知限制

- 仅支持 HTTP 推送订阅方式，不支持 Stream 模式与机器人聊天消息。
- 审批表单 `dic_form` 字段按钉钉原始结构透传，具体结构取决于你的审批模板。

## 隐私

见 [PRIVACY.md](PRIVACY.md)。
