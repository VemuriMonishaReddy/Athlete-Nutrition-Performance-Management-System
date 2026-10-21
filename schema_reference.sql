-- REFERENCE / RECONSTRUCTION ONLY -- NOT A VERIFIED LIVE DATABASE DUMP.
-- Compare with SHOW CREATE TABLE for every live table before using this file.
-- This creates a separate reference database so it does not overwrite the user's DB.
CREATE DATABASE IF NOT EXISTS athlete_management_reference;
USE athlete_management_reference;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE IF NOT EXISTS Sport (
  Sport_ID INT AUTO_INCREMENT PRIMARY KEY,
  Sport_Name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Nutritionist (
  Nutritionist_ID INT AUTO_INCREMENT PRIMARY KEY,
  Name VARCHAR(100) NOT NULL,
  Qualification VARCHAR(100),
  Contact VARCHAR(15)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Food (
  Food_ID INT AUTO_INCREMENT PRIMARY KEY,
  Food_Name VARCHAR(100) NOT NULL,
  Category VARCHAR(50),
  Calories DECIMAL(8,2),
  Protein DECIMAL(8,2),
  Carbohydrates DECIMAL(8,2),
  Fat DECIMAL(8,2),
  CHECK (Calories IS NULL OR Calories >= 0),
  CHECK (Protein IS NULL OR Protein >= 0),
  CHECK (Carbohydrates IS NULL OR Carbohydrates >= 0),
  CHECK (Fat IS NULL OR Fat >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Exercise (
  Exercise_ID INT AUTO_INCREMENT PRIMARY KEY,
  Exercise_Name VARCHAR(100) NOT NULL,
  Exercise_Type VARCHAR(50),
  Muscle_Group VARCHAR(50),
  Difficulty_Level VARCHAR(30)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `User` (
  User_ID INT AUTO_INCREMENT PRIMARY KEY,
  Username VARCHAR(50) NOT NULL UNIQUE,
  Password VARCHAR(255) NOT NULL COMMENT 'Store a password hash, never plaintext',
  Role ENUM('Admin','Coach','Nutritionist','Athlete') NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS App_User (
  User_ID INT AUTO_INCREMENT PRIMARY KEY,
  Username VARCHAR(100) NOT NULL UNIQUE,
  Password_Hash VARCHAR(255) NOT NULL,
  Role ENUM('ADMIN','COACH','NUTRITIONIST','ATHLETE') NOT NULL,
  Athlete_ID INT NULL,
  Coach_ID INT NULL,
  Nutritionist_ID INT NULL,
  Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Coach (
  Coach_ID INT AUTO_INCREMENT PRIMARY KEY,
  Name VARCHAR(100) NOT NULL,
  Experience INT,
  Contact VARCHAR(15),
  Sport_ID INT,
  CONSTRAINT fk_coach_sport FOREIGN KEY (Sport_ID) REFERENCES Sport(Sport_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (Experience IS NULL OR Experience >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Athlete (
  Athlete_ID INT AUTO_INCREMENT PRIMARY KEY,
  Name VARCHAR(100) NOT NULL,
  Age INT,
  Gender VARCHAR(20),
  Height DECIMAL(5,2),
  Weight DECIMAL(5,2),
  Contact VARCHAR(15),
  Sport_ID INT NOT NULL,
  Coach_ID INT NULL,
  CONSTRAINT fk_athlete_sport FOREIGN KEY (Sport_ID) REFERENCES Sport(Sport_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_athlete_coach FOREIGN KEY (Coach_ID) REFERENCES Coach(Coach_ID)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CHECK (Age IS NULL OR Age > 0),
  CHECK (Height IS NULL OR Height > 0),
  CHECK (Weight IS NULL OR Weight > 0)
) ENGINE=InnoDB;

-- PROVISIONAL: verify exact columns and FK rules using SHOW CREATE TABLE User_Account.
CREATE TABLE IF NOT EXISTS User_Account (
  User_ID INT AUTO_INCREMENT PRIMARY KEY,
  Username VARCHAR(100) NOT NULL UNIQUE,
  Password_Hash VARCHAR(255) NOT NULL,
  Role VARCHAR(30) NOT NULL,
  Athlete_ID INT NULL,
  Coach_ID INT NULL,
  Nutritionist_ID INT NULL,
  CONSTRAINT fk_user_account_athlete FOREIGN KEY (Athlete_ID) REFERENCES Athlete(Athlete_ID)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_user_account_coach FOREIGN KEY (Coach_ID) REFERENCES Coach(Coach_ID)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_user_account_nutritionist FOREIGN KEY (Nutritionist_ID) REFERENCES Nutritionist(Nutritionist_ID)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Diet_Plan (
  Diet_ID INT AUTO_INCREMENT PRIMARY KEY,
  Athlete_ID INT NOT NULL,
  Nutritionist_ID INT NOT NULL,
  Plan_Name VARCHAR(100) NOT NULL,
  Start_Date DATE NOT NULL,
  End_Date DATE,
  Calories_Target DECIMAL(8,2),
  CONSTRAINT fk_diet_athlete FOREIGN KEY (Athlete_ID) REFERENCES Athlete(Athlete_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_diet_nutritionist FOREIGN KEY (Nutritionist_ID) REFERENCES Nutritionist(Nutritionist_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (End_Date IS NULL OR End_Date >= Start_Date),
  CHECK (Calories_Target IS NULL OR Calories_Target >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Diet_Plan_Food (
  Diet_ID INT NOT NULL,
  Food_ID INT NOT NULL,
  Meal_Type VARCHAR(50) NOT NULL,
  Quantity DECIMAL(8,2),
  PRIMARY KEY (Diet_ID, Food_ID, Meal_Type),
  CONSTRAINT fk_dpf_diet FOREIGN KEY (Diet_ID) REFERENCES Diet_Plan(Diet_ID)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_dpf_food FOREIGN KEY (Food_ID) REFERENCES Food(Food_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (Quantity IS NULL OR Quantity > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Workout_Plan (
  Workout_ID INT AUTO_INCREMENT PRIMARY KEY,
  Athlete_ID INT NOT NULL,
  Coach_ID INT NOT NULL,
  Plan_Name VARCHAR(100) NOT NULL,
  Start_Date DATE NOT NULL,
  End_Date DATE,
  CONSTRAINT fk_workout_athlete FOREIGN KEY (Athlete_ID) REFERENCES Athlete(Athlete_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_workout_coach FOREIGN KEY (Coach_ID) REFERENCES Coach(Coach_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (End_Date IS NULL OR End_Date >= Start_Date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Workout_Exercise (
  Workout_ID INT NOT NULL,
  Exercise_ID INT NOT NULL,
  Sets INT,
  Repetitions INT,
  Duration_Minutes DECIMAL(8,2),
  PRIMARY KEY (Workout_ID, Exercise_ID),
  CONSTRAINT fk_we_workout FOREIGN KEY (Workout_ID) REFERENCES Workout_Plan(Workout_ID)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_we_exercise FOREIGN KEY (Exercise_ID) REFERENCES Exercise(Exercise_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (Sets IS NULL OR Sets > 0),
  CHECK (Repetitions IS NULL OR Repetitions > 0),
  CHECK (Duration_Minutes IS NULL OR Duration_Minutes >= 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Attendance (
  Attendance_ID INT AUTO_INCREMENT PRIMARY KEY,
  Athlete_ID INT NOT NULL,
  Attendance_Date DATE NOT NULL,
  Status ENUM('Present','Absent') NOT NULL,
  CONSTRAINT fk_attendance_athlete FOREIGN KEY (Athlete_ID) REFERENCES Athlete(Athlete_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT
  -- Add UNIQUE (Athlete_ID, Attendance_Date) only if confirmed by the live schema/business rules.
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Competition (
  Competition_ID INT AUTO_INCREMENT PRIMARY KEY,
  Sport_ID INT NOT NULL,
  Competition_Name VARCHAR(150) NOT NULL,
  Competition_Date DATE NOT NULL,
  Location VARCHAR(150),
  CONSTRAINT fk_competition_sport FOREIGN KEY (Sport_ID) REFERENCES Sport(Sport_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Performance (
  Performance_ID INT AUTO_INCREMENT PRIMARY KEY,
  Athlete_ID INT NOT NULL,
  Competition_ID INT NOT NULL,
  Score DECIMAL(8,2),
  Rank_Position INT,
  Medal VARCHAR(20),
  Performance_Date DATE NOT NULL,
  CONSTRAINT fk_performance_athlete FOREIGN KEY (Athlete_ID) REFERENCES Athlete(Athlete_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_performance_competition FOREIGN KEY (Competition_ID) REFERENCES Competition(Competition_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (Score IS NULL OR Score >= 0),
  CHECK (Rank_Position IS NULL OR Rank_Position > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Progress (
  Progress_ID INT AUTO_INCREMENT PRIMARY KEY,
  Athlete_ID INT NOT NULL,
  Record_Date DATE NOT NULL,
  Weight DECIMAL(5,2),
  BMI DECIMAL(5,2),
  Body_Fat_Percentage DECIMAL(5,2),
  Notes VARCHAR(255),
  CONSTRAINT fk_progress_athlete FOREIGN KEY (Athlete_ID) REFERENCES Athlete(Athlete_ID)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CHECK (Weight IS NULL OR Weight > 0),
  CHECK (BMI IS NULL OR BMI > 0),
  CHECK (Body_Fat_Percentage IS NULL OR (Body_Fat_Percentage >= 0 AND Body_Fat_Percentage <= 100))
) ENGINE=InnoDB;

-- This reference DDL creates structure only; it does not insert demo rows.
-- App_User linked person IDs intentionally have no FK here to match the known live metadata.
