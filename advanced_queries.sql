-- Athlete Management System: documented analytical SQL queries
-- Run after selecting the athlete_management database.
-- These queries assume the column names described in schema_reference.sql.

USE athlete_management;

-- Q1. Athlete, sport, and assigned coach (multi-table JOIN).
SELECT a.Athlete_ID, a.Name AS Athlete_Name, a.Age,
       s.Sport_Name, c.Name AS Coach_Name
FROM Athlete AS a
JOIN Sport AS s ON s.Sport_ID = a.Sport_ID
LEFT JOIN Coach AS c ON c.Coach_ID = a.Coach_ID
ORDER BY a.Name;

-- Q2. Diet plan with the athlete and responsible nutritionist.
SELECT dp.Diet_ID, dp.Plan_Name, a.Name AS Athlete_Name,
       n.Name AS Nutritionist_Name, dp.Start_Date, dp.End_Date,
       dp.Calories_Target
FROM Diet_Plan AS dp
JOIN Athlete AS a ON a.Athlete_ID = dp.Athlete_ID
JOIN Nutritionist AS n ON n.Nutritionist_ID = dp.Nutritionist_ID
ORDER BY dp.Start_Date DESC;

-- Q3. Workout plans with their exercises (five-table JOIN).
SELECT wp.Workout_ID, wp.Plan_Name, a.Name AS Athlete_Name,
       c.Name AS Coach_Name, e.Exercise_Name, we.Sets,
       we.Repetitions, we.Duration_Minutes
FROM Workout_Plan AS wp
JOIN Athlete AS a ON a.Athlete_ID = wp.Athlete_ID
JOIN Coach AS c ON c.Coach_ID = wp.Coach_ID
JOIN Workout_Exercise AS we ON we.Workout_ID = wp.Workout_ID
JOIN Exercise AS e ON e.Exercise_ID = we.Exercise_ID
ORDER BY wp.Workout_ID, e.Exercise_Name;

-- Q4. Athlete count by sport (GROUP BY, COUNT, LEFT JOIN).
SELECT s.Sport_ID, s.Sport_Name,
       COUNT(a.Athlete_ID) AS Total_Athletes
FROM Sport AS s
LEFT JOIN Athlete AS a ON a.Sport_ID = s.Sport_ID
GROUP BY s.Sport_ID, s.Sport_Name
ORDER BY Total_Athletes DESC;

-- Q5. Performance summary per athlete (COUNT, AVG, MAX, MIN).
SELECT a.Athlete_ID, a.Name AS Athlete_Name,
       COUNT(p.Performance_ID) AS Total_Performances,
       AVG(p.Score) AS Average_Score,
       MAX(p.Score) AS Highest_Score,
       MIN(p.Score) AS Lowest_Score
FROM Athlete AS a
LEFT JOIN Performance AS p ON p.Athlete_ID = a.Athlete_ID
GROUP BY a.Athlete_ID, a.Name
ORDER BY Average_Score DESC;

-- Q6. Attendance percentage per athlete (CASE, SUM, COUNT, NULLIF).
SELECT a.Athlete_ID, a.Name AS Athlete_Name,
       COUNT(at.Attendance_ID) AS Total_Records,
       SUM(CASE WHEN at.Status = 'Present' THEN 1 ELSE 0 END) AS Days_Present,
       ROUND(100.0 * SUM(CASE WHEN at.Status = 'Present' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(at.Attendance_ID), 0), 2) AS Attendance_Percentage
FROM Athlete AS a
LEFT JOIN Attendance AS at ON at.Athlete_ID = a.Athlete_ID
GROUP BY a.Athlete_ID, a.Name
ORDER BY Attendance_Percentage DESC;

-- Q7. Athletes with at least one score above the overall average (subquery).
SELECT DISTINCT a.Athlete_ID, a.Name AS Athlete_Name
FROM Athlete AS a
JOIN Performance AS p ON p.Athlete_ID = a.Athlete_ID
WHERE p.Score > (SELECT AVG(Score) FROM Performance)
ORDER BY a.Name;

-- Q8. Athletes with no diet plan (correlated NOT EXISTS subquery).
SELECT a.Athlete_ID, a.Name AS Athlete_Name
FROM Athlete AS a
WHERE NOT EXISTS (
    SELECT 1 FROM Diet_Plan AS dp WHERE dp.Athlete_ID = a.Athlete_ID
)
ORDER BY a.Name;

-- Q9. Athletes whose recorded weight exceeds the average non-NULL weight.
SELECT Athlete_ID, Name, Weight
FROM Athlete
WHERE Weight > (SELECT AVG(Weight) FROM Athlete WHERE Weight IS NOT NULL)
ORDER BY Weight DESC;

-- Q10. Sports with more than one athlete (GROUP BY + HAVING).
SELECT s.Sport_Name, COUNT(a.Athlete_ID) AS Total_Athletes
FROM Sport AS s
JOIN Athlete AS a ON a.Sport_ID = s.Sport_ID
GROUP BY s.Sport_ID, s.Sport_Name
HAVING COUNT(a.Athlete_ID) > 1
ORDER BY Total_Athletes DESC;

-- Q11. Competitions with multiple performance records.
SELECT c.Competition_ID, c.Competition_Name,
       COUNT(p.Performance_ID) AS Total_Performances,
       AVG(p.Score) AS Average_Score, MAX(p.Score) AS Highest_Score
FROM Competition AS c
JOIN Performance AS p ON p.Competition_ID = c.Competition_ID
GROUP BY c.Competition_ID, c.Competition_Name
HAVING COUNT(p.Performance_ID) > 1
ORDER BY Total_Performances DESC;

-- Q12. Foods, meal types, and nutritional values in each diet plan.
SELECT dp.Diet_ID, dp.Plan_Name, a.Name AS Athlete_Name,
       f.Food_Name, dpf.Meal_Type, dpf.Quantity,
       f.Calories, f.Protein, f.Carbohydrates, f.Fat
FROM Diet_Plan AS dp
JOIN Athlete AS a ON a.Athlete_ID = dp.Athlete_ID
JOIN Diet_Plan_Food AS dpf ON dpf.Diet_ID = dp.Diet_ID
JOIN Food AS f ON f.Food_ID = dpf.Food_ID
ORDER BY dp.Diet_ID, dpf.Meal_Type, f.Food_Name;
