-- Add profile_picture column to users table
-- Run this in your Railway MySQL database if the column doesn't exist
-- If you get an error saying the column already exists, that's fine - just ignore it

-- Check if column exists first (optional - just for verification)
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'users' 
AND COLUMN_NAME = 'profile_picture';

-- Add the column (will error if it already exists, which is fine)
ALTER TABLE users 
ADD COLUMN profile_picture VARCHAR(500) NULL;

-- Verify the column was added
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'users' 
AND COLUMN_NAME = 'profile_picture';

