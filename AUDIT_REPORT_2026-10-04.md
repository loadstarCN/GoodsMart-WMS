# GoodsMart-WMS 审核报告与修复跟踪（2026-10-04）

> 范围：Backend（system + warehouse 全部模块，重点是 09-29 之后新增的报关单证、FedEx 自动运单、商品原产国、goods.spec_updated webhook）、Web（业务页面全部（上次只审了 /admin、/apikeys 和认证），以及报关 / FedEx 新界面）、APP（全部代码 + Android 壳 + 发布流水线）。Station、Website 未覆盖。
> 基线：Backend `748b80d`、Web `6ff10ab`、APP `b0d3ef8`（1.3.1），即主仓库 `c92c569` 记录的子模块指针。
> 方法：只读审计（7 个子任务并行，按范围拆分）+ 临时测试复现（约 80 个用例，全部在 scratchpad，未写入仓库）+ 自动检查。
> 路径均相对各子仓库根目录；`[BE]` = Backend、`[WEB]` = Web、`[APP]` = APP。编号接续 09-29 报告。
>
> **自动检查**
> - Backend：全量 pytest 666 passed。**本机 `.venv` 缺 reportlab / pypdf / pillow / fakeredis**（`requirements.txt` 里有），报关 / 运单测试在本机 venv 跑不起来，且每个请求都要等 Redis 超时；本次用 scratchpad 里按 `requirements.txt` 新建的 venv 跑。
> - Web：`npm ci` + `build_test` 通过；`nuxi typecheck` 72 个错误，全在旧模板组件与 CookieRef 类型声明，新增的报关代码 0 个，不影响运行。
> - APP：vitest 86/86、vue-tsc、eslint、build 全部通过。
>
> **状态图例**：⬜ 未开始 · 🔄 进行中 · ✅ 已修复 · ⏭ 暂不修（附原因） · ❓ 待确认

---

## 〇、优先处理

| 优先级 | 编号 | 一句话 |
|---|---|---|
| 1 | B-47 | API Key 所属公司没有启用仓库时，32 个列表 / 统计 / 搜索接口返回**全平台**数据 |
| 2 | B-48 | JWT 建 DN 可在请求体带别家 `api_key_id`，让别家系统收到带合法签名的伪造 webhook |
| 3 | B-50 | 拣货 / 收货 / 分拣等状态转换不锁单据行，PG 下重复提交会重复记账（超卖、幻影库存） |
| 4 | B-49 | ASN 同一商品多行明细时 `sorted_stock` 重复入账，多出的货能上架成在库 |
| 5 | W-23 / A-37 | 完成发货时填了快递费就被 400 16033 拒（Web、APP 都按字符串提交） |
| 6 | B-51 | 只有 `staff_edit` 的员工可以改 company_admin 的密码并接管 |
| 7 | B-52 | ASN / DN 统计缓存键不含租户，60 秒内跨公司串数据 |
| 8 | A-38 ~ A-42 | PDA 作业：分拣 / 打包重试重复提交、盘点记错库位、上架 / 下架 / 移库提交到上次的库位 |
| 9 | B-57 | 同一 DN 两条有效发货任务可绕过运单锁、CI 运单号校验和单证过期判定 |
| 10 | B-59 / B-60 | 一个租户的慢速 webhook 接收端能让全平台推送停摆 |

---

## 一、Backend

### 🔴 严重

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| B-47 | ✅ | **API Key 跨租户读全平台数据**（B-05 修得不完整）：绑定公司的 Key，若该公司没有启用中的仓库（刚开通未建仓，或 company_admin 把唯一仓库停用），`g.accessible_warehouses = []`，`add_warehouse_filter` 遇空列表**不加任何过滤**。`GET /inventory/`、`/asn/`、`/dn/`、`/delivery/` 等 32 个列表 / monthly-stats / status-overview-stats / details/search 返回所有公司的数据。员工路径有拦截，API Key 路径没有；详情接口不受影响（返回 403） | `warehouse/common/decorators.py:123-145`、`warehouse/common/utils.py:13-15` | Key 有公司但无启用仓库时直接 403；`add_warehouse_filter` 在"需要过滤但列表为空"时返回空集（如 `warehouse_ids=[]` → `IN ()` 恒假） |
| B-48 | ✅ | **伪造他公司 webhook**（B-04 修得不完整）：`POST /dn/` 只在 API Key 认证时覆盖 `api_key_id`，JWT 路径下请求体里的值原样入库；`emit()` 不校验 Key 与单据同公司。A 公司管理员建 DN 时带 B 公司集成 Key 的 id（自增可枚举）和 B 的订单号，走完流程后 B 的系统收到用 B 自己密钥签名的 `dn.in_progress / delivered / completed`。ASN 已修（`asn/views.py:89` 强制覆盖），DN 漏了 | `warehouse/dn/views.py:87-89`、`dn/services.py:468`、`system/webhook/services.py:24-55` | 照 ASN 写法 `data['api_key_id'] = api_key.id if api_key else None`；`emit()` 校验 Key 公司 == 单据公司 |
| B-49 | ✅ | **ASN 同商品多行时 `sorted_stock` 重复入账**：`_update_and_calculate_quantity` 按商品汇总分拣量后把总量赋给每一行，`asn_completed` 再逐行累加。两行各 5 件、分拣 10 件完成后 `sorted_stock=20`，`POST /putaway/ quantity=20` 成功，`onhand_stock` 变 20（实物 10）；`asn.completed` webhook 两行也各报 10。接口不拒重复商品，ERP 按采购行推送很常见 | `warehouse/asn/services.py:189-193`、`:633` | 建单 / 改单 / sync / 加明细都拒绝重复 goods_id（DN 已有 16025）；或按行分摊分拣量。**上线前先查存量 ASN 有无重复行** |
| B-50 | ✅ | **状态转换不锁单据行**：单据 / 任务不加锁读出，第二个并发请求在库存 / 库位 FOR UPDATE 上等第一个提交后，仍按内存里的旧状态继续执行。已用双会话交错复现：拣货完成提交两次 → 同库位扣 10（实拣 5）、吃掉另一张 DN 的预占（超卖）、`picked_stock=10`、多建一个打包任务；收货提交两次 → `received_stock=20`、两个分拣任务；分拣完成两次 → 10 件幻影 `sorted_stock`。只有 delivery complete 用了"锁 DN + refresh" | `picking/services.py:522-559`、`sorting/services.py:510-524`、`asn/services.py:572-591,676`、`packing/services.py:426-441`、`delivery/services.py:471-493`、`dn/services.py:788,826,971`、`adjustment/services.py:312-331`、`cyclecount/services.py:297-317` | 每个状态转换开头只按主键锁任务行和所属 DN/ASN 行（`FOR UPDATE`，照 `CustomsService._lock`），`refresh()` 后重查状态；或 `UPDATE ... WHERE status=:old` 检查影响行数。批次追加接口同样先锁任务行 |

### 🟠 高

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| B-51 | ✅ | **普通员工接管 company_admin**：staff 写接口只校验同公司，不校验目标权限是否高于调用者。只有 `staff_edit` 的员工 `PUT /staff/<company_admin> {"password":...}` → 200，可直接登录；也可 `{"roles":[]}` 剥权、DELETE、给自己加全公司仓库 | `warehouse/staff/views.py:11-15,85-110`、`services.py:150-190` | 非 company_admin 不能操作权限不是自己子集的员工；`warehouse_ids` ⊆ 调用者可访问范围 |
| B-52 | ✅ | **统计缓存跨租户**：`@cache.cached(query_string=True)` 的键只有路径 + 查询参数，不含 `X-WAREHOUSE-ID` 与调用者；生产 Redis 多 worker 共享。A 公司请求后 60 秒内 B 公司同 URL 拿到 A 的统计 | `asn/views.py:279,305`、`dn/views.py:275,301` | 自定义缓存键编入公司与可访问仓库，或去掉缓存 |
| B-53 | ✅ | **调整单 / 盘点单明细 `goods_id` 不校验公司**：填 B 公司商品 id → 201，响应回显 B 的 code、名称、价格、品牌、尺寸、原产国，可枚举拖走全平台商品目录。5 个端点：`POST /adjustment/`、`POST /adjustment/<id>/details/`、`PUT /adjustment/<id>/details/<did>`、`POST /cyclecount/`、`PUT /cyclecount/<id>/details/<did>` | `adjustment/services.py:211,248`、`cyclecount/services.py:95,226` | 商品必须属于单据仓库所在公司 |
| B-54 | ✅ | **打包少打或不打即可完成，差额永久留在 `picked_stock`**：完成只校验 packed ≤ picked，`dn_packed` 只搬已打包量。拣 5 打 3 → 发货签收后 `picked_stock` 剩 2、`total_stock` 多 2；零批次直接完成则 5 件全留 | `packing/services.py:426-441`、`dn/services.py:851-864` | 完成时要求每商品 packed == picked，否则 409；或把差额显式退回 `sorted_stock` |
| B-55 | ✅ | **库位停用 / 改类型不重算，上架 / 移库允许进停用库位**：有 6 件货的库位停用后，下一次重算 `onhand_stock` 少 6，GoodsLocation 仍是 10；standard → damaged 后 onhand 仍 10，按库位汇总标准库位 0、残次 10 | `location/services.py:79-95`、`putaway/services.py:88`、`transfer/services.py:108-111`；汇总见 `goods/services.py:584-586` | 有货时禁止停用 / 改类型（或改完重算）；上架 / 移库目标必须启用 |
| B-56 | ✅ | **下架接口信任客户端 `reason='picking'`**：此时货不进 `sorted_stock` 也不进 `picked_stock`，只有 `removal_edit` 的作业员 `POST /removal/ {reason:'picking', quantity:4}` 让 `total_stock` 凭空少 4，等于免审批报损；`/removal/bulk` 同样 | `removal/services.py:90,119-120` | 对外接口白名单 reason；`picking` 只允许拣货流程内部调用 |
| B-57 | ✅ | **同一 DN 两条有效发货任务**：打包自动生成 T1，再 `POST /delivery/` 建 T2（无运单时允许）。(a) 运单建在 T2，完成 T1（不带运单号）→ 200，DN delivered，FedEx 运单仍 active 且再也无法在 WMS 取消（16065）；(b) T2 存运单号 BBB 并签发 CI，T1 存 AAA 后完成 → CI 印 BBB、实际出货 AAA，单证指纹只看 T2 所以不判过期；(c) `dn.delivered` webhook 用 `.first()` 无排序取任务，`tracking_number` 可能为 null 或不一致 | `dn/customs_services.py:710-717,945,1157`、`delivery/services.py:61-62,116-130,209-250,416-466`、`dn/services.py:890-893`、`dn/carrier_services.py:1152-1158` | 一张 DN 只允许一条未完成的有效发货任务（`create_task` 与 `create_delivery_task_from_dn` 都校验，409）；海外 DN 的完成 / 存运单号 / 改任务要求 `task.id == _delivery_task(dn).id`；`_guard_document_awb` 比较"写入后任务上的运单号"；webhook 取被完成的那条任务 |
| B-58 | ✅ | **已取消的自动运单号可继续出库**：(a) 有效运单期间 `PUT /delivery/<id>/tracking {"tracking_number":"7946 0000 0001"}`（面单分组写法）比对时忽略空格通过、原样入库；取消时按原字符串比较不相等 → 不清空，重签的 CI 仍印已取消的 AWB，完成发货 200；(b) 正常取消后，完成发货时带刚取消的号（PDA 表单还停在旧预填值）也 200 | `dn/carrier_services.py:538,553,1208,1213-1219`、`delivery/services.py:325-331` | 有自动运单时运单号统一存 `shipment.tracking_number` 的标准写法；取消时按规范化后的值比较；`assert_tracking_matches` 拒绝本 DN 已取消 / 补偿取消的号（16078） |
| B-59 | ✅ | **webhook 推送无总时长 / 响应体上限，一个租户可停摆全平台推送**：`requests.post(timeout=10)` 只限两次读之间的间隔；company_admin 把 `webhook_url` 指向自己的 https 服务，回 200 头后每 9 秒滴 1 字节，`_send_event` 永不返回，APScheduler `max_instances=1` 让后续每轮都被跳过，所有租户停发；期间该事件行锁与事务不释放（手动重试卡住、以后改 `webhook_events` 的迁移也卡住）。变体：几 GB 正文 / gzip 炸弹 → 调度 worker OOM，`attempts` 未提交，重启后再取同一条 → 崩溃循环（urllib3 2.5.0 另有 CVE-2025-66471/66418）。已复现：同参数请求 24 秒才返回 | `system/webhook/services.py:210-216,268-274`、`scheduler.py:26-33` | `stream=True` + 读上限（~64KB）+ 单调时钟总时限；HTTP 期间不持行锁（先标 `sending` 带租约提交，发送后回写）；连续失败熔断；urllib3 ≥ 2.6.3 |
| B-60 | ✅ | **全局 FIFO 饿死其他租户；合并时清零退避**：每轮按 `created_at` 取 100 条。(a) A 公司 CSV 导入 150 行带原产国 → 150 条事件，任何公司的 `dn.delivered` 下一轮发不出去；1 万行时按默认 30 分钟间隔约延迟 50 小时；(b) A 的接收端连不上（每次 10 秒），每轮约 17 分钟耗在 A，B 永远排不到；(c) 同一商品再改规格把已在退避中的失败事件 `attempts=0`、`next_retry_at=None`，坏接收端永远到不了 `MAX_ATTEMPTS`。另：`scheduler.py` 默认间隔 30 分钟，`.env.example` 写"默认 1" | `system/webhook/services.py:136-139,252-258`、`scheduler.py:22`、`.env.example:76-77` | 按 Key 轮转或每 Key 每轮限额，单据事件优先；合并到 `attempts>0` 的事件时保留退避（或作废旧的另建新）；按时间预算循环取；统一默认值 |
| B-61 | ✅ | **盘点批量保存改写已完成的明细**：不跳过 completed 行，且把每行 `operator_id` 改成当前用户。配合 W-28（Web 提交整单）与 A-39（APP 扫码记错行），会覆盖他人结果、改写已完成行的实盘数与差异，后续调整单随之错误 | `cyclecount/services.py:374-392` | 拒绝或跳过 completed 明细（16017）；只更新有变化的行 |
| B-62 | ✅ | **同一盘点单可重复生成调整单**：`create_adjustment_by_cyclecount` 无唯一性校验，`complete_adjustment` 按差值累加。连点两次 → 两张调整单，都审批完成后库存被调两倍。前端也无提交锁（W-29） | `adjustment/services.py:339-382,308-330` | 调整单记录来源盘点单并加唯一约束，重复生成返回 409 |

### 🟡 中

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| B-63 | ✅ | **FedEx 取消在事务内、持 DN 行锁调外部 API，且无中间状态**：PG 上最长约 90 秒阻塞同 DN 的完成发货、存运单号、改箱子；FedEx 已取消但本地提交失败 / worker 被杀时，记录仍 active、面单与运单号都在、无留痕，可照常带已取消面单发货。建单已刻意避免这种写法 | `dn/carrier_services.py:1145-1171,1194-1226` | 照建单分三段：加锁标"取消中"提交 → 不持锁调 FedEx → 加锁落最终状态；结果不明时拦发货（16079）并给人工确认入口 |
| B-64 | ✅ | **提交其实成功但调用方收到异常时，补偿会取消有效运单**：`_save` 的 COMMIT 生效但应答丢失 → 补偿取消 FedEx 运单；记录已是 active 不被改写 → WMS 显示有效运单，FedEx 上已作废 | `dn/carrier_services.py:868-873,984-1020,1048-1052` | 补偿前另开事务重读记录，已是 active 且运单号相同就不取消 |
| B-65 | ✅ | **补偿取消失败后无法重试取消，确认作废后可建第二张**：`unknown/compensation_failed` 且带运单号的记录，cancel 只处理 active（16075）；确认作废不调 FedEx、不看运单号，且只需 `packing_edit` | `dn/carrier_services.py:1112-1139,1153-1155`、`carrier_views.py:31` | 带运单号的 unknown 允许 cancel 重试；这类记录的确认作废先尝试取消或要求更强确认；收紧权限 |
| B-66 | ✅ | **运单有效期间，CI 依赖的主数据变了仍可重签 CI**：改商品原产国（`PUT /goods/<id>/origin-country` 只需仓库作业权限）、公司 / 仓库出口资料后 `POST /customs-documents/issue` → 201，新 CI 与已提交 FedEx（含 ETD）的申报不一致；pending 期间同样 | `dn/customs_services.py:1044-1052,758-760`、`carrier_services.py:579-592` | 存在 pending / active / unknown 记录时，单证数据除 AWB 外有变化 → 409 16076，要求先取消运单 |
| B-67 | ✅ | **海外件完成发货或存运单号时可换承运商**：签发 CI（印 Yamato）后在完成弹窗选 Sagawa → 200，CI 不变、DN 锁定无法重签；`PUT /delivery/<id>/tracking` 在有效自动运单期间也能改 `carrier_id`（`PUT /delivery/<id>` 会拦 16078） | `delivery/services.py:332-335,443-462`、`dn/customs_services.py:946,974` | `assert_ready_to_ship` 返回 CI 承运商，不一致 409；`save_tracking` 也调 `_assert_shipment_carrier` |
| B-68 | ✅ | **单价精度超过币种小数位**：JPY `unit_value=99.5`×3 → CI 印单价 100、金额 299；`0.4` → 印 0 且不报 `UNIT_VALUE_MISSING`；FedEx 收到 unitPrice 99.5 | `dn/customs_services.py:335,753-757,811,962`、`carrier_services.py:657` | 解析时按币种小数位校验（16063），或先量化单价再算金额；量化后 ≤0 视为缺失 |
| B-69 | ✅ | **`PUT /goods/<id>/origin-country` 绕过仓库范围并回传全部仓库库存**：只绑仓库 A、只有 `sorting_edit` 的员工，对只在仓库 B 有库存的商品 GET → 404，PUT → 200 且响应带出 B 的库位、数量、仓库名；不带 `X-WAREHOUSE-ID` 也 200。`PUT /goods/<id>` 同样回传未过滤的 `storage_records` | `goods/views.py:139-149,160-179` | 加 `@warehouse_required()` + 非管理员 `check_goods_access`；响应改精简模型或按 GET 过滤 |
| B-70 | ✅ | **商品规格数值无有限性 / 范围校验；CSV 重复 code 500**：CSV 与 JSON 都接受 `NaN`、`Infinity`、负数、超大值。PG 上 NaN 入 numeric 后商品接口输出非法 JSON；写入 json 列的事件 payload 被 PG 拒（CSV 导入 / API Key 建的 ASN 完成 500）；报关比较 `Decimal('NaN')` 抛 InvalidOperation；Infinity 溢出 numeric(8,3)。CSV 两行同一新 code → IntegrityError 500，无行号 | `goods/views.py:35-43`、`goods/services.py:306-309` | 共用校验器（有限、0 < weight ≤ 99999.999、尺寸为正）；CSV 先查文件内重复 code 报行号；IntegrityError / DataError 映射 409/400 |
| B-71 | ✅ | **部署失败后磁盘是新代码、库是旧 schema；无健康检查与并发控制**：`reset --keep` 先切代码，之后 `pip install` 或 `flask db upgrade` 失败（09-29 已实际发生），旧进程继续跑，但 pm2 任何一次自动重启都会用新代码连旧 schema（如 `goods.origin_country` 不存在 → 商品与所有 API Key 鉴权 500）；`pm2 restart` 立即返回 0，新代码启动即崩 Actions 仍显示成功；无 `concurrency`；迁移无 `lock_timeout`（碰上 B-59 会无限期阻塞全站）；`--keep` 静默保留服务器本地改动 | `.github/workflows/deploy.yml:22-28` | 新目录 / 新 commit 上装依赖跑迁移成功后再切换（release 目录 + 软链），失败 `reset --keep ORIG_HEAD`；重启后健康探测失败回滚；`concurrency: deploy-backend`；迁移前 `SET lock_timeout`；`git status --porcelain` 非空就中止 |
| B-72 | ✅ | **运行配置与 FedEx 90 秒时限对不上（需上服务器确认 pm2 实际命令）**：仓库 `uwsgi.ini` 是 1 进程 1 线程、无 harakiri / enable-threads / lazy-apps，`chdir=/var/www/wms_api`（实际部署目录是 `api_wms`），用 `daemonize` 与 pm2 冲突；按它跑，一次建单期间整个 API（含 PDA）串行阻塞，nginx 默认 60 秒先断开。若按 README 用 gunicorn（默认 `--timeout 30`），worker 30 秒被杀，建单落到 `unknown/interrupted`。另：时限只在每次发请求前检查，connect 超时按每个 IP 计、DNS 无超时，不是硬上限 | `uwsgi.ini:15,21`、`README-zh.md:571,579`、`config.py:76-81`、`dn/fedex_client.py:114-126` | 核实 pm2 启动命令；worker 超时 ≥ 时限 + 15 秒 + 余量（如 150 秒），nginx read timeout 同步；多进程；或把 `FEDEX_CREATE_BUDGET_SECONDS` 调到 worker 超时 − 20 秒以下；修正或删除过时的 `uwsgi.ini`　→ 2026-10-05 部署日志确认：pm2 运行 `gunicorn app:app -w 1 --threads 4 -b 127.0.0.1:5002 --timeout 120`。worker 超时 120 秒 大于建单时限 90 秒 + 补偿 15 秒；FedEx 调用只占一个线程，不阻塞全站。`uwsgi.ini` 未被使用 |
| B-73 | ✅ | **W-01 的后端 nh3 清洗从未落地**：09-29 报告标 ✅，但任何提交（`git log -S nh3 --all` 为空）和 `requirements.txt` 都没有 nh3。商品 `description` 原样入库（JSON 与 CSV），只靠 Web 端 DOMPurify；Station、Wholesale 等直接渲染该字段的系统仍有存储型 XSS 风险 | `goods/services.py:245,304`、`goods/views.py:329` | 补后端 nh3 白名单清洗（JSON + CSV）；存量数据跑一次清洗 |
| B-74 | ✅ | **API Key 不随公司过期 / 停用失效**（B-08 未覆盖 Key）：公司过期或停用后 JWT 已 401，Key 照常读写；Key 绑定的用户被停用后退化成公司级 Key，范围从单仓库**扩大**到全公司 | `system/third_party/utils.py:23-44` | 应用 Key 时检查公司 `is_active` / `expired_at`；绑定用户停用直接 401 |
| B-75 | ✅ | **有 `warehouse_edit` 或 `api_keys_edit` 的普通员工可扩大自己的仓库范围**：`PUT /warehouse/<别的仓库> {"manager_id": 自己}` 把它加进自己的可访问列表；建一个不绑用户的 Key 即覆盖全公司仓库 | `warehouse/services.py:93-133`、`third_party/services.py:91-130` | 仓库与 API Key 写操作加仓库范围校验，或只允许 company_admin |
| B-76 | ✅ | **payment 7 个端点只校验公司不校验仓库**：只负责仓库 B 的员工可查看 / 修改 / 处理 / 取消仓库 A 的收款，也能为 A 的 DN 新建收款 | `payment/views.py` | `@warehouse_required()` + 按 DN 仓库校验 + 列表仓库过滤 |
| B-77 | ✅ | **停用角色不生效**：收集权限时不看角色 `is_active`，停用 company_admin 角色后持有者权限照旧，停用角色仍能被分配 | `system/common/permissions.py:29,107` | 只统计启用角色；拒绝分配停用角色 |
| B-78 | ✅ | **已审批调整单可能永远完成不了**：正向调整的目标库位还没有该商品的库位记录（"在新库位发现 3 件"），或审批后库位被清空 → 完成 404 13003；单据已冻结，改不了删不掉，没有驳回或取消 | `adjustment/services.py:318-322` | 完成时库位记录不存在且调整量为正就新建；增加驳回 / 取消动作 |
| B-79 | ✅ | **盘点系统数在开始盘点时快照**：快照后正常拣走 20 件，盘点员如实点到 80，差异仍按 80−100=−20 算，调整后系统剩 60（实物 80） | `cyclecount/services.py:268-276,385-389` | 录入实盘时取当时系统数；或盘点期间冻结库位 |
| B-80 | ✅ | **盘点完成不检查是否已录入**：未录入的明细实盘默认 0，生成的调整单把库位清零 | `cyclecount/services.py:309-317` | 完成前要求每条明细已录入 |
| B-81 | ✅ | **`POST /sorting/`、`/picking/`、`/packing/`、`/delivery/` 不看单据状态与活动任务**：同一 ASN 两个分拣任务，没分拣的先完成 → ASN 按 0 实收完成，另一个任务的货再也完成不了；多余拣货任务一直占库位余量；pending DN 手工建了子任务后 `DELETE /dn/<id>` 500 | `sorting/services.py:208-246`、`picking/services.py:83-100`、`packing/services.py:83-100`、`delivery/services.py:209-250` | 限制单据状态与活动任务数，或删掉这四个手工建任务接口（任务由单据流转自动创建）；delivery 部分同 B-57　→ 手工新建发货任务接口 `POST /delivery/` 已去掉（用户决定，发货任务只由打包完成生成）；`POST /sorting/`、`/picking/`、`/packing/` 仍未限制 |
| B-82 | ✅ | **删除带明细的拣货 / 打包批次必 500**：关联没设级联，ORM 把明细 `batch_id` 置空撞 NOT NULL；已拣货的 DN 想取消必须先逐条删明细 | `picking/services.py:453-465`、`packing/services.py:362-374` | 加级联删除，或禁止删除非空批次返回 409 |
| B-83 | ✅ | **DN 拣货完成后没有取消或回退流程**：picked / packed / delivered 取消都 409，货只能靠库存调整处理。B-33 的取消只覆盖拣货开始之前 | `dn/services.py:971-1003` | 设计拣货后的取消（退回 `sorted_stock` 待上架）或明确的回退流程 |
| B-84 | ✅ | **删除被单据引用的主数据一律 500**：supplier / carrier / recipient / goods / location / warehouse 的 service 直接 `delete`，撞外键 RESTRICT，`error.py` 兜底成 "Internal server error" | 各主数据 `services.py`、`extensions/error.py:181-195` | 照公司删除（44003）先统计关联返回 409；前端提示改用停用 |
| B-85 | ✅ | **数值字段收到空串或 0 时 PG 500**：ASN weight / volume、库位 width / depth / height / capacity 原样写 Float 列，`""` → `invalid input syntax for type double precision`；库位尺寸 0 撞 `chk_dimension_positive`。SQLite 测不出 | `asn/services.py:117-119,511-513`、`location/services.py:61-70,88-91` | service 层空串转 null + 数值与范围校验（与 B-18 一并） |
| B-86 | ✅ | **盘点单、调整单列表 `keyword` 不在 parser**：`cyclecount/views.py` 读 `args.get('keyword')` 永远是 None（service 其实支持）；adjustment service 也没实现 keyword | `cyclecount/views.py`、`adjustment/views.py` 的 pagination parser | parser 补 `keyword`；adjustment service 实现过滤 |

### 🔵 低

| ID | 状态 | 问题 | 位置 |
|---|---|---|---|
| B-87 | ✅ | FedEx 写库阶段的业务异常原样返回：建单进行中别人把 DN 发货了，补偿失败后记录是 unknown（带运单号），接口却回 409 16065，不带 `unresolved`，Web 不重读状态，操作员不知道 FedEx 上可能有单 → 补偿后统一包装成 502 + `details.unresolved` | `dn/carrier_services.py:868-873`、`delivery/services.py:317-318`、`dn/customs_services.py:1057-1061` |
| B-88 | ✅ | 自动运单结果不明（unknown）时不带运单号仍可完成发货，之后可能存在的 FedEx 运单无法在 WMS 取消，无留痕（6cca7cc 只拦了带运单号的情况）→ 有 unresolved 时一律 16079 或要求显式确认并留痕 | `delivery/services.py:61-62`、`dn/carrier_services.py:539-547` |
| B-89 | ✅ | 用户取消时 FedEx 200 但缺 `cancelledShipment` 也视为成功（`strict=False`，补偿取消用的是 strict）→ 统一 strict，缺字段按结果不明处理 | `dn/carrier_services.py:976,1181` |
| B-90 | ✅ | `goods.spec_updated` 合并语义：同一 `X-Webhook-Id` 先后带不同 payload（按 id 去重的接收方丢新数据）；SKIP LOCKED 另建事件后旧的可能晚到；`changed_at` 只精确到秒，同秒乱序会应用旧值 → 只合并 `attempts==0` 的事件；发送前有更新的同 dedupe_key 事件就作废当前；`changed_at` 毫秒或递增版本号　→ 已改为只合并 `attempts==0` 的事件、失败过的另建新事件并作废旧的、领取时有更新的同对象事件就作废当前；`changed_at` 精度未改 | `system/webhook/services.py:120-143`、`views.py:103-113` |
| B-91 | ✅ | 两个推送进程并发时，失败事件被立即重发（加锁后重读只查 `status` 不查 `next_retry_at`；README 建议的 cron 与进程内调度器会同时跑） | `system/webhook/services.py:268-271` |
| B-92 | ✅ | Key 停用或取消订阅后，已排队事件仍推送（只查 `webhook_url`）；订阅不看 Key 是否有 `goods_read` | `system/webhook/services.py:69-81,178-182` |
| B-93 | ✅ | SSRF 残留（B-11 不完整）：`100.64.0.0/10` 判为公网，含阿里云元数据 `100.100.100.200`；校验与连接各解析一次 DNS（rebinding 窗口）。因要求 https 且不跟随重定向，当前危害有限 → `not ip.is_global` + 连接时固定已校验 IP | `system/webhook/utils.py:167-172` |
| B-94 | ✅ | 配置开关大小写敏感会静默失效：`WEBHOOK_URL_STRICT=true` 关掉 SSRF 校验、`RATELIMIT_ENABLED=1` 关掉登录限流、`SCHEDULER_ENABLED=true` 不启动调度器；漏设 `FLASK_ENV` 走开发配置（500 带 SQL）；生产不强制 `SETTINGS_ENCRYPTION_KEY` | `config.py:30-31,37,41,47`、`app.py:19-32` |
| B-95 | ✅ | 依赖：`urllib3==2.5.0` 有 CVE（与 B-59 叠加），应 ≥ 2.6.3；`fakeredis`、`pytest` 等测试依赖装进生产；本机 `.venv` 与 `requirements.txt` 不一致　→ urllib3 已升到 2.6.3（兼容 Python 3.9+）；测试依赖仍在生产 requirements | `requirements.txt` |
| B-96 | ✅ | CI 的 Shipper 栏：公司 `country_code` 为空而仓库有国家时不印国家，也不报 problem（检查用出口国、打印用公司国家） | `dn/customs_services.py:840,985` |
| B-97 | ✅ | 承运商名（常为日文，如"ヤマト運輸"）印在英文 CI 上，无非拉丁字符检查 → 加入 `EXPORTER_NON_LATIN_TEXT` 检查或改印 code / 英文名 | `dn/customs_services.py:668-688,974` |
| B-98 | ✅ | 20 万円 9 位统计番号提示只在币种为 JPY 时判断，USD 57,000 也不提示 → 换算后判断，或非 JPY 出"无法判断请人工确认" | `dn/customs_services.py:882-889` |
| B-99 | ✅ | 收件人 8 个字段各约 240 个以上 CJK 字符时 reportlab `LayoutError` → 签发 500（非拉丁收件人只是 warning，能走到渲染） | `dn/customs_documents.py:172-204`、`customs_services.py:86` |
| B-100 | ✅ | department 4 个端点在未绑定用户的 API Key 下 500（`g.current_user` 为空），不泄露数据 | `department/views.py:31,71,85,98` |
| B-101 | ✅ | `GET /goods/<id>` 给 `lazy='dynamic'` + `delete-orphan` 的 `storage_records` 赋过滤后列表，序列化时对其他仓库库位记录发 DELETE。GET 不写审计日志、请求结束回滚，不会真删，但 PG 上这些行在请求期间被行锁，阻塞同商品的拣货、移库 → 用局部变量过滤，不要给关系赋值 | `goods/views.py:132-135` |
| B-102 | ✅ | 拣货 / 分拣 / 打包 `create_batch` 不幂等：同 payload 重试只要累计不超计划量就重复累加；并发超量要到完成时才拦 | 各 `services.py` 的 `create_batch` |
| B-103 | ✅ | 多商品单据按请求顺序逐个加锁，两请求商品顺序相反时 PG 死锁 → 500（读码论证）→ 按 goods_id 排序后加锁 | `dn/services.py:107,800`、`adjustment/services.py:318` |
| B-104 | ✅ | sorting 统计接口带 `sorting_type` 参数直接 500（引用不存在的字段） | `sorting/services.py:585,660` |
| B-105 | ✅ | 调整单职责分离可绕开：只禁创建人审批，审批人可先改别人单的明细数量再自己审批 | `adjustment/services.py:233-256,301` |
| B-106 | ✅ | B-45 不完整：SMTP 测试接口仍回显异常原文（仅平台超管可调） | `system/settings/views.py:45` |
| B-107 | ✅ | `_ensure_inventory` 先查后插，同一新商品首次并发建 ASN 主键冲突 500 | `asn/services.py:124-130` |
| B-108 | ✅ | `list_goods_locations` 没有 ORDER BY，APP 分页批量查询在 PG 上可能重复或漏行 | `goods/services.py:456-510` |
| B-109 | ✅ | 业务码一码多义：14003 同时表示"缺仓库 id"和"移库源库位无此商品"；16033 同时表示"明细数量非法"和"运费非法"。前端按码映射文案，提示误导（见 A-44）。→ 运费已改用独立码 16081；14003 仍一码多义（APP 已对 14003 优先显示后端原文） | `transfer/views.py:131-132`、`transfer/services.py:121`、`delivery/services.py:38` |
| B-110 | ✅ | webhook `EVENT_TYPES` 缺 `asn.cancelled`，按该类型筛选日志被 choices 拒绝 | `system/webhook/schemas.py:18-25` |
| B-111 | ✅ | （修复 B-50 时发现）DN / ASN 取消只把下属任务 `is_active` 置 False、状态不变，停用的任务仍能 process、追加批次，只在 complete 时被单据状态挡下 → 需定规则：直接拒绝停用任务的一切操作 | 各任务 `services.py`、`dn/services.py`、`asn/services.py` 的 cancel |
| B-112 | ✅ | （修复 B-50 时发现）sorting `update_task` 可以改 `asn_id`，此时只锁了原 ASN | `sorting/services.py` |
| B-113 | ✅ | （修复 B-54 时发现）拣货 0 件也能完成，之后打包任务按新规则（16082）永远完成不了，DN 卡在 picked，而取消只支持 pending / in_progress → 拣货完成也拒绝 0 件，或允许取消这种 DN | `picking/services.py`、`dn/services.py` |
| B-114 | ✅ | （修复 B-58 时发现）已确认作废（dismissed）但带运单号的自动运单记录，其运单号仍可用于发货（只拦了 cancelled 与补偿取消） | `dn/carrier_services.py` |

---

## 二、Web

### 🟠 高

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| W-23 | ✅ | **填了快递费就完成不了发货**：运费框是 `type="text"` + v-maska，`v-model` 无 `.number`，提交字符串 `"1500"`；后端（09-29 加的校验）`not isinstance(cost, (int, float))` → 400 16033，英文提示且无三语文案。填了又清空则提交 `""`，同样 400。APP 同样（A-37） | `app/pages/delivery/detail/[id].vue:89,376-378`、`[BE] delivery/services.py:35-38` | 前端空串转 null、其余 `Number()`；后端同时接受数字字符串并给运费独立业务码（见 B-109） |
| W-24 | ✅ | **轮询 / 刷新 / 网关超时后才看到的建单结果不刷新单证区，可能打印作废的 CI/PL**：`emit('changed')` 只在 create / cancel 成功时发出；`load()`、轮询、建单失败后重读都不通知父组件。504 但后端已建单、或建单中刷新页面 → 后端已作废旧 CI/PL 并签发带 AWB 的新版，卡片仍显示旧版，点"打印 CI"打出作废且无 AWB 的 PDF（后端 `get_document` 不检查 status，作废版本照样能下载） | `app/components/customs/CarrierShipmentPanel.vue:97-120,159-186,325-327,338,377`、`DnCustomsCard.vue:262-265,297-306`、`[BE] dn/customs_services.py:1121` | `load()` 比较前后运单（id / tracking / status）或 unresolved 由有变无时 `emit('changed')`；读到有效运单时清掉 `failure` |
| W-25 | ✅ | **员工信息与当前仓库缓存从不刷新，换人登录沿用上一个人的公司和仓库**：`logUserOut` 不清 localStorage 的 `staffInfo`、`warehouse_id` cookie 和 `warehouseStore`；Header 只在 `staffInfo` 为空时拉 `/staff/current`。A 的 token 过期回登录页，B 在同一浏览器登录 → 页头是 A 的公司、请求带 A 的 `X-WAREHOUSE-ID`（全部 12001），只能手动点"退出"才恢复。停用当前仓库后所有页面 14002，下拉仍显示该仓库；新建仓库不出现在下拉 | `app/utils/auth.ts:65-72`、`app/stores/auth.ts:95-126`、`app/stores/staff.ts:9`、`app/components/common/Header.vue:148-166`、`app/pages/warehouse/index.vue:86-99`、`app/pages/company/index.vue:91-93` | `logUserOut` 清 staffInfo / warehouse_id / warehouseStore；登录成功无条件拉 `/staff/current` 并用新列表校验 cookie；仓库增删改与公司保存后刷新 |
| W-26 | ✅ | **ASN / DN 取消接口没有接入**：全仓没有调用 `PUT /asn/<id>/cancel/`、`PUT /dn/<id>/cancel/`，只有 pending 状态的"关闭"。误签收的 ASN（received）无法回退，`received_stock` 一直挂着；DN 进入 in_progress 后无法取消，`dn_stock` 一直被预占。16052 / 16053 / 16059 / 16060 无文案 | `app/pages/asn/index.vue:287-292`、`asn/detail/[id].vue:241-252`、`dn/index.vue:301-313`、`dn/detail/[id].vue:241-257` | 列表与详情页对 pending / received 的 ASN、pending / in_progress 的 DN 加"取消"按钮（带确认），补文案 |
| W-27 | ✅ | **分拣任务可在 Web 删除，删除后 ASN 永远停在 received**：ASN 只能经分拣完成推进到 completed，而 Web 没有新建分拣任务的入口，也没有取消入口（W-26） | `app/pages/sorting/index.vue:236-238`、`[BE] sorting/services.py:250-259` | Web 去掉删除按钮，或后端禁止删除 ASN 自动生成的任务；配合 W-26 |
| W-28 | ✅ | **盘点明细保存把整单所有行都提交**：`.filter(item => item.new_cyclecount_quantity !== 0)` 过滤的是 map 之后的对象（没有该字段），过滤永远不生效。A、B 同时打开同一张盘点单，B 的保存会把 A 刚录的结果覆盖成打开时的旧值（后端见 B-61） | `app/pages/cyclecount/detail/[id].vue:68-77` | 先 filter 后 map，只提交本次有录入的行 |
| W-29 | ✅ | **"生成调整单"可重复点击**：成功后按钮不消失、不跳转、无提交锁（后端见 B-62） | `app/pages/cyclecount/detail/[id].vue:207-234,~427` | 提交锁；成功后跳转到调整单或隐藏按钮 |
| W-30 | ✅ | **DN 编辑页把明细数量强制压成 1；新建页显示的可用量偏大**：编辑页上限取 `available_stock`（已扣掉本单预占），DN 已预占 10、onhand 10 时上限为 0，把 10 改成 9 → `clampValue` 压成 0 再改成 1，保存后数量变 1。新建页 `available_stock` 含残损与退货库存，按页面最大值提交被 16032 拒（且只提示"操作失败"） | `app/pages/dn/edit/[id].vue:240-256,292-301,~429`、`dn/add.vue:179`、`[BE] inventory/models.py:166`、`dn/services.py:99-120` | 编辑页上限 = `available_stock_for_sale + 本单原数量`；新建页用 `available_stock_for_sale` |

### 🟡 中

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| W-31 | ✅ | **"取消运单"和"已核对解除"不带目标标识**：body 是 `{}` / `{confirm:true}`，后端取"最新的 unresolved / 当前 active"。A 看着结果不明的 #1（交易 X）去 FedEx 核对，期间 B 解除 #1 并重建、#2 超时（交易 Y），A 回来点"已核对" → 解除的是没人核对过的 #2，再建单可能重复运单与运费；取消同理 | `app/components/customs/CarrierShipmentPanel.vue:360-366,401-404`、`[BE] dn/carrier_views.py:118-131`、`carrier_services.py:1114,1147` | 弹确认前重新 GET；请求带 `unresolved_id` / `tracking_number`，后端不一致返回 409（前后端一起改） |
| W-32 | ✅ | **结果不明时打包页和配送页的单证概要显示"尚未在 FedEx 建运单"**，配送页流程第 2 步还写着"FedEx 不可用时在承运商系统手工建"，容易引导手工重复建单 | `app/components/customs/CustomsDocStatus.vue:84-87,152-159` | `carrierStatus.unresolved` 存在时醒目显示"结果不明 / 建单中"并链接到 DN 单证卡片 |
| W-33 | ✅ | **商品编辑：非 Quill 格式的描述一打开就判定为"已修改"**：快照在 Quill 挂载前拍，vue-quill 设内容后异步触发 text-change，emit 出规范化（包 `<p>`）的 HTML。CSV / API 导入的纯文本描述，只改价格也会带上 description，覆盖期间 CSV 导入的新描述（04dee46 想避免的情况）；"没有修改"提示永远不出现 | `app/pages/goods/edit/[id].vue:126-129,210-211`、`app/utils/goodsForm.ts:83-88` | description 只在用户真正操作编辑器后参与比较，或在首次 text-change 后再记原值 |
| W-34 | ✅ | **箱子有未保存修改时仍可"在 FedEx 建运单"或"生成单证"**，用的是已保存的旧箱子；之后再保存箱子 16076，只能取消重建。`DnPackagesEditor` 暴露了 `dirty` 但无人使用 | `app/components/customs/DnCustomsCard.vue:576-584`、`DnPackagesEditor.vue:197`、`CarrierShipmentPanel.vue:297-305` | 父组件读 `dirty`，建单 / 生成单证前拦截或提示保存 |
| W-35 | ✅ | **16076、16078（no-tracking 变体）的文案让用户"取消运单"，但结果不明 / 进行中时没有取消入口**（只有"已核对"）。后端 16076 不带 details | i18n `biz-errors.code-16076`、`code-16078-no-tracking`、`app/utils/bizError.ts:19`、`[BE] dn/customs_services.py:611` | 按 `details.status` 给"先核对并解除"变体；后端 16076 补 details |
| W-36 | ✅ | **表单提交失败只显示"操作失败"，吞掉后端原因；业务码文案基本没有**：asn / dn / cyclecount / location / staff / supplier / carrier / recipient / department 的 add 与 edit 页 `onError` 固定 `t('action-results.failed')`；`biz-errors` 只有报关相关 23 个码，16029 / 16032 / 16033 / 16036 / 16037、16051–16062、10012 / 10013、44001–44003 及 unresolved 原因 `connection_error` / `server_error` / `interrupted`、blocker `INCOTERM_DUTIES_MISMATCH` 都没有。库存不足、数量小数、缺仓库、无权授予角色都只见"操作失败"，中日文界面弹英文 | `asn/add.vue:205`、`asn/edit/[id].vue:229`、`dn/add.vue:216`、`dn/edit/[id].vue:231`、`cyclecount/add.vue:120`、`location/*`、`staff/*`、`supplier/*`、`carrier/*`、`recipient/*`、`department/*`；`i18n/locales/*.json` | 统一 `bizErrorMessage(error)`，无文案时回落后端 message；补三语文案 |
| W-37 | ✅ | **非 company_admin 员工首次进入或选"全部仓库"时，仓库内页面全部 14003**：Header 不默认选仓库，`WarehouseSelector` 对所有人提供"全部仓库"；新建表单里选了仓库也不会作为 `X-WAREHOUSE-ID` 发送（后端只读 query / header）。`dn/add.vue:247`、`cyclecount/add.vue:131` 未选仓库时搜索商品直接 TypeError | `app/components/common/Header.vue:157-166`、`app/components/UI/WarehouseSelector.vue:9-13`、`asn/add.vue:162-176`、`dn/add.vue:162-176`、`cyclecount/add.vue:71-90`、`[BE] common/decorators.py:19` | 非管理员自动选第一个可访问仓库并隐藏"全部仓库"；表单提交用所选仓库作为 header |
| W-38 | ✅ | **盘点单、调整单列表搜索无效**（后端 parser 无 `keyword`，见 B-86） | `app/pages/cyclecount/index.vue:44-46`、`adjustment/index.vue:44-46` | 随 B-86 |
| W-39 | ✅ | **签收时间按 UTC 存储，显示早 9 小时**：`formatDateTimeWithoutTimezone` 对 Date 用 `toISOString()` 后去掉 Z，东京 10:00 存成 01:00 | `app/pages/delivery/detail/[id].vue:127-136`、`app/utils/date.ts:133-134` | `dayjs(d).format('YYYY-MM-DDTHH:mm:ss')` |
| W-40 | ✅ | **新建与保存无防重复提交**：按钮是 `NuxtLink`，无 loading / disabled。网络慢连点两次生成两张 ASN / DN，DN 重复预占 | `asn/add.vue:457`、`dn/add.vue:520`、`cyclecount/add.vue:291`、各主数据 add / edit | `submitting` 锁 + 请求期间禁用 |
| W-41 | ✅ | **数值框填了又清空，以空串提交 → PG 500**（后端见 B-85） | `asn/add.vue:345,352`、`asn/edit/[id].vue:377,384`、`location/add.vue:176-201`、`location/edit/[id].vue:192-215` | 空串转 null、其余转数字 |
| W-42 | ✅ | **没有任何按权限的展示控制**：菜单（含 apikeys、company、staff）与操作按钮全部渲染，无 `adjustment_approve` 的人也看到"审批"，点击 403 英文 | `app/data/menuData.js`、`app/components/common/Sidebar.vue`、`adjustment/detail/[id].vue:256-258` | 登录时带回权限列表，菜单与按钮按权限隐藏 |

### 🔵 低

| ID | 状态 | 问题 | 位置 |
|---|---|---|---|
| W-43 | ✅ | PDF 查看 / 打印的降级路径无效：iframe `print()` 抛错后在异步回调里 `window.open(..., 'noopener')`（返回值恒 null）；弹窗被拦截时点击无任何反馈 | `app/composables/customs/customsDocuments.ts:237-245,259-266,334` |
| W-44 | ✅ | "超时，运单可能已在 FedEx 生成"也出现在取消超时和 ETD 上传超时上（`failure.timeout` 不分 action） | `CarrierShipmentPanel.vue:280-291,715` |
| W-45 | ✅ | 轮询最多约 5 分钟，后端 10 分钟才判 stale，之后页面一直转圈"本页会自动刷新"；卸载发生在轮询请求进行中时，回调重新排程、后台继续请求 | `CarrierShipmentPanel.vue:159-186`、`[BE] carrier_services.py:68` |
| W-46 | ✅ | 取消失败（16075 已被他人取消）或建单冲突（16072）后不重读状态，画面停在旧状态 | `CarrierShipmentPanel.vue:271-274,360-368` |
| W-47 | ✅ | 申告价额为 0 时显示"申告价额 JPY 0 已随运单提交 / 已自动调整"（后端把 0 视为不提交） | `DeclaredValueNotice.vue:32-33`、`carrierShipment.ts:421-432` |
| W-48 | ✅ | 公司 / 仓库出口资料的"非拉丁字符"提示误报：前端 `hasNonAscii` 对换行、Müller、é 也报，后端 `has_non_latin` 允许这些 | `customsDocuments.ts:143`、`company/index.vue:45-51`、`warehouse/add.vue`、`warehouse/edit/[id].vue` |
| W-49 | ✅ | 箱子录入多余小数被静默四舍五入（12.3456 kg → 12.346；12.34 cm → 123 mm） | `DnPackagesEditor.vue:138-168` |
| W-50 | ✅ | 历史版本里的 ZPL / EPL 面单用 PDF 模式取文件，查看 / 下载报 `Unexpected content type` | `DnCustomsCard.vue:667-671` |
| W-51 | ✅ | 签发人、建单人显示裸用户 ID | `CarrierShipmentPanel.vue:240,557`、`DnCustomsCard.vue:165,609` |
| W-52 | ✅ | i18n：插值参数缺失（`dn/detail/[id].vue:451` 缺 `{operator}`；`goods/detail/[id].vue:101,148,204` 缺 `{entity}`）；缺 key（`common.loading`、`dn.fields.packaging-info`、`location.fields.weight`）；key 多一个引号（`common.validation.goods-exists"`，asn / dn 的 add 与 edit）；用错 key（密码过短提示用 `name-required`、DN 收货人为空提示用 `supplier-required`）；硬编码文案（delivery / sorting / cyclecount / picking 详情）　→ 多引号的 key 与盘点页英文提示已修，其余未改 | 各处 |
| W-53 | ✅ | 死链：`/cyclecount/${task_id}` 路由不存在（应为 `/cyclecount/detail/`） | `goods/detail/[id].vue:676`、`location/detail/[id].vue:734` |
| W-54 | ✅ | DN 详情头部与打印页复制自 ASN：显示英文硬编码 `expected_arrival_date:`（DN 无此字段）、判断不存在的 received 状态；打印页承运商栏显示 `supplier.contact / phone` 与不存在的 `tracking_number` | `dn/detail/[id].vue:131-136`、`dn/print/[id].vue:104-107` |
| W-55 | ✅ | 时间线"已分拣 / 已拣货 / 已打包"时间为空或错：`reduce` 无初值且返回类型不一致；`sorting_time`、`picking_time`、`packing_time` 只在明细模型里，列表项没有 | `asn/detail/[id].vue:91-97`、`dn/detail/[id].vue:110-122` |
| W-56 | ✅ | 商品上传：公司缺失时直接 return，`uploading` 永远 true，转圈不停 | `goods/upload.vue:66-70` |
| W-57 | ✅ | webhook 日志事件类型筛选缺 `goods.spec_updated`、`asn.cancelled`（后端见 B-110） | `webhook-logs/index.vue:76-82` |
| W-58 | ✅ | 部署：`rm: true` 先删 `/var/www/admin_wms` 再拷贝，pm2 重启前有空窗，中途失败站点直接挂；无 `concurrency`；第三方 action 按 tag 引用未固定 SHA | `.github/workflows/deploy.yml` |

---

## 三、APP

### 🟠 高

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| A-37 | ✅ | **填了快递费就完成不了发货**：`el-input type="number"` 的 v-model 仍是字符串，`completePayload` 原样提交 → 400 16033，且 APP 把 16033 映射成"明细数量必须为正数"（见 A-44）。同 W-23 | `src/views/DeliveryManagement/DeliveryDetail.vue:147-155,312-313` | `v-model.number` 或提交前转换，空串删除字段 |
| A-38 | ✅ | **分拣 / 打包"完成"失败后重试，同一批次再提交一次**：先提交批次再完成任务；完成超时 / 失败后不重拉、不清已录数量，重试再交一次。分拣计划 10、扫 4 后完成失败重试 → 累计 8 未超计划，ASN 多记 4；打包同理虚增 `packed_quantity`，CI 数量随之错。两页也无防连点（A-03 只修了拣货页） | `src/views/ReceivingManagement/SortingDetail.vue:70-85`、`src/views/DeliveryManagement/PackDetail.vue:111-140`；`[BE] sorting/services.py:63-104`、`packing/services.py:246` | 照 `PickingDetail.vue:185-210`：`submitting` 锁、批次成功后立即清空已录数量、`finally` 里 `init()` |
| A-39 | ✅ | **盘点扫码只按商品编码命中第一行**：明细按"商品 × 库位"生成，同一 JAN 多行时在 B 库位扫码永远加到 A 库位行；A 行已完成时输入框隐藏，员工看不到计数在涨；保存时提交 A 行"新增 + 原值"，改写已完成行（后端见 B-61） | `src/views/InventoryManagement/StocktakingDetail.vue:52-57,143-155` | 扫码只匹配未完成行；同码多行时让员工选库位或先选中当前库位行；只提交未完成行 |
| A-40 | ✅ | **上架 / 下架 / 移库：库位没查到或弹窗取消后，沿用上一次的 `location_id`**：上一单选了 A-10，这一单输入 B-20 但输错 / 命中 > 5 条 / 弹窗点取消，输入框显示新码，提交落在 A-10（点取消时完全无提示） | `src/views/InventoryManagement/Add.vue:123-146`、`Remove.vue:120-143`、`Move.vue:133-161` | 库位输入一改动就清空 id；只在 `confirmLocation` 命中时写入；提交前校验显示码与 id 对应的码一致 |
| A-41 | ✅ | **列表回来静默刷新用 `list.length` 当 `per_page`，最老的任务被挤出列表**：待处理 7 条（1 页），返回时新增 2 条，刷新只取最新 7 条，最老那条不见；继续滚动取第 2 页（每页 10）也取不到，哨兵一直可见不再触发。keep-alive 引入 | `src/hooks/useList.ts:58-74` | 刷新用 `per_page = params.page * params.per_page`（≤ 200）重拉已加载范围；补单测 |
| A-42 | ✅ | **上架页多商品选择弹窗点"确认"抛 TypeError，再点一次数量变 2**：`push` 后同步 `getElementById(...).scrollIntoView()`，DOM 未渲染拿到 null，`dialogVisibleGoods = false` 没执行；员工再点 → 走"已在列表"分支 +1 | `src/views/InventoryManagement/Add.vue:68` | 先关弹窗，`await nextTick()` 后 `?.scrollIntoView()` |

### 🟡 中

| ID | 状态 | 问题 | 位置 | 修法 |
|---|---|---|---|---|
| A-43 | ✅ | **`useList` 请求无序号保护**：从详情返回时刷新请求在途，员工马上扫单号搜索，搜索先回、刷新后回 → 输入框是扫到的单号、列表是未过滤的旧数据，可能点错单；`loading` 被先完成的请求置 false，又可能触发翻页 | `src/hooks/useList.ts:36-51,58-74,76-90` | 每次请求带递增序号，只接受最新；search / changeStatus 作废在途请求 |
| A-44 | ✅ | **error.json 按码一刀切，后端一码多义时提示误导**：14003（移库源库位无此商品）显示"需要提供有效的仓库ID"，正好与 A-40 的错库位同时出现；16033（运费非法）显示"明细数量必须为正数"；16062（分拣超计划量）缺失、显示英文 | `src/utils/request.ts:80-86`、`src/utils/error.json` | 后端改专用码（B-109）或对已知多义码优先显示后端 message；补 16062 |
| A-45 | ✅ | **发布流水线：签名密钥与 npm / vite 第三方代码在同一个 job，wrapper 校验在 `npm ci` 之前**：任何被投毒的 npm 依赖（安装脚本或 vite 插件）可在校验后替换 `gradle-wrapper.jar` 或写 `~/.gradle/init.d/*.gradle`，下一步 gradle 运行时环境里有 keystore 路径和两个密码 → 正式签名私钥外传。签名步骤还从 jitpack.io 拉 JsBridge（无校验） | `.github/workflows/release-apk.yml:31,51-58,65-76` | 拆两个 job：① `npm ci --ignore-scripts` 构建、上传 dist，不给签名 secret；② 新 runner 上 checkout、wrapper 校验、放入 dist、签名发布，不执行 npm 代码。加 `gradle/verification-metadata.xml` 或 `distributionSha256Sum` |
| A-46 | ✅ | **发布无闸门，任何有写权限的人都能用正式证书直接发布到所有 PDA**：`workflow_dispatch` 可选任意分支、`v*` 标签可打在任意提交；版本号一致即签名并 SSH 覆盖生产下载地址；无 `environment` 审批、无 main 限制、无版本递增检查；未声明 `permissions:`，checkout 默认把 GITHUB_TOKEN 写进 `.git/config`；`${{ steps.ver.outputs.version }}` 直接拼进 run 脚本 | `.github/workflows/release-apk.yml:14-17,28,93-104` | `environment: production` + 必需审批人；只允许 main / 受保护标签；`permissions: contents: read` + `persist-credentials: false`；版本号走 env；校验签名证书 SHA-256 指纹与 versionCode 递增 |

### 🔵 低

| ID | 状态 | 问题 | 位置 |
|---|---|---|---|
| A-47 | ✅ | 16078 的 `details.carrier_id` 是请求传入值，APP 当作自动运单的承运商"改回"，实际什么也没改；`DeliveryDetail.spec.ts:342` 把这个错误理解写进了测试 → 用 `details.carrier`（code）匹配或重拉详情 | `DeliveryDetail.vue:171-177`、`src/utils/customs.ts:342`；`[BE] delivery/services.py:76-92` |
| A-48 | ✅ | 打包页的面单兜底锁定是死代码：`/dn/<id>/customs` 的 `current_documents` 只有 CI、PL，没有 shipping_label；`ExportPacking.spec.ts:200` 模拟的数据后端不会返回 | `src/components/ExportPacking/index.vue:47-49`；`[BE] customs_services.py:31,487-495` |
| A-49 | ✅ | APP 不看 `documents_outdated`：打包员快选改原产国后单证变过期，打包页仍显示"已生成 v1"，直到完成发货才被 16069 拦 → 显示"单证已过期，请在 PC 重新生成" | `ExportPacking/index.vue:40`、`DeliveryDetail.vue:30-52`；`[BE] customs_services.py:906-910` |
| A-50 | ✅ | 退出登录不调 `/system/user/logout`，refresh token 服务端仍有效 7 天；`allowBackup=false` 在 targetSdk ≥ 31 挡不住设备间迁移（D2D），需补 `dataExtractionRules` | `src/views/Warehouse/Select.vue:47-50`、`src/stores/index.ts:74-80`、`android/app/src/main/AndroidManifest.xml:16` |
| A-51 | ✅ | 发货详情：签收日期可选未来（`disabledDate` 恒 false）；承运商列表不传 `per_page`，第 20 条以后选不到；运输方式只有 express、pickup（后端 8 种） | `DeliveryDetail.vue:20-24,229-231` |
| A-52 | ✅ | 打包详情字段标签错位：「运输方式」显示承运商名、「承运商」显示仓库名；已完成状态显示「已拣货」 | `PackDetail.vue:198,205-206` |
| A-53 | ✅ | **JsBridge 1.0.4 的消息转义需真机确认（若成立是高危）**：本机没有该 aar 源码。若 `dispatchMessage` 用 `loadUrl("javascript:...('%s')")` 且只转义引号不处理 `%27`，扫一个内容带 `%27);…//` 的二维码即可在 APP 页面执行脚本、读 localStorage 里的 Token → 先在测试机扫这样的码确认；修法是改 `evaluateJavascript` + JSON 编码，或原生侧只放行条码字符 | `android/` JsBridge 依赖 |

---

## 四、对 09-29 报告的更正

| 原编号 | 原状态 | 实际 | 本次编号 |
|---|---|---|---|
| W-01 | ✅（后端 nh3 白名单清洗） | 后端清洗从未落地，只有前端 DOMPurify | B-73 |
| B-04 | ✅ | `POST /dn/` 的 `api_key_id` 漏了 | B-48 |
| B-05 | ✅ | 绑定公司但无启用仓库的 Key 不过滤 | B-47 |
| B-08 | ✅ | 吊销 / 过期只覆盖 JWT，没覆盖 API Key | B-74 |
| B-11 | ✅ | `100.64.0.0/10` 与 DNS rebinding 残留 | B-93 |
| B-45 | ✅ | SMTP 测试接口仍回显异常原文 | B-106 |
| A-03 | ✅ | 只修了拣货页，分拣、打包页同样问题 | A-38 |

---

## 五、已核实无问题（保留）

- **鉴权覆盖**：256 个端点中，除 6 个登录类接口与 `limiter/test` 外全部有 `permission_required`，权限名全部在 seed 中；所有 `/<id>` 与子资源都校验归属（payment 例外，见 B-76）；明细、批次、单证都校验属于路径里的父单据；未绑定用户的 Key 写操作统一 400/11008
- **PG 行锁**：全仓 7 处 `with_for_update` 都安全（库存与库位查询带 `lazyload('*')`；DN 与报关 `_lock` 只查主键；WebhookEvent 无 joined 关系）；库位与库存的读—改—写都在锁下
- **库存不变量**：正常入库、正常出库、短拣、短分拣、pending / received 的 ASN 取消、pending / in_progress 的 DN 取消，走完后各字段 ≥ 0、`total_stock` = 各分量之和、库位汇总一致、预占归零
- **事务**：所有写服务都有 `@transactional`；bulk 接口全成功或全回滚；审计日志只记 POST/PUT/DELETE
- **迁移链**：单 head `a5e6f7a8b9c0`；SQLite 上 e0f1 → head → e0f1 → head 实测通过；PG 离线 SQL 审读：新列都可空或带默认值，约束与索引显式命名且长度合规；迁移后 schema 与模型只差两处无害的 server_default
- **FedEx 建单**：pending 先提交、调 FedEx 时不开事务不持锁；部分唯一索引兜底并发与双击；错误分类（确定失败 / 结果不明）正确；OAuth token 进程内缓存带锁、提前 60 秒刷新、不落日志；公司白名单在持锁时检查；面单下载要读权限 + 仓库归属 + 属于该 DN，`no-store`；地址超长拦截不截断；冒烟脚本拒绝非 sandbox 地址
- **报关单证**：PDF 存数据库 bytea、只经鉴权接口下载；XML 转义正确，无 Paragraph 标记注入；控制字符、emoji、多种文字不崩；500 行约 1 秒、峰值约 18MB；单证指纹覆盖全部印刷内容；唯一发货入口是 `complete_task → delivery_dn`；金额计算用 Decimal；同商品在 DN 明细不能重复；国家表 249 个代码前后端一致
- **商品与 webhook**：`update_goods` 对缺省字段不覆盖，CSV append / override 不清原产国与规格；spec_updated 按列精度比较、不变不发；广播按公司、Key 启用、已订阅过滤，无跨公司 payload；签名与 Id / Timestamp 仍有效；订阅设置与 CSV 导入没有引入新的服务端 URL 请求
- **Web**：删除的接口不再被调用；单据推进都走动作端点，PUT 不再带 status 与过程量；批次只提交单据内商品；所有 `v-html` 都经 `sanitizeHtml` 或是未引用的模板组件；列表过滤参数（盘点 / 调整的 keyword 除外）都在 parser；server 代理只放行 `/system/`、`/warehouse/`、`/tasks/` 并屏蔽 doc；报关 / FedEx 接口契约（URL、方法、字段、枚举、业务码 16063–16080）一致；i18n 三语各 1273 个 key 完全一致
- **APP**：新增接口契约一致；箱子单位换算与范围与后端一致；完成发货的运单号处理与后端口径一致；keep-alive 缓存在切仓库、登出、登录失效时销毁，没有串仓库或串账号；Android 壳 `allowFileAccess*` 全关、禁混合内容、`usesCleartextTraffic=false`、CaptureActivity 未导出、release 不可调试；签名材料只从环境变量读，构件只含 APK
- **测试 / 构建**：见文首与文末自动检查结果

---

## 六、未覆盖 / 需上服务器确认

- **服务器**：pm2 实际启动命令、uwsgi / gunicorn 与 nginx 超时（B-72）、`.env` 的 `FLASK_ENV`、`WEBHOOK_PUSH_INTERVAL_MINUTES`、是否另有 webhook cron（B-91）
- **nginx 是否覆盖 `X-Forwarded-For`**：Nuxt 的 h3 `proxyRequest` 原样转发客户端自带的 XFF 且不追加；若 nginx 不覆盖，后端 ProxyFix 会信任伪造 IP，登录限流可被绕过
- **PG 真库**：B-50 用双会话交错在 SQLite 上模拟复现；B-103 死锁与 B-101 行锁影响只做了读码论证
- **FedEx 侧取值**：币种代码表完整性、非美加国家是否必须州代码、收件人非拉丁字符是否接受、"已取消"错误码实际取值
- **真机**：A-53 JsBridge 转义；09-29 遗留的 A-05 / A-29 真机扫码确认
- **GitHub 设置**：仓库默认 Actions token 权限、发布服务器上 `publish` 的强制命令与 OSS 覆盖策略
- **角色配置**：`/staff/current` 需要 `staff_read`，若某角色没有该权限，该员工拿不到仓库列表（W-37 相关）
- **未审**：Station、Website；OSS 上传实现；库存快照定时任务；IP 黑白名单运行逻辑；性能与 N+1

---

## 七、复现材料

临时测试在本次会话的 scratchpad（会话结束后可能被清理，修复时建议把对应用例移入 `tests/`）：
`C:\Users\panyu\AppData\Local\Temp\claude\C--Workshop-GoodsMart-WMS\116db052-410f-4dd7-baae-d901ee52f08e\scratchpad\`

| 目录 | 内容 |
|---|---|
| `a1\` | 报关单证：`test_a1_ship.py`、`test_a1_misc.py`、`test_a1_fedex_multi.py`、`test_a1_pdf*.py`、`test_a1_apikey.py`、`test_a1_perf.py` |
| `a2\` | FedEx：`test_audit_fedex.py`、`test_audit_fedex2.py`、`test_audit_fedex3.py`（FakeFedex mock，未联网） |
| `a3\` | 商品 / webhook / 迁移：`test_a3_findings.py`、`drip_server_test.py`、`mig\` |
| `a4\` | 全局横扫：`test_e2e_flows.py`、`test_race_interleave.py`、`test_goods_get_orphan.py`、`forkA\`、`forkB\`、`forkC\` |
| `bevenv\` | 按 `requirements.txt` 新建的完整 venv（运行：在 Backend 目录下 `<bevenv>\Scripts\python.exe -m pytest -p no:cacheprovider -c pytest.ini <路径> -q`） |

---

## 八、自动检查结果

| 项目 | 结果 |
|---|---|
| Backend pytest（scratchpad venv，按 `requirements.txt`） | ✅ 666 passed（28 分钟）。现有用例全绿，本报告的问题都是测试没覆盖到的场景 |
| Web `npm ci` + `build_test` | ✅ 通过 |
| Web `nuxi typecheck` | 72 个错误，全在旧模板组件与 CookieRef 类型声明，新代码 0 个 |
| APP vitest | ✅ 86/86 |
| APP vue-tsc / eslint / build | ✅ 通过 |

---

## 九、修复日志

| 日期 | 批次 | 内容 |
|---|---|---|
| 2026-10-04 | 0 | 审计完成，建立本跟踪文档。Backend 64 项（🔴4 / 🟠12 / 🟡24 / 🔵24）、Web 36 项（🟠8 / 🟡12 / 🔵16）、APP 17 项（🟠6 / 🟡4 / 🔵7，其中 A-53 ❓）。B-72、A-53 需上服务器或真机确认 |
| 2026-10-04 | 1 | **🔴 + 运费 + 鉴权 🟠 + APP 作业 🟠**：B-47~B-53、W-23、A-37~A-44 ✅，B-109 🔄。<br>**Backend**：`add_warehouse_filter` 遇到「受仓库范围限制但列表为空」直接 403，API Key 所属公司无启用仓库时 403（12001）；`POST /dn/` 照 ASN 强制覆盖 `api_key_id`，新增 `require_source_api_key`（来源 Key 必须属于单据公司）；ASN 明细同一商品只能一行（16025），存量重复行的分拣量只记第一行；新增 `warehouse/common/locks.py:lock_row`（只锁主键 + refresh），所有单据 / 任务状态转换、批次增删、明细增改先锁父单据再锁任务行（含 payment）；运费接受数字字符串、空串完成发货时不改已存值、非法改用新码 16081；员工写接口校验目标权限 ⊆ 调用者（12007）且仓库范围 ⊆ 调用者（12001）；ASN / DN 统计缓存键加入仓库范围（`scoped_cache_key`）；调整单 / 盘点明细的商品必须属于单据公司（`require_company_goods`）。新增测试 `test_tenant_scope_regressions.py`、`test_asn_duplicate_goods.py`、`test_delivery_shipping_cost.py`、`test_concurrent_transitions.py`（共 54 个）；改 `test_asn.py::test_create_asn_detail`（原用例给 ASN 加了已存在的商品）。全量 **720 passed**。<br>**Web**：发货页运费空串转 null、其余转数字；三语补 `biz-errors.code-16081`。`build_test` 通过。<br>**APP**：快递费转数字（A-37）；分拣 / 打包加提交锁、批次成功即清空、`finally` 重拉（A-38）；盘点扫码只匹配未完成行、同码多行要求先选库位行、只提交未完成且有录入的行（A-39）；上架 / 下架 / 移库库位输入一改动即清空 id、提交前校验显示码与已选码一致（A-40）；`useList` 刷新按「已加载页数 × 每页」并带请求序号（A-41、A-43）；上架多商品弹窗先关再 `nextTick` 滚动（A-42）；error.json 补 16062、16081，14003 优先显示后端原文（A-44）；CLAUDE.md 同步。vitest 120/120、vue-tsc、eslint、build 通过。<br>**上线前**：① 生产库先查存量重复行 `SELECT asn_id, goods_id, count(*) FROM asn_details GROUP BY asn_id, goods_id HAVING count(*) > 1;`（有结果时，未完成的 ASN 需人工合并；已完成的不影响）；② B-50 在 SQLite 上用双会话交错验证，建议在 PG 上用两个会话手工跑一次拣货完成并发；③ APP 需真机验证盘点多库位扫码、库位输入框清空 id、分拣 / 打包断网重试。已提交到各仓库 `fix/audit-1004` 分支（Backend `2f8327e` / Web `7785af4` / APP `6fd679f`），**未推送、未合并到 main**。 |
| 2026-10-04 | 2 | **剩余 🟠**：B-54~B-62、W-24~W-30 ✅，顺带 B-67、B-91、B-92 ✅，B-81、B-90、B-95、W-52 🔄。<br>**Backend 库存**：少打包差额从 picked_stock 退回 sorted_stock（用户选定），打包 0 件拒绝（16082）；库位有货时禁止停用 / 改类型 / 删除（16084），上架 / 移库目标库位须启用（16085），`lock_row` 增加 `shared` 参数；下架 reason 白名单（16083），拣货下架走内部参数 `from_picking`；盘点批量保存含已完成明细整单 409 16017，只给改动的行写 operator；调整单新增 `cyclecount_id`，同一盘点单重复生成 409 16086（details.adjustment_id）；已收货 ASN 的分拣任务禁止删除（16087）。<br>**Backend 发货 / 运单**：一张 DN 只允许一条未完成的发货任务（16090），打包完成自动生成时复用已有的手工任务；海外 DN 只能操作当前发货任务（16091）；`_guard_document_awb` 比较写入后的运单号；`dn.delivered` 用被完成任务的运单号；运单号统一存自动运单的标准写法，取消按规范化值清空，已取消的运单号再用 → 16078（details.status=cancelled）；有效运单期间 `save_tracking` 不能改承运商，完成发货换承运商与 CI 不一致 → 16092。<br>**Backend webhook**：发送放子线程、总时限 15 秒、正文最多读 64KB；三段式（领取标 sending 写租约 → 不持锁发送 → 回写），`skip_locked`；每 Key 每批 ≤20 条、单据事件优先、按时间预算取批；连续 3 次连接失败熔断；只合并 `attempts==0` 的事件，失败过的另建并把旧的标 superseded；停用 Key / 取消订阅的事件作废；推送间隔默认值 30 → 1 分钟（与 `.env.example`、README 一致）；urllib3 2.6.3。<br>**迁移**：`152c6ebfb7ab`（adjustments.cyclecount_id）→ `3a9d6c1e8b42`（webhook_events.lease_expires_at），单 head；SQLite 上 a5e6 ↔ head 来回升降级通过。<br>**Web**：W-24~W-30；登录 / 退出 / 仓库与公司变更后刷新员工信息并校验当前仓库（`useFetch` 缓存导致的旧数据一并修掉）；ASN / DN 取消按钮；新业务码三语文案（16017、16052/16053/16059/16060、16078-cancelled、16082~16087、16090~16092）；webhook 日志页支持 sending / superseded；16086 跳到已有调整单；发货页 16091 / 16092 弹窗。`build_test` 通过，typecheck 仍是原有 72 个。<br>**APP**：error.json 补 16082~16087、16090~16092；16078 已取消运单号的弹窗并清掉表单里的号码；16091 / 16092 弹窗。vitest 122/122、vue-tsc、eslint、build 通过。<br>**测试**：新增 `test_inventory_guards.py`、`test_delivery_task_guards.py`、`test_webhook_push_robustness.py`（共 47 个）；因行为变化改了 10 个旧用例。全量 **767 passed**。<br>**上线前**：① 查一张 DN 多条未完成发货任务 `SELECT dn_id, count(*) FROM delivery_tasks WHERE is_active AND status IN ('pending','in_progress') GROUP BY dn_id HAVING count(*) > 1;`；② 查停用但仍有货的库位 `SELECT l.id, sum(gl.quantity) FROM locations l JOIN goods_locations gl ON gl.location_id = l.id WHERE NOT l.is_active GROUP BY l.id HAVING sum(gl.quantity) > 0;`；③ 以前少打包留在 picked_stock 的差额需人工修正；④ 生产 `.env` 若未设 `WEBHOOK_PUSH_INTERVAL_MINUTES`，推送间隔将从 30 分钟变为 1 分钟；⑤ 迁移在 PG 上只做了离线 SQL 审读。已提交到各仓库 `fix/audit-1004` 分支（Backend `2f8327e` / Web `7785af4` / APP `6fd679f`），**未推送、未合并到 main**。 |
| 2026-10-04 | 3 | **用户决定的 5 条规则**：B-111、B-113、B-114 ✅，B-81 的发货部分完成。<br>**Backend**：任务所属 DN / ASN 取消后（任务 `is_active=False`），拣货 / 分拣 / 打包 / 发货任务的一切操作 → 409 16088（`require_active_task`，在各任务 `_lock` 与完成发货处）；拣货一件都没拣不能完成 → 409 16089；修复前留下的「picked 但一件没拣」DN 允许取消（拣货 / 打包任务一并停用，预占已在拣货完成时释放）；已确认作废（dismissed）的自动运单号与已取消的一样不能再用（16078，details.status 仍为 cancelled，新增 record_status）；已收货 ASN 还有其他启用中的分拣任务时允许删除，删最后一个仍是 16087；去掉 `POST /delivery/` 与 `DeliveryTaskService.create_task`（16090 不再出现），README 同步。新增 `test_task_lifecycle_rules.py`（6 个），改写 `test_delivery.py`、`test_delivery_task_guards.py`、`test_carrier_shipment.py`、`test_isolation_outbound.py`、`test_dn.py` 中依赖手工建发货任务或旧取消规则的用例。<br>**Web**：DN 详情页「picked 且一件没拣」也显示取消按钮；三语补 16088、16089。**APP**：error.json 补 16088、16089。<br>**注意**：外部系统若调用过 `POST /warehouse/delivery/`，上线后会收到 405（Web / APP 均未调用；Wholesale 侧需确认）。已提交到 `fix/audit-1004`（Backend `fdafed9` / Web `e35ca2e` / APP `d9eb85e`），未推送。 |
| 2026-10-05 | 4 | **🟡 全部（B-72 除外）+ 顺带的 🔵**：B-63~B-71、B-73~B-86 ✅（B-72 仍 ❓），顺带 B-87、B-88、B-89、B-101、B-110、B-112 ✅；W-31~W-42、W-58 ✅；A-45、A-46 ✅。<br>**用户决定**：去掉 `POST /sorting/`、`/picking/`、`/packing/`（405）；已拣货 / 已打包未发货的 DN 可取消，货退回 sorted_stock；流水线一起改。<br>**Backend FedEx / 单证**：取消运单改三段式，新状态 `cancelling`（迁移 `6b8f2d4c1e7a`，更新 CHECK 约束与唯一索引）；写库报错先重读再决定是否补偿；带运单号的结果不明记录可重试取消，作废前先问 FedEx（未确认 16094）；写库阶段异常统一 502 16095；取消缺 `cancelledShipment` 按结果不明；运单未结束时数据变化的单证不能重签（16076 `DOCUMENT_DATA_CHANGED`）；单价超过币种小数位 → 400 16063，存量超精度先量化再算；cancel / dismiss 可带目标标识（不符 16093）；16076 统一带 details；建单结果不明或取消中时完成发货一律 16079。<br>**Backend 权限 / 主数据**：`origin-country` 与 `PUT /goods/<id>` 加仓库范围，响应不再带全部仓库库存，GET 不再给 ORM 关系赋值；商品数值统一校验（16100），CSV 重复编码带行号（16101），IntegrityError / DataError → 409 44005 / 400 16102；商品描述 nh3 清洗（`nh3==0.3.7`，另有存量清洗脚本 `scripts/sanitize_goods_description.py`）；API Key 随公司停用 / 过期、绑定用户停用失效（401）；非公司管理员不能新建 / 删除仓库、改负责人（16104），只能管理绑定自己的 Key（16105）；payment 加仓库范围；停用角色不再授予权限、不能被分配（16103）；被引用的主数据删除 → 409 44004。`/staff/current` 只要求登录，返回 `permissions` 与 `is_company_admin`。<br>**Backend 库存 / 流程**：调整单可取消（`PUT /adjustment/<id>/cancel/`，`adjustment_approve`，用 `is_active=False` 表示），正向调整缺库位记录时新建、负向缺记录 409 16113；盘点录入时取当时系统数，未录入不能完成（16114，提交 0 也算录入）；删除带明细的批次级联删除；DN 取消扩展到 picked / packed（有未结束运单 16110，新增 `dn.cancelled` 事件）；库位有历史记录不能删（44009）；数值字段空串转 null 并校验（16115）；盘点 / 调整列表 keyword 生效；分拣任务不能改 ASN（16116）。<br>**流水线**：Backend 部署加并发锁、脏工作区中止、失败回到部署前提交、迁移 lock_timeout、重启后探测新增的 `GET /health`、失败回滚代码（不回滚库）；Web 部署改为上传新目录后原子切换并探测、失败切回；APP 发布拆成 build（`npm ci --ignore-scripts`，无签名 secret）与 sign-and-release（`environment: production`，校验证书指纹、包名、版本），只允许 main / `v*` 标签，action 固定 SHA。<br>**Web**：W-31~W-42 与上述后端改动的界面跟进（取消运单 / 作废前重读并带目标、取消结果不明与重试、单证概要醒目提示、商品描述误判、箱子未保存拦截、统一业务码文案、非管理员默认仓库、签收时间本地化、防重复提交、数值空串、菜单与按钮按权限显示、调整单取消与已取消筛选、盘点按「录入过」提交、DN picked / packed 取消、webhook 事件筛选）。三语各 1380 个 key。<br>**APP**：16079 文案覆盖「取消中」；error.json 补 16114、16115。<br>**测试**：新增 `test_carrier_hardening.py`、`test_platform_guards.py`、`test_process_guards.py`、`test_health.py`、`test_staff_current.py` 与 B-112 用例；因行为变化改写了一批旧用例。全量 916 个全部通过（运行在打印汇总行前被系统因内存不足中止，进度已到 100% 且无失败标记）。Web `build_test` 通过、typecheck 仍 72；APP vitest 122/122、vue-tsc、eslint、build 通过。<br>**上线前**：① GitHub：APP 仓库建 `production` environment（审批人、分支 `main` 与标签 `v*`）并把签名 / 发布 secret 移进去，配置 `RELEASE_CERT_SHA256`；Backend 设 `BACKEND_HEALTH_URL`、Web 设 `WEB_HEALTH_URL`（默认 5002 / 3002，需确认）；APP 本机生成 `android/gradle/verification-metadata.xml`；② 服务器：`/var/www/api_wms` 的 `git status --porcelain` 必须为空，pm2 进程要能运行 git；③ 数据：绑定已停用用户的 API Key（上线后 401）、商品重量 / 价格中的 NaN 或负值、报关快照里超精度的单价（单证会变成过期）、进行中的盘点（修复前提交过的行可能需要重新保存），先在 PG 上查，并先 dry-run 一次描述清洗脚本；④ 外部系统（Wholesale）：新事件 `dn.cancelled`；`POST /delivery|sorting|picking|packing/` 已去掉；非公司管理员员工 token 调 payment、`PUT /goods/<id>` 需带 `X-WAREHOUSE-ID`；超精度单价的 DN 会被 400 拒绝。已提交到 `fix/audit-1004`（Backend `2071a0e` / Web `e5a6c23` / APP `313be4f`），未推送。 |
| 2026-10-05 | 5 | **剩余 🔵**：除 B-72（需上服务器确认 pm2 命令与端口，部署日志会打印）外全部 ✅；A-53 确认存在漏洞并已修复。<br>**Backend 平台 / 单证**：`goods.spec_updated` 增加单调递增的 `changed_at_ms`（`changed_at` 格式不变）；webhook SSRF 改用 `is_global`，严格模式下建连时解析并校验地址、只连校验过的 IP（SNI / 证书仍按原域名），不再走环境代理；布尔配置统一解析（`1/true/yes/on`，不区分大小写），生产必须有合法的 `SETTINGS_ENCRYPTION_KEY`，`WEBHOOK_URL_STRICT` 生产默认开启，未设 `FLASK_ENV` 而库不是 sqlite 时只告警；测试依赖移到 `requirements-dev.txt`；CI Shipper 国家与检查同源；承运商名含非拉丁字符报 `CARRIER_NON_LATIN_TEXT`；非 JPY 币种给 `JP_EXPORT_VALUE_UNVERIFIED` 警告；收件人过长排版溢出 → 409 16117；department 在 API Key 下不再 500；SMTP 测试不回显异常；`list_goods_locations` 稳定排序；单证 `issued_by_user`、运单 `created_by_user` 带用户名（W-51）。<br>**Backend 流程**：分拣 / 拣货 / 打包追加批次支持 `client_batch_id` 幂等（重放 200、内容不同 409 16121、格式不对 400 16123）；统一加锁顺序（父单据 → 任务 → 库存行按 goods_id → 库位行按 goods_id, location_id）；sorting 等统计去掉不存在的 `sorting_type` 过滤；调整单记录明细最后修改人，修改人不能自审（16122）；库存行 / 库位库存行「先查后插」改为 savepoint 插入、冲突重读；移库源库位无此商品改用 16120，14003 只表示缺仓库。迁移 `9d3f7b2a4c61`（三张批次表 `client_batch_id` + 唯一约束，`adjustments.details_modified_by`）。<br>**Web**：W-43~W-57（PDF 降级下载、超时提示只针对建单、轮询按记录时间截止与卸载停止、失败后重读、申告价额 0、非拉丁判定与后端一致、箱子小数位提示、ZPL/EPL 只下载、签发人显示用户名、i18n 遗留、死链、DN 详情 / 打印字段、时间线、上传卡死、webhook 事件筛选）；分拣 / 拣货 / 打包提交带 `client_batch_id`；16120~16123 文案。三语各 1399 个 key。<br>**APP**：批次提交带 `client_batch_id`（失败保留录入，重试为同一 id 重放）；16078 按承运商 code 匹配；打包页锁定只看运单接口；单证过期提示；退出登录调后端吊销 refresh token；Manifest 补 `dataExtractionRules` / `fullBackupContent`；签收日期不能选未来、承运商取 100 条、运输方式 8 种；打包详情标签修正；error.json 补 16120~16123、14003 去掉多义处理。**A-53**：反编译确认 JsBridge 1.0.4 不转义单引号，`'+alert(1)+'` 的二维码即可执行脚本；在 Kotlin 层加 `BarcodeFilter`（只放行 `[A-Za-z0-9 \-_.:/+=]`、≤512 字符），本机 Gradle 编译与原生单测通过，需真机扫码确认。<br>**测试**：新增 `test_platform_followups.py`、`test_process_followups.py`；Backend 全量 **1005 passed**；Web `build_test` 通过、typecheck 仍 72；APP vitest 167/167、vue-tsc、eslint、build 通过。<br>**上线前补充**：① 生产 `.env` 的 `SETTINGS_ENCRYPTION_KEY` 必须是合法 Fernet 密钥（09-29 已设置，确认即可）；② 服务器出网如果依赖 `HTTPS_PROXY`，严格模式下 webhook 会失败，需确认；③ 以前写成 `true` / `1` 实际不生效的开关上线后会生效；④ 生产 venv 里的 fakeredis / pytest 不会被自动卸载；⑤ 承运商名是日文的公司签发 CI 会被拦，先改英文名；公司国家与仓库国家不一致的海外 DN 单证会变成过期；⑥ Wholesale：`goods.spec_updated` 新增 `changed_at_ms`；⑦ 前端与后端需同时上线（旧后端可能拒收 `client_batch_id`）；⑧ APP 需真机验证扫码过滤、备份排除、退出吊销与批次重放。已提交到 `fix/audit-1004`（Backend `13d9b27` / Web `6823c2f` / APP `c7b63ca`），未推送。 |
| 2026-10-05 | 6 | **上线**：Backend 首次按新流水线部署被服务器上的未跟踪文件（`.env.bak-20260930-082144-osskey`、`.scheduler.lock`）拦下，代码 / 库 / 进程均未改动；修正为只检查已跟踪文件（未跟踪文件只提示），`.gitignore` 补这两类文件（Backend `15e3ac5`）。第二次部署成功：迁移 `a5e6f7a8b9c0` → `152c6ebfb7ab` → `3a9d6c1e8b42` → `6b8f2d4c1e7a` → `9d3f7b2a4c61`，健康探测 `status=ok commit=15e3ac5`，`748b80d → 15e3ac5`。Web `6823c2f`：已上线（健康探测 HTTP 200，buildId=7c6d1a4d-bf1f-4739-b637-53e8cf3ea017，上一版在 /var/www/admin_wms_prev）。<br>**待办**：服务器上的 `.env.bak-*`（含密钥）移出仓库目录；商品描述清洗 dry-run 后 `--apply`；（可选）卸载生产 venv 里的测试依赖；APP 建 `production` environment 与 `RELEASE_CERT_SHA256` 后升 1.3.2 发版；上线后验证见上线清单第六节。 |
