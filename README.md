# Athlete Nutrition & Performance Management System

Flask + MySQL DBMS college project, extended from the existing CRUD application without deleting existing project tables or records.

## Features
- Four roles: ADMIN, COACH, NUTRITIONIST, ATHLETE
- Session-based login/logout
- Role-based navigation and authorization
- Existing CRUD modules preserved
- Dashboard statistics from MySQL
- Athlete-only personal records page
- Food and Exercise generic CRUD screens that read the existing table structure dynamically
- Parameterized MySQL queries
- Flash messages and responsive UI

## Requirements
- Python 3.10+
- MySQL 8+
- Existing database: `athlete_management`

## Setup
1. Open Terminal in this project directory.
2. Create/activate a virtual environment.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Edit `.env` with your MySQL credentials.
5. Make sure the existing database `athlete_management` is running.
6. Run:
   `python app.py`
7. Open: http://127.0.0.1:5000

On first login, the application creates only `App_User` if it does not exist. Existing project tables and records are not dropped or recreated.

## Demo accounts
- ADMIN: `admin` / `admin123`
- COACH: `coach` / `coach123`
- NUTRITIONIST: `nutritionist` / `nutrition123`
- ATHLETE: `athlete` / `athlete123`

The default coach, nutritionist, and athlete accounts are linked to the first existing record in their respective tables when the authentication table is first created. Change credentials for real deployment.

## Database safety
The project does not contain a destructive database reset script. Do not run `DROP DATABASE` or delete existing records for demonstration.

## Important
If your MySQL account does not have permission to create the `App_User` table, run `database/auth_setup.sql` once using an account with CREATE permission, then start the Flask app.


## UI refresh

The interface has a responsive ATHLETE+ visual system with a refreshed sign-in page, role-specific dashboards, responsive navigation, improved tables/forms, and a mobile menu. Styles live in `static/css/style.css`; small progressive enhancements live in `static/js/script.js`. The UI refresh does not require database schema changes.
