# GoodsMart WMS - Open Source Warehouse Management System  

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Backend - Flask](https://img.shields.io/badge/Backend-Flask-green.svg)](https://flask.palletsprojects.com/)
[![Frontend - Nuxt.js](https://img.shields.io/badge/Frontend-Nuxt.js-00DC82.svg)](https://nuxt.com/)
[![Database - PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)](https://www.postgresql.org/)

[中文 README](./README-zh.md)

**GoodsMart WMS** is a modern, fully-featured open-source warehouse management system designed for small and medium-sized enterprises, offering a professional solution for warehouse operations management.  

## 🎯 Key Features  

- **🔄 Full-Stack Solution** – Includes complete frontend and backend code, ready to use out-of-the-box  
- **📱 Multi-Platform Support** – Web + Mobile (in development)  
- **🔧 Modular Design** – Easy to extend and customize  
- **🌍 Internationalization** – Multi-language support (CN/EN/JP), globally applicable  

## 🏗️ System Architecture  

```
GoodsMart WMS Ecosystem  
├── 🖥️ GoodsMart-WMS-Backend    – Flask API Backend Service  
├── 🌐 GoodsMart-WMS-Web       – Nuxt.js Web Frontend  
├── 📱 GoodsMart-WMS-Mobile    – Mobile App (Coming Soon)  
└── 📚 GoodsMart-WMS-Docs      – Comprehensive Documentation  
```

## ✨ Core Features  

### 📦 Inventory Management  
- **Real-Time Inventory Monitoring** – Multi-dimensional inventory queries and alerts  
- **Batch Management** – Product batch and serial number tracking  
- **Inventory Adjustments** – Stocktaking, loss reporting, and transfers  
- **Inventory Alerts** – Low stock warnings and expiration reminders  

### 🏢 Warehouse Operations  
- **Multi-Warehouse Management** – Unified management of multiple warehouses  
- **Location Management** – Detailed storage location management and optimization  
- **Inbound Management** – Purchase receiving, transfer receiving, and return receiving  
- **Outbound Management** – Sales shipping, transfer shipping, and requisition shipping  

### 🔍 Product Management  
- **Product Information** – Complete product attribute management  
- **Category Management** – Multi-level product classification system  
- **Barcode Management** – Supports multiple barcode formats  
- **Supplier Management** – Supplier information maintenance  

### 📊 Reporting & Analytics  
- **Inventory Reports** – Real-time inventory status reports  
- **Inbound/Outbound Reports** – Inbound and outbound transaction statistics  
- **Stocktake Reports** – Inventory variance analysis  
- **Operation Logs** – Comprehensive operation audit trails  

### 👥 Access Control  
- **Role-Based Permissions** – Multi-role permission management system  
- **Operation Permissions** – Fine-grained functional permission control  
- **Data Permissions** – Data access restricted by warehouse  
- **Security Auditing** – Operation logs and security audits  

## 🚀 Quick Start  

### Manual Installation  
```bash  
# 1. Deploy the backend  
git clone https://github.com/yourusername/GoodsMart-WMS-Backend.git  
cd GoodsMart-WMS-Backend  
# Follow the backend README instructions  

# 2. Deploy the frontend  
git clone https://github.com/yourusername/GoodsMart-WMS-Web.git  
cd GoodsMart-WMS-Web  
# Follow the frontend README instructions  
```  

## 📋 Tech Stack  

| Component         | Technology          | Description                     |  
|-------------------|---------------------|---------------------------------|  
| **Backend API**   | Flask + SQLAlchemy  | RESTful API service             |  
| **Frontend Web**  | Nuxt.js 4           | Modern frontend framework       |  
| **Database**      | PostgreSQL          | Enterprise relational database  |  
| **Caching**       | Redis               | High-performance caching        |  
| **Task Queue**    | Celery              | Asynchronous task processing    |  

## 🌟 Use Cases  

- **🏭 Manufacturing** – Raw material and finished goods warehouse management  
- **🛒 Retail** – Product inventory and store distribution management  
- **📚 Libraries & Archives** – Book and archival material storage management  
- **🏥 Healthcare** – Medicine and medical equipment inventory management  
- **🚚 Logistics & Warehousing** – Third-party warehousing services management  

## 🎯 Design Philosophy  

GoodsMart WMS focuses on pure warehouse management needs, providing:  
- **Professionalism** – Deeply optimized warehouse operation workflows  
- **Usability** – Intuitive user interface and smooth operation experience  
- **Reliability** – Stable and reliable data management and transaction processing  
- **Extensibility** – Modular design for easy functional expansion  

## 🤝 Contributing  

We welcome contributions in all forms! Please refer to:  

- docs/CONTRIBUTING.md – How to participate in development  
- docs/CODE_STYLE.md – Code style guidelines  
- docs/ROADMAP.md – Project development plan  

## 📞 Support & Communication  

- 📖 https://github.com/loadstarCN/GoodsMart-WMS-Docs  
- 🐛 https://github.com/loadstarCN/GoodsMart-WMS/issues  
- 💬 https://github.com/loadstarCN/GoodsMart-WMS/discussions  
- 📧 Email Support: goodsmart@goodsmart.jp  

## 📄 License  

This project is licensed under the **GNU Affero General Public License v3.0**. For details, please see the LICENSE file.  

> 💡 Note: The AGPLv3 license requires that all modifications and derivative works must be open source. For commercial licensing, please contact us for commercial authorization.  

## 🙏 Acknowledgments  

Thanks to all the developers, testers, and documentation writers who have contributed to this project. Special thanks to:  

- The open-source community for providing excellent tools and libraries  
- Early users for their valuable feedback  
- Contributors for their hard work  

---

**Get started with GoodsMart WMS and experience a professional-grade warehouse management solution!** 🚀