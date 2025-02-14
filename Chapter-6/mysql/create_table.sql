USE team_9_rds;
CREATE TABLE department (
    number VARCHAR(50) NOT NULL PRIMARY KEY,
    name VARCHAR(200) NULL
);

CREATE TABLE employee (
    number VARCHAR(100) NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    salary VARCHAR(20) NOT NULL,
    department_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (department_id) REFERENCES department(number) ON DELETE CASCADE
);

CREATE TABLE project (
    number VARCHAR(20) NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE workson (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(100) NOT NULL,
    project_id VARCHAR(20) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employee(number) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES project(number) ON DELETE CASCADE
);
