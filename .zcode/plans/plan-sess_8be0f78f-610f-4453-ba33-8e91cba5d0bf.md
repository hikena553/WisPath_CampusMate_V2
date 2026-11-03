# 资讯账号管理（自选账号管理）实现计划

## Context

管理端「资讯管理」页（`frontend/src/views/admin/FeedSourcesPage.vue`，页签：资讯源管理 / 资讯条目）需要新增第三个页签「账号管理」，维护一批**资讯账号**。这些账号由系统自动在学生端**交流社区**（`community_posts`）发帖，内容为：爬取新闻的逐条转发 + 每日重点汇总帖。

已与用户确认的决策：
1. **帖子展示位**：交流社区帖子流（复用作者/头像/点赞/评论/关注整套机制）。
2. **发帖机制**：每日定时汇总帖 + 新资讯逐条转发，两者都要；另提供手动「立即发布」。

关键事实（探索已确认）：
- `community_posts.student_id` 无外键，作者信息由 `api/community.py::_post_out` 从 users 查（查不到显示「匿名同学」）→ 资讯账号必须是 users 表真实记录。
- `UserRole` 仅 student/teacher/admin（`backend/app/models/user.py:8`）；MySQL 列为 `sa.Enum('STUDENT','TEACHER','ADMIN', name='userrole')`（存枚举**名**大写）。
- 资讯爬取已有：`feed_ingest.ingest_all` 每 30 分钟入库 `external_feed_items`（含 `is_highlight`、`source_type` 7 类）。
- 周期任务统一在 `backend/app/tasks/periodic.py::start_periodic_tasks` 登记。
- admin 鉴权：`Depends(require_role(UserRole.ADMIN))`（`app/core/deps.py:80`）。
- 数据库规范（docs/数据库规范.md）：新表 BIGINT 主键、布尔 is_ 前缀、唯一约束 uq_{表}_{语义}、迁移禁 autogenerate 手写且可 downgrade、`campus_ddl` 跑迁移。
- 架构铁律：api/ 禁内联 DTO（`admin/feeds.py` 是历史遗留，新代码 DTO 下沉 schemas/）、路由在 `app/api/admin/__init__.py` include、服务层不 import FastAPI。

## 设计

- **角色**：`UserRole` 新增 `MEDIA = "media"`；资讯账号禁止登录（登录接口校验后 403），username 自动生成 `media_XXXX`，密码随机不外发，name/avatar/signature 即社区展示形象。
- **新表 2 张**：
  - `media_accounts`：id、user_id（FK users.id，unique）、enabled、content_scope JSON（绑定的 source_type 列表，空=全部）、created_at/updated_at。
  - `media_posts`：id、account_user_id（index）、post_id（FK community_posts.id）、feed_item_id（String 大 ID？int index，无 FK——feed 条目是物理删除的快照）、kind（digest/relay）、digest_date DATE NULL、created_at。唯一约束 `uq_media_posts_relay(account_user_id, feed_item_id)` 防重复转发、`uq_media_posts_digest(account_user_id, digest_date)` 防重复日报。
- **发帖管道**（`services/media_account_service.py`）：
  - `relay_new_items`：每 30 分钟，取近一周期新入库且未被任一启用账号转发过的 `external_feed_items`，按各账号 content_scope 匹配后逐条发帖（标题=条目标题截 100，内容=摘要+来源+链接）；每周期每账号上限 20 条防刷屏，唯一约束兜底幂等。
  - `publish_digest`：每日 8 点后首个扫描周期补发（`now.hour >= 8 且 digest_date < 今天`），聚合该账号范围内近 24h 条目（is_highlight 优先，top 8），生成「今日重点汇总」帖；LLM 可用时润色导语（走 `llm_service`），额度耗尽/未配置则模板拼接兜底。
  - `run_media_publish_cycle`：周期循环统一入口 = 转发 + 汇总，单账号 try/except 容错。
- **帖子分类**：社区帖子分类白名单新增「资讯」（后端 `CATEGORIES` + 前端 categoryFilters），资讯帖与普通学生帖视觉区分。

## 改动清单

### 后端
1. `backend/app/models/user.py` — UserRole 加 `MEDIA = "media"`。
2. **新建** `backend/app/models/media.py` — MediaAccount / MediaPost；`models/__init__.py` 导出。
3. **新建** `backend/alembic/versions/s0e1f2a3b4c5_media_accounts.py` — 手写迁移：users.role ENUM 追加 'MEDIA'（先 inspector 判断幂等）+ 两张新表；downgrade 完整回退；revision 链接 head `r9d0e1f2a3b4`。
4. **新建** `backend/app/schemas/media_account.py` — DTO（列表项含发帖数/最近发帖时间）。
5. **新建** `backend/app/services/media_account_service.py` — 账号 CRUD（建/删用户+配置）、publish_digest、relay_new_items、run_media_publish_cycle、手动发布；删帖清理复用 `api/community.py::delete_post` 的互动清理模式。
6. **新建** `backend/app/api/admin/media_accounts.py` — GET/POST `/admin/media/accounts`、PATCH/DELETE `/{id}`、POST `/{id}/publish`；`backend/app/api/admin/__init__.py` include_router。
7. `backend/app/api/auth.py` — 账号密码登录与 QQ 登录处对 `role == MEDIA` 返回 403「该账号为系统资讯账号，不支持登录」。
8. `backend/app/api/community.py:24` — CATEGORIES 加「资讯」。
9. `backend/app/tasks/periodic.py` — 新增 `_periodic_media_publish`（30 分钟间隔）并注册进 `start_periodic_tasks`。
10. `backend/app/seed.py` — 幂等加 1 个演示资讯账号（如「绵小城资讯站」）。

### 前端
11. `frontend/src/api/admin.ts` — MediaAccount 类型 + 5 个请求函数（`/admin/media/accounts` 前缀）。
12. `frontend/src/views/admin/FeedSourcesPage.vue` — L159 后加第三个 `el-tab-pane label="账号管理" name="accounts"`：列表（头像+名称+username / 内容方向 tags / 状态 / 发帖数 / 最近发帖 / 操作：编辑·启停·立即发布·删除）+ 新增/编辑弹窗（表单校验参考 TeachersPage 的 FormInstance 模式：名称必填、头像 URL 可选预览、签名、内容方向多选空=全部、启用开关）+ 删除二次确认（提示其帖子将一并删除）。
13. `frontend/src/views/student/CommunityView.vue` — categoryFilters（约 L230）加「资讯」分类。

## 注意事项
- 枚举对外输出字符串值走 `app.utils.enum_helpers` 现有机制。
- relay 只转发当日新条目；资讯条目被管理端删除后 media_posts 留存（快照语义，无 FK 不阻塞）。
- 学生管理/教师管理按 role 过滤，不受 media 角色污染；admin 仪表盘按角色统计天然排除。
- ProfilePage 个人主页被 `openUserHomepage(bot_id)` 打开时需验证不崩（实现时顺带验证，学生专属区块为空属可接受）。

## 验证
1. 迁移：`backend/.venv/Scripts/python.exe -m alembic upgrade head`（走 campus_ddl 配置）+ `scripts/db_bootstrap.py --check` 一致性。
2. 后端冒烟：`.venv/Scripts/python.exe -c "import app.main"`。
3. 接口链路（.venv 起 uvicorn :8000，admin 登录）：建账号 → 立即发布 → `GET /api/community/posts?category=资讯` 验证帖子作者/头像/内容；重复发布验证 digest 幂等提示；手动调 `run_media_publish_cycle` 两次验证转发不重复；media 账号登录返回 403。
4. LLM 额度先探（AGENTS.md 坑），耗尽时验证模板兜底文案正常发帖。
5. 前端 `npm run build` 零报错（沙箱带 `TMP=TEMP=TMPDIR=$PWD/.tmpbuild` 前缀）。
6. E2E 收尾杀干净验证服务（netstat 反查 PID → taskkill），报告写明起了什么服务、是否已杀。