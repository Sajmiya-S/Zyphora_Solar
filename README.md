# ☀️ Zyphora Solar ERP

A **modular Django-based ERP system for solar companies** designed to manage the complete lifecycle of solar projects — from lead generation to installation, licensing, procurement, finance, and final project completion.

Built for **solar EPC companies, contractors, and startups**, this system replaces manual tracking with a structured, scalable workflow.

---

## 🌍 Problem Statement

Solar businesses often struggle with:

* ❌ Disconnected systems for CRM, projects, and finance
* ❌ Poor visibility of installation and licensing progress
* ❌ Delays in approvals (KSEB, MNRE)
* ❌ Manual coordination between teams

---

## 💡 Solution

Zyphora Solar ERP provides a **centralized, role-based platform** that:

* Tracks projects across all phases
* Connects CRM → Projects → Procurement → Finance
* Manages licensing workflows step-by-step
* Improves accountability and team coordination

---

## 🚀 Core Modules

### 🔹 CRM (Customer Management)

* Lead tracking
* Customer data management
* Conversion to projects

---

### 🔹 Project Management

* Full lifecycle tracking:

  * Installation
  * Licensing
  * Energisation
  * Completion
* Status-based workflow
* Engineer & team assignment

---

### 🔹 Installation Module

* Structure work tracking
* Electrical work tracking
* Task completion updates

---

### 🔹 Licensing Module

Structured government approval tracking:

* Preparation
* KSEB Processing
* MNRE Processing
* Subsidy & Closure

✔ Task-based workflow
✔ Document uploads
✔ Role-based access

---

### 🔹 Procurement Module

* Material requirement tracking
* Purchase coordination
* Vendor workflow (extendable)

---

### 🔹 Finance Module

* Project-related financial tracking
* Payment management (extendable)

---

### 🔹 Public Module

* Landing pages / website integration
* Project showcase capability

---

## 🔐 Role-Based Access

| Role       | Responsibilities       |
| ---------- | ---------------------- |
| Admin      | Full system control    |
| Engineer   | Installation execution |
| Liaison    | Licensing & approvals  |
| Accountant | Finance & Expense      |
| Staff      | Installation tasks     |


---

## 🛠️ Tech Stack

* **Backend**: Django (Python)
* **Frontend**: HTML, CSS, Bootstrap
* **Database**: SQLite (Development)
* **Architecture**: Modular Django Apps

---

## 📂 Project Structure

```
Zyphora_Solar/
│── users/          # Authentication & roles
│── crm/            # Lead & customer management
│── projects/       # Core project lifecycle
│── procurement/    # Materials & purchasing
│── finance/        # Financial tracking
│── public/         # Website / landing pages
│── templates/
│── static/
│── manage.py
```

---

## ⚙️ Installation

```bash
# Clone repository
git clone https://github.com/Sajmiya-S/Zyphora_Solar.git
cd Zyphora_Solar

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Run server
python manage.py runserver
```

---

## 📊 Workflow Overview

1. Lead Created (CRM)
2. Converted to Project
3. Installation Phase
4. Licensing Phase
5. Procurement & Finance Tracking
6. Energisation
7. Project Completed
