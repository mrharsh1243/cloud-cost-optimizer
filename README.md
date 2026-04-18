# Cloud Cost Optimizer: FinOps Automation Engine

> **Automated, read-only AWS waste detection system for modern FinOps teams.**

Cloud Cost Optimizer is a high-performance SaaS backend designed to identify and quantify infrastructure waste across multiple AWS accounts and regions. Built with a security-first approach, it provides a comprehensive inventory and applies modular, rule-based logic to detect idle or unutilized resources—helping organizations reduce their cloud bill by up to 30%.

---

## 🚀 Project Status: Day 16/30 (MVP Hardening)
The core architecture and scanning engine are fully operational.
- [x] **Week 1-2 Core Complete**: FastAPI backend, modular AWS scanners, and SQLite persistence.
- [x] **Advanced Waste Detection**: Logic for 12 key waste rules across 7 AWS services.
- [x] **Dynamic Configuration**: Rule-based system with database-driven thresholds and toggles.

---

## ✨ Key Features
*   **Global Infrastructure Sync**: Scans all AWS regions automatically to find hidden resources.
*   **Modular Waste Engine**: Independent detection logic for EC2, RDS, EBS, ELB, NAT Gateways, and more.
*   **Security-First Architecture**: Strictly **Read-Only**. Uses AWS STS `AssumeRole` to access infrastructure without storing long-term customer secrets.
*   **Rule Configuration API**: Dynamically enable/disable rules or adjust waste thresholds (e.g., CPU % or idle days) via API.
*   **Unified Inventory**: A single source of truth for all cloud assets, regardless of type or region.

---

## 🔍 Waste Detection Rules
The system currently applies 12 specialized rules to identify cost-saving opportunities:

| Resource | Rule Name | Waste Condition | Default Threshold |
| :--- | :--- | :--- | :--- |
| **EC2** | `EC2_STOPPED_AGE` | Instance has been stopped for too long | > 7 Days |
| **EC2** | `EC2_IDLE_CPU` | Instance is running but doing no work | < 5% Avg CPU |
| **EBS** | `EBS_UNATTACHED` | Volume exists but is not plugged into a server | Immediate |
| **EBS** | `EBS_SNAPSHOT_AGE` | Manual snapshot is outdated | > 30 Days |
| **RDS** | `RDS_STOPPED` | Database instance is stopped | Immediate |
| **RDS** | `RDS_IDLE_CONN` | Database has zero active connections | 0 Max Conn (7 Days) |
| **RDS** | `RDS_SNAPSHOT_AGE` | Manual DB snapshot is outdated | > 30 Days |
| **LB** | `LB_NO_TARGETS` | Load Balancer has no servers assigned | Immediate |
| **LB** | `LB_NO_TRAFFIC` | Load Balancer is receiving no requests | 0 Req (7 Days) |
| **NAT** | `NAT_NO_ROUTE` | Gateway is not attached to any route table | Immediate |
| **NAT** | `NAT_NO_TRAFFIC` | Gateway exists but processes no data | 0 Bytes (7 Days) |
| **EIP** | `EIP_UNASSOCIATED` | Static IP is reserved but not in use | Immediate |

---

## 🔐 AWS Setup Guide

To allow the optimizer to analyze your infrastructure, you must create a cross-account IAM role.

### 1. Create the IAM Role
1. Create a role named `CloudOptimizerRole`.
2. Set the **Trust Relationship** to allow the account where this application is hosted to perform `sts:AssumeRole`.
3. Attach the following **Read-Only FinOps Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CoreReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "elasticloadbalancing:Describe*",
        "autoscaling:Describe*",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:GetMetricData",
        "ce:GetCostAndUsage",
        "ce:GetDimensionValues",
        "ce:GetReservationUtilization",
        "ce:GetSavingsPlansUtilization",
        "ce:GetSavingsPlansCoverage",
        "pricing:GetProducts",
        "tag:GetResources",
        "tag:GetTagKeys",
        "tag:GetTagValues"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 🛠 Installation & Usage (Linux)

### 1. Clone & Setup Environment
```bash
git clone https://github.com/your-repo/cloud-cost-optimizer.git
cd cloud-cost-optimizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize the Rules Engine
Populate the local database with the default FinOps thresholds:
```bash
python3 init_rules.py
```

### 3. Start the Server
```bash
uvicorn main:app --reload
```

### 4. Access the API
Open your browser and navigate to:
`http://localhost:8000/docs`
This will open the **Interactive Swagger UI**, allowing you to test all endpoints manually.

---

## 📑 API Guide (Main Endpoints)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/scan-all` | **The Big Red Button**: Triggers all scanners and runs waste analysis. |
| `GET` | `/waste` | Returns the main dashboard summary and detailed list of waste. |
| `GET` | `/resources` | Returns the global inventory of all discovered AWS assets. |
| `GET` | `/rules` | Lists all 12 configurable waste detection rules. |
| `PATCH` | `/rules/{id}` | Update a specific rule (e.g., change CPU threshold to 10%). |
| `GET` | `/summary` | Executive view showing total potential monthly savings. |

---

## 🧠 Architecture Overview
- **`aws_scanners.py`**: Handles Boto3 integration, multi-region loops, and CloudWatch metric collection.
- **`waste_engine.py`**: The "Brain" – applies business logic to inventory data to flag waste.
- **`db.py`**: SQLAlchemy models for Inventory, Waste, Rules, and Scan Logs.
- **`read_api.py`**: Clean, consumption-ready endpoints for the frontend dashboard.
- **`scan_api.py`**: Orchestration layer for triggering infrastructure syncs.