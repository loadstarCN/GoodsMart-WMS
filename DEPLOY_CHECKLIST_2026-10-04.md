# 上线清单：2026-10-04 审计修复

> 对应审核报告 `AUDIT_REPORT_2026-10-04.md`（修复日志第 1~5 批）。四个仓库的 `main` 已在本地合并 `fix/audit-1004`，**尚未推送**。
> Backend / Web 的 `main` 一推送就由 GitHub Actions 自动部署到生产；APP 打 `v*` 标签才发布。请按本清单的顺序执行。
>
> | 仓库 | 合并后的 main | 部署方式 |
> |---|---|---|
> | Backend | `15e3ac5` | 推送 main → 自动部署（含数据库迁移）——**2026-10-05 已上线** |
> | Web | `6823c2f` | 推送 main → 自动部署——**2026-10-05 已上线（健康探测 HTTP 200，buildId=7c6d1a4d-bf1f-4739-b637-53e8cf3ea017，上一版在 /var/www/admin_wms_prev）** |
> | APP | `c7b63ca` | 改版本号 → 推送 main → 打 `v1.3.2` 标签 → 审批后发布 |
> | 主仓库 | 见 `git log -1` | 推送 main（只更新子模块指针） |

---

## 一、GitHub 设置（推送前）

### Backend 仓库
- [ ] 在服务器上确认 Backend 实际监听的端口：`pm2 describe wms-api`（看启动命令 / 参数 / `PORT`），或 `ss -ltnp | grep python`
- [ ] Settings → Secrets and variables → Actions → Variables 新建 `BACKEND_HEALTH_URL`，例如 `http://127.0.0.1:<端口>/health`
  - 不设时默认 `http://127.0.0.1:5002/health`；地址完全连不上时，部署会在动代码之前中止（安全，但部署不了）
  - 生产如果开了 IP 白名单（`CHECK_WHITELIST`），把 `127.0.0.1` 加进白名单，否则探测拿到 403

### Web 仓库
- [ ] 确认 Nuxt 服务端口（`pm2 describe` 对应进程，start 脚本是 3002；直接跑 `index.mjs` 且没设 `PORT` 时是 3000）
- [ ] 新建仓库变量 `WEB_HEALTH_URL`，例如 `http://127.0.0.1:3002/`

### APP 仓库
- [ ] Settings → Environments → New environment，名字 `production`
  - [ ] 勾选 Required reviewers，添加审批人（建议同时勾选 Prevent self-review）
  - [ ] Deployment branches and tags 选 Selected，添加分支 `main` 和标签 `v*`
- [ ] 把以下 secret 移进 `production` environment，并删除仓库级的同名 secret：
  `WMS_ANDROID_KEYSTORE_B64`、`WMS_ANDROID_KEYSTORE_PASSWORD`、`WMS_ANDROID_KEY_ALIAS`、`APK_PUBLISH_SSH_KEY`、`APK_PUBLISH_HOST`、`APK_PUBLISH_KNOWN_HOSTS`
- [ ] `VITE_API_BASE_URL`、`VITE_SENTRY_DSN` **留在仓库级**（构建 job 不在 environment 里，读不到 environment 的 secret）
- [ ] 新建变量 `RELEASE_CERT_SHA256`（放 environment 或仓库级都可以）：正式证书的 SHA-256 指纹
  - `keytool -list -v -keystore release.p12 -storetype PKCS12 -alias <别名>` 的 SHA256 一行，或
  - 对 1.3.1 的 APK 执行 `apksigner verify --print-certs`，取 `Signer #1 certificate SHA-256 digest`
- [ ] （建议）Settings → Rules → Rulesets → New tag ruleset：目标 `v*`，限制创建 / 更新 / 删除，只允许管理员绕过
- [ ] （建议，本机）在 `android/` 下执行 `./gradlew --write-verification-metadata sha256 help assembleRelease`，提交生成的 `android/gradle/verification-metadata.xml`；`gradle/wrapper/gradle-wrapper.properties` 加 `distributionSha256Sum=9631d53cf3e74bfa726893aee1f8994fee4e060c401335946dba2156f440f24c`

---

## 二、服务器检查（推送前）

- [ ] **备份数据库**（这次有 4 个迁移）：`pg_dump -Fc warehouse > /root/backups/warehouse_pre_audit1004_$(date +%F_%H%M).dump`
- [ ] `/var/www/api_wms` 下 `git status --porcelain` 输出为空（不为空时部署会中止并打印出来）
- [ ] 记下当前提交，便于人工回滚：`cd /var/www/api_wms && git rev-parse HEAD`
- [ ] `.env` 检查：
  - [ ] `FLASK_ENV=production`
  - [ ] `SETTINGS_ENCRYPTION_KEY` 存在且是合法 Fernet 密钥（现在生产缺了就**启动失败**）：
    `python -c "import os;from cryptography.fernet import Fernet;Fernet(os.environ['SETTINGS_ENCRYPTION_KEY'].encode());print('ok')"`
  - [ ] `WEBHOOK_PUSH_INTERVAL_MINUTES`：没设的话，推送间隔会从 30 分钟变成 1 分钟
  - [ ] 布尔开关现在按 `1 / true / yes / on`（不分大小写）解析。逐个看 `RATELIMIT_ENABLED`、`SCHEDULER_ENABLED`、`WEBHOOK_URL_STRICT`、`CHECK_WHITELIST`、`CHECK_BLACKLIST` 等：以前写成 `true` / `1` 而实际没生效的，上线后会生效
  - [ ] 生产默认开启 `WEBHOOK_URL_STRICT`，严格模式下 webhook **不走** `HTTPS_PROXY` 等代理。服务器出网如果依赖代理，先确认
- [ ] pm2 进程能执行 `git`（`/health` 用它取当前提交）：`sudo -u <pm2 运行用户> git -C /var/www/api_wms rev-parse --short HEAD`
- [ ] Python 版本：`nh3==0.3.7`、`urllib3==2.6.3` 需要 Python ≥ 3.9（生产是 3.10，没问题）

---

## 三、生产数据检查（推送前，在 PostgreSQL 上只读执行）

| # | 查什么 | SQL | 有结果时怎么办 |
|---|---|---|---|
| 1 | ASN 同一商品多行（B-49） | `SELECT asn_id, goods_id, count(*) FROM asn_details GROUP BY asn_id, goods_id HAVING count(*) > 1;` | 未完成的 ASN 人工合并成一行；已完成的不受影响 |
| 2 | 一张 DN 多条未完成发货任务（B-57） | `SELECT dn_id, count(*) FROM delivery_tasks WHERE is_active AND status IN ('pending','in_progress') GROUP BY dn_id HAVING count(*) > 1;` | 删掉多余的 pending 任务，否则海外件会被 16091 拦住 |
| 3 | 停用但仍有货的库位（B-55） | `SELECT l.id, l.code, sum(gl.quantity) FROM locations l JOIN goods_locations gl ON gl.location_id = l.id WHERE NOT l.is_active GROUP BY l.id, l.code HAVING sum(gl.quantity) > 0;` | 重新启用，或先把货移走 |
| 4 | 绑定已停用用户的 API Key（B-74） | `SELECT k.id, k.system_name FROM api_keys k JOIN users u ON u.id = k.user_id WHERE k.is_active AND NOT u.is_active;` | 上线后这些 Key 会 401；确认是否还在用 |
| 5 | 公司已停用或过期的 API Key（B-74） | `SELECT k.id, k.system_name, c.name FROM api_keys k JOIN companies c ON c.id = k.company_id WHERE k.is_active AND (NOT c.is_active OR (c.expired_at IS NOT NULL AND c.expired_at < now()));` | 同上 |
| 6 | 商品重量 / 价格里的 NaN 或负值（B-70） | `SELECT id, code, weight, price FROM goods WHERE weight = 'NaN' OR price = 'NaN' OR weight <= 0 OR price < 0;` | 修正数据（这些商品现在保存会被 16100 拒绝） |
| 7 | 报关快照里超过币种小数位的单价（B-68） | `SELECT c.dn_id, c.currency, l->>'goods_code', l->>'unit_value' FROM dn_customs c, json_array_elements(c.lines) l WHERE l->>'unit_value' IS NOT NULL AND (l->>'unit_value')::numeric <> round((l->>'unit_value')::numeric, CASE WHEN upper(c.currency) IN ('JPY','KRW','VND','CLP','ISK','PYG','UGX','XAF','XOF') THEN 0 ELSE 2 END);` | 这些 DN 的单证会变成「已过期」，需要重签；已有有效运单的要先取消运单 |
| 8 | 公司国家与仓库国家不一致（B-96） | `SELECT w.id, w.country_code, c.country_code FROM warehouses w JOIN companies c ON c.id = w.company_id WHERE coalesce(upper(w.country_code),'') <> coalesce(upper(c.country_code),'');` | 这些仓库发出的海外单，现有单证会变成过期，需要重签 |
| 9 | 承运商名含非 ASCII 字符（B-97，初筛） | `SELECT id, company_id, name FROM carriers WHERE is_active AND name ~ '[^\x01-\x7F]';` | 日文等名称上线后签发 CI 会被拦，先改成英文名（Müller 这类拉丁字母不受影响） |
| 10 | 进行中的盘点（B-79 / B-80） | `SELECT id, task_name FROM cycle_count_tasks WHERE is_active AND status = 'in_progress';` | 修复前提交过、但值没变的行没有录入标记，完成时会被 16114 拦下，需要重新保存一次 |
| 11 | 以前少打包留在 picked_stock 的差额（B-54） | `SELECT i.goods_id, i.warehouse_id, i.picked_stock, coalesce((SELECT sum(d.picked_quantity) FROM dn_details d JOIN dn ON dn.id = d.dn_id WHERE dn.is_active AND dn.status = 'picked' AND d.goods_id = i.goods_id AND dn.warehouse_id = i.warehouse_id), 0) AS picked_in_open_dn FROM inventory i WHERE i.picked_stock > 0;` | `picked_stock` 明显大于 `picked_in_open_dn` 的，人工核对后用调整单修正 |

- [ ] 商品描述清洗先 dry-run（只打印会变更的条数和商品 id）：`cd /var/www/api_wms && python scripts/sanitize_goods_description.py`
- [ ] 在管理端复核普通员工以前建的「公司级」API Key（未绑定用户的）：仍然有效，确认是否需要保留

---

## 四、外部系统（Wholesale）确认

- [ ] 以下接口已去掉（返回 405）：`POST /warehouse/delivery/`、`/warehouse/sorting/`、`/warehouse/picking/`、`/warehouse/packing/`
- [ ] 新 webhook 事件 `dn.cancelled`（已拣货 / 已打包的 DN 也可以取消了），接收方能处理或忽略
- [ ] `goods.spec_updated` 新增 `changed_at_ms`（毫秒，单调递增），接收方按它判断新旧；上线前已排队的事件没有这个字段，用 `changed_at` 兜底
- [ ] 失败过的 `goods.spec_updated` 不再被新数据覆盖，而是新建一条事件、旧的作废
- [ ] DN 报关单价的小数位超过币种允许位数（JPY 0 位，其它 2 位）时建单返回 400 16063
- [ ] ASN 明细同一商品多行 → 400 16025
- [ ] API Key：所属公司停用 / 过期、或绑定的用户停用 → 401；公司没有启用中的仓库 → 403
- [ ] 用普通员工（非 company_admin）的 token 调 payment、`PUT /goods/<id>` 时需要带 `X-WAREHOUSE-ID`
- [ ] 运费非法改用 16081（以前是 16033）；移库源库位无此商品改用 16120（以前是 14003）

---

## 五、推送与上线顺序

1. [ ] 完成「一~四」
2. [ ] **推送 Backend**：`git -C GoodsMart-WMS-Backend push origin main`
   - Actions 日志依次确认：
     - `[deploy] pm2 wms-api: exec=… args=… cwd=… PORT=…`：这就是审核报告 B-72 要确认的启动信息，请记下来
     - 部署前探测：旧代码没有 `/health`，显示 HTTP 404 是正常的
     - `flask db upgrade` 从 `a5e6f7a8b9c0` 依次到 `152c6ebfb7ab` → `3a9d6c1e8b42` → `6b8f2d4c1e7a` → `9d3f7b2a4c61`
     - 「健康探测通过：status=ok commit=13d9b27」
   - 失败时：代码会自动回到部署前的提交、Actions 标红；数据库**不会**自动回滚（迁移整条链在一个事务里，迁移本身失败会整体回滚）
3. [ ] Backend 上线后：
   - [ ] 商品描述清洗：dry-run 的结果确认无误后执行 `python scripts/sanitize_goods_description.py --apply`
   - [ ] （可选）卸载生产 venv 里的测试依赖：`pip uninstall -y fakeredis pytest iniconfig pluggy sortedcontainers`
4. [ ] **推送 Web**：`git -C GoodsMart-WMS-Web push origin main`
   - 日志确认「健康探测通过：HTTP 200，buildId=…」；失败会自动切回 `admin_wms_prev`，失败的构建留在 `admin_wms_failed_<sha>`
5. [ ] **推送主仓库**：`git push origin main`（只更新子模块指针和本清单、审核报告）
6. [ ] **发布 APP**（Backend 上线之后；APP 提交批次带的 `client_batch_id` 需要新后端）：
   - [ ] `package.json` 与 `android/app/build.gradle` 升到 `1.3.2` / versionCode `7`，提交到 main 并推送
   - [ ] 在该提交上打标签并推送：`git tag v1.3.2 && git push origin v1.3.2`
   - [ ] build job 日志显示「上一个已发布标签：v1.3.1（versionCode 6）」；sign-and-release 停在 Waiting for review → 审批 → 确认「签名证书指纹一致」

---

## 六、上线后验证

### Web / Backend
- [ ] `curl <BACKEND_HEALTH_URL>` 返回 `{"status":"ok","commit":"13d9b27"}`
- [ ] 公司管理员和普通员工各登录一次：员工自动选中仓库、菜单按权限显示
- [ ] DN 完成发货时填运费（如 1500）能成功
- [ ] webhook 日志页能看到新状态（推送中 / 已作废），Wholesale 正常收到事件
- [ ] 海外单：单证卡片、FedEx 运单状态显示正常（如果有在途运单）
- [ ] （建议）在 PG 上用两个会话手工跑一次「拣货完成」并发提交，确认第二个被拦（B-50）

### APP 真机（PDA）
- [ ] 扫码注入：内容为 `'+alert(1)+'` 和 `%27+alert(1)+%27` 的二维码，扫描后只弹 Toast、页面不弹窗；正常 JAN 码和库位码照常识别
- [ ] 分拣 / 拣货 / 打包：提交时断网，录入保留；恢复后再点一次不重复记数
- [ ] 盘点：同一 JAN 多库位时先点库位行再扫码；盘到 0 件的行也能提交，未录入时不能完成盘点
- [ ] 上架 / 下架 / 移库：改了库位码后点取消再提交会被拦下
- [ ] 退出登录后，旧 refresh token 调 `/system/user/refresh` 返回 401
- [ ] Android 12 以上：换机迁移 / `adb shell bmgr backupnow jp.goodsmart.wms` 后需要重新登录
- [ ] 海外单打包后快选原产国，打包页和发货页都出现「单证已过期」提示

---

## 七、回滚

- **Backend 代码**：部署失败会自动回滚。人工回滚：`cd /var/www/api_wms && git reset --keep <部署前提交> && pm2 restart wms-api`
- **数据库**：不建议 `flask db downgrade`（会丢掉新列里的数据，例如调整单来源、批次 `client_batch_id`、取消中的运单状态会被映射回 active）。必要时用第二节的 `pg_dump` 备份恢复
- **Web**：部署失败会自动切回。人工回滚：`mv /var/www/admin_wms /var/www/admin_wms_bad && mv /var/www/admin_wms_prev /var/www/admin_wms && pm2 restart <web 进程>`
- **APP**：发布前把线上的 `gm_wms.apk` 另存一份（09-29 的做法是 `gm_wms-<版本>.apk`），需要时覆盖回去
