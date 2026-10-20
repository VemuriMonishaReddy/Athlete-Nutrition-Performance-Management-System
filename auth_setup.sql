-- Authentication table added by the completed project.
-- This does not drop, alter, or delete any existing project table.
USE athlete_management;

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
