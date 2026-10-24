CREATE DATABASE air_tracker;

USE air_tracker;

CREATE TABLE airports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    iata_code VARCHAR(10),
    airport_name VARCHAR(100),
    city VARCHAR(100),
    country VARCHAR(100)
);INSERT INTO airports (iata_code, airport_name, city, country)
VALUES
('DEL', 'Indira Gandhi International', 'New Delhi', 'India'),
('BOM', 'Chhatrapati Shivaji Maharaj', 'Mumbai', 'India'),
('BLR', 'Bangalore Bengaluru', 'Bangalore', 'India'),
('CCU', 'Netaji Subhash Chandra Bose', 'Kolkata', 'India'),
('HYD', 'Rajiv Gandhi International', 'Hyderabad', 'India');

SELECT * FROM airports
WHERE city = 'New Delhi';

SELECT * FROM airports
WHERE city = 'MUMBAI';

SELECT * FROM airports
WHERE city = 'Bangalore';

SELECT * FROM airports
WHERE city = 'kolkata';

SELECT * FROM airports
WHERE city = 'Hyderabad';

SELECT * FROM airports

SELECT COUNT(*) AS total_airports
FROM airports;

SELECT * FROM airports
ORDER BY city ASC;

SELECT airport_name, city
FROM airports
WHERE country = 'India';

SELECT COUNT(*) AS total_airports
FROM airports;

INSERT INTO airports (iata_code, airport_name, city, country)
VALUES
('MAA', 'Chennai International', 'Chennai', 'India'),
('COK', 'Cochin International', 'Kochi', 'India'),
('GOI', 'Goa International', 'Goa', 'India'),
('AMD', 'Sardar Vallabhbhai Patel International', 'Ahmedabad', 'India'),
('PNQ', 'Pune Airport', 'Pune', 'India'),
('LKO', 'Chaudhary Charan Singh International', 'Lucknow', 'India'),
('PAT', 'Jay Prakash Narayan Airport', 'Patna', 'India'),
('IXR', 'Birsa Munda Airport', 'Ranchi', 'India'),
('BBI', 'Biju Patnaik International', 'Bhubaneswar', 'India'),
('IXC', 'Chandigarh Airport', 'Chandigarh', 'India');

SELECT COUNT(*) AS total_airports
FROM airports;

ALTER TABLE airports
ADD airport_type VARCHAR(20);
USE air_tracker;
UPDATE airports
SET airport_type = CASE
    WHEN iata_code IN ('DEL', 'BOM', 'BLR', 'CCU', 'HYD',
                       'MAA', 'COK', 'GOI', 'AMD', 'BBI')
    THEN 'International'
    ELSE 'Domestic'
END;

SELECT iata_code, airport_name, city, airport_type
FROM airports
ORDER BY airport_type, city;

SELECT airport_type, COUNT(*) AS total
FROM airports
GROUP BY airport_type;

SELECT *
FROM airports
WHERE airport_type = 'International';

SELECT *
FROM airports
WHERE airport_type = 'Domestic';

SELECT
    airport_type,
    city,
    airport_name,
    iata_code
FROM airports
ORDER BY airport_type, city;

CREATE TABLE flights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    flight_number VARCHAR(20),
    airline VARCHAR(100),
    departure_airport VARCHAR(10),
    arrival_airport VARCHAR(10),
    flight_status VARCHAR(30)
);

INSERT INTO flights
(flight_number, airline, departure_airport, arrival_airport, flight_status)
VALUES
('AI101', 'Air India', 'DEL', 'BOM', 'Scheduled'),
('6E202', 'IndiGo', 'RNC', 'DEL', 'Scheduled'),
('UK303', 'Vistara', 'BOM', 'BLR', 'Delayed'),
('6E404', 'IndiGo', 'CCU', 'HYD', 'Scheduled'),
('AI505', 'Air India', 'BLR', 'DEL', 'Landed');

SELECT * FROM flights;

SELECT flight_status, COUNT(*) AS total_flights
FROM flights
GROUP BY flight_status;

SELECT
    f.flight_number,
    f.airline,
    a1.city AS departure_city,
    a2.city AS arrival_city,
    f.flight_status
FROM flights f
LEFT JOIN airports a1
    ON f.departure_airport = a1.iata_code
LEFT JOIN airports a2
    ON f.arrival_airport = a2.iata_code;
    
    SELECT
    airline,
    flight_status,
    COUNT(*) AS total_flights
FROM flights
GROUP BY airline, flight_status
ORDER BY airline;

SELECT
    airline,
    COUNT(*) AS total_flights
FROM flights
GROUP BY airline
ORDER BY total_flights DESC;

SELECT
    flight_status,
    COUNT(*) AS total_flights,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM flights), 2) AS percentage
FROM flights
GROUP BY flight_status;

SELECT
    departure_airport,
    COUNT(*) AS total_departures
FROM flights
GROUP BY departure_airport
ORDER BY total_departures DESC;

SELECT
    arrival_airport,
    COUNT(*) AS total_arrivals
FROM flights
GROUP BY arrival_airport
ORDER BY total_arrivals DESC;

SELECT
    f.flight_number,
    f.airline,
    a1.city AS departure_city,
    a2.city AS arrival_city,
    f.flight_status
FROM flights f
JOIN airports a1
    ON f.departure_airport = a1.iata_code
JOIN airports a2
    ON f.arrival_airport = a2.iata_code
ORDER BY f.flight_number;

SELECT
    flight_number,
    airline,
    departure_airport,
    arrival_airport,
    flight_status
FROM flights
WHERE flight_number = 'AI101';

UPDATE flights
SET flight_status = 'Delayed'
WHERE flight_number = 'AI101';

SELECT flight_number, airline, flight_status
FROM flights
WHERE flight_number = 'AI101';

SELECT
    flight_number,
    airline,
    departure_airport,
    arrival_airport,
    flight_status
FROM flights
WHERE flight_status = 'Delayed';

SELECT
    flight_status,
    COUNT(*) AS total_flights
FROM flights
GROUP BY flight_status
ORDER BY total_flights DESC;