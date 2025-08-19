import os
from openai import OpenAI

# Test the AIML API
client = OpenAI(
    base_url="https://api.aimlapi.com/v1",
    api_key="f87410da13bb43cd80898ed92a7b13d6",
)

try:
    response = client.chat.completions.create(
        model="openai/gpt-5-2025-08-07",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant who knows everything.",
            },
            {
                "role": "user", 
                "content": "Tell me, why is the sky blue?",
            },
        ],
    )
    
    print(f"✅ API Test Successful!")
    print(f"Full response: {response}")
    
    if response.choices and len(response.choices) > 0:
        message = response.choices[0].message.content
        print(f"Assistant: {message}")
        
        # Also write to file for full output
        with open("api_test_result.txt", "w") as f:
            f.write(f"API Test Result:\nMessage: {message}\nFull Response: {response}")
    else:
        print("No choices in response")
        with open("api_test_result.txt", "w") as f:
            f.write(f"No choices in response. Full response: {response}")
    
except Exception as e:
    print(f"❌ API Test Failed!")
    print(f"Error: {str(e)}")