# 改版上线审核与 PDA 兼容检查

日期：2026-11-09。范围：Backend、Web、Android/PDA 的部署链路、数据库升级及新版接口兼容；同时形成原生客户端重构方案。

基线：Backend `f2019bf`、Web `054e29d`、APP `7e684f7`，分支均为 `codex/wms-ui-refactor-20261028`。根据用户后续授权，本轮修复已提交并推送至各子仓库同名分支，主仓库本次提交同步子模块指针与审核记录。未合并 main、打发布标签或操作生产环境。

| 仓库 | 已推送提交 |
|---|---|
| Backend | `9d2f1bb`：部署门禁、完整 PostgreSQL 升级检查与测试夹具修复 |
| Web | `15e8159`：部署前执行业务回归 |
| APP | `a7b6870`：混批少装兼容、1.4.3/16 发布准备与原生客户端设计 |

本地 `.playwright-mcp/`、`tmp/`、`GoodsMart-WMS-Backend-testspeed/` 均未纳入提交。

## 审核结论

本地自动验证通过。旧版模型到新版的完整 PostgreSQL 迁移、库存/出库/批次测试、Web 生产服务启动、PDA 业务测试和 Android release 构建均已验证。发现并修复现有 PDA 混批少装无法完成的问题，以及部署验证未串联、发布版本号未递增等发布缺口。

这不是生产已上线的结论：生产数据库实际版本与配置、正式发布工作流、正式签名包及 PDA 真机联调仍需上线验收。

## 修复内容

| 问题 | 修复 | 位置 |
|---|---|---|
| 后端部署与 PostgreSQL 测试独立运行，测试失败仍可能部署 | 测试工作流支持 `workflow_call`，部署 `needs: validate`；加入完整后端回归和改版前升级验证 | Backend `.github/workflows/deploy.yml`、`test-postgres.yml` |
| 部署脚本 fetch 后直接部署最新 main，可能跳过本次检查 | 部署固定到本次 `github.sha`，并确认它仍在 main 历史上 | Backend `.github/workflows/deploy.yml` |
| 只测试最后一个迁移，新增 19 个迁移没有完整升级证据 | 固定改版前提交建立真实旧模型、写样本、连续升级全部迁移、重复升级、比较模型、保留旧行、库存对账、重复权限初始化和健康接口检查；只允许空的 `wms_migration_*` 测试库，不删除原库 | Backend `scripts/manual/migration_upgrade.py` |
| Web / APK 发布流程没有执行已有业务回归 | Web 加入 38 项回归；APK 构建前执行类型检查和单元测试 | Web/APP 发布工作流 |
| APK 仍是已发布的 1.4.2 / 15，会被版本门禁拒绝 | 同步 package.json、lock 和 Gradle 为 1.4.3 / 16 | APP 版本文件 |
| APP 缺少后端地址时仍能构建；HTTP 地址又被 WebView 混合内容策略禁止 | 发布前校验 HTTPS 地址，拒绝空地址、非法协议及内嵌凭据 | APP `.github/workflows/release-apk.yml` |
| 新后端要求混批少装确认实装批次，旧 PDA 只发完成请求，返回 16172 | 保存打包总数后读取 `/lot-allocations`，逐批次确认数量；检查整数、上限、合计，支持明确填 0，保留失败输入；待确认时暂停扫码和改数量，重试不重复保存批次 | APP `DeliveryManagement.ts`、`PackDetail.vue`、三语言文案及测试 |
| 新批次测试修补历史夹具时显式插入 ID，PostgreSQL 序列未同步导致假失败 | 仅在 PostgreSQL 测试夹具中同步 picking/packing 批次序列；随后整份批次测试通过 | Backend `tests/test_lot_operations.py` |

旧 PDA 调整箱重尺寸时不携带 `contents` 的情况也已核对：后端保留原箱内容，改变已有内容的箱数会拒绝，因此不会因简化编辑静默删除 PC 分配。

## 验证结果

| 检查 | 结果 | 本地证据 |
|---|---|---|
| Backend 全量 SQLite/fakeredis | **1747 passed** | `tmp/deploy-audit-backend-20261109.log` |
| PostgreSQL 16 库存子集 | **105 passed** | `tmp/deploy-audit-pg-stock-20261109.log` |
| PostgreSQL 出库/状态转换/并发子集 | **203 passed** | `tmp/deploy-audit-pg-outbound-20261109.log` |
| PostgreSQL 批次作业，包括实际混批少装与跨订单隔离 | **13 passed** | `tmp/deploy-audit-pg-lot-compat-20261109.log` |
| 完整升级 | **19 个迁移通过**；15 张表的旧样本保留；模型无差异、库存对账通过 | `tmp/deploy-audit-migration-upgrade-20261109.log` |
| 最新迁移往返 | **通过** | `tmp/deploy-audit-migration-roundtrip-20261109.log` |
| Web | **类型检查、38 项测试、生产构建通过** | `tmp/deploy-audit-web-{typecheck,tests,build}-20261109.log` |
| Web 构建产物启动 | **通过**；本次 buildId、页面、静态资源、API 路径和鉴权/仓库请求头透传；文档代理拒绝 | `tmp/deploy-web-smoke-20261109.mjs` |
| PDA | **类型检查、299 项测试、生产资源构建通过** | `tmp/deploy-audit-app-{typecheck,tests}-20261109.log`、`tmp/deploy-audit-app-android-assets-20261109.log` |
| PDA 混批界面浏览器检查 | **通过**；390/320px 无横向溢出，未填阻止完成，0/3 实装请求正确；截图已查看 | `tmp/deploy-packing-browser-20261109.mjs`、`tmp/deploy-audit-packing-mobile-20261109.png` |
| Android | **4 项 Kotlin 单测通过，lintVitalRelease、assembleRelease 通过**；生成未签名 1.4.3 / 16 APK | `tmp/deploy-audit-app-android-20261109.log`、APP `android/app/build/outputs/apk/release/` |
| 工作流 | YAML 解析、24 个 shell 脚本语法检查通过；Git diff 无空白错误 | `tmp/validate-workflows-20261109.py` |

完整升级起点是 `pre-ui-refactor` 所指的 `d3b2c2e`（脚本固定该标签对象），迁移版本从 `5b8e2d7c4a91` 到 `a1d5e9f6b378`。测试库为本地独立 PostgreSQL 16.15 实例，只绑定 127.0.0.1:55439；没有连接生产数据库。为缩短临时库反复建表测试耗时关闭了该测试实例的同步落盘，这些检查不用于证明断电恢复或持久化能力。

浏览器检查使用隔离的模拟 API；实际后端批次校验、库存与来源行为由上述 PostgreSQL 测试覆盖。正式服务器、真机扫码及承运商仍需环境验收。

构建警告：Web 在 Windows 下提示找不到 sharp 平台二进制，但构建与上述启动检查通过；生产 Linux 安装/构建应以发布工作流结果为准。Python 存在既有弃用和测试夹具警告，无测试失败。

## 上线顺序与剩余环境验收

1. 各子仓库修改已提交并推送，主仓库本次提交同步指针。下一步在预发使用生产配置结构验证 HTTPS API、Redis、对象存储和定时任务。确认实际服务器数据库版本与迁移起点；本地样本不能代替生产备份和数据检查。
2. 首轮切换安排作业维护窗口，备份 PostgreSQL，记录后端提交、Web 构建和已发布 APK。确认 `FLASK_ENV=production`、密钥、仓库时区及健康地址正确。
3. Backend 先发布：等待全量回归、完整升级和 PostgreSQL 子集通过，再迁移、初始化权限、启动与健康探测；核对数据库已到 `a1d5e9f6b378` 和库存审计结果。
4. Web 后发布，核对 buildId、登录、选仓和关键作业。PDA 1.4.3 在新后端可用后签名发布，验证原签名证书、versionCode 16 和覆盖安装；本地 unsigned APK 不能作为正式安装包。
5. 真实 PDA 覆盖收货/批次上架、同商品多批次拣货、混批少装、盘点 0、移库、发货以及断网后重试。确认 PC 已录箱内容不会在 PDA 改尺寸后丢失。真实打印和承运商动作按实际启用功能联调。
6. 代码回滚不回滚数据库；一旦新业务已写入批次/来源等数据，须核实旧代码对这些数据的处理能力再回退。正式 Android 回退也不能假定系统允许安装更低 versionCode。

本轮未执行以上生产发布步骤。

## 原生客户端

当前客户端仍为 Vue + WebView，尚未原生重写。已形成 [Android/PDA 原生客户端设计](GoodsMart-WMS-APP/docs/NATIVE_CLIENT_DESIGN.md)：完整原生化现场作业，以 Kotlin + Compose 为方向；分析、配置、批量编辑、报关和对账保留 PC；移动端提供任务、扫码、查询摘要、批次确认、草稿和恢复。

方案明确了全部现场功能的完成边界、接口契约、弱网下的提交确认、设备扫码适配、原签名覆盖升级与验收要求。原生代码实现不包含在本轮已完成项中。
