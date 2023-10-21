CREATE TABLE IF NOT EXISTS users(
    user_id serial PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    second_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS patients(
    patient_id INT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    birth_date DATE NOT NULL,
    is_male BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments(
    appointment_id serial PRIMARY KEY,
    appointment_time TIMESTAMP NOT NULL,
    patient_id INT NOT NULL,
    user_id INT NOT NULL,
    blood_pressure VARCHAR(255),
    pulse INT NOT NULL,
    swell VARCHAR(255),
    complains TEXT,
    diagnosis TEXT,
    disease_complications TEXT, 
    comorbidities TEXT,
    disease_anamnesis TEXT,
    life_anamnesis TEXT,
    echocardiogram_data TEXT,

    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);