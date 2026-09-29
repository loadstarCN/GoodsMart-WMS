# GoodsMart-WMS 审核报告与修复跟踪（2026-09-29）

> 范围：Backend（system + warehouse 全部模块）、Web 管理端（/admin、/apikeys、认证、鉴权中间件）、APP（Vue + Android 壳）。Station、Website 未覆盖。
> 方法：只读审计 + 后端完整测试（初始 292 通过 / 1 失败）+ APP vitest / vue-tsc / eslint / build。
> 路径均相对各子仓库根目录；`[BE]` = Backend、`[WEB]` = Web、`[APP]` = APP。
>
> **当前状态（2026-09-29 收尾）**：Backend 46 项中 44 ✅ / B-18 🔄 / B-46 部分；Web 22 项全 ✅；APP 36 项中 31 ✅ / A-05、A-29 ❓需真机验证 / A-17、A-25、A-30 ⏭。后端测试 467 通过，Web `build_test` 通过，APP vitest/vue-tsc/eslint/build 通过。**所有改动尚未提交。**
>
> **状态图例**：⬜ 未开始 · 🔄 进行中 · ✅ 已修复 · ⏭ 暂不修（附原因） · ❓ 待确认

---

## 一、Backend

### 🔴 严重

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| B-01 | ✅ | 公司管理员可通过 API Key 自我提权：创建/更新 API Key 时 `permissions`（自由 JSON）与 `user_id` 原样透传，`permissions:["all_access"]` 即获平台权限 | `system/third_party/views.py:60-74`、`services.py:45-77`、`models.py:93` | `permissions` ⊆ 调用者权限且非超管禁 `all_access`；非超管禁设 `user_id`；更新同样校验 |
| B-02 | ✅ | staff 模块无租户归属：company_admin 可 `PUT /staff/<自己> {"roles":["admin"]}`、改他公司员工密码、在他公司植入账号；`roles` 按名查表无白名单；`company_id` 取自请求体 | `warehouse/staff/views.py:44-84`、`services.py:86,99-106,130-140` | staff 调用者强制 `company_id`；roles 白名单（禁含 `all_access` 的角色）；`/<id>` 归属校验；`warehouse_ids ⊆ 本公司仓库` |
| B-03 | ✅ | 主数据跨租户 IDOR：supplier / carrier / goods / location / goods_locations / payment 详情 GET/PUT/DELETE 与 POST 无归属校验，update 可改 `company_id`；goods 列表对 staff 不加公司过滤；staff 可创建公司、枚举全部租户；`PUT /company/<自己>` 可改 `expired_at`、`is_active`；department PUT 可改 `company_id`；recipient/goods POST 对 staff 不校验 `company_id` | `supplier/views.py:39-80`、`carrier/views.py:44-84`、`goods/views.py:63-125`、`goods/services.py:99-106`、`location/views.py:39-77`、`payment/views.py`、`company/views.py:13-46`、`company/services.py:91-92`、`department/services.py:70` | 照 `recipient` 的 `_request_company_id()` 模式统一加归属校验；update 禁改 `company_id`/`warehouse_id`；company 的 `expired_at`/`is_active` 仅超管可改；staff 禁建公司 |
| B-04 | ✅ | 单据级写接口大面积缺归属校验：ASN/DN/Sorting/Picking/Packing/Delivery/CycleCount/Adjustment 的 PUT/DELETE `/<id>`、`/details/*`、`/batches/<id>`；POST 不校验 body 里的 `warehouse_id/asn_id/dn_id`（可占满他仓 `dn_stock`） | `asn/views.py:56-116,175-231`、`dn/views.py:54-111,170-222`、其余模块同构；共约 77/130 端点 | 所有 `/<id>` 及子资源加 `@warehouse_required()` + `check_warehouse_access(单据.warehouse_id)`；POST 校验 body 外键归属 |
| B-05 | ✅ | 未绑定用户的 API Key 不受租户隔离：`_enforce_company_scope` 遇 `company_id=None` 放行；`g.api_key_company_id` 只在 6 个 list + 2 个 POST 用到 | `system/third_party/views.py:9-30`、`utils.py:62-79` | 无 company 且非超管一律拒绝；API Key 路径统一用 `g.api_key_company_id` |
| B-06 | ✅ | 拣货完成后 `sorted_stock` 虚增、`total_stock` 双计：`complete_task` → `create_removal_record(reason='picking')` → `removal_completed` 无条件 `sorted_stock += q`，随后 `dn_picked` 又 `picked_stock += q`；`sorted_stock` 无流程扣减，已发货的货可再次上架 | `picking/services.py:502-513`、`removal/services.py:117`、`inventory/services.py:285-296,312-323` | `removal_completed` 区分拣货来源不进 `sorted_stock`；补全流程库存一致性测试 |
| B-07 | ✅ | GoodsLocation 直写接口 `POST/PUT /goods/locations/` 绕过所有单据流程，不同步 Inventory | `goods/views.py:159-191`、`services.py:355-394` | 移除写端点或加 `warehouse_required` + 归属 + 同步 Inventory |
| B-08 | ✅ | 停用用户/过期公司 JWT 永久有效：`user_lookup_loader` 只查存在性；`permission_required` 用 flask_jwt_extended 的 `current_user` 不看 `is_active`；`/refresh` 不查 `is_active`、`refresh_token_expires_at`、公司 `expired_at`；剩余 <24h 即发新 7 天 refresh 且旧的不作废；无 `token_in_blocklist_loader`；改密/重置不吊销 | `app.py:44-49`、`system/common/permissions.py:49-51`、`user/services.py:66-109` | lookup 检查 `is_active` + 公司过期；refresh 校验；Redis 黑名单（停用/改密/重置/登出时写入） |
| B-09 | ✅ | `activity_logs` 明文保存 `access_token`/`refresh_token`/`smtp_password`/`webhook_secret`/验证码：脱敏只匹配顶层精确键名；`logs_read` 即可读；列表 `keyword` 对正文 `ilike` | `system/logs/utils.py:8-17,67-78`、`views.py:54-59`、`services.py:34-35` | 递归 + 包含匹配脱敏；`/login`、`/refresh`、`/settings/smtp`、`/api-keys` 不记响应体；keyword 不搜正文 |
| B-10 | ✅ | 密码重置码可暴破（`random` 6 位、5 分钟、无限流、错误不计数）；`/forgot-password` 返回 "User not found" 枚举、同步 SMTP 阻塞、可无限发邮件 | `user/services.py:212-260`、`views.py:80-112`、`extensions/limiter.py:19-25` | `secrets`；错 5 次作废；`/login` `/forgot` `/reset` 限流；forgot 统一返回"若存在将发送"；发信异步 |
| B-11 | ✅ | Webhook SSRF：`webhook_url` 无校验、跟随重定向；retry 接口回显 `last_error`（含目标 URL） | `system/webhook/services.py:88-112`、`views.py:94-113`、`third_party/services.py:57,74` | 仅 https、拒绝私网/环回/链路本地、`allow_redirects=False`；`last_error` 不含 URL |

### 🟠 高

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| B-12 | ✅ | 状态/审计字段可被客户端批量赋值绕过状态机：`PUT /dn/<id> {"status":...}`、`PUT /delivery/<id> {"status":"signed"}`、`PUT /adjustment/<id> {"status":"approved"}`、DN 创建可传 `picked/packed/delivered_quantity` | `dn/services.py:303,322-324,364,370`、`delivery/services.py:158`、`adjustment/services.py:109` 等 8 处 | service 层白名单可更新字段，`status/is_active/created_by/*_quantity/*_at` 剔除 |
| B-13 | ✅ | Packing / Sorting 批次重复提交直接累加无上限；packing 会撞 `packed<=picked` 约束 500 卡死 | `packing/services.py:273-287`、`sorting/services.py:326-335` | 移植 picking 的 `_assert_within_planned`；拒绝 `goods_id ∉ 单据明细` |
| B-14 | ✅ | 拣货明细 `PUT /picking/<id>/details/<did>` 可改 `location_id` 到别仓库，complete 时跨仓扣库存 | `picking/services.py:175-194,498` | complete 前重跑 `_assert_location_stock` + 校验 `location.warehouse_id == dn.warehouse_id`；或禁用明细 PUT |
| B-15 | ✅ | DN 明细新增/修改/同步不校验可用量，可无限超额预占 | `dn/services.py:440-601` | 抽"排除本单预占的可用量校验"在 create/update/sync 复用；`quantity<=0` 拒绝 |
| B-16 | ✅ | packing 列表缺 `add_warehouse_filter`；transfer 列表缺 `warehouse_required` → 跨公司泄露 | `packing/views.py:26-47`、`transfer/views.py:23-50` | 补齐 |
| B-17 | ✅ | JWT 用户按 `goods_code` 建 ASN/DN 时公司固定为 1 | `asn/services.py:209,236,374,459`、`dn/services.py:254,272,450,544` | 从 `Staff.company_id` 取，缺省报错 |
| B-18 | 🔄 | 全项目 `expect()` 无 `validate=True`；`generate_input_fields` 检查 `readOnly` 而属性是 `readonly` → 零校验；缺字段/负数/dict 代 list 全部 500 | `system/common/utils.py:13-14`、各 views | 开 `RESTX_VALIDATE`；修 `readonly`；service 层统一数量 >0 校验　→ service 层数量/必填/列表校验已统一到 `warehouse/common/validation.py`，`readonly` 已修；`RESTX_VALIDATE` 仍未开启（asn 等输入模型的 `required=True` 会拦 PUT 局部更新，需先拆分 create/update 模型） |
| B-19 | ✅ | GoodsLocation 读改写无 `with_for_update`（putaway/removal/transfer/adjustment），多 worker 时丢更新 | `putaway/services.py:93-104`、`removal/services.py:92-113`、`transfer/services.py:104-138`、`adjustment/services.py:278-289` | 统一 `FOR UPDATE` |
| B-20 | ✅ | 登录无限流无锁定；审计日志可用 `Content-Type: application/json; charset=utf-8` 绕过脱敏、非 UTF-8 请求体让写操作不留记录 | `user/views.py:25-38`、`logs/utils.py:67-78,99-102` | `default_limits` + `/login` 限流；`request.is_json`；`decode(errors='replace')` |
| B-21 | ✅ | 平台管理员无 API 停用 `user` 账号（`update_user` 忽略 `is_active`）；删除级联删其 API Key | `user/services.py:146-186`、`third_party/models.py:45-50` | `update_user` 支持 `is_active`（禁自停）；删除前检查 API Key |
| B-22 | ✅ | API Key 明文存储、列表/详情回传 `key` 与 `webhook_secret`；`generate_api_key()` 未使用 | `third_party/services.py:50`、`schemas.py:30-40` | 存哈希，仅创建时回显一次；`webhook_secret` 只写不读 |
| B-23 | ✅ | `JWT_SECRET_KEY` 默认 `super-secret-jwt`、`CORS_ORIGINS` 默认 `*`、生产 DB 默认 sqlite，无启动校验 | `config.py:17,22,53` | 生产缺失即 `RuntimeError` |
| B-24 | ✅ | inventory 详情路径 `warehouse_id` 不经 `check_warehouse_access`；warehouse PUT 的 manager 归属比对客户端 `company_id`、旧 manager 不解绑 | `inventory/views.py:55-65`、`warehouse/services.py:91-125` | 补校验 |
| B-25 | ✅ | 种子权限缺 `inventory_edit/inventory_delete/webhook_read/webhook_edit`；5 个模块 stats 端点错用 `sorting_read`，adjustment stats 调的是 CycleCount 服务 | `seed_permissions.py`、`picking/views.py:279,302` 等 | 补种子；改权限名与服务 |

### 🟡 中

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| B-26 | ✅ | 快照任务 `len(Query)` → `/tasks/inventory_snapshot` 500、每晚定时任务报错；唯一失败的测试 | `tasks/snapshot.py:13` | `.all()` / `.count()` |
| B-27 | ✅ | `/system/user/*`、`/company`、`/api-keys` 列表过滤参数未在 parser 定义永远无效；`?all=true` 无效；`per_page` 无上限 | `user/schemas.py:113`、`views.py:128-131,190-193,252-255`、`common/pagination.py:74` | 补 `add_argument`；`max_per_page` |
| B-28 | ✅ | scheduler：`FLASK_ENV` 默认值与 config 不一致；`flask db upgrade`/seed 也起调度线程；Windows 无 fcntl 双启动；uwsgi 无 `enable-threads`；日志默认值 '1' vs '30' | `scheduler.py:20,48-70`、`app.py:84-85` | 用 `Config.FLASK_ENV`；`SCHEDULER_ENABLED` 开关只在 WSGI 入口启 |
| B-29 | ✅ | IP 黑白名单整个模块是死功能（`check_ip` 未注册、CRUD 不写 Redis）；无 `ProxyFix`，反代下 `remote_addr` 恒为代理 IP | `app.py:62,77-78`、`limiter/services.py:28-51` | 加 `ProxyFix`；注册 `check_ip`；服务层同步 Redis |
| B-30 | ✅ | 审计日志有 POST/PUT/DELETE 接口可伪造篡改；无保留期；`save_large_data` 文件无清理 | `logs/views.py:37-76` | 审计表只读 |
| B-31 | ✅ | SMTP 密码 Fernet 密钥与密文同表 | `settings/services.py:19-44` | 密钥来自环境变量 |
| B-32 | ✅ | Webhook 无事件 ID/时间戳可重放；整批单次 commit；`webhook_secret` 为空静默不签名 | `webhook/services.py:76-148` | 加 `X-Webhook-Id`/`Timestamp` 入签名；逐条 commit |
| B-33 | ✅ | DN/ASN 进入流程后无取消路径，预占永久占用 | `dn/services.py:772`、`asn/services.py:632` | 增加 cancel 并释放预占 |
| B-34 | ✅ | Adjustment approve/complete 同权限；approved 后明细仍可改；`create_adjustment_from_cyclecount` 不要求盘点 completed | `adjustment/views.py:104,125`、`services.py:199-228,299-311` | 独立 `adjustment_approve`；approved 后冻结 |
| B-35 | ✅ | picking/packing `POST /<id>/details/` 不设 `batch_id` 而列 NOT NULL → 必 500（死端点）；`process_task` 缺 `@transactional` | `picking/services.py:150-158,475-484`、`packing/services.py:158-166` | 移除死端点或补 batch；加装饰器 |
| B-36 | ✅ | `location/views.py:2 from amqp import NotFound` 误导入；`requirements.txt` UTF-16 且含 amqp/billiard/kombu/flower/vine/Flask-Script/mcp/uvicorn/starlette/tornado/pip-review 等无引用包 | `location/views.py:2`、`requirements.txt` | 删导入；转 UTF-8 并清理 |
| B-37 | ✅ | 根目录 `test_webhook.py`/`test_webhook_real.py` 用真实配置建 `all_access` key、改生产 key | 根目录 | 移到 tests/ 或加 guard |
| B-38 | ✅ | `password_hash` 可空 → 无密码 staff 登录 500 | `user/models.py:108-112`、`services.py:353` | `check_password` 判空 |
| B-39 | ✅ | `company.email`/`supplier.email`/`staff.phone` 全局唯一 → 跨公司冲突与枚举 | models | 改为 (company_id, x) 联合唯一 |
| B-40 | ✅ | `asn_completed` 静默清零负 `received_stock`；CycleCount `POST /<id>/details/` 不校验 task 归属；Delivery PUT 可改 `dn_id`；`update_task_detail` 接受 `status/operator_id` | `inventory/services.py:258-260`、`cyclecount/views.py:158-183`、`delivery/services.py:148` | 报错 / 补校验 / 白名单 |
| B-41 | ✅ | 测试缺口：零跨公司 403、零 API Key 路径、零 refresh/inactive、零脱敏、零全流程库存一致性；`test_picking.py:441` 无效断言 | `tests/` | 补关键用例 |

### 🔵 低

| ID | 状态 | 问题 | 位置 |
|---|---|---|---|
| B-42 | ✅ | N+1：列表 schema lambda 逐行访问 `x.details`；`dn/services.py:111-138` 每明细 2 次查询 | `asn/schemas.py:74-126`、`sorting/schemas.py:91-99`、`picking/schemas.py:93-101` |
| B-43 | ✅ | 只读 IDOR：putaway/removal/transfer `GET /<id>` 无仓库校验 | `putaway/views.py:78-83`、`removal/views.py:76-81`、`transfer/views.py:92-97` |
| B-44 | ✅ | 代码残留：`adjustment/views.py:114-115` 重复 raise、两个同名类；复制粘贴类名 `PickingStatusOverviewStats`；`logs/models.py:57 trace_id`、`limiter/models.py:32,70 ip_type` 不存在；`api_key_input_model/update_model` 定义未用；`role_required` 无调用；`/system/user/test` 调试端点 | 各处 |
| B-45 | ✅ | 错误信息外泄：`user/views.py:92-93,111-112`、`settings/views.py:44-45` 直接 `str(e)`；`error.py` 对 `ValueError` 生产也回 `str(error)` | `extensions/error.py:85-100` |
| B-46 | ✅ | 快照逐行 INSERT、无保留策略；上传无 `MAX_CONTENT_LENGTH`；bulk_upload 缺列 500；schema/model 类型不一致（payment currency 默认、goods 尺寸 Float/Integer、`Goods.created_by` SET NULL + nullable=False） | 各处　→ 上传体积上限、schema/model 类型对齐、`Goods.created_by` 可空已做；库存快照保留期策略未做（需业务定义保留天数） |
---

## 二、Web 管理端

### 🔴 严重

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| W-01 | ✅ | 富文本 `description` 存储型 XSS：Quill 录入、后端原样存、`v-html` 渲染、CSV 导入可绕过编辑器；token cookie 非 HttpOnly、无吊销 | `app/pages/goods/add.vue:167`、`goods/detail/[id].vue:378`、`location/detail/[id].vue:358`、`department/detail/[id].vue:70`、`goods/upload.vue:23`、`[BE] goods/services.py:130,187` | 后端 `nh3` 白名单清洗；前端 DOMPurify |
| W-02 | ✅ | 管理端「新建权限」必 500（后端给无 `is_active` 列的 `Permission` 传 kwarg） | `app/pages/admin/permissions/add.vue:36-38`、`[BE] user/services.py:381-385` | 后端删 `is_active` 引用 |

### 🟠 高

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| W-03 | ✅ | `secure: true` cookie 在 http:// 部署下不保存 → 登录即弹回 | `app/stores/auth.ts:19` | `secure: location.protocol === 'https:'` |
| W-04 | ✅ | 编辑已设 `expired_at` 的租户保存必失败（后端回 ISO 串，前端原样 PUT，后端 `strptime('%Y-%m-%d')`） | `tenants/[id].vue:46,153`、`[BE] company/services.py:79-80` | 前端 `slice(0,10)`、空转 null；后端 `fromisoformat` |
| W-05 | ✅ | 新建租户后无入口创建首个员工；用户页无新增/编辑/改角色/改密码 | `tenants/add.vue`、`users/index.vue` | 租户页加初始管理员；用户页补新增/编辑 |
| W-06 | ✅ | 用户页"停用/启用"假按钮；用户/角色/权限/租户/API Key 搜索与 Tab 因后端 parser 未定义参数全部无效 | `users/index.vue:66-92`、各 index.vue:43 `keyword` | 后端 B-21/B-27；前端对齐参数名 |
| W-07 | ✅ | API Key "仅显示一次"提示不实，列表可随时复制完整 key；`webhook_secret` 随列表返回 | `apikeys/index.vue:297-300,372-373,449` | 配合后端 B-22 改为只显示前缀 |
| W-08 | ✅ | 平台管理员点"修改密码"被中间件弹回 `/admin/` | `Header.vue:297`、`auth.global.ts:27-30` | 放行 `/authentication/reset-password` |

### 🟡 中

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| W-09 | ✅ | 401 后 `logUserOut()` 不跳转，admin 布局空白；登出仅客户端 | `authFetch.ts:60-62`、`useAuthFetch.ts:48-52`、`layouts/admin.vue:2` | 401 统一 `navigateTo('/auth/login')`；调后端 logout |
| W-10 | ✅ | 登录失败原因被 store 吞掉统一显示"账号或密码错误"；按钮无 loading；`authenticateUser` 与 `refreshToken` 共用 `loading` | `stores/auth.ts:46-48,66-68`、`login.vue:119-133,238` | store 返回 message；按钮绑定 loading |
| W-11 | ✅ | forgot-password 原样展示后端 `str(e)` → 枚举与内部错误泄露 | `forgot-password.vue:54-56,73-75,107-109` | 配合后端 B-10 通用文案 |
| W-12 | ✅ | 删除租户遇 FK RESTRICT 必 500，确认框未说明后果；删除后 API Key 变孤儿 | `tenants/index.vue:50-64`、`[BE] company/services.py:99-105` | 后端先校验关联返回 409 + 停用 API Key；前端文案 |
| W-13 | ✅ | 可删自己、可删使用中的角色 | `users/index.vue:50-64,179`、`[BE] user/services.py:190-197,331-337` | 前端隐藏；后端拒绝 |
| W-14 | ✅ | 侧栏"日志"指向不存在的 `/admin/logs/` | `data/adminMenuData.js:56-64` | 删菜单或补页面 |
| W-15 | ✅ | 两套请求封装不一致（`useAuthFetch` 无刷新锁、不暴露后端 message）；store 内 `useFetch`；`http.ts` 硬编码中文 | `useAuthFetch.ts:14-30`、`stores/auth.ts:41,108`、`utils/http.ts:72,82` | store 改 `$fetch`；统一 |
| W-16 | ✅ | 前端"加密"密钥打进 bundle；换 key 部署后 `userInfo` 解密失败、token 仍在 → 管理员被踢到员工首页且无法自愈 | `utils/storage.ts:7-10`、`auth.global.ts` | 解密失败清 cookie 跳登录 |

### 🔵 低

| ID | 状态 | 问题 | 位置 |
|---|---|---|---|
| W-17 | ✅ | `passwordInput` 无 `autocomplete`；reset-password 忽略后端 message | `components/UI/passwordInput.vue:3-12`、`authentication/reset-password.vue:100-102` |
| W-18 | ✅ | `dayjs` 固定 `zh-cn`；favicon 指向模板路径；`app.vue:20` 重复 icon link | `plugins/dayjs.client.ts:7`、`nuxt.config.ts:31` |
| W-19 | ✅ | `apiBase` 放 public runtimeConfig；`server/api/[...].ts` 无路径白名单会透传 Swagger | `nuxt.config.ts:124`、`server/api/[...].ts` |
| W-20 | ✅ | `package.json`：`main: gulpfile.js`、`yarn`/`install` 作依赖、约 20 个零引用依赖（leaflet、fullcalendar、google-map、codemirror、faker、gridjs、lightgallery、photoswipe、vue-chart-3、echarts、form-wizard、star-rating、select2、draggable、slider、animation.css、vee-validate、countup）；`plugin.d.ts` 声明 vuex/dropzone | `package.json`、`nuxt.config.ts` manualChunks |
| W-21 | ✅ | 残留：`Header.vue:151` console.log；`menuData.js:1` 顶层 `useLocalePath()`；`admin/index.vue:18-27` `tenants.active/expired` 未计算；`apikeys/index.vue:533,159` 硬编码文案 | 各处 |
| W-22 | ✅ | 会话 cookie 无 `maxAge`，7 天 refresh 形同虚设；`vue-tsc` 不在 devDependencies；deploy 用 `npm install` 且 `rm: true` | `stores/auth.ts`、`package.json`、`deploy.yml` |

---

## 三、APP

### 🔴 严重

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| A-01 | ✅ | `@sentry/vue`、`vue-i18n` 未在 `package.json`/lockfile，干净安装 build 必挂 | `src/main.js:11-12`、`package.json` | 写入 dependencies |
| A-02 | ✅ | 扫码匹配 `current` 不复位：扫到不在单内的条码给上一次命中商品 +1（分拣、盘点）；拣货"不在本单"提示只首次有效；`searchJan` 同 | `SortingDetail.vue:116,149-171`、`StocktakingDetail.vue:122,141-157`、`PickingDetail.vue:182,186-207` | 局部 `findIndex` |
| A-03 | ✅ | 拣货"完成"失败后 `checked` 不清，重试重复 POST 同一批次；`save/complete/start` 无锁可连点；空 details 也 POST | `PickingDetail.vue:113-161` | `submitting` 锁；成功后清 checked；catch 里 `init()` |
| A-04 | ✅ | `request.js` 过期分支不 reject 也不清 token → 页面 TypeError、守卫放行 | `src/utils/request.js:40-43` | `removeItem('token')` + `reject`；识别其余 JWT 文案；未知码显示后端 message |
| A-05 | ✅ | Android `allowUniversalAccessFromFileURLs`/`allowFileAccessFromFileURLs`/`MIXED_CONTENT_ALWAYS_ALLOW`/`usesCleartextTraffic`/`allowBackup` 全开 | `MainActivity.kt:51-60`、`AndroidManifest.xml:15,21` | `WebViewAssetLoader` + 关闭开关 + `allowBackup=false`　→ 已改为 WebViewAssetLoader（`AssetBridgeWebView.kt`，已核实 JsBridge 1.0.4 的 `generateBridgeWebViewClient` 可覆写），四个开关全关；2026-09-29 已装到小米 21091116AC（Android 12）真机：页面加载正常、无崩溃；扫码桥接待登录后人工点"扫一扫"确认。页面来源变为 `https://appassets.androidplatform.net`，生产 `CORS_ORIGINS` 必须包含它 |
| A-06 | ✅ | 非 company_admin 员工首次选仓时 `/staff/current` 带 `@warehouse_required()` 抛 14003，列表永远转圈 | `Select.vue:11`、`[BE] staff/views.py:88-93` | 后端 `/staff/current` 豁免；APP 空态区分错误 |

### 🟠 高

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| A-07 | ✅ | 盘点页 JAN 框失焦即崩（读 `detail.value.asn.details`） | `StocktakingDetail.vue:123-137` | 改 `task_details` |
| A-08 | ✅ | 拣货页每次扫码清空所有库位已选 | `PickingDetail.vue:188-192` | 删除 |
| A-09 | ✅ | 数量输入无边界：负数/小数/0/NaN 可提交（Picking/Move/Remove/Stocktaking/Pack） | `PickingDetail.vue:335,56,77`、`Move.vue:207`、`Remove.vue:194`、`StocktakingDetail.vue:262`、`PackDetail.vue:244,87` | `:min="1" :precision="0"` + 提交校验 |
| A-10 | ✅ | `Home.vue` 刷新链路：refresh token 写进 `token`、失败无 catch → 后续 422 无法恢复；`expires` 写死 23h/7d 不用 `expires_in`；登出不清 `refresh_token/expires` | `Home.vue:15-22`、`stores/index.js`、`Select.vue:30-35` | 重写为：过期时用 refresh token 单独请求，成功写回 access + 新 refresh + `expires_in`；失败清空跳登录 |
| A-11 | ✅ | ESLint 未忽略 `android/**`，`npm run lint --fix` 会改写 APK 内 JS；files 不含 `.ts` | `eslint.config.js:10,14-16` | ignores 加 android；files 加 ts |
| A-12 | ✅ | `.js`/`.ts` 同名并存，Vite 先解析 `.js`，`.ts` 是死代码；vue-tsc 4 错（`@vue/tsconfig` 需 TS ≥5.8） | `src/utils/request.*`、`src/stores/index.*`、`src/api/*.*` | 删 `.js` 副本让 `.ts` 生效（先合并差异）；升 TS |
| A-13 | ✅ | Cypress 骨架不可运行（fixture 缺失、事件无监听、选择器不匹配） | `cypress/e2e/*.cy.ts` | 修或删 |

### 🟡 中

| ID | 状态 | 问题 | 位置 |
|---|---|---|---|
| A-14 | ✅ | 商品多选对话框"取消"关错变量 `dialogVisibleLocation` → 应为 `dialogVisibleGoods` | `Add.vue:236`、`Move.vue:245`、`Remove.vue:230` |
| A-15 | ✅ | 命中恰 5 条时静默/误报（`res.total < 5`） | `Add.vue:42,134`、`Move.vue:137`、`Remove.vue:121` |
| A-16 | ✅ | `Remove.vue` `getLocation` 无空值保护，空框失焦查全表 | `Remove.vue:116-117` |
| A-17 | ⏭ | 扫码不区分商品/库位条码，一律当 JAN | `Add.vue:153-170`、`Move.vue:161-178`、`Remove.vue:139-156`　→ 库位条码无可区分规则，仅改提示文案；需业务侧定义库位码格式后再做 |
| A-18 | ✅ | `useList` 200 条上限 UI 无提示；`Goods/List.vue`、`Location/List.vue` 自建 observer 不 disconnect 且 root 为 null | `useList.ts`、`Goods/List.vue:47-66`、`Location/List.vue:36-46` |
| A-19 | ✅ | `getLocation` 不传 `per_page`，>20 库位不可选 | `PickingDetail.vue:39` |
| A-20 | ✅ | "可拣"显示物理库存未减已保存批次 → 二次可再选同量 → 16036 | `PickingDetail.vue:294,323` |
| A-21 | ✅ | `SortingDetail.vue:275` `@change="handleDamageQuantity(e, index)"` `e` 未定义；正常数量无负数保护 | `SortingDetail.vue:275` |
| A-22 | ✅ | `PackDetail` 分两次保存第二次必报不一致（不扣 `tmp_packed_quantity`） | `PackDetail.vue:50` |
| A-23 | ✅ | `vite.config.js` `devServer.proxy` 不是 Vite 选项 | `vite.config.js:28-36` |
| A-24 | ✅ | dist → android assets 无脚本靠手工 | `package.json` |
| A-25 | ⏭ | 主 chunk 1.2 MB（Element Plus 全量） | `main.js:4-7`　→ 离线包体积收益低且按需引入的样式无法在本机验证，暂不做 |
| A-26 | ✅ | 17 处 `console.log` | 各 views |
| A-27 | ✅ | `error.json` 缺 12 个后端码（16029/16034/16035/16036/16030/16031/16032/16033/16037/43001/10007/10008）、13005 已废、12005 重复 | `src/utils/error.json` |
| A-28 | ✅ | `GoodsItem/index.vue:17` 硬编码 http 图片；本地 `no_picture.png` 未用 | `GoodsItem/index.vue:17` |

### 🔵 低

| ID | 状态 | 问题 | 位置 |
|---|---|---|---|
| A-29 | ✅ | `AndroidManifest.xml` `tools:replace` 声明在 activity 元素上（合法但应移到根）；`onBackPressed` 已弃用 | `AndroidManifest.xml:36-40`、`MainActivity.kt:97`　→ 已改（`xmlns:tools` 移根、`OnBackPressedCallback`）；随 A-05 一起真机验证 |
| A-30 | ⏭ | ZXing 摄像头方案与 PDA 物理扫描头（键盘楔子/广播）不兼容；输入框只 `@blur` | `MainActivity.kt`、各输入框　→ PDA 物理扫描头（键盘楔子 / 广播）适配需要目标机型信息，暂不做 |
| A-31 | ✅ | 死代码：`src/jsBridge.js` 与 `views/jsBridge.js` 无人 import；`Search/index.vue` 未定义变量；HelloWorld/TheWelcome/icons 脚手架；`DeliveryManagement/List.vue` 是 ASN 列表复制品；`QuantityBox` 无引用 | 各处 |
| A-32 | ✅ | `vite-plugin-pwa`/`workbox-window` 未启用；`prepare: cypress install`；version 0.0.0 vs 1.0.1；`android/local.properties` 被跟踪 | `package.json`、git |
| A-33 | ✅ | `sentry.ts` `maskAllText:false` 会回放客户信息；i18n 零使用 | `src/utils/sentry.ts:14-17` |
| A-34 | ✅ | `Goods/Detail.vue:32-45` 残留 `test()` 测试代码 | `Goods/Detail.vue` |
| A-35 | ✅ | `CLAUDE.md` 与现状不符（硬编码 baseURL、`useList.js`、Android 加载 http） | `CLAUDE.md` |
| A-36 | ✅ | `Home.vue:10-12` setup 里 `router.push('/login')` 冗余 | `Home.vue` |

---

## 四、已核实无问题（保留）

- 后端 182 个端点全部有 `permission_required`，无匿名可写端点；`/<id>` GET 与 `process/complete/receive/close/batches POST` 等动作端点仓库校验正确；`recipient` 模块 `_request_company_id()` 隔离正确
- 此前修复的三个 bug（DN 库存不足误报、重复拣货批次路径、PG FOR UPDATE + outer join）方式正确、有回归测试
- Webhook outbox 模式随事务提交；HMAC 实现正确；payload 无跨公司数据；`@transactional` 嵌套语义正确；OSS 上传防护完整；密码 werkzeug 哈希
- Web：SMTP 密码不会被 `********` 覆盖；角色编辑权限列表拉全量、提交 id 一致；`PermissionSelector` 覆盖 84 个权限；209 个 i18n key 三语齐全；`.env.*` 未入库；删除均二次确认
- APP：全 src 无 `v-html`；`useList.ts` observer 正确清理；API 路径与后端一致；`Add.vue` 提交前校验完整

---

## 五、修复日志

| 日期 | 批次 | 内容 |
|---|---|---|
| 2026-09-29 | 0 | 审计完成，建立本跟踪文档 |
| 2026-09-29 | 1 | **Backend 系统层**：B-01/02/05/06/08/09/10/11/16/20/21/22/23/26/27/28/29/30/31/32/36/37/38/45 ✅，B-03（company/department 部分）、B-25（种子部分）🔄。新增 `extensions/jwt.py` 统一回调 + Redis 吊销、`system/webhook/utils.py` URL 校验、`warehouse/common/ownership.py` 归属辅助、`/system/user/logout`、`tests/test_security.py`、migration `c8d1e2f3a4b5`（API Key 哈希）。测试 306 通过。**注意**：部署时需 `flask db upgrade`；现有明文 API Key 会被就地哈希，客户端无需改；`.env` 建议新增 `TRUSTED_PROXY_COUNT`、`CORS_ORIGINS`、`SETTINGS_ENCRYPTION_KEY`（见 `.env.example`）。 |
| 2026-09-29 | 1 | **Web**：W-01、W-03~W-22 ✅（W-02 为后端修复）。新增 `app/utils/sanitize.ts`（DOMPurify）、`app/pages/admin/logs/index.vue`、用户新增/编辑弹窗、租户初始管理员；删 21 个零引用依赖；`npm run build_test` 通过。 |
| 2026-09-29 | 1 | **APP**：`android/local.properties` 取消跟踪（A-32 部分）；其余由 app-fix 处理中。 |
| 2026-09-29 | 2 | **APP**：A-01~04/06~16/18~24/26~28/31~36 ✅；A-05/A-29 ❓（Android 壳已改为 `WebViewAssetLoader`，需真机验证）；A-17/25/30 ⏭。`.js`/`.ts` 副本合并为 `.ts`，TypeScript 升 5.9，`vue-tsc`/`eslint src`/`vitest`/`build` 全部通过；新增 `scripts/copy-to-android.mjs` + `npm run build:android`；`error.json` 补 12 码；CLAUDE.md 重写。 |
| 2026-09-29 | 3 | **Backend 业务模块**（三个子代理并行）：B-03/04/07/12/13/14/15/17/19/24/25/33/34/35/39/40/41/42/43/44/46 ✅，B-18 🔄。新增共享层 `warehouse/common/{ownership,validation,locks}.py`（归属校验 / 数量校验 / GoodsLocation 行锁 / `require_actor_user_id`），`warehouse_required` 支持绑定公司的 API Key；新增 `PUT /asn/<id>/cancel/`、`PUT /dn/<id>/cancel/`，删除 `POST/PUT/DELETE /goods/locations/*` 与 picking/packing 的 `POST /<id>/details/`；migration `d9e2f3a4b5c6`（supplier.email 公司内唯一、goods.created_by 可空）、`e0f1a2b3c4d5`（staff.phone 公司内唯一）；新增 `tests/test_isolation_{inbound,outbound,master}.py` 等约 170 个用例。业务码撞号已统一（新码 16051–16062、10012/10013、44001–44003），APP `error.json` 已补 38 条。**前端需知的行为变化**：所有单据 PUT 不再接受 `status`/`is_active`/过程量；`POST /dn/`、location/cyclecount/adjustment 的 POST 及子资源要求非 company_admin 员工带 `X-WAREHOUSE-ID`（Web/APP 已全局注入）；拣货/分拣/打包批次拒绝不在单据内的商品；未绑定用户的 API Key 做写操作返回 400/11008。 |
| 2026-09-29 | 4 | **收尾**：`warehouse/common/decorators.py` 模型改为延迟导入（断开与各模块 views 的循环导入）；19 个 warehouse views 的 `g.current_user.id` 统一为 `require_actor_user_id()`（无用户的 API Key 写操作 400/11008）；后端全量 **467 passed**（审计前 292）。三个子仓库的改动**均未提交**。 |
| 2026-09-29 | 5 | **部署（进行中）**：Backend 已推送 `58c6a68`+`a9af3ce`（Redis 降级）；服务器安装了 Redis、`.env` 加 `TRUSTED_PROXY_COUNT=1`/`REDIS_URL`、种子权限已入库（+5）。**迁移失败**：生产库 51 张表 owner 是 `postgres`，应用账号 `warehouse` 无法 `ALTER TABLE`（GitHub Actions 两次部署也因此卡在 `flask db upgrade`）。线上 API 已**回退到 `d4d66b7`**（detached HEAD）等待 owner 移交。APK 1.1.0（versionCode 3）已上传 OSS `download/gm_wms.apk`（旧包备份为 `gm_wms-1.0.1.apk`），APP 仓库已推送 `a458bd7`。Web 已提交 `5c1099b` 未推送（等后端上线）。 |
| 2026-09-29 | 6 | **部署完成**：db 主机上把 warehouse 库全部表/序列 owner 从 `postgres` 移交给 `warehouse`（备份 `/root/backups/warehouse_pre_audit_2026-09-29_1222.sql.gz`），此后 Actions 里的 `flask db upgrade` 可自动执行；线上 API 切回 `main`（a9af3ce）、迁移到 `e0f1a2b3c4d5`、已重启并探测通过；`api_wholesale` 的 `WMS_API_KEY` 与哈希后的库记录匹配，集成不受影响。Web 5c1099b 已推送并由 Actions 部署到 `/var/www/admin_wms`。主仓库子模块指针 d160431 已推送。**待办**：服务器 `.env` 设置 `CORS_ORIGINS`（含 `https://appassets.androidplatform.net`）与 `SETTINGS_ENCRYPTION_KEY`；APP 1.1.0 真机验证；db 主机 root 密码本次在会话中使用过，建议轮换。 |
| 2026-09-29 | 7 | **收尾配置**：服务器 `.env` 设 `CORS_ORIGINS=https://appassets.androidplatform.net,null`（`null` 为旧版 file:// APK 来源，PDA 全部升到 1.1.0 后去掉）与 `SETTINGS_ENCRYPTION_KEY`（生产库 `system_settings` 为空，SMTP 从未配置，找回密码邮件需先在管理端填 SMTP）；Backend `717da3f` 让 `CORS_ORIGINS` 支持逗号分隔。此次由 GitHub Actions 自动完成 pull → migrate → restart，部署链路已恢复正常。CORS 探测：APP 来源与 null 放行、其它来源无 ACAO 头。 |
