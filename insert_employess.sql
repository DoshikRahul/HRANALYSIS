CREATE TABLE IF NOT EXISTS employeess (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employeesID VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(100) NOT NULL,
    company VARCHAR(255) NOT NULL
);

INSERT INTO employeess (employeesID, password, name, email, role, company) VALUES ('E001', 'pass123', 'John Doe', 'john@example.com', 'Manager', 'ForteAI');
INSERT INTO employeess (employeesID, password, name, email, role, company) VALUES ('E002', 'secret', 'Jane Smith', 'jane@example.com', 'Engineer', 'ForteAI');
INSERT INTO employeess (employeesID, password, name, email, role, company) VALUES ('E003', 'hello123', 'Sam Wilson', 'sam@example.com', 'Analyst', 'ForteAI');
-- All rows from your CSV will be here

COMMIT;
