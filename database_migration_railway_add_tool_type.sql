-- Migration: Add tool_type column to animations table (Railway)
-- This allows us to distinguish between faceswap, fomd, and makeittalk

-- Add tool_type column to animations table
ALTER TABLE animations 
ADD COLUMN tool_type ENUM('faceswap', 'fomd', 'makeittalk') DEFAULT 'makeittalk' AFTER user_id;

-- Create index for better query performance
CREATE INDEX idx_animation_tool_type ON animations(tool_type);

