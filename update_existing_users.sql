-- Update existing users to mark them as verified
-- Run this in your Railway MySQL database to fix existing users

UPDATE users 
SET email_verified = TRUE 
WHERE verification_code IS NULL OR email_verified = FALSE;

