# GoodsMart WMS - 开源仓库管理系统

[https://img.shields.io/badge/License-AGPL%20v3-blue.svg](https://www.gnu.org/licenses/agpl-3.0)
[https://img.shields.io/badge/Backend-Flask-green.svg](https://flask.palletsprojects.com/)
[https://img.shields.io/badge/Frontend-Nuxt.js-00DC82.svg](https://nuxt.com/)
[https://img.shields.io/badge/Database-PostgreSQL-336791.svg](https://www.postgresql.org/)

**GoodsMart WMS** 是一个现代化、功能完整的开源仓库管理系统，专为中小型企业设计，提供专业的仓库运营管理解决方案。

## 🎯 项目特色

- **🔄 全栈解决方案** - 包含前后端完整代码，开箱即用
- **📱 多端支持** - Web端 + 移动端（开发中）
- **🔧 模块化设计** - 易于扩展和定制
- **🌍 国际化** - 多语言支持（中/英/日)，全球可用

## 🏗️ 系统架构

```
GoodsMart WMS 生态系统
├── 🖥️ GoodsMart-WMS-Backend    - Flask API 后端服务
├── 🌐 GoodsMart-WMS-Web       - Nuxt.js Web 前端
├── 📱 GoodsMart-WMS-Mobile    - 移动端（即将推出）
└── 📚 GoodsMart-WMS-Docs      - 完整文档
```

## ✨ 核心功能

### 📦 库存管理
- **实时库存监控** - 多维度库存查询和预警
- **批次管理** - 商品批次、序列号跟踪管理
- **库存调整** - 库存盘点、报损、调拨功能
- **库存预警** - 低库存预警和过期提醒

### 🏢 仓库运营
- **多仓库管理** - 支持多个仓库的统一管理
- **库位管理** - 精细化库位管理和优化
- **入库管理** - 采购入库、调拨入库、退货入库
- **出库管理** - 销售出库、调拨出库、领用出库

### 🔍 商品管理
- **商品信息** - 完整的商品属性管理
- **分类管理** - 多级商品分类体系
- **条码管理** - 支持多种条码格式
- **供应商管理** - 供应商信息维护

### 📊 报表分析
- **库存报表** - 实时库存状态报表
- **出入库报表** - 出入库流水统计
- **盘点报表** - 库存差异分析
- **操作日志** - 完整的操作审计跟踪

### 👥 权限控制
- **角色权限** - 多角色权限管理系统
- **操作权限** - 细粒度功能权限控制
- **数据权限** - 按仓库划分数据权限
- **安全审计** - 操作日志和安全审计

## 🚀 快速开始

### 手动安装
```bash
# 1. 部署后端
git clone https://github.com/yourusername/GoodsMart-WMS-Backend.git
cd GoodsMart-WMS-Backend
# 按照后端README操作

# 2. 部署前端  
git clone https://github.com/yourusername/GoodsMart-WMS-Web.git
cd GoodsMart-WMS-Web
# 按照前端README操作
```

## 📋 技术栈

| 组件 | 技术选择 | 说明 |
|------|----------|------|
| **后端API** | Flask + SQLAlchemy | RESTful API 服务 |
| **前端Web** | Nuxt.js 4 | 现代化前端框架 |
| **数据库** | PostgreSQL | 企业级关系数据库 |
| **缓存** | Redis | 高性能缓存服务 |
| **任务队列** | Celery | 异步任务处理 |

## 🌟 适用场景

- **🏭 制造企业** - 原材料和成品仓库管理
- **🛒 零售行业** - 商品库存和门店配送管理  
- **📚 图书档案** - 图书资料仓储管理
- **🏥 医疗行业** - 药品和医疗器械库存管理
- **🚚 物流仓储** - 第三方仓储服务管理

## 🎯 设计理念

GoodsMart WMS 专注于纯粹的仓库管理需求，提供：
- **专业化** - 深度优化的仓库作业流程
- **易用性** - 直观的用户界面和操作体验
- **可靠性** - 稳定可靠的数据管理和事务处理
- **扩展性** - 模块化设计便于功能扩展

## 🤝 参与贡献

我们欢迎各种形式的贡献！请参阅：

- docs/CONTRIBUTING.md - 如何参与开发
- docs/CODE_STYLE.md - 代码编写规范
- docs/ROADMAP.md - 项目发展计划

## 📞 支持与交流

- 📖 https://github.com/loadstarCN/GoodsMart-WMS-Docs
- 🐛 https://github.com/loadstarCN/GoodsMart-WMS/issues
- 💬 https://github.com/loadstarCN/GoodsMart-WMS/discussions
- 📧 邮箱支持: goodsmart@goodsmart.jp

## 📄 许可证

本项目采用 **GNU Affero General Public License v3.0** 许可证，详情请查看 LICENSE 文件。

> 💡 请注意：AGPLv3 许可证要求所有修改和衍生作品必须开源。如需商业使用许可，请联系我们获取商业授权。

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者、测试者和文档编写者。特别感谢：

- 开源社区提供的优秀工具和库
- 早期用户提供的宝贵反馈
- 贡献者们的辛勤工作

---

**开始使用 GoodsMart WMS，体验专业级的仓库管理解决方案！** 🚀