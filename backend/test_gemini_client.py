import sys
import os

# Add the current directory to path to ensure it finds gemini_client
sys.path.append(os.path.dirname(__file__))

from gemini_client import GeminiAbletonClient

def main():
    # Use the argument from the terminal if provided, otherwise default to a ping
    if len(sys.argv) > 1:
        user_prompt = sys.argv[1]
    else:
        user_prompt = "Can you send a ping to Ableton for me?"

    print(f"Testing GeminiAbletonClient...")
    print(f"User Prompt: {user_prompt}\n")

    client = GeminiAbletonClient()
    
    # We call .chat() because that is what is defined in your gemini_client.py
    response = client.chat(user_prompt)

    print("\nClient Response:")
    print(response)

if __name__ == "__main__":
    main()