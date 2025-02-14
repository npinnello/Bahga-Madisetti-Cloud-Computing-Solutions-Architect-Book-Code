
INSERT INTO department VALUES ("1001", "ECE"); 
 
INSERT INTO employee (number, name, salary,department_id) VALUES ("5001", "Alex", "50000", "1001"); 
 
INSERT INTO project VALUES ("201", "Cloud"); 
 
INSERT INTO workson(employee_id,project_id) VALUES ("5001", "201");
