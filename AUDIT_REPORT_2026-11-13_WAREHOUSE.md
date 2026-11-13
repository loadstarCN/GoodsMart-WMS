# 仓库作业功能完整性审核

日期：2026-11-13。范围：当前工作区 WMS Backend 的模型、API、库存记账与作业服务，交叉检查 Web、PDA 和 Station 的相关入口。本轮按仓库收货、退货、库存控制、盘点、移库与出库闭环审核，不重复上一轮批发站接口问题。

本轮确认 6 项问题：3 项直接影响作业或库存正确性，3 项仓库管理功能缺口。随后按“挨个完成”逐项实现。下文保留最初审核证据；修复后的流程、权限、接口和旧单据升级处理见 [仓库作业说明](GoodsMart-WMS-Backend/doc/warehouse-workflows.md)。开始审核时已有的工作区改动保持保留。

实现范围：盘点冻结、冲突拦截及关联复盘；正常/破损/退货库存分别预占退供；批次冻结与审计；跨仓调出、在途、分批接收和差异处理；原销售单退货授权、隔离实收、双人处理审核及退供回退。配套 Web 页面、PDA 按用途拣货、三语文案、库存流水关联导航和两版数据库迁移已加入。

## 1. P1：缺少盘点期间的库存移动控制或盘点时点校验

**已通过真实 Flask API 的隔离测试复现。** 库位 A 账实各 10 件，开始盘点，工作人员数到 10 件；保存前另一人移 2 件到 B。移库成功，保存实盘 10 时系统重新取 A 的账面数 8，生成盘盈 2。另一用户审批并完成调整后，A=10、B=2，账面总库存变成 12，实物总数仍为 10。

证据：[录入时读取当前库存](GoodsMart-WMS-Backend/warehouse/cyclecount/services.py:62)、[移库直接记账](GoodsMart-WMS-Backend/warehouse/transfer/services.py:152)、[按差额执行调整](GoodsMart-WMS-Backend/warehouse/adjustment/services.py:415)。

缺的不是单次请求的数据库锁，而是从实际点数到提交结果之间的作业控制。应支持盘点范围冻结，或者记录实际盘点时点、库存版本与期间变动；发生冲突要求重新确认，不能直接把移动算成盘盈亏。现场纸质盘点后集中录入尤其容易触发。

验收：点数与保存之间发生上架、移库、拣货时，阻止冲突或可靠核算，不产生虚假差异；保存后发生的合法移动也不能被后续调整覆盖。

## 2. P1：同一库存可以被不同盘点单重复调整

**已通过隔离 API 测试复现。** 同一商品、库位、批次账面 10，两张盘点单均录入实际 9，在任一调整入账前各生成 -1 的调整单；两单均可审批、完成，最终账面 8。也就是说，用第二张盘点单做复核，可能再次扣掉同一笔损失。

现有重复校验只覆盖一张盘点单内部；生成调整时，只检查当前盘点单是否已生成调整，没有跨盘点单的范围重叠或差异版本检查。

证据：[单内唯一性检查](GoodsMart-WMS-Backend/warehouse/cyclecount/services.py:33)、[仅按 cyclecount_id 查重](GoodsMart-WMS-Backend/warehouse/adjustment/services.py:502)、[累加差额](GoodsMart-WMS-Backend/warehouse/adjustment/services.py:415)。

应对未结算盘点范围建立占用或冲突校验，并提供复盘关联：初盘、复盘形成一份最终差异，而不是两份可独立过账的差异。跨单过账还应检查是否已有其他盘点调整消化同一差异。

验收：上述两次实盘最终只能形成一次 -1；同范围的下一轮独立盘点在前轮结清后仍能正常开展。

## 3. P1：破损退供应商有单据类型，但出库路径不可用

**已通过两项隔离测试确认。** `damage_to_supplier` 使用普通销售出库的可售库存校验。只有破损库存 5、可售库存 0 时，退供 5 件在建单阶段即返回 `400 / 16032`。另一个测试隔离拣货规则：即使单据已进入拣货，类型为破损退供，选择破损库位仍返回 `400 / 16162`。

证据：[DN 类型](GoodsMart-WMS-Backend/warehouse/dn/models.py:58)、[统一按可售库存预占](GoodsMart-WMS-Backend/warehouse/dn/services.py:137)、[统一限制 standard 库位](GoodsMart-WMS-Backend/warehouse/picking/services.py:284)。

当前不能在保持“破损品”属性的情况下完成退供。把货先移回正常库位会改变可售口径，不应成为必经路径。过期品退供也需要与普通发货的效期准入区分。

应按出库用途区分可用库存、预占、允许拣货的库存状态和批次准入，同时保留供应商关联、原因及责任记录。

验收：普通销售继续禁止破损品；破损退供从破损库存预占、拣货、打包、发运，全程不增加可售库存，并正确释放取消的预占。

## 4. P1：批次冻结只有底层字段与校验，缺少操作闭环

模型已有 `active / hold`，可售计算和发货校验也读取批次状态；但创建接口固定 `active`，修改接口只接受日期纠正，没有冻结、解冻及原因审计入口。对现有批次提交 `status=hold` 在隔离测试中返回 400，状态保持 active。后端相关路由与前端检索未发现其他批次冻结入口。

证据：[状态字段](GoodsMart-WMS-Backend/warehouse/stock/models.py:83)、[创建字段白名单](GoodsMart-WMS-Backend/warehouse/goods/lots.py:108)、[修改只允许日期纠正](GoodsMart-WMS-Backend/warehouse/goods/lots.py:157)、[冻结库存排除逻辑](GoodsMart-WMS-Backend/warehouse/stock/lot_policy.py:77)、[发货复核](GoodsMart-WMS-Backend/warehouse/stock/lots.py:45)。

收到批次质量异常通知时，仓管无法通过正常入口立即冻结整批；逐库位搬到退货/破损区也不能替代对已拣、已打包货物的批次控制。

应补冻结/解冻权限、原因、操作历史、影响库存与待出库单查询，并明确已有预占及已拣/已打包单据如何暂停或恢复。不能仅给字段增加一个编辑框。

验收：冻结阻止新销售预占及后续发货，展示受影响单据；解冻有记录，且不擅自消除效期等其他限制。

## 5. P2：跨仓调拨缺少调出—在途—调入关联

**代码路径确认，未执行完整跨仓物流仿真。** ASN 和 DN 都有 `transfer` 类型，但现有移库服务明确要求来源、目标在同一仓库。ASN/DN 模型与建单路径未提供统一调拨主单、对方仓库、关联调出/调入明细及收货核销机制；类型目前主要作为分类字段使用。

证据：[移库仅限同仓](GoodsMart-WMS-Backend/warehouse/transfer/services.py:119)、[ASN 类型及字段](GoodsMart-WMS-Backend/warehouse/asn/models.py:28)、[DN 类型及字段](GoodsMart-WMS-Backend/warehouse/dn/models.py:58)、[移库记录模型](GoodsMart-WMS-Backend/warehouse/transfer/models.py:4)。

实际 A 仓发 10、B 仓收 8 时，只能人工维护两端单据，系统不能依靠一条调拨业务核销已发、在途、实收和差异。现有普通发货在途库存不能替代跨仓收货核销。

应增加调拨主单与双端关联，支持分批发收、原批次延续、短收/破损确认、撤销限制及在途账龄。单仓经营可以后排，多仓经营应前置。

验收：发 10、收 8 后，两端库存和剩余 2 件在途/差异可核对；重复接收不得重复增库存，来源与目标批次一致。

## 6. P2：客户退货缺少来源核对与处置记录

**已通过隔离 API 测试复现现有路径。** 新商品没有原出库记录，也可以仅凭供应商 ID 创建 `return_from_customer`，经过普通分拣将 3 件标为良品并直接上标准库位，最终可售库存增加 3。测试未绕过正常收货、分拣和上架服务。

证据：[客户退货仍要求 supplier_id](GoodsMart-WMS-Backend/warehouse/asn/services.py:326)、[ASN 数据结构](GoodsMart-WMS-Backend/warehouse/asn/models.py:28)、[完成收货按普通良品/破损记账](GoodsMart-WMS-Backend/warehouse/asn/services.py:700)。

这里并非“完全不能退货”，而是缺少原 DN/客户/原批次关联、累计可退数量、退货原因及明确处置结论。系统无法校验是否重复退、超量退，也没有将返库待检、可再售、返修、报废、退供形成独立处置链。普通分拣的良品/破损分类不能覆盖全部退货处置。

应增加退货关联及处置流程；允许无原单退货时，作为有原因、权限和审计的例外处理，不宜强制所有退货必须找到原单。

验收：已发 5、已退 3 后再次退 3 能提示超额；无原单退货走例外流程；未确认可再售前不进入销售可用库存。

## 最初审核的验证边界（修复前）

已确认存在批次效期策略、收货破损/拒收、部分拣货/少装、取消回库、盘点补录、盲盘打印及调整审批，不将其笼统列为缺失。拣货面补货任务、多计量单位和序列号等场景，本轮未完成足够验证，不计入确认问题数。

本轮使用仓库现有 venv、真实 Flask 路由、SQLite 隔离测试库和 fakeredis。新增的 6 项诊断用例全部通过，含测试结束后的库存行表/流水对账；这里的“通过”表示成功确认上述现状，不表示缺陷已修复。盘点案例中账面、缓存和流水仍相互一致，因此仅靠技术对账无法识别与实物的偏差。

- [诊断脚本](logs/audit_warehouse_operations_20261113.py)
- [运行结果](logs/audit-warehouse-operations-20261113.log)

复现命令（Backend 目录）：

```powershell
.\venv\Scripts\python.exe -m pytest -c pytest.ini -p tests.conftest ..\logs\audit_warehouse_operations_20261113.py -q -s --tb=short
```

没有执行生产数据操作、真实承运商请求、PDA 真机验收或 PostgreSQL 并发压力测试。本轮两个盘点问题使用确定的顺序交错即可触发，不依赖数据库并发竞争。

## 逐项实现后的验证

六项均已实现，新增功能与旧作业入口共用库存记账、权限和事务框架，详情见文首流程说明。

- 后端完整回归：1788 passed、3 skipped；这 3 项依赖 PostgreSQL 行锁的测试另在 PostgreSQL 中运行通过。
- PostgreSQL 库存、流水矩阵及并发回归：55 passed；补录盘点、历史迁移和退货回退追加复验：20 passed。
- 盘点补录改为先冻结后录入后，相关盘点、权限及迁移回归：48 passed、1 skipped（该并发项已在 PostgreSQL 通过）。
- Web：42 项回归通过，类型检查与构建通过；PDA：13 项拣货相关回归通过，类型检查通过。
- PostgreSQL 从原始版本升级成功，既有样本行保留、库存对账通过；两版新增迁移分别及连续降级/升级后，数据库结构与模型一致。

主要结果日志保存在 `logs/warehouse-backend-final.log`、`logs/warehouse-pg-final.log`、`logs/warehouse-pg-closing.log`、`logs/warehouse-count-final.log`、`logs/warehouse-web-tests.log`、`logs/warehouse-web-build.log` 与 `logs/warehouse-migration-*.log`。

以上验证在本地隔离数据上完成，未操作业务数据库、真实承运商或 PDA 真机。上线前需执行新增迁移，并按流程说明处理未关联的旧调拨、旧客户退货单及未受保护的历史盘点。
