-- Migration: Add tool_type column to animations table
-- This allows us to distinguish between faceswap, fomd, and makeittalk

USE face_animation_db;

-- Add tool_type column to animations table
ALTER TABLE animations 
ADD COLUMN tool_type ENUM('faceswap', 'fomd', 'makeittalk') DEFAULT 'makeittalk' AFTER user_id;

-- Update existing records if any (optional, for existing data)
-- UPDATE animations SET tool_type = 'makeittalk' WHERE tool_type IS NULL;

-- Create index for better query performance
CREATE INDEX idx_animation_tool_type ON animations(tool_type);

