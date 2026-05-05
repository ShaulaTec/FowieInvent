# FOWIEINVENT — SYSTEM REQUIREMENTS

An open-source project by ShaulaTec  

**Version:** 0.2  
**Date:** April 2026  

## Frontend Repo https://github.com/YalukR/FowieInvent_fe.git

---

## 1. OVERVIEW

### What is it?
FowieInvent is a modular, scalable, multi-tenant inventory management system. It is designed as a modern alternative to spreadsheets and paper-based tracking, and serves as a foundational architecture for a future full ERP system.

### Purpose
To help small and medium-sized businesses improve inventory control and operational efficiency.

### Motivation
Many existing solutions are financially inaccessible or overly complex for small businesses. FowieInvent aims to provide a flexible and accessible open-source alternative.

### Technology
- **Backend:** Python / Django REST Framework  
- **Frontend:** Angular + PrimeNG  
- **Architecture:** Decoupled frontend and backend  
- **License:** AGPL (fully open source)  

---

## 2. MODULAR ARCHITECTURE

FowieInvent is designed as part of a scalable ecosystem composed of independent modules:

- **Inventory** (current implementation)  
- **POS (Point of Sale)** (planned)  
- **Personnel Management** (planned)  

Each module is designed to operate independently or in combination.

### Integration rules (design-level):
- Inventory + POS: sales reduce stock automatically  
- Inventory + Personnel: movements track the responsible user  
- POS + Personnel: sales track the responsible user  
- POS can operate without inventory (no stock deduction)  
- Personnel module is independent  

This modularity must be considered in database design and business logic, even if only the inventory module is currently implemented.

---

## 3. FUNCTIONAL REQUIREMENTS

### 3.1 MULTI-TENANCY
- **FR01:** Each tenant represents an isolated business entity  
- **FR02:** No tenant can access data from another tenant  
- **FR03:** Tenant lifecycle states: active, inactive, suspended  

### 3.2 USERS
- **FR04:** Each user belongs to exactly one tenant  
- **FR05:** Users are assigned a single role  
- **FR06:** The system must support configurable limits per tenant (e.g., users, products, categories)  

### 3.3 ROLES AND PERMISSIONS (DYNAMIC RBAC)
- **FR07:** Tenants can create custom roles  
- **FR08:** Permissions are predefined by the system and cannot be modified by tenants  
- **FR09:** Permissions are organized per module  
- **FR10:** Tenants only see permissions for enabled modules  
- **FR11:** Permission validation must always be enforced in the backend  

#### Initial inventory permissions:
- view_inventory  
- edit_product  
- delete_product  
- register_movement  
- view_history  
- generate_report  
- manage_categories  
- manage_users  
- manage_roles  

---

### 3.4 PRODUCT MANAGEMENT
- **FR12:** Products must include: name, category, quantity, unit, and creation date  
- **FR13:** Products are organized by tenant-defined categories  
- **FR14:** Product deletion must be logical (soft delete)  

---

### 3.5 INVENTORY MOVEMENTS
- **FR15:** The system must record stock entries and exits  
- **FR16:** Each movement includes: product, quantity, timestamp, and user  
- **FR17:** Movement history must be queryable per product  

---

### 3.6 DASHBOARD
- **FR18:** The system must provide a dashboard displaying:
  - Stagnant products (no movement in X days)  
  - Low-stock products  
  - Active modules  

---

### 3.7 REPORTS
- **FR19:** The system must generate basic inventory reports  
- **FR20:** Reports must be exportable as PDF  
- **FR21:** Report access is controlled by permissions  

---

### 3.8 NOTIFICATIONS
- **FR22:** The system must generate notifications for relevant events:
  - Low stock  
  - System-related alerts  
- **FR23:** Notifications must indicate their associated module  

---

## 4. NON-FUNCTIONAL REQUIREMENTS

### 4.1 SECURITY
- **NFR01:** Strict tenant data isolation  
- **NFR02:** Secure password hashing (bcrypt or equivalent)  
- **NFR03:** Session expiration after inactivity  
- **NFR04:** Protection against SQL Injection, XSS, and CSRF  
- **NFR05:** Backend-enforced authorization  

---

### 4.2 PERFORMANCE
- **NFR06:** Response time under 2 seconds for common operations  
- **NFR07:** Support at least 30 concurrent users without significant degradation  

---

### 4.3 AVAILABILITY
- **NFR08:** Target availability of 99%  
- **NFR09:** Recovery time under 1 hour  

---

### 4.4 SCALABILITY
- **NFR10:** Must support growth in number of tenants without structural redesign  
- **NFR11:** Limits and modules must be configurable  
- **NFR12:** Must allow integration of future modules without breaking existing structure  
- **NFR13:** RBAC must scale by adding permissions, not redesigning roles  

---

### 4.5 USABILITY
- **NFR14:** Usable by non-technical users  
- **NFR15:** Responsive design (desktop and mobile)  

---

### 4.6 MAINTAINABILITY
- **NFR16:** Clear coding conventions and documentation  
- **NFR17:** Automated database backups (recommended daily)  

---

### 4.7 COMPATIBILITY
- **NFR18:** Compatible with modern browsers (Chrome, Firefox, Edge, Safari)  

---

## 5. SCOPE LIMITATIONS

- No electronic invoicing support  
- No POS module (yet)  
- No personnel module (yet)  
- No barcode scanner integration (yet)  
- No payroll or supplier payment management  

---

## 6. GLOSSARY

- **Tenant:** Isolated business account  
- **Module:** Independent functional unit  
- **ERP:** Combination of all modules  
- **RBAC:** Role-Based Access Control  
- **Permission:** System-defined action assigned to roles  
- **Soft delete:** Logical deletion without removing data  
- **Minimum stock:** Threshold for alerts  

---

## License

This software is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

You are free to use, modify, and distribute this software under the terms of the license. Any modifications or derivative works must also be distributed under the same license.

## FowieInvent

An open-source system by ShaulaTec  
*Sic parvis magna.*  
