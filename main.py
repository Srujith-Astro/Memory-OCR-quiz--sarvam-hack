import os
import sys
from dotenv import load_dotenv
from sarvamai import SarvamAI

# Load environment variables from .env
load_dotenv()

api_key = os.getenv("SARVAM_API_KEY")
if not api_key:
    print("Error: SARVAM_API_KEY is not set in the environment or .env file.", file=sys.stderr)
    sys.exit(1)

# Initialize the Sarvam client
client = SarvamAI(api_subscription_key=api_key)

# Make a chat completion call with sarvam-105b-conversations
response = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[
        {"role": "user", "content": "Hello! Please introduce yourself briefly in one sentence."}
    ],
)

# Print the reply
print(response.choices[0].message.content)
