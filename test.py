#!/usr/bin/env python3
"""
Simple test script to check Google API key functionality
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_google_api_key():
    """Test if Google API key is working"""
    print("🧪 Testing Google API Key...")
    
    # Get API key from environment
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables")
        return False
    
    if api_key == "your_google_api_key_here":
        print("❌ GOOGLE_API_KEY is still set to placeholder value")
        return False
    
    try:
        # Initialize Google Gemini model
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        response = llm.invoke("Write me a ballad about LangChain")
        
        print(f"✅ API Key is working!")
        print(f"📝 Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"❌ API Key test failed: {str(e)}")
        
        # Check for specific error types
        if "API_KEY_INVALID" in str(e):
            print("🔑 Error: Invalid API key")
        elif "API key expired" in str(e):
            print("⏰ Error: API key has expired")
        elif "quota" in str(e).lower():
            print("📊 Error: API quota exceeded")
        elif "permission" in str(e).lower():
            print("🚫 Error: Permission denied")
        
        return False

def test_openai_api_key():
    """Test if OpenAI API key is working (optional)"""
    print("\n🧪 Testing OpenAI API Key...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return False
    
    if api_key == "your_openai_api_key_here":
        print("❌ OPENAI_API_KEY is still set to placeholder value")
        return False
    
    try:
        from langchain_openai import ChatOpenAI
        
        model = ChatOpenAI(
            model="gpt-3.5-turbo",
            api_key=api_key,
            temperature=0.1
        )
        
        test_prompt = "Say 'Hello, OpenAI API test successful!' and nothing else."
        
        print("📡 Sending test request to OpenAI...")
        response = model.invoke(test_prompt)
        
        print(f"✅ OpenAI API Key is working!")
        print(f"📝 Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API Key test failed: {str(e)}")
        return False

def main():
    """Run all API key tests"""
    print("🚀 API Key Test Suite\n")
    
    # Test Google API
    google_works = test_google_api_key()
    
    # Test OpenAI API (optional)
    # openai_works = test_openai_api_key()
    
    print(f"\n📊 Test Results:")
    print(f"  Google API: {'✅ Working' if google_works else '❌ Failed'}")
    # print(f"  OpenAI API: {'✅ Working' if openai_works else '❌ Failed'}")
    
    if google_works:
        print("\n🎉 At least one API is working! You can use the Smart Reply Clone.")
    else:
        print("\n⚠️  No APIs are working. Please check your API keys in the .env file.")

if __name__ == "__main__":
    main()
