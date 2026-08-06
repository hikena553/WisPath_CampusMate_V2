# 对话侧边栏 & 项目式对话设计

## 目标
为智能体对话增加侧边栏，支持历史对话管理、项目式对话、对话标题自动摘要、搜索和侧边栏折叠。

## 数据模型

### Conversation
```python
class ConversationType(str, Enum):
    NORMAL = "normal"
    PROJECT = "project"

class ProjectTemplate(str, Enum):
    COMPETITION = "competition"      # 学科竞赛
    THESIS = "thesis"                 # 毕业论文/设计
    PRACTICE = "practice"             # 社会实践
    CERTIFICATE = "certificate"       # 证书考取
    STUDENT_WORK = "student_work"     # 学生工作
    CUSTOM = "custom"                 # 自定义项目

class Conversation(Base):
    id: int PK
    user_id: int FK → users.id
    title: str                        # 侧边栏名（普通=首条摘要，项目=用户命名）
    type: ConversationType
    project_template: str | None      # 仅项目类型
    project_stage: str | None         # 当前阶段名称
    is_active: bool                   # 默认 True
    created_at: datetime
    updated_at: datetime
```

### Message
```python
class ConversationMessage(Base):
    id: int PK
    conversation_id: int FK → conversations.id
    role: str                         # user / assistant
    content: text
    timestamp: datetime
```

## API 接口

| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| GET | `/api/agent/conversations` | — | `Conversation[]` | 按 updated_at 倒序 |
| POST | `/api/agent/conversations` | `{type, project_template?, title?}` | `Conversation` | 新建对话 |
| PUT | `/api/agent/conversations/:id` | `{title?, project_stage?}` | `Conversation` | 更新标题/阶段 |
| DELETE | `/api/agent/conversations/:id` | — | `{message}` | 级联删除消息 |
| GET | `/api/agent/conversations/:id/messages` | — | `Message[]` | 按时间正序 |
| POST | `/api/agent/chat` | `{conversation_id, message, history?, file_url?}` | SSE | 新增 conversation_id |

扩展聊天接口：后端收到消息后，自动保存到 `conversation_id` 对应的对话。如果是该对话首条消息，自动调用 LLM 提取摘要作为 `title`。

## 前端组件结构

```
StudentLayout.vue
└── ChatShell.vue (新组件，包裹 ChatPanel + Sidebar)
    ├── Sidebar.vue
    │   ├── 搜索框 (input，实时过滤标题)
    │   ├── +新对话 按钮
    │   ├── +新建项目 (下拉菜单选模板/自定义)
    │   ├── ─── 分组 ───
    │   ├── ▼ 项目对话 (可折叠，默认收起)
    │   │   ├ 图标+标题+阶段标签+进度条
    │   │   └ ...
    │   └── ▼ 历史对话 (可折叠，默认展开)
    │       └ 标题+日期
    └── ChatPanel.vue (右面板，原有逻辑扩展)
```

## 对话生命周期

```
进入 /student
  └── 若无 active 对话 → 创建新 normal 对话
  └── 若有 active 对话 → 恢复

首次发消息
  └── 保存到 DB
  └── 调用 LLM 提取摘要设为 title（异步）

点「+新对话」
  └── 当前对话有消息 → 保存，标记非 active，创建新 normal 对话
  └── 当前对话无消息 → 直接创建新 normal 对话（旧空白对话丢弃）

切换页面再回来
  └── 回到上次 active 对话（通过 conversation_id 恢复）

侧边栏点击历史对话
  └── 加载该对话消息，设为 active

搜索框
  └── 输入过滤对话 title，匹配结果高亮，点击加载
```

## 项目模板阶段

| 模板 | 阶段 |
|------|------|
| 学科竞赛 | 赛前准备 → 方案设计 → 实施优化 → 答辩展示 |
| 毕业论文 | 选题开题 → 文献综述 → 实验/调研 → 撰写修改 → 答辩 |
| 社会实践 | 方案申报 → 前期准备 → 实施执行 → 总结评优 |
| 证书考取 | 考情分析 → 学习规划 → 备考刷题 → 考前冲刺 |
| 学生工作 | 活动策划 → 审批协调 → 执行落地 → 复盘总结 |
| 自定义项目 | 自由阶段（用户自行添加） |

## 错误处理

- 对话加载失败 → 显示错误提示，可重试
- 消息发送失败 → 保留在输入框，显示发送失败提示
- 标题摘要 LLM 超时 → 使用首条消息前 20 字作为 fallback 标题
- 侧边栏搜索无结果 → 显示「无匹配对话」

## 非功能性需求

- 侧边栏宽度 280px，可折叠至 48px（仅图标）
- 侧边栏收起状态保持（localStorage 持久化）
- 消息分页加载（初始加载最近 50 条，滚动加载更多）
- 对话列表不超过 100 条，超出自动清理最早记录
