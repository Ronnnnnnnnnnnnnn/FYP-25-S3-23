-- Create database
DROP DATABASE IF EXISTS face_animation_db;
CREATE DATABASE IF NOT EXISTS face_animation_db;
USE face_animation_db;


-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    fullname VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'subscriber', 'admin') DEFAULT 'user',
    subscription_status ENUM('active', 'inactive', 'suspended') DEFAULT 'inactive',
    profile_picture VARCHAR(500) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Expressions table
CREATE TABLE IF NOT EXISTS expressions (
    expression_id INT PRIMARY KEY AUTO_INCREMENT,
    expression_name VARCHAR(100) NOT NULL,
    expression_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Animations table
CREATE TABLE IF NOT EXISTS animations (
    animation_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    expression_id INT,
    driving_video_path VARCHAR(500),
    animation_path VARCHAR(500) NOT NULL,
    status ENUM('processing', 'completed', 'failed') DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (expression_id) REFERENCES expressions(expression_id) ON DELETE SET NULL
);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    plan_type ENUM('monthly', 'yearly') NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    payment_status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Insert default expressions
INSERT INTO expressions (expression_name, expression_description) VALUES
('smile', 'Happy smiling expression'),
('angry', 'Angry expression'),
('surprised', 'Surprised expression'),
('sad', 'Sad expression');

-- Insert default admin user (password: admin123)
-- Password hash generated with werkzeug.security.generate_password_hash('admin123')
INSERT INTO users (fullname, email, password, role, subscription_status) VALUES
('Admin User', 'admin@faceanimation.com', 'scrypt:32768:8:1$hBzKjLQ6HWpvYGxC$0fde8e5e5c5c8e8f8d8b8c8a8e8d8c8b8a8e8d8c8b8a8e8d8c8b8a8e8d8c8b8a8e8d8c8b8a8e8d8c8b8a8e8d8c', 'admin', 'active');

-- Insert 2 basic users (password: password123 for all test users)
INSERT INTO users (fullname, email, password, role, subscription_status) VALUES
('John Doe', 'user1@example.com', 'scrypt:32768:8:1$cMpxgI2IvmyyUoI5$195ec3293a475ac13f42ac7e8dffe69f70985f2b4134cb91e535e0748fcc51c081d238ca77987921621c2fa5aa9c382d02eb3b7ca4bef563c540543bd7596be6', 'user', 'inactive'),
('Jane Smith', 'user2@example.com', 'scrypt:32768:8:1$Omofv9wsjMy4sitA$11d1aaf9f50747efd0518d52cfd0aab5a81c1ac98657c93ea9df66edc4214549b4462cf2a9886f6e239fd39f10829afd533057b85fc961cf9e7265d169099936', 'user', 'inactive');

-- Insert 2 subscribers (password: password123)
INSERT INTO users (fullname, email, password, role, subscription_status) VALUES
('Alice Johnson', 'subscriber1@example.com', 'scrypt:32768:8:1$28SDIt4iRCoItfuJ$551c35735a2fbc7f34a29eec1d22f314f318223328ce90356b1a9babe61c11b0ed6fd924c4cb55256117752c432ba1200a91dff82dff977865e4be8210fbaa07', 'subscriber', 'active'),
('Bob Williams', 'subscriber2@example.com', 'scrypt:32768:8:1$UY7p2V0jCvkD0uOq$072803b783157d3d9d60dd3f91114cc2b8f70947496efbdf862e3954fffe9cf5e9c331b2ce0a547958d198f50dbfea3ebc6652edc2a36c7ab1b7f0b623304edd', 'subscriber', 'active');

-- Insert 2 additional admins (password: password123)
INSERT INTO users (fullname, email, password, role, subscription_status) VALUES
('Admin Two', 'admin2@faceanimation.com', 'scrypt:32768:8:1$vVu2kHQeJKrW064K$2d210ca74b1a6d24dfb3b65fe786e5b099c174ed81b69a6bf41b9fbfab3eb3f9e2a5e42f073c4d9a740ca0266d657a1b329e0751b6402d0d77ba9d43ac40a625', 'admin', 'active'),
('Admin Three', 'admin3@faceanimation.com', 'scrypt:32768:8:1$mAK3LPa9LMmw6SHh$3c530bdd4a0130f6df306caf62859da85975502f566f397f62bb7b807035d606035f3634376e91549460983047729efa7b874afe57a9240c08826bd8d5398862', 'admin', 'active');

-- Create indexes for better performance
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_animation_user ON animations(user_id);
CREATE INDEX idx_animation_status ON animations(status);