# Gmail OAuth Redirect URI Setup

## Problem
When running the Gmail OAuth flow, you may get an error like:
```
Error: redirect_uri_mismatch
The redirect URI in the request, http://localhost:XXXXX/, does not match the ones authorized for the OAuth client.
```

This happens because the redirect URI used by the application doesn't match what's configured in Google Cloud Console.

---

## Solution: Configure Redirect URI in Google Cloud Console

### Step 1: Go to Google Cloud Console

1. Visit: https://console.cloud.google.com/
2. Sign in with your Google account
3. Select your project (or create a new one if needed)

### Step 2: Navigate to OAuth Consent Screen

1. In the left sidebar, click **APIs & Services**
2. Click **OAuth consent screen**
3. If not already configured:
   - Choose **External** user type
   - Click **CREATE**
   - Fill in required fields:
     - App name: "ECOWAS Summit TWG System"
     - User support email: your email
     - Developer contact: your email
   - Click **SAVE AND CONTINUE**
   - Skip scopes (click **SAVE AND CONTINUE**)
   - Add test users if needed
   - Click **SAVE AND CONTINUE**

### Step 3: Configure OAuth Client Credentials

1. In the left sidebar, click **Credentials**
2. Find your OAuth 2.0 Client ID (the one with ID: `736599407229-g254ltfkjpj3dc3nnmp5hn1cr8gr6mlu.apps.googleusercontent.com`)
3. Click on the client ID name to edit it

### Step 4: Add Redirect URI

In the **Authorized redirect URIs** section, add this URL:

```
http://localhost:8080/
```

**Important**:
- Include the trailing slash `/`
- Use `http://` (not `https://`) for localhost
- Port must be `8080` (matches the code)

Click **SAVE** at the bottom.

### Step 5: Verify Configuration

After saving, your OAuth client should have:

**Authorized redirect URIs**:
- `http://localhost:8080/`
- `http://localhost:8080` (optional, but some systems need both)

You can add both versions to be safe.

---

## Alternative: Use Multiple Ports

If you want flexibility, you can add multiple redirect URIs:

```
http://localhost:8080/
http://localhost:8081/
http://localhost:8082/
http://localhost:9000/
```

Then the application can use any of these ports.

---

## Testing the OAuth Flow

After configuring the redirect URI:

### 1. Delete existing token (if any)
```bash
rm backend/credentials/gmail_token.json
```

### 2. Run the chat agent
```bash
cd backend
source venv/bin/activate
python scripts/chat_agent.py --agent supervisor
```

### 3. OAuth flow should trigger
- Browser window opens automatically
- You see Google sign-in page
- Choose your Google account
- Click "Allow" to grant Gmail access
- Browser shows: "The authentication flow has completed. You may close this window."
- Terminal shows: "Credentials saved to ./credentials/gmail_token.json"

### 4. Test email functionality
```
You: send a demo report to fredrickodondi9@gmail.com
```

**Expected**: "Email sent successfully! Message ID: [id]"

---

## Troubleshooting

### Error: "redirect_uri_mismatch"

**Solution**:
1. Check that redirect URI in Google Cloud Console is exactly: `http://localhost:8080/`
2. Make sure there's a trailing slash
3. Wait 1-2 minutes for changes to propagate
4. Try again

### Error: "Access blocked: This app's request is invalid"

**Solution**:
1. Make sure OAuth consent screen is configured
2. Add your email as a test user
3. Make sure app is in "Testing" mode (not "Production")

### Browser doesn't open automatically

**Solution**:
1. Look for URL in terminal output
2. Manually copy and paste URL into browser
3. Complete authorization
4. Browser will redirect to localhost:8080

### Port 8080 already in use

**Option 1**: Kill the process using port 8080
```bash
# Find process using port 8080
lsof -ti:8080
# Kill it
kill -9 $(lsof -ti:8080)
```

**Option 2**: Use a different port

Edit [gmail_service.py](app/services/gmail_service.py#L74):
```python
creds = flow.run_local_server(port=8081)  # Use 8081 instead
```

Then add `http://localhost:8081/` to authorized redirect URIs in Google Cloud Console.

---

## Security Notes

### OAuth Credentials
- **gmail_credentials.json** contains OAuth client ID and secret
- These are NOT highly sensitive (they identify your app, not your account)
- Still should not be committed to public repositories

### OAuth Token
- **gmail_token.json** contains your actual access token
- This IS highly sensitive (grants access to YOUR Gmail)
- Must NEVER be committed to any repository
- Already in .gitignore ✅

### Scopes
Current scope: `https://mail.google.com/` (full Gmail access)

If you only need read access, you can change to:
```python
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
```

But note: This will prevent sending emails.

---

## Configuration Files Reference

### Current Configuration

**File**: [app/services/gmail_service.py](app/services/gmail_service.py#L72-L74)
```python
# Use fixed port 8080 for consistent redirect URI
# Make sure to add http://localhost:8080/ to authorized redirect URIs in Google Cloud Console
creds = flow.run_local_server(port=8080)
```

**Redirect URI**: `http://localhost:8080/`

**OAuth Client ID**: `736599407229-g254ltfkjpj3dc3nnmp5hn1cr8gr6mlu.apps.googleusercontent.com`

**Credentials File**: `backend/credentials/gmail_credentials.json`

**Token File**: `backend/credentials/gmail_token.json` (auto-generated after OAuth)

---

## Quick Setup Checklist

- [ ] Go to https://console.cloud.google.com/
- [ ] Navigate to APIs & Services → Credentials
- [ ] Find OAuth client ID: `736599407229-...`
- [ ] Add authorized redirect URI: `http://localhost:8080/`
- [ ] Click SAVE
- [ ] Wait 1-2 minutes
- [ ] Delete old token: `rm backend/credentials/gmail_token.json`
- [ ] Run: `python scripts/chat_agent.py --agent supervisor`
- [ ] Complete OAuth in browser
- [ ] Test: `send a demo report to fredrickodondi9@gmail.com`
- [ ] Verify: Email sent successfully ✅

---

## Additional Resources

- **Google Cloud Console**: https://console.cloud.google.com/
- **Gmail API Documentation**: https://developers.google.com/gmail/api
- **OAuth 2.0 Documentation**: https://developers.google.com/identity/protocols/oauth2

---

**Last Updated**: December 26, 2025
**Status**: Redirect URI configured to use port 8080
**Action Required**: Add `http://localhost:8080/` to Google Cloud Console
