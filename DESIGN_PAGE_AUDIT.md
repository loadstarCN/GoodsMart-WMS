# WMS 设计稿逐页验收清单

基准：恢复的 preview/*.dc.html。文件存在不等于完成；所有页面须核验数据、交互、视觉及权限后才能标为通过。
每页检查：桌面/窄屏；字体/字重/行高；内外间距/横线；字段和筛选；空/加载/失败/无权限；真实后端/隔离；关键操作；打印页另核纸张、跨页及多语言。
V2/深色稿列为设计变体，不能擅自将互斥设计合并；共用组件亦逐项覆盖。

| 设计稿 | 对应实现或待定位范围 | 状态 | 已确认差异/证据 |
|---|---|---|---|
| AdjustmentDetail.dc.html | adjustment/*（需精确核验） | 未验收 | 待逐页检查 |
| AdjustmentList.dc.html | components/operations/InventoryTaskList.vue | 部分修复，未验收 | 分页12px、顶部选仓切换重置页码；已截图，尚未完整视觉验收 |
| AdminHome.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| AdminLogs.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| AdminPermissions.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| AdminRoles.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| AdminSettings.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| AdminSidebar.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| AdminTenantDetail.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| AdminTenants.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| AdminUsers.dc.html | admin/*（需精确核验） | 未验收 | 待逐页检查 |
| ApiKeys.dc.html | apikeys/index.vue | 部分修复，未验收 | 补编辑+更多、签名/订阅/无URL状态与三栏横线；新增公司隔离真实推送汇总并通过2项测试；布局样本桌面/手机已看；调用历史仍未记录，真实非空验收未完成 |
| AsnDetail.dc.html | asn/*（需精确核验） | 未验收 | 待逐页检查 |
| AsnForm.dc.html | asn/*（需精确核验） | 未验收 | 待逐页检查 |
| AsnList.dc.html | asn/*（需精确核验） | 未验收 | 待逐页检查 |
| AsnPrint.dc.html | asn/*（需精确核验） | 未验收 | 待逐页检查 |
| AuthRecover.dc.html | auth/*（需精确核验） | 未验收 | 待逐页检查 |
| CarrierForm.dc.html | carrier/*（需精确核验） | 未验收 | 待逐页检查 |
| CarrierInvoiceImport.dc.html | 缺失：运费账单导入 | 未验收 | 待逐页检查 |
| CarrierList.dc.html | carrier/index.vue | 部分核对，未验收 | 已对照1000px表宽、方法次行/连接图标、设置操作和隐藏操作表头；实际单行桌面已看；API/文件/定期揽收隔离样本及390px已看；实际多方法数据仍待核 |
| CarrierSteps.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| CartonLabel.dc.html | 待定位（不能视为已实现） | 未验收 | 待逐页检查 |
| CommercialInvoice.dc.html | 待定位（不能视为已实现） | 未验收 | 待逐页检查 |
| Company.dc.html | company/*（需精确核验） | 未验收 | 待逐页检查 |
| CustomsPackingList.dc.html | 待定位（不能视为已实现） | 未验收 | 待逐页检查 |
| CycleCount.dc.html | cyclecount/detail/[id].vue | 部分修复，未验收 | 24px段距、独立盘点打印入口已补；余下差异未完整验收 |
| CycleCountForm.dc.html | cyclecount/*（需精确核验） | 未验收 | 待逐页检查 |
| CycleCountList.dc.html | components/operations/InventoryTaskList.vue | 部分修复，未验收 | 分页12px、进度条紫色、缺失日期占位；已看真实加载截图，字段/交互仍需完整核验 |
| CycleCountSheet.dc.html | cyclecount/print/[id].vue | 部分修复，未验收 | 盲盘/明盘、三语、A4实际单页已核；60行多语长名称隔离打印压力测试保留全部行/重复表头，已修页脚孤页；批号契约等仍未验收 |
| Dashboard.dc.html | dashboard/*（需精确核验） | 未验收 | 待逐页检查 |
| DashboardV2A.dc.html | dashboard/*（需精确核验） | 未验收 | 待逐页检查 |
| DashboardV2A_Dark.dc.html | dashboard/*（需精确核验） | 未验收 | 待逐页检查 |
| DashboardV2B.dc.html | dashboard/*（需精确核验） | 未验收 | 待逐页检查 |
| DashboardV2B_Dark.dc.html | dashboard/*（需精确核验） | 未验收 | 待逐页检查 |
| Delivery.dc.html | delivery/*（需精确核验） | 未验收 | 待逐页检查 |
| DeliveryCustoms.dc.html | delivery/*（需精确核验） | 未验收 | 待逐页检查 |
| DeliveryList.dc.html | delivery/index.vue | 部分修复，未验收 | 配送阶段标签/计数和后端筛选已接通；承运商、计划发货下限筛选；桌面/390px已看，24项相关测试通过；揽收列等仍缺 |
| DeliveryPrint.dc.html | delivery/*（需精确核验） | 未验收 | 待逐页检查 |
| DepartmentList.dc.html | department/*（需精确核验） | 部分修复，未验收 | 760px表宽、24px列距、操作菜单及员工字重已核；实际HR桌面/手机抽屉已看，无保存；长字段/权限状态仍待核 |
| DnForm.dc.html | dn/*（需精确核验） | 未验收 | 待逐页检查 |
| DnList.dc.html | dn/*（需精确核验） | 未验收 | 待逐页检查 |
| FreightReconciliation.dc.html | 缺失：reports/freight.vue | 未验收 | 待逐页检查 |
| GoodsAnalytics.dc.html | goods/*（需精确核验） | 未验收 | 待逐页检查 |
| GoodsDetail.dc.html | goods/*（需精确核验） | 未验收 | 待逐页检查 |
| GoodsExport.dc.html | goods/*（需精确核验） | 未验收 | 待逐页检查 |
| GoodsForm.dc.html | goods/*（需精确核验） | 未验收 | 待逐页检查 |
| GoodsImport.dc.html | goods/*（需精确核验） | 未验收 | 待逐页检查 |
| GoodsLabel.dc.html | goods/label/[id].vue | 未验收 | 基准标签已恢复并截图核对；真实批号接入；自定义尺寸溢出提示已验证；其余语言/边界继续检查 |
| GoodsList.dc.html | goods/*（需精确核验） | 未验收 | 待逐页检查 |
| InboundReport.dc.html | reports/inbound.vue | 部分修复，未验收 | 已补供应商筛选及同范围CSV、实际收货SKU规格覆盖、独立盘点准确率/6月图；桌面与手机字体/链接色/横线已查看，真实空数据与隔离布局样本分开记录；收货差异、上架时效等仍缺，未整页验收  已补逐商品短收/多收/破损汇总、单据计数/首20条链接及图表表格切换；33项文档报表测试通过、布局样本已查；拒收暂无独立字段、上架时效仍缺，不作完整验收 |
| Inventory.dc.html | inventory/*（需精确核验） | 未验收 | 待逐页检查 |
| InventoryAnalytics.dc.html | reports/inventory.vue | 部分修复，未验收 | 真实日终走势断线口径、库龄20px条/13px文字、件数与SKU切换、表格及高库龄Top4后端已补；实际500未知库龄/2SKU桌面手机已查，3项指标测试通过；已查隔离高库龄长名/日期及ABC桌面手机，补ABC底色/参考线/堆叠/表格/分类筛选；曲线含零出库SKU，未分类单列；库龄图表/表格已可筛选下方明细（按FIFO档内正数量），实际未知2SKU和空档已查；原稿跳库存结存入口仍待衔接，实际非空业务验收、库容及效期仍缺 |
| InventoryThresholds.dc.html | inventory/*（需精确核验） | 未验收 | 待逐页检查 |
| InventoryV2A.dc.html | inventory/*（需精确核验） | 未验收 | 待逐页检查 |
| InventoryV2B.dc.html | inventory/*（需精确核验） | 未验收 | 待逐页检查 |
| LocationDetail.dc.html | location/*（需精确核验） | 未验收 | 待逐页检查 |
| LocationForm.dc.html | location/*（需精确核验） | 未验收 | 待逐页检查 |
| LocationLabel.dc.html | location/label/[id].vue | 未验收 | 待逐页检查 |
| LocationList.dc.html | location/index.vue | 部分修复，未验收 | 补240px库区导航/精确筛选及全范围后端计数；顶部换仓清理库区与页码并刷新；字体/14px筛选内距/10px行距/横线已对照，真实3行桌面/390px已看，6项测试通过；地图、批选与占用筛选仍缺 |
| Login.dc.html | auth/login.vue | 未验收 | 待逐页检查 |
| Main.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| MainV2A.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| MainV2B.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| OperatorReport.dc.html | reports/operator.vue | 部分新增，未验收 | 已接真实分权限统计及CSV；新增任务散点/全任务中位数斜线、按人日热力图，25接口/20前端测试；隔离布局样本桌面及窄屏已看；已合并双阶段五卡/按操作人双列及热力图，29接口测试含单阶段权限隔离；已补日格/人员行任务抽屉及后台分页/权限隔离；目的地筛选/前期对比及完整视觉仍缺 |
| OutboundReport.dc.html | reports/outbound.vue | 部分修复，未验收 | 已开放对应读权限入口，期间/类型/前月同期对比（月末及闰日已测）/全范围CSV，按交承运商日期每日聚合，已恢复单据方格/件数柱/周末底色/今天线/单日筛选/图表表格切换；21项后端测试通过，隔离布局截图已查；分布三列及前期竖线已接真实聚合/筛选/CSV，22项后端测试通过，桌面390px隔离布局已查；处理时长分阶段中位数/P90表已接任务完成时间并通过24项后端测试，堆叠图/最慢单据与半年准时率已补并通过25项后端测试；隔离布局已查，补按承运商和币种分组的当前净运费/上期/缺失数据；零金额保留，取消运单排除；异常、账单对账/每kg价格及最终整页视觉仍待补 |
| Packing.dc.html | packing/detail/[id].vue | 部分修复，未验收 | 流程条及24px段距修正；已有加载截图，装箱/打印等仍需完整核验 |
| PackingList.dc.html | packing/*（需精确核验） | 部分修复，未验收 | 复核状态、96x4进度条、实际操作人已校正；最终桌面截图已复核，完成态与全部业务入口仍待核 |
| Patterns.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| PdaPickRoute.dc.html | 缺失：PDA 路线 | 未验收 | 待逐页检查 |
| Picking.dc.html | picking/detail/[id].vue | 部分修复，未验收 | 流程胶囊/8px节点/2px横线与24px段距已对照；打印单和按路线等仍缺 |
| PickingList.dc.html | picking/*（需精确核验） | 部分修复，未验收 | 真实商品种数/件数、打印入口、操作人与时间口径、状态标签已校正；最终桌面已看；打印历史/PDA批量操作仍缺 |
| PickPrint.dc.html | picking/print/[id].vue | 部分新增，未验收 | A4三语单页/60行5页已核；只读无批次标准库位建议/缺货/已拣记录，6项测试通过；完整批次与路线仍缺 |
| PickRoute.dc.html | 待定位（不能视为已实现） | 未验收 | 待逐页检查 |
| Pickup.dc.html | 待定位（不能视为已实现） | 未验收 | 待逐页检查 |
| Print.dc.html | 待定位（不能视为已实现） | 未验收 | 待逐页检查 |
| PutawayQueue.dc.html | 待定位（不能视为已实现） | 未验收 | 待逐页检查 |
| RecipientDetail.dc.html | recipient/*（需精确核验） | 未验收 | 待逐页检查 |
| RecipientForm.dc.html | recipient/*（需精确核验） | 未验收 | 待逐页检查 |
| RecipientList.dc.html | recipient/index.vue | 部分修复，未验收 | 已恢复头像、12px间距、900px表宽/隐藏操作表头；不再把无外部编号误判为手工来源，缺来源明确未记录；实际2行桌面已看；完整来源追踪仍缺 |
| Roles.dc.html | 待定位（不能视为已实现） | 部分修复，未验收 | 已定位components/admin/RoleManager.vue；平台页恢复16px标题、1:2字段及权限矩阵横线，独立作业权限保留；公司自定义角色后端及员工数仍缺，不能视为完整实现 |
| SearchResults.dc.html | search/index.vue | 未验收 | 待逐页检查 |
| Sidebar.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| SortingDetail.dc.html | sorting/*（需精确核验） | 未验收 | 待逐页检查 |
| SortingList.dc.html | sorting/*（需精确核验） | 未验收 | 待逐页检查 |
| StaffForm.dc.html | components/staff/StaffForm.vue | 部分修复，未验收 | 已对照密码分隔线/生成按钮、6px角色卡片/8px间距、账号启用/授权说明；实际编辑及390px已看、生成/隐藏有效；发送重设邮件与完整状态待核 |
| StaffList.dc.html | staff/index.vue | 部分修复，未验收 | 已校正姓名次行职位/工号、邮箱电话层次、12px头像间距、920px表宽、角色标签；补精确角色筛选及公司隔离测试；浏览器桌面实际数据已看、角色筛选返回1人；长字段和所有状态仍待核 |
| StockLedger.dc.html | inventory/ledger.vue | 未验收 | 已补期间汇总、批号分组、走势、批号列、类别结存；已修筛选与时区日期；按用户要求发货才计出库；已补权限控制的真实商品搜索/选择/清除及深链名称，顶部换仓重置页码；实际G001桌面/390px已看；紧凑筛选及完整多状态视觉仍待核验 |
| StockSummaryReport.dc.html | reports/stock-summary.vue | 部分修复，未验收 | 已补全范围汇总卡及变动拆分/流水链接；21项库存接口测试通过；已补分类/品牌分组、分页展开和两层明细表头；已补全范围CSV导出；已对照补期间下拉、本月/上月/按月/自定义并浏览器核验；已恢复紧凑筛选条，分类/品牌读取权限内真实分组选项，支持未设置与分页；已补期初末库存类别拆分及流水链接，并补CSV分类列和分组汇总一致性（含已拣/已打包，发货计出库）；已校正接口时区及明细跳转时间边界；完整视觉验收待补 |
| SupplierForm.dc.html | supplier/*（需精确核验） | 未验收 | 待逐页检查 |
| SupplierList.dc.html | supplier/index.vue | 部分核对，未验收 | 已校正12px头像间距、操作表头及无到货记录状态；实际2行桌面已看；完整多状态/权限视觉仍待核 |
| Tokens.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| TokensV2A.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| TokensV2B.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| Topbar.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| TopbarSpec.dc.html | 共用组件/设计规范，需映射核验 | 未验收 | 待逐页检查 |
| WarehouseDetail.dc.html | warehouse/*（需精确核验） | 未验收 | 待逐页检查 |
| WarehouseForm.dc.html | warehouse/*（需精确核验） | 未验收 | 待逐页检查 |
| WarehouseLayout.dc.html | warehouse/*（需精确核验） | 未验收 | 待逐页检查 |
| WarehouseList.dc.html | warehouse/*（需精确核验） | 未验收 | 待逐页检查 |
| WarehouseMap.dc.html | warehouse/*（需精确核验） | 未验收 | 待逐页检查 |
| WebhookLogs.dc.html | webhook-logs/index.vue | 部分修复，未验收 | 补读取错误重试/防旧响应、次行重试时间、20px表边距、目标系统筛选（权限控制及分页全量选项）；布局样本列表/抽屉已看，不触发推送；单据列/时间筛选仍缺 |

## 执行记录

- 2026-10-26：全量设计稿已列入清单，无页面因存在路由而标为完成。已建立当前任务每小时自动跟进，完成后暂停。

## 用户业务口径覆盖设计稿（2026-10-26）
- **拣货不计正式出库，发货完成才计出库。** 默认仓库结存包含已拣货、已打包，发货后在途不计入。优先用户指示，不得恢复 StockLedger 原稿的拣货出库口径。样式继续以原稿为准。
- 流水新增期间汇总、批号分组及走势图，修复类别结存跨库位统计，仍须完整验收；其他页面仍未验收。

## 用户交互规则覆盖设计稿（2026-10-26）
- 列表、报表、分析统一使用顶部仓库选择，页面内不重复提供仓库筛选器。顶部切换须刷新范围，旧URL仓库参数不得覆盖顶部；切换清除旧页码。业务表单中的目标仓库、单据所属仓库和仓库授权字段保留。
- 已清理收发存汇总、库存分析、入库分析、出库分析、历史库存、商品分析的重复选择器；单仓分析在全部仓库状态提示从顶部选仓。

## 用户视觉方向更新（2026-10-28）
- 保持现有布局、控件位置与交互流程，允许在原字号和字体体系上做专业视觉美化；不再机械保留线稿感。
- 已修复拣货详情库位文字/选择按钮贴边：12px间距、500字重编号、13px浅紫行内操作，禁用/焦点状态保留。
- 公共卡片轻阴影、表头浅底/文字层次、行悬停与直接相邻操作间距已更新。桌面检查拣货、商品、收货通知、收货分析；390px拣货检查无页面溢出，选择库位弹窗打开/取消通过。收货分析本次为空数据，仅验空态外观，未据此验收完整报表。
- 其余页面逐页视觉验收仍未完成。

## 2026-10-28 最新视觉决定
- 用户放弃新视觉提案，保持当前已实现样式；生成的设计稿不作为后续实施依据。
- 淡网格背景试用后已按用户要求移除，恢复纯色背景。其他样式及交互保持。

- 2026-10-28：收货分析修复接收未分拣被误算短收的问题。差异仅统计数量已确认的completed ASN，接收日期/准时率仍按接收事件；35项报表测试通过，未据此声明全页面验收。

- 2026-10-28：收货规格覆盖率同步限定数量已确认的ASN；37项报表回归通过，保持现有页面样式。

- 2026-10-28：PICK-1已有数据中文A4打印样本实际PDF渲染检查通过（1页，条码/表格/签名完整）；长列表、多语言及实物扫码仍未据此验收。盘点/标签/打印/仓库/批号42项后端回归通过。

- 2026-10-28：PICK-1英文/日文A4打印各1页已实际渲染查看，表头换行、签名、条码完整；单行样本三语言检查完成，长列表及实物扫码仍待验收。
