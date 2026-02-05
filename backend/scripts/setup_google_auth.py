#!/usr/bin/env python3
"""
Unified Google OAuth Setup
Generates token.json for Calendar, Drive, and Gmail access.
This script is used to bypass Service Account key restrictions.
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# All required scopes for the system
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

def main():
    creds = None
    
    # Check if token exists
    if os.path.exists('token.json'):
        print("Existing token.json found. You can delete it to start fresh.")
    
    # Check for credentials file
    # This should be the 'Client ID' JSON downloaded from Google Console
    creds_file = 'google_credentials.json'
    if not os.path.exists(creds_file):
        # Fallback to standard name
        if os.path.exists('credentials.json'):
            creds_file = 'credentials.json'
            print(f"Using standard '{creds_file}'...")
        else:
            print(f"ERROR: {creds_file} (or credentials.json) not found!")
            print("Please download your OAuth 2.0 Client ID JSON and rename it to 'google_credentials.json' in this folder.")
            return
    
    # Run OAuth flow
    print("Starting OAuth flow...")
    print("A browser window will open. Please authorize the application using your admin account.")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
        
        # The new credentials likely require a strict Redirect URI.
        # We will use port 8080. 
        print("Opening browser for authentication...")
        print("IMPORTANT: Ensure 'http://localhost:8080/' is added to Authorized Redirect URIs in Google Cloud Console.")
        
        creds = flow.run_local_server(port=8080, prompt='select_account')
        
        # Save the credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        
        print("\n✅ SUCCESS! token.json created.")
        print("--------------------------------------------------")
        print("NEXT STEPS:")
        print("1. Open token.json and copy its entire text content.")
        print("2. Go to Railway -> Backend -> Settings -> Variables.")
        print("3. Add/Update 'GOOGLE_TOKEN_JSON' with that content.")
        print("4. Deploy. The system will now have full Google access!")
    except Exception as e:
        print(f"Authentication failed: {e}")

if __name__ == '__main__':
    main()
