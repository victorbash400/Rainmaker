"""
Debug script to check the OpenAI API key format
"""

import os
from app.core.config import settings

def debug_api_key():
    """Debug the API key loading"""
    
    print("🔍 Debugging OpenAI API Key...")
    
    # Check raw environment variable
    raw_key = os.getenv("OPENAI_API_KEY")
    print(f"Raw env var: '{raw_key}'")
    print(f"Raw env var length: {len(raw_key) if raw_key else 'None'}")
    print(f"Raw env var starts with: '{raw_key[:20] if raw_key else 'None'}...'")
    
    # Check settings
    settings_key = settings.OPENAI_API_KEY.get_secret_value()
    print(f"Settings key: '{settings_key}'")
    print(f"Settings key length: {len(settings_key)}")
    print(f"Settings key starts with: '{settings_key[:20]}...'")
    
    # Check for extra characters
    if settings_key.startswith('='):
        print("❌ API key has extra '=' at the beginning!")
        corrected_key = settings_key.lstrip('=')
        print(f"Corrected key would be: '{corrected_key[:20]}...'")
    elif settings_key.startswith('sk-'):
        print("✅ API key format looks correct")
    else:
        print(f"❌ API key doesn't start with expected 'sk-': starts with '{settings_key[:10]}'")

if __name__ == "__main__":
    debug_api_key()