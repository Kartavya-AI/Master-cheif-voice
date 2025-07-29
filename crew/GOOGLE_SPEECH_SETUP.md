# Google Speech-to-Text Setup Guide

## 1. Create Google Cloud Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign up for a free account (includes $300 free credits)
3. Create a new project or select an existing one

## 2. Enable Speech-to-Text API
1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Speech-to-Text API"
3. Click on it and press **ENABLE**

## 3. Create Service Account
1. Go to **IAM & Admin** > **Service Accounts**
2. Click **CREATE SERVICE ACCOUNT**
3. Enter a name (e.g., "speech-to-text-service")
4. Click **CREATE AND CONTINUE**
5. Add role: **Speech-to-Text Admin** or **Editor**
6. Click **DONE**

## 4. Generate Service Account Key
1. Click on the service account you just created
2. Go to the **KEYS** tab
3. Click **ADD KEY** > **Create new key**
4. Select **JSON** format
5. Download the JSON file

## 5. Set Environment Variable
1. Save the downloaded JSON file securely
2. Set the environment variable:

### Windows:
```bash
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\service-account-key.json
```

### macOS/Linux:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

### In .env file:
```
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\service-account-key.json
```

## 6. Install Dependencies
```bash
pip install google-cloud-speech
```

## Free Tier Limits
- **60 minutes** of speech recognition per month
- Standard models included
- Enhanced models available with limits

## Pricing (after free tier)
- Standard models: $0.006 per 15 seconds
- Enhanced models: $0.009 per 15 seconds
- Data logging models: $0.004 per 15 seconds

## Features
✅ High accuracy speech recognition
✅ Automatic punctuation
✅ Word-level confidence scores
✅ Multiple language support
✅ Real-time and batch processing
✅ Enhanced models for better accuracy
