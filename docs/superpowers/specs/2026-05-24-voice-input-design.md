# 语音输入功能设计

## 概述
为 AI 智能体（绵小城）增加语音输入能力，用户可通过麦克风说话，浏览器自动将语音转为文字填入聊天输入框。

## 架构

### 方案
- **主方案：** Web Speech API（`SpeechRecognition`），浏览器原生语音识别，实时转写
- **回退方案：** MediaRecorder 录制音频 → 后端 DashScope ASR（`paraformer` 模型）转写
- 转写后的文字**填入输入框**，用户确认后可编辑再发送，不直接提交

### 流程图

```
用户点击麦克风
    ├─ 浏览器支持 Web Speech → 开始监听
    │   ├─ 实时中间结果 → 填入输入框（灰色高亮）
    │   └─ 最终结果 → 填入输入框（常亮）
    │
    └─ 浏览器不支持 → 按钮置灰 + tooltip 提示
        └─ (回退：显示"录制"按钮 → 录音 → 上传 → ASR → 填入输入框)
```

## 前端改动

### `ChatPanel.vue` 新增 VoiceInputBtn

| 状态 | UI | 行为 |
|------|----|------|
| idle | ⚪ 灰色麦克风按钮 | 点击开始监听 |
| listening | 🔴 红色脉冲麦克风 + "正在聆听..." tooltip | 实时转写，中间结果灰色显示在输入框 |
| result | 正常状态 | 最终文字填入输入框，用户可编辑 |
| unsupported | 灰色禁用 + tooltip | 提示不支持，无操作 |
| error | ⚠️ 红色闪烁 | 语音识别失败提示 |

### 兼容性检测

```typescript
const supported = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
```

### 语音配置

- 语言：`zh-CN`
- 连续识别：`continuous: true`
- 中间结果：`interimResults: true`
- 最大时长：60 秒静音自动停止

### 状态管理

- `isListening: ref<boolean>` — 是否正在录音
- `recognition: ref<SpeechRecognition | null>` — 识别器实例
- 组件卸载时自动停止录音、释放资源

## 后端改动

### 新增 `POST /api/agent/speech-to-text`

- **请求：** `multipart/form-data`，字段 `file`（音频文件）
- **格式：** wav / mp3 / webm
- **大小限制：** 10MB
- **处理：** 调用阿里云 DashScope `paraformer` 实时语音识别 API
- **响应：** `{ "text": "转写后的文字" }`
- **错误：** 转写失败返回 422

### `llm_service.py` 新增方法

```python
def speech_to_text(audio_bytes: bytes, filename: str) -> str
```

使用 DashScope 的 `paraformer` 模型进行语音识别。

## 隐私说明

- 语音数据仅用于转写，不做持久化存储
- 录音仅在用户点击麦克风按钮时进行，松手/点击停止即结束
- 上传至 DashScope 的音频不保存到服务器磁盘

## 实施步骤

1. 实现前端 VoiceInputBtn（Web Speech API 主方案）
2. 实现后端 `/api/agent/speech-to-text` 端点
3. 前端集成回退录制 UI（API 方案）
4. 验证：Chrome / Edge / Safari 桌面端语音输入工作正常
