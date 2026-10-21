# Test cases and validation plan

**Status key:** Not run / Pass / Fail. Fill the result column only after performing the test against the local environment.

| ID | Test | Procedure | Expected result | Actual result/status |
|---|---|---|---|---|
| T01 | Application starts | Configure valid `.env`; run `python app.py` | Flask starts without import/config errors | Not run |
| T02 | Missing secret | Unset `FLASK_SECRET_KEY`; start app | Startup fails with a clear configuration error | Not run |
| T03 | Database connection | Use valid MySQL credentials and database | App connects and required tables can be queried | Not run |
| T04 | Invalid DB credentials | Use a deliberately incorrect local password | Connection fails; no credentials are printed to a public log | Not run |
| T05 | Login success | Sign in with a valid local demo account | User reaches the authorized application page | Not run |
| T06 | Login failure | Enter an incorrect password | Login rejected without disclosing whether the username exists | Not run |
| T07 | Logout | Log out, then use browser back or visit a protected route | Protected route redirects to login | Not run |
| T08 | Role restriction | Sign in with each role and try a disallowed route | Disallowed route is denied/redirected | Not run |
| T09 | Athlete CRUD | Create, read, edit, and delete a disposable test athlete | Changes persist; required-field and FK rules are enforced | Not run |
| T10 | Diet plan | Create a diet plan with valid athlete/nutritionist IDs | Plan is stored and appears in listing | Not run |
| T11 | Workout plan | Create a plan and associate an exercise | Plan and junction rows display correctly | Not run |
| T12 | Attendance | Add Present and Absent records | Records and attendance report are consistent | Not run |
| T13 | Performance/progress | Add valid score and progress record | Values persist and appear in the relevant screens | Not run |
| T14 | FK integrity | Try a disposable row with a nonexistent FK | Database rejects the invalid reference | Not run |
| T15 | SQL injection input | Enter a quote/string such as `' OR '1'='1` in a text field | It is treated as data, not executable SQL | Not run |
| T16 | Advanced queries | Execute each query in `database/advanced_queries.sql` | Query executes; inspect results for correctness | Not run |
| T17 | Data restoration | Restore sanitized dump into a separate dev DB | Tables and expected row counts are reproduced | Not run |
| T18 | Git hygiene | Inspect staged files with `git status` | `.env`, secrets, local data dumps, and venv are absent | Not run |

## Validation commands

```sql
USE athlete_management;
SHOW TABLES;
SHOW CREATE TABLE Athlete;
SHOW CREATE TABLE User_Account;
SHOW INDEX FROM Attendance;
SELECT COUNT(*) AS athlete_count FROM Athlete;
SELECT COUNT(*) AS diet_plan_count FROM Diet_Plan;
SELECT COUNT(*) AS workout_plan_count FROM Workout_Plan;
```

Run destructive CRUD tests only with disposable test records in a development database. Do not use the production or only copy of project data.
