# Farm Irrigation Management System

# What does the project do?

The Farm Irrigation Management System is a web application designed to manage agricultural irrigation systems. It uses the Flask framework to maintain application logic and SQLAlchemy for interacting with the PostgreSQL database. The application allows users to define cultivation zones, schedule irrigations, and record real-time irrigation events. Additionally, it integrates with the Wiseconn service to fetch and update data in real time, ensuring that irrigation operations are accurate and efficient.

# Why is the project useful?

This project is useful for several reasons:

Efficiency in irrigation management: It allows farmers to schedule and monitor irrigations efficiently, ensuring that each cultivation zone receives the appropriate amount of water.

Resource savings: By optimizing water use, the system helps to reduce waste and promotes the sustainable use of water resources.

Automation and precision: Integration with Wiseconn and the use of APScheduler for scheduling automatic tasks ensure that operations are performed precisely and without constant manual intervention.

Detailed records: It maintains detailed records of all irrigation operations, allowing users to continuously analyze and improve their irrigation strategies.

The application is an agricultural irrigation management solution that combines various technologies to provide efficient management of cultivation zones and their irrigation needs. It uses a clean and well-defined architecture with separate modules for different responsibilities, facilitating scalability and maintenance.

# Ubibot Integration

The Farm Irrigation Management System also integrates with the Ubibot API to further enhance the precision and efficiency of irrigation management. Ubibot provides real-time environmental data that can be used to make more informed irrigation decisions. This includes data from sensors monitoring temperature, ambient temperature, radiation, humidity, ambient humidity, soil conductivity, and more.


# Who maintains and contributes to the project?
The project is maintained and developed by the following contributors:

Bedomax
Heimdallgg
GestionD
The contributors work together to ensure that the system is robust, scalable, and user-friendly, addressing the needs of users and continuously improving its functionalities.

## Table of Contents
1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)

---

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd Integraciones
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:

| Variable | Description |
|----------|-------------|
| `API_KEY` | Wiseconn API key for irrigation sensors |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask secret key for sessions |
| `UBIBOT_ACCOUNT_KEY` | Ubibot API key for environmental sensors |
| `SENDGRID_API_KEY` | SendGrid API key for email alerts |

Example `.env`:
```env
API_KEY=your_wiseconn_api_key
DATABASE_URL=postgresql://user:password@host:5432/database
SECRET_KEY=your_secret_key
UBIBOT_ACCOUNT_KEY=your_ubibot_key
SENDGRID_API_KEY=your_sendgrid_key
```

### Local Development
For local development, create a `.env.local` file to override settings (e.g., use a local database):

```env
DATABASE_URL=postgresql://localhost/donar_dev
```

The `.env.local` file takes precedence over `.env`.

---

## Usage

### Run once
```bash
python run.py
```

### Run with scheduler (production)
```bash
python task_scheduler.py
```

This starts the scheduled tasks:
- **Hourly**: Fetch data from Wiseconn and Ubibot sensors
- **Daily at 7:20 AM**: Send alert emails for disconnected sensors

