# Sequence Diagrams for FirstMod-AI

This directory contains sequence diagrams for all user stories in the FirstMod-AI application. Each diagram is formatted for use with [sequencediagram.org](https://sequencediagram.org).

## How to Use

1. Open the desired `.txt` file
2. Copy all content between the `COPY FROM HERE ↓` and `COPY UNTIL HERE ↑` markers
3. Paste into [https://sequencediagram.org](https://sequencediagram.org)
4. The diagram will be automatically generated

## Diagram Categories

### Guest User Stories
- **US-G-001**: Sign Up - Create New Account
- **US-G-002**: View Sample Animations
- **US-G-003**: Login - Authenticate User

### User (Free) Stories
- **US-U-002**: Logout - End User Session
- **US-U-003**: Face Swap - Swap Faces Between Images (Technical)
- **US-U-008**: Edit Profile Picture
- **US-U-009**: Update Profile Information
- **US-U-010**: Change Password
- **US-U-011**: Delete Account
- **US-U-012**: Pay for Subscription
- **US-U-013**: Preview Source Image for Face Swap
- **US-U-014**: Preview Target Image for Face Swap

### Subscriber Stories
- **US-S-008**: FOMD Animation Generation (Technical)
- **US-S-012**: MakeItTalk - Talking Portrait Generation (Technical)
- **US-S-027**: Preview Source Image for FOMD
- **US-S-028**: Play Driving Video for FOMD
- **US-S-034**: Preview Source Image for MakeItTalk
- **US-S-035**: Preview Audio File for MakeItTalk

### Admin Stories
- **US-A-001**: Admin Login
- **US-A-006**: Create Admin Account
- **US-A-007**: Load All Users
- **US-A-009**: Edit User Profile (Admin)
- **US-A-010**: Suspend User
- **US-A-013**: Activate User

## Technical Features

The following features have detailed technical sequence diagrams:
- **Face Swap**: Includes Gradio API integration, face detection, and face swapping process
- **FOMD**: Includes HuggingFace API calls, face detection, keypoint extraction, and animation generation
- **MakeItTalk**: Includes facial landmark detection, audio processing, lip sync generation, and animation creation

## Notes

- All diagrams are based on the actual codebase implementation
- Queue position and cleanup after 7/30 days are ignored as per requirements
- Progress bars are simplified to match actual code implementation
- Face animation features (FOMD, FaceSwap, MakeItTalk) have more technical detail
- Other features (login, logout, preview) are kept simpler

## File Naming Convention

Files are named using the pattern: `{USER_STORY_ID}_{Description}.txt`

Example: `US-G-001_Signup.txt` = Guest story #001 for Sign Up

