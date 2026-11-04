# 管理员端功能设计文档

## 概述

为智慧校园AI服务平台构建完整的管理员端，包含AI知识库管理、密码管理、教师管理、数据导入导出四大功能模块。参照教师端布局风格，保持一致的用户体验。

## 功能需求

### 1. AI知识库管理（混合方案）

#### 1.1 手动问答对管理
- 表格展示所有 KnowledgeItem（分类、问题、答案、标签）
- 支持增删改查操作
- 分类筛选：办事流程、校园导航、规章制度、校园生活、自定义
- 关键词搜索功能

#### 1.2 文档上传
- 支持上传 PDF/Word/TXT 文件
- 后端解析文档内容，自动分块存储
- 使用向量化（Embedding）存入向量数据库
- 支持语义检索（比现有关键词匹配更智能）
- 上传状态显示：成功/失败/处理中

#### 1.3 智能体检索逻辑（后端修改）
- 用户提问 → 先检索本地知识库
- 检索方式：问答对关键词匹配 + 文档语义检索
- 找到相关结果 → 基于结果生成回答
- 未找到 → 调用联网搜索API获取实时信息

### 2. 密码管理

#### 2.1 管理员端重置密码
- 教师/学生列表每行增加"重置密码"按钮
- 点击确认后重置为默认密码 `123456`
- 操作后提示"已重置为默认密码123456"

#### 2.2 教师端/学生端修改密码
- 个人资料页增加"修改密码"按钮
- 输入项：旧密码 + 新密码 + 确认新密码
- 修改成功后标记 `password_changed=True`
- 按钮变为灰色提示"密码已修改过"（仅允许修改一次）
- 登录时若未修改过密码，弹窗提醒"请及时修改初始密码"

### 3. 教师管理

#### 3.1 教师列表
- 表格展示所有教师：姓名、工号、学院、所带学生数量
- 支持搜索和筛选

#### 3.2 教师详情
- 点击教师行 → 展开详情抽屉
- 显示教师基本信息
- 显示所带学生列表：姓名、学号、专业、班级、综合评分、危机等级
- 点击学生可跳转查看学生成长档案

### 4. 数据导入导出

#### 4.1 导出功能
- 选择导出范围：学生/教师
- 导出格式：Excel (.xlsx)
- 包含基本信息字段
- 支持按学院、专业、班级筛选后导出

#### 4.2 导入功能
- 上传 Excel 文件
- 预览即将导入的数据
- 显示统计：新增X条、跳过X条（重复学号/工号）
- 确认后执行导入
- 跳过重复记录（学号/工号重复）
- 导入完成后显示结果报告

## 页面布局设计

### AdminLayout.vue（参照 TeacherLayout）

```
┌─────────────────────────────────────────────────┐
│ 顶部栏：Logo"绵小城" | 校训 | 折叠按钮           │
├──────────┬──────────────────────────────────────┤
│ 左侧导航 │                                      │
│ (200px)  │          主内容区域                   │
│          │        <router-view />               │
│ 首页     │                                      │
│ 知识库   │                                      │
│ 教师管理 │                                      │
│ 学生管理 │                                      │
│ 数据管理 │                                      │
│          │                                      │
│ ──────── │                                      │
│ 管理员   │                                      │
│ 头像+名称│                                      │
│ [退出]   │                                      │
└──────────┴──────────────────────────────────────┘
```

### 导航菜单

| 路径 | 图标 | 名称 | 说明 |
|------|------|------|------|
| `/admin` | HomeFilled | 首页 | Dashboard 概览统计 |
| `/admin/knowledge` | Document | 知识库 | AI知识库管理 |
| `/admin/teachers` | User | 教师管理 | 教师列表+学生详情 |
| `/admin/students` | UserFilled | 学生管理 | 学生列表 |
| `/admin/data` | Upload | 数据管理 | 导入导出 |

## 数据库设计

### User 表新增字段

```python
# backend/app/models/user.py
password_changed = Column(Boolean, default=False, comment="是否已修改过密码")
```

### 新增表：DocumentChunk（文档分块）

```python
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)  # 分块内容
    chunk_index = Column(Integer, nullable=False)  # 分块序号
    embedding = Column(JSON, nullable=True)  # 向量表示
    created_at = Column(DateTime, default=func.now())
```

### 新增表：Document（文档元数据）

```python
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf/docx/txt
    file_path = Column(String(500), nullable=False)
    status = Column(String(20), default="processing")  # processing/completed/failed
    chunk_count = Column(Integer, default=0)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
```

## API 设计

### 知识库管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/admin/knowledge` | 获取知识库列表 | admin |
| POST | `/api/admin/knowledge` | 新增问答对 | admin |
| PUT | `/api/admin/knowledge/{id}` | 修改问答对 | admin |
| DELETE | `/api/admin/knowledge/{id}` | 删除问答对 | admin |
| POST | `/api/admin/knowledge/upload` | 上传文档 | admin |
| GET | `/api/admin/knowledge/documents` | 获取文档列表 | admin |
| DELETE | `/api/admin/knowledge/documents/{id}` | 删除文档 | admin |

### 教师管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/admin/teachers` | 教师列表（含学生数量） | admin |
| GET | `/api/admin/teachers/{id}/students` | 教师所带学生详情 | admin |

### 学生管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/admin/students` | 学生列表 | admin |

### 密码管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/admin/reset-password/{user_id}` | 重置密码为123456 | admin |
| PUT | `/api/user/change-password` | 用户修改密码 | student/teacher |

### 数据导入导出

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/admin/export?role=student` | 导出Excel | admin |
| POST | `/api/admin/import` | 导入Excel | admin |

## 前端文件结构

```
frontend/src/
├── views/
│   └── admin/
│       ├── AdminLayout.vue      # 管理员布局（参照TeacherLayout）
│       ├── HomePage.vue         # 首页概览
│       ├── KnowledgePage.vue    # 知识库管理
│       ├── TeachersPage.vue     # 教师管理
│       ├── StudentsPage.vue     # 学生管理
│       └── DataPage.vue         # 数据导入导出
├── router/
│   └── index.ts                 # 新增admin路由
├── api/
│   └── admin.ts                 # 管理员API封装
└── stores/
    └── admin.ts                 # 管理员状态管理（可选）
```

## 后端文件结构

```
backend/app/
├── api/
│   └── admin.py                 # 管理员路由
├── models/
│   ├── user.py                  # 新增password_changed字段
│   ├── knowledge.py             # 已有，可能需要扩展
│   └── document.py              # 新增Document和DocumentChunk模型
├── schemas/
│   └── admin.py                 # 管理员相关Pydantic模型
└── services/
    ├── knowledge_service.py     # 知识库服务（文档解析、向量化）
    └── import_export_service.py # 导入导出服务
```

## 技术选型

### 文档解析
- PDF: PyPDF2 或 pdfplumber
- Word: python-docx
- 文本: 直接读取

### 向量化与检索
- 方案: sentence-transformers + FAISS/ChromaDB
- 备选: 调用阿里云DashScope的Embedding API

### Excel处理
- 导出: openpyxl
- 导入: openpyxl + pandas

### 联网搜索（可选）
- 调用外部搜索API（百度/Google）
- 或使用LLM的联网能力（如果支持）

## 用户体验流程

### 管理员登录后
1. 首页显示系统概览：用户统计、知识库条目数、今日AI对话数
2. 侧边栏导航切换各功能模块

### 知识库管理流程
1. 查看现有问答对列表
2. 可手动添加/编辑/删除问答对
3. 可上传文档，系统自动解析并显示状态
4. 文档解析完成后自动加入知识库

### 密码重置流程
1. 管理员在教师/学生列表找到目标用户
2. 点击"重置密码"按钮
3. 确认对话框："确定将该用户密码重置为123456？"
4. 确认后显示成功提示

### 教师查看流程
1. 教师列表显示所有教师及所带学生数量
2. 点击教师行 → 右侧抽屉显示详情
3. 抽屉内显示教师信息 + 学生列表
4. 点击学生可查看学生成长档案

### 数据导入流程
1. 选择导入类型（学生/教师）
2. 上传Excel文件
3. 系统预览数据，显示"新增X条，跳过X条"
4. 确认导入
5. 显示导入结果报告

## 验收标准

- [ ] 管理员登录后进入管理员端，布局与教师端风格一致
- [ ] 知识库支持增删改查问答对
- [ ] 知识库支持上传PDF/Word/TXT文档并自动解析
- [ ] 智能体优先检索本地知识库回答问题
- [ ] 管理员可重置教师/学生密码为123456
- [ ] 教师/学生可在个人资料修改密码（仅一次）
- [ ] 教师列表显示所带学生数量
- [ ] 点击教师可查看其学生详情
- [ ] 支持导出学生/教师数据为Excel
- [ ] 支持导入Excel数据，跳过重复记录
- [ ] 所有操作有适当的权限控制
