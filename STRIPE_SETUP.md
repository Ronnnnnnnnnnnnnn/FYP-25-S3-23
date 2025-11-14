# Stripe Payment Integration Setup Guide

This guide will help you complete the Stripe payment integration setup for your Flask application on Railway.

## ✅ What's Been Implemented

1. **Database Schema Updated** - Added Stripe-related fields to `users` and `subscriptions` tables
2. **Stripe Python Package** - Added `stripe` to `requirements.txt`
3. **Backend API Endpoints**:
   - `/api/stripe/create-checkout-session` - Creates Stripe checkout session
   - `/api/stripe/verify-session/<session_id>` - Verifies payment session
   - `/api/stripe/webhook` - Handles Stripe webhooks
   - `/api/stripe/cancel-subscription` - Cancels user subscription
4. **Frontend Updated** - Payment page now uses Stripe Checkout
5. **Payment Success Page** - Created success page with verification
6. **Subscriber Dashboard** - Updated to handle subscription cancellation

## 🔧 Step-by-Step Setup Instructions

### Step 1: Create Stripe Account

1. Go to https://stripe.com and create an account
2. Complete the account setup

### Step 2: Get Stripe API Keys

1. Go to Stripe Dashboard → Developers → API keys
2. Copy your keys:
   - **Publishable key** (starts with `pk_test_` for test, `pk_live_` for live)
   - **Secret key** (starts with `sk_test_` for test, `sk_live_` for live)

⚠️ **IMPORTANT**: Use **TEST keys** during development!

### Step 3: Create Products in Stripe Dashboard

1. Go to Stripe Dashboard → Products
2. Click "Add product"

#### Create Monthly Plan:
- **Name**: Monthly Plan
- **Price**: $9.99
- **Billing**: Recurring (monthly)
- Click "Add product"

#### Create Yearly Plan:
- **Name**: Yearly Plan
- **Price**: $99.99
- **Billing**: Recurring (yearly)
- Click "Add product"

### Step 4: Get Price IDs

After creating products:
1. Click on each product you created
2. Copy the **Price ID** (starts with `price_`)
   - Example: `price_1ABC123monthly` for monthly
   - Example: `price_1XYZ789yearly` for yearly

### Step 5: Set Up Webhook Endpoint

1. Go to Stripe Dashboard → Developers → Webhooks
2. Click "Add endpoint"
3. Enter your webhook URL: `https://your-railway-app.railway.app/api/stripe/webhook`
4. Select events to listen to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Click "Add endpoint"
6. Copy the **Signing secret** (starts with `whsec_`)

### Step 6: Configure Railway Environment Variables

In your Railway project settings, add these environment variables:

```
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_PRICE_ID_MONTHLY=price_your_monthly_price_id
STRIPE_PRICE_ID_YEARLY=price_your_yearly_price_id
FRONTEND_URL=https://your-railway-app.railway.app
```

### Step 7: Update Database Schema

Run the updated `database_schema_railway.sql` on your Railway MySQL database to add the new Stripe-related columns:

```sql
ALTER TABLE users 
ADD COLUMN stripe_customer_id VARCHAR(255) NULL,
ADD COLUMN stripe_subscription_id VARCHAR(255) NULL,
ADD COLUMN subscription_plan VARCHAR(50) NULL,
ADD COLUMN subscription_end_date DATE NULL;

ALTER TABLE subscriptions 
MODIFY payment_status ENUM('pending', 'completed', 'failed', 'canceled') DEFAULT 'pending',
ADD COLUMN stripe_subscription_id VARCHAR(255) NULL,
ADD COLUMN stripe_price_id VARCHAR(255) NULL;
```

### Step 8: Deploy and Test

1. Commit and push all changes to GitHub
2. Railway will automatically redeploy
3. Test with Stripe test cards:
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
   - Use any future expiry date (e.g., `12/34`)
   - Use any 3-digit CVC (e.g., `123`)

## 📋 Pricing Plans

- **Monthly Plan**: $9.99/month
- **Yearly Plan**: $99.99/year (Save $19.89 - 16% off)

## 🔐 Security Notes

1. **Never expose secret keys** in frontend code
2. Always validate webhook signatures
3. Use HTTPS in production (Railway handles this)
4. Test with test keys before going live

## 🧪 Testing Checklist

- [ ] Create checkout session
- [ ] Complete payment with test card
- [ ] Verify payment success page
- [ ] Check database updated correctly
- [ ] Test subscription cancellation
- [ ] Verify webhook receives events
- [ ] Test subscription renewal

## 🚀 Going Live

When ready for production:

1. Switch to **LIVE keys** in Railway environment variables:
   - `STRIPE_SECRET_KEY` → `sk_live_...`
   - `STRIPE_PUBLISHABLE_KEY` → `pk_live_...`
2. Create live products in Stripe Dashboard
3. Update price IDs to live price IDs
4. Set up live webhook endpoint
5. Update `FRONTEND_URL` to production URL

## 📚 Additional Resources

- Stripe Documentation: https://stripe.com/docs
- Stripe Testing: https://stripe.com/docs/testing
- Webhook Guide: https://stripe.com/docs/webhooks

## 🆘 Troubleshooting

### Issue: "Price ID not configured"
**Solution**: Make sure you set `STRIPE_PRICE_ID_MONTHLY` and `STRIPE_PRICE_ID_YEARLY` in Railway environment variables

### Issue: Webhook not receiving events
**Solution**: 
- Verify webhook URL is accessible (HTTPS required)
- Check webhook signing secret is correct
- Ensure webhook endpoint is listening for correct events

### Issue: Payment succeeds but access not granted
**Solution**: 
- Check webhook is receiving `checkout.session.completed` event
- Verify webhook is updating database correctly
- Check server logs for webhook errors

---

Your Stripe integration is ready! Follow the steps above to complete the setup. 🎉

