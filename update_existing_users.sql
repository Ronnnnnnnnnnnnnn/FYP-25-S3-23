-- Update existing users to mark them as verified
-- Run this in your Railway MySQL database to fix existing users
-- This marks all existing users (created before email verification) as verified

UPDATE users 
SET email_verified = TRUE 
WHERE verification_token IS NULL OR email_verified = FALSE;

