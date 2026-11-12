# WMS 与批发站接口及业务流程审核

日期：2026-11-12。范围：WMS Backend、WMS Web、批发 API、批发 Admin、批发商城；覆盖商品建档、到货预告、实收与破损、出库、撤单、回调、重试、物流、地址及异常恢复入口。

审核在上一轮六项修复后的工作区确认 **10 项缺陷及 6 项功能缺口**。用户随后要求按顺序全部完成，已进入修复及复核阶段。下文“已确认缺陷”保留修复前的复现证据，当前实施结果以文末记录为准。

审核初始基线：WMS Backend `9fc340f`、WMS Web `15e8159`、批发 API `cc80e23`、Admin `75b848b`、商城 `ae18612`，包含上一轮修复。提交前已合并远端 API `3fd629d`、Admin `49ba504`，保留商品主数据同步、WMS 实测规格优先和实际业务时刻等新行为。修复验证使用内存库及独立本地 PostgreSQL 测试集群。用户随后授权完成后提交、推送；批发站 main 推送会触发其现有部署工作流，WMS 保持当前改版分支。

## 已确认缺陷

P1：阻断正常业务且缺少业务入口补救。P2：条件性错误、状态不一致或重要可见性缺失。

### D01 短收或破损完成后无法登记补货

**P1，真实 API 与签名回调已复现。** 采购 10 件，ASN 预告 10 件，完成时良品 8 件、破损 2 件。批发站正确记录实收 8 件和部分到货，但再登记补到的 2 件返回 400，提示剩余可登记量为 0。

原因是登记校验始终扣除历史预告数量，没有在 ASN 结束后释放短收额度。正常拆成两次各预告 5 件不受影响。

位置：[到货登记额度](../GoodsMart/GoodsMart-Wholesale-API/app/api/scm/deliveries.py:515)、[到货候选额度](../GoodsMart/GoodsMart-Wholesale-API/app/api/scm/deliveries.py:246)、[WMS 良品及破损回传](GoodsMart-WMS-Backend/warehouse/asn/services.py:739)。

修复方向：在途 ASN 按预告占用额度，已结束 ASN 按确认的业务口径结算；补收、破损换货须有明确入口。回归应覆盖短收、破损、取消、分批到货以及并发登记，避免释放后超登记。

### D02 仓库取消单据后批发站没有完整恢复流程

**P1，ASN 与 DN 两条链均已复现。**

- ASN：WMS 已收货未分拣的取消会发送 `asn.cancelled / closed`；批发站返回 200，但保留 `processing` 和旧 ASN ID。取消采购单被 `PO_HAS_PENDING_ASN` 拦截，重新推送被 `WMS_ASN_ALREADY_CREATED` 拦截。WMS 对 pending ASN 的关闭路径还没有发送取消事件，因而只补批发回调处理并不完整。
- DN：仓库取消后批发站只记录关闭日志，仍保留 `preparing / processing` 和旧 DN ID。手动推送返回 400 `WMS_DN_ALREADY_CREATED`；后台也没有确认撤回后重建指示的入口。上轮修复的是“新 DN 已绑定后隔离旧回调”，没有解决重建入口本身。

位置：[ASN 回调分支](../GoodsMart/GoodsMart-Wholesale-API/app/api/webhook/wms.py:182)、[ASN 重推限制](../GoodsMart/GoodsMart-Wholesale-API/app/services/scm/wms_asn.py:33)、[采购取消限制](../GoodsMart/GoodsMart-Wholesale-API/app/api/scm/purchase_orders.py:1363)、[WMS pending 关闭](GoodsMart-WMS-Backend/warehouse/asn/services.py:755)、[WMS received 取消事件](GoodsMart-WMS-Backend/warehouse/asn/services.py:812)、[DN 回调](../GoodsMart/GoodsMart-Wholesale-API/app/api/webhook/wms.py:437)、[DN 重推限制](../GoodsMart/GoodsMart-Wholesale-API/app/api/admin/management.py:3619)。

修复方向：区分仓库指示被撤回与客户订单被取消，保留旧指示历史；核实仓库已关闭后允许明确的重新下发或结束流程，避免简单清空 ID 导致重复收发货。所有 ASN 取消路径应统一发送事件。

### D03 商品存在性判断仍使用模糊 JAN

**P2，客户端行为已复现，对端查询语义已核对。** `ensure_goods` 默认模糊查询且只取第一条。查询 `4580590129474` 时，若命中 `PREFIX4580590129474`，客户端直接返回后者 ID，不创建准确 JAN。ASN 随后按准确 JAN 建单，WMS 精确查找失败，返回 400 / 16030。首次登记及自动、手动重推均使用默认模式。

位置：[客户端默认匹配](../GoodsMart/GoodsMart-Wholesale-API/app/services/wms_client.py:240)、[首次登记调用](../GoodsMart/GoodsMart-Wholesale-API/app/api/scm/deliveries.py:602)、[WMS 模糊列表过滤](GoodsMart-WMS-Backend/warehouse/goods/services.py:269)、[ASN 精确解析](GoodsMart-WMS-Backend/warehouse/asn/services.py:94)。

修复方向：业务关联统一精确匹配商品编码；停用商品及唯一约束冲突单独处理，不能把相似编码当成同一商品。

### D04 手动推送 DN 失败仍返回创建成功

**P2，真实 API 已复现。** 模拟 WMS 创建 DN 报错，手动推送接口返回 HTTP 200、`message="WMS DN 作成完了"`，同时 `wms_dn_id=null`、`wms_status=failed`。响应自身矛盾，会让调用方误报成功。

位置：[手动推送接口](../GoodsMart/GoodsMart-Wholesale-API/app/api/admin/management.py:3677)。

修复方向：成功必须以有效 DN ID 为条件；失败返回明确的失败结果并保留推送日志。

### D05 重试额度按重复日志计数而提前耗尽

**P2，内存调度流程已复现。** 外层手动推送或调度任务记录一次日志，内部 `_create_wms_dn` 又记录一次；重试上限按日志行数计算。设置上限 10，在一次手动推送及后续自动重试场景中，实际创建调用仅 5 次，已有 10 条日志，单据便进入 `abandoned`。

位置：[外层调度日志](../GoodsMart/GoodsMart-Wholesale-API/app/scheduler.py:296)、[内部推送日志](../GoodsMart/GoodsMart-Wholesale-API/app/api/shop/shipments.py:967)、[计次及停止条件](../GoodsMart/GoodsMart-Wholesale-API/app/services/wms_push_logger.py:64)。

修复方向：每次真实尝试仅记录一次，或为一次尝试设置唯一标识；操作审计与重试次数分开计算。

### D06 同一 DN 的旧物流回调仍能覆盖新详情

**P2，签名回调乱序已复现。** 同一 DN、同一运单先收到已送达，再收到旧的运输中事件，最终出库状态仍是 `delivered`，物流详情却变为 `in_transit`，送达时间被清空。

上轮加入的 DN ID 校验能隔离不同 DN，不能判断同一 DN 的物流快照先后。WMS 的发送前去重能淘汰待发旧事件，但无法撤回已经在途的请求。

位置：[批发完整覆盖物流快照](../GoodsMart/GoodsMart-Wholesale-API/app/services/shipment_tracking.py:97)、[WMS 跟踪事件载荷](GoodsMart-WMS-Backend/warehouse/dn/tracking_services.py:393)、[发送前淘汰旧事件](GoodsMart-WMS-Backend/system/webhook/services.py:315)。

修复方向：物流快照加入来源版本或采集时刻，在消费者落库时比较；不能单纯按配送状态大小排序，因为异常状态也可能合法变化。

### D07 WMS 已建运单但批发站尚无单号时无法手动刷新

**P2，页面和接口条件已核对。** 后台刷新按钮以本地 `trackingNumber` 为空为禁用条件；API 实际只要求已绑定 DN。准备出库阶段 WMS 已建运单甚至已返回跟踪信息时，本地仍可能没有单号，用户无法触发原本受支持的刷新。

位置：[按钮禁用条件](../GoodsMart/GoodsMart-Wholesale-Admin/app/components/shipment/TrackingCard.vue:11)、[API 按 DN 查询](../GoodsMart/GoodsMart-Wholesale-API/app/api/admin/management.py:554)、[回调补填运单号条件](../GoodsMart/GoodsMart-Wholesale-API/app/api/webhook/wms.py:633)。

修复方向：按是否存在可查询的 WMS 指示及操作状态决定是否允许刷新；无可跟踪运单由接口给出明确原因。

### D08 自动发货或签收被阻止的原因没有展示

**P2，响应到页面的数据链已核对。** WMS 已揽收，但计划发货日期等条件阻止自动发货时，接口返回 `wms_problem`。Admin 类型未包含该字段，页面丢弃刷新响应并直接提示成功；后续详情也未保存这项原因。

位置：[API 返回原因](../GoodsMart/GoodsMart-Wholesale-API/app/api/admin/management.py:604)、[客户端响应类型](../GoodsMart/GoodsMart-Wholesale-Admin/app/stores/api/useShipmentServices.ts:84)、[页面丢弃响应](../GoodsMart/GoodsMart-Wholesale-Admin/app/pages/shipments/[id].vue:735)。

修复方向：明确区分跟踪查询成功与仓库业务处理成功，显示具体阻塞原因及下一步处理位置。

### D09 修改地址簿会改变已发货出库记录的地址

**P2，真实商城 API 已复现。** 出库单已发货并绑定 DN700，修改地址簿街道返回 200；再次读取同一历史出库单，地址变为新街道，DN 不变。展示内容与 WMS 的固定收件快照及实际运单不一致。

原因是出库记录只有地址 ID，序列化时实时读取地址簿；地址修改限制只覆盖待支付和准备出库阶段。

位置：[地址修改校验](../GoodsMart/GoodsMart-Wholesale-API/app/api/shop/addresses.py:265)、[出库地址序列化](../GoodsMart/GoodsMart-Wholesale-API/app/api/shop/shipments.py:167)、[商城展示](../GoodsMart/GoodsMart-Wholesale-Web/app/pages/mypage/shipments.vue:106)。

修复方向：在出库单中保存收件地址快照；地址簿修改供后续出库使用，不覆盖历史记录。存量快照回填应说明能否从 WMS 获取原始地址。

### D10 同秒重试可能误确认尚未处理成功的回调

**P2，窄范围边界已复现。** 使用同一事件 ID、同一时间戳的合法签名请求，第一次业务处理返回 503，第二次返回 200 `duplicate delivery ignored`，业务处理器只执行一次。

原因是业务执行前写入 Redis 去重标记，失败没有释放。WMS 时间戳为整数秒，同秒立即重试可能命中；正常间隔 30 分钟的自动重试会使用新时间戳，不受这一特定边界影响。

位置：[业务前写入去重标记](../GoodsMart/GoodsMart-Wholesale-API/app/api/webhook/wms.py:83)、[去重后才执行业务](../GoodsMart/GoodsMart-Wholesale-API/app/api/webhook/wms.py:125)、[WMS 秒级时间戳](GoodsMart-WMS-Backend/system/webhook/services.py:263)。

修复方向：区分处理中和已完成投递；失败释放或允许重试，只有业务成功后才能将后续重放确认成已完成。

## 功能缺口

以下与业务设计范围有关，不能一概视为当前生产故障。

| 编号 | 缺口与影响 | 代码证据及建议 |
|---|---|---|
| G01 | 回调耗尽后，批发站缺少主动对账及修复入口；已绑定指示可能长期停在 processing | [WMS 十次失败停止](GoodsMart-WMS-Backend/system/webhook/services.py:478)；[批发只重试创建失败的 ASN](../GoodsMart/GoodsMart-Wholesale-API/app/scheduler.py:198)。补处理中的 ASN/DN 拉取对账及人工恢复。WMS 现有手工重推 webhook 仍可用于补救。 |
| G02 | 已有首次手动推送 API，但后台没有调用入口；登记时不通知 WMS，或后来才启用 WMS，无法从单据页补推 | [手动推送 API](../GoodsMart/GoodsMart-Wholesale-API/app/api/admin/management.py:3654)；[日志页只允许失败记录重试](../GoodsMart/GoodsMart-Wholesale-Admin/app/pages/supply/wms-logs/index.vue:117)。补首次发送入口并复用后端防重复校验，不应自动发送所有原本选择不通知的记录。 |
| G03 | 到货登记、列表及详情不显示 WMS 同步状态，实收 0 无法区分仓库未收货与根本没有收到通知 | [登记失败仍返回业务记录创建成功](../GoodsMart/GoodsMart-Wholesale-API/app/api/scm/deliveries.py:620)；[登记组件忽略同步状态](../GoodsMart/GoodsMart-Wholesale-Admin/app/components/supply/DeliveryCreateDialog.vue:816)。在单据上显示预告量、ASN 编号、同步状态及重试入口。 |
| G04 | 仓库拣货、打包进度仅在后台可见，客户仍统一看到准备中 | [Shop 序列化](../GoodsMart/GoodsMart-Wholesale-API/app/api/shop/shipments.py:115)、[商城进度](../GoodsMart/GoodsMart-Wholesale-Web/app/pages/mypage/shipments.vue:335)。如新版承诺向客户展示仓库进度，需要补 Shop API 和页面；现有证据不足以认定这是既定产品要求。 |
| G05 | 少发后只保留修改后的数量，客户缺少申请量、实发量、差额原因的记录 | [回调覆盖数量](../GoodsMart/GoodsMart-Wholesale-API/app/api/webhook/wms.py:692)、[明细模型](../GoodsMart/GoodsMart-Wholesale-API/app/models/shipment.py:110)。保留原申请数和实发数。自动补发及追加运费属于需确定的业务规则。 |
| G06 | 供应商固定采用 WMS ID 1，缺少真实供应商映射及默认 ID 配置 | [明确的默认策略](../GoodsMart/GoodsMart-Wholesale-API/app/api/scm/deliveries.py:583)。当前注释表明这是有意默认，不能断言现网错误；多供应商统计、换公司或无该 ID 的部署需要补映射和配置。 |

## 已覆盖的流程与验证结果

| 流程 | 审核结果 |
|---|---|
| 普通仓库员工密钥调用、商品更新、结构化收件人及 DN 地址、佐川地址字段 | 上一轮实际客户端对 WMS 内存接口的 14 次请求验证通过，修复保留 |
| 商品规格同秒乱序、ASN 旧快照、旧 DN 迟到事件隔离 | 上一轮新增 13 项契约回归通过；本轮未发现这些修复被撤销，但发现同 DN 物流版本缺口 D06 |
| 入库良品与破损、同 JAN 多采购行、超计划分拣 | 破损不分配给客户，多行按预告比例摊回；WMS 默认拒绝超计划分拣。补收额度另见 D01 |
| 仓库取消与重新下发 | D02 阻断，必须完成两端状态及操作入口 |
| 推送失败和重试 | D04、D05、D10；恢复与界面入口另见 G01—G03 |
| 物流查询及自动发货异常 | D06—D08；出库主状态防倒退存在，但不等于详情防倒退 |
| 客户历史地址与少发说明 | D09、G05 |
| 海外报关快照再送、CI/PL 后台取回及失败补取 | 未发现新的明确入口缺口；CI/PL 仅后台查看是现有明确设计，不列为商城缺陷 |

本轮验证：批发 Admin 相关 6 个测试文件、32 项测试通过；独立 SQLite 内存复现得到下列结果。上一轮的批发 API 294 项、WMS 前端 38 项为既有回归基线，并非本轮重新全量执行。

```text
SHORT_RECEIPT          callback=200 expected=10 received=8 next=400 remaining=0
CANCEL_ASN            callback=200 processing retained; cancelPO=400; retryASN=400
CANCEL_DN             callback=200 preparing/processing DN700 retained; repush=400
FUZZY_GOODS           similar JAN returned as existing; exact goods create_calls=0
MANUAL_PUSH_FAILURE   HTTP200 success message; wms_dn_id=null; wms_status=failed
RETRY_BUDGET          configured=10 actual_create_attempts=5 log_count=10 abandoned
LATE_TRACKING         shipment_status=delivered tracking_status=in_transit delivered_at=null
HISTORICAL_ADDRESS    address update=200; shipped record now shows new address; DN unchanged
FAILED_RECEIPT_DEDUPE first=503 second=200 handler_calls=1
```

修复前主审计复现脚本保留在本地 `logs/audit_wholesale_round2.py`（历史诊断，不作为修复后通过标准）。其余入库及商城复现通过独立内存测试脚本执行。生产数据库、实际 webhook 投递、正式密钥权限和真实承运商请求不在本次运行结果内。

## 修复顺序

1. 优先完成 D01、D02，明确短收补货以及仓库撤单后的恢复规则，同时补关联后台入口。
2. 修复 D03—D06、D10，统一精确商品关联、真实尝试计次、失败响应和事件版本保护；加入 G01 对账能力。
3. 修复 D07—D09，并补 G02、G03 的运营入口与状态显示。
4. 按用户本次授权实施 G04—G06；上线时仍须为已有批发 API 密钥补齐上一轮要求的 delivery_edit 权限。

上述复现是修复前的审核记录，不代表当前代码仍保留这些行为。

## 修复实施及复核记录

本轮 **10 项缺陷及 6 项功能缺口均已完成实现与回归**，提交前已合并远端新增功能。以下为最终实施结果：

| 项目 | 实施结果 |
|---|---|
| D01 | 在途按预告占用额度，已结束按良品实收结算；短收可登记补到数量，同采购单登记串行校验。 |
| D02 | 所有 ASN 关闭路径发事件；ASN/DN 保留旧指示及关闭记录，确认远端关闭后才能重建，旧回调不再生效。 |
| D03—D05 | JAN 默认精确；DN 失败返回 503；一轮真实推送只计一条尝试日志。 |
| D06、D10 | 跟踪快照按来源微秒时刻拒绝迟到/重复版本；回调处理成功后才标记完成，失败释放去重占位。 |
| D07—D09 | 刷新按 DN 可查询性启用；持久展示仓库阻塞与查询错误；出库地址固定快照，历史回填标注来源。 |
| G01—G03 | 定时轮换对账及手工对账；首次发送、撤回、重建、历史与错误入口；登记预告/实收及失败提示。 |
| G04—G06 | 商城仓库作业阶段、原申请/实发/少发数量；供应商单独映射及 `WMS_DEFAULT_SUPPLIER_ID` 默认配置。 |

已完成的跨仓库验证：

- 批发 API 完整相关套件：SQLite **709 项通过、3 项跳过**；跳过的 PostgreSQL 专用迁移/竞态已在下列真实 PostgreSQL 套件通过。测试阻断未 mock 的 requests HTTP。
- 批发 API：独立 PostgreSQL 上 **100 项恢复/版本/时区/迁移测试通过**；双线程同旧 ASN 重建仅调用一次创建，另一请求返回 409；同采购单剩余量并发登记仅一笔成功。真实执行 `d4 → e1 → e6` 升级、地址/申请数量回填，以及 e6 降级再升级。
- WMS Backend：独立 PostgreSQL 上 ASN、取消生命周期、仓库作业回调、物流跟踪共 **52 项通过**；包括 pending 关闭、pending 取消、received 取消均只产生一次通知，以及物流异常/恢复的完整版本快照。
- 合并后的真实 Wholesale `WMSClient` 调用真实 WMS Flask 路由：**31 次请求通过契约断言**，覆盖精确 JAN（相似 JAN 不混用）、员工密钥权限、商品批量查找/更新、结构化地址、佐川字段、ASN/DN 关闭后重建、同业务单已存在指示复用及主动对账读取接口。无运单刷新按预期返回 409，不是权限错误。脚本：[check_wholesale_contract.py](scripts/check_wholesale_contract.py)。
- 商城：相关 **163 项测试通过**，包含页面 48 项；日英中三语及 390px/1200px 浏览器布局检查通过；Nuxt 客户端、SSR 和 Nitro 生产构建通过。
- Admin：合并后相关 **107 项测试通过**（含远端数量回归），Nuxt 生产构建通过；隔离 Chromium 页面流程通过，1440px/390px 无横向溢出或 JS 错误。

自动补发和追加运费规则不作推测：少发释放后的剩余商品继续使用现有出库申请流程，并在前后台显示原申请、实发及少发数量。

部署与历史数据说明：

- API 需执行 `flask db upgrade`（现有 main 部署工作流已包含）；e6 接续远端 e1，不产生迁移分叉。Admin/商城在 API 更新后部署。
- WMS 现有批发密钥需具备 `delivery_edit`；权限模板的修改只影响后续新建密钥，不自动修改已有密钥。
- 供应商映射为空时使用 `WMS_DEFAULT_SUPPLIER_ID`，默认 1；实际配置须对应目标 WMS 公司中的供应商。
- 新出库保留创建时地址和申请数。旧地址先按现存地址回填并标记 `legacy_current`，只有取得完整 WMS `ship_to` 后才标记为 WMS 历史快照；无法凭当前数据库还原已丢失的旧原申请数，回填值使用现存明细数量。
- 另发现既有空库初始化问题：旧迁移 `36ff10ac2681` 为不存在的 `goods.order_count` 建索引，导致全历史从零升级失败。本次验证的是现有 d4/e1 部署库的增量升级；该早期初始化缺陷未混入本轮接口修复。

## 提交交付

| 仓库 | 提交 | 推送分支 |
|---|---|---|
| Wholesale API | `ab5b92f` | `main` |
| Wholesale Admin | `b37839d` | `main` |
| Wholesale Web | `f9813d7` | `main` |
| WMS Backend | `00ec84f` | `codex/wms-ui-refactor-20261028` |
| WMS Web | `ecc2424` | `codex/wms-ui-refactor-20261028` |

GoodsMart 总仓库 `37bacaf` 同步了三个批发子模块。WMS 总仓库同步本报告、可复跑契约脚本和两个 WMS 子模块。已有的库存报表/阈值等无关工作区修改、截图、日志及临时 PostgreSQL 运行文件没有加入提交。临时 PostgreSQL 测试服务已停止。
