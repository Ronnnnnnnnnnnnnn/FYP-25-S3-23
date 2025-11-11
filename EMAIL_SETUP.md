# Email Setup Guide

## Option 1: SendGrid (Recommended for Railway)

SendGrid is more reliable for cloud platforms and has a free tier (100 emails/day).

### Step 1: Create SendGrid Account
1. Go to https://signup.sendgrid.com/
2. Sign up for a free account
3. Verify your email address

### Step 2: Create API Key
1. Go to SendGrid Dashboard → Settings → API Keys
2. Click "Create API Key"
3. Name it: "Flask App"
4. Select "Full Access" or "Restricted Access" → "Mail Send"
5. Click "Create & View"
6. **Copy the API key immediately** (you won't see it again!)

### Step 3: Verify Sender Email (Optional but Recommended)
1. Go to SendGrid Dashboard → Settings → Sender Authentication
2. Click "Verify a Single Sender"
3. Fill in your details:
   - From Email: `fyp25s323@gmail.com` (or your preferred email)
   - From Name: FirstMod-AI
   - Reply To: `fyp25s323@gmail.com`
4. Check your email and click the verification link

### Step 4: Set Railway Environment Variables
Go to Railway → Your Web Service → Variables tab, and add/update:

```
MAIL_SERVER = smtp.sendgrid.net
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = apikey
MAIL_PASSWORD = SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MAIL_DEFAULT_SENDER = fyp25s323@gmail.com
```

**Important:** Replace `SG.xxxxxxxx...` with your actual SendGrid API key!

### Step 5: Redeploy
Railway will automatically redeploy. Wait 2-3 minutes, then test signup again.

---

## Option 2: Gmail (Current Setup - May Timeout)

If you want to keep using Gmail, make sure you're using an **App Password**:

### Step 1: Generate Gmail App Password
1. Go to https://myaccount.google.com/security
2. Enable "2-Step Verification" if not already enabled
3. Go to "App passwords"
4. Select "Mail" and "Other (Custom name)"
5. Name it: "Railway Flask App"
6. Click "Generate"
7. Copy the 16-character password

### Step 2: Update Railway Environment Variables
```
MAIL_SERVER = smtp.gmail.com
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = fyp25s323@gmail.com
MAIL_PASSWORD = xxxx xxxx xxxx xxxx (your app password, no spaces)
MAIL_DEFAULT_SENDER = fyp25s323@gmail.com
```

**Note:** Gmail SMTP may timeout on Railway. SendGrid is more reliable.

---

## Testing

After setting up, test by:
1. Signing up a new account
2. Check your email inbox (and spam folder)
3. You should receive the OTP email within seconds

## Troubleshooting

- **Emails not arriving?** Check spam folder
- **Timeout errors?** Switch to SendGrid
- **Still not working?** Check Railway logs for email errors

