import base64
import subprocess
import os
import sys
from google import genai
from dotenv import load_dotenv

def get_script_dir():
    # Helper to find the current directory of this python file
    # to load the .env specifically from here.
    return os.path.dirname(os.path.realpath(__file__))

# Load environment variables from .env file located in the same directory
env_path = os.path.join(get_script_dir(), '.env')
load_dotenv(dotenv_path=env_path)

# Initialize Gemini client
# It will automatically look for the GOOGLE_API_KEY in the environment
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found")
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.5-flash'
except Exception as e:
    subprocess.run(["notify-send", "pyCheat Error", "Failed to initialize Gemini. Did you set GOOGLE_API_KEY in .env?"])
    sys.exit(1)

def capture_screen():
    """Captures a user-selected region using slurp and grim, returns jpeg format bytes."""
    # Use slurp to let user select a region
    slurp_result = subprocess.run(["slurp"], capture_output=True, text=True)
    if slurp_result.returncode != 0:
        raise Exception(f"slurp failed or cancelled: {slurp_result.stderr.decode('utf-8')}")
    geometry = slurp_result.stdout.strip()

    # Use grim to capture the selected region
    result = subprocess.run(["grim", "-g", geometry, "-t", "jpeg", "-"], capture_output=True)
    if result.returncode != 0:
        raise Exception(f"grim failed: {result.stderr.decode('utf-8')}")
    return result.stdout

def get_answer(image_bytes):
    """Sends the screenshot to Gemini API and returns the AI's concise answer."""
    prompt = "Analyze the problem shown in the image and give me ONLY the answer(s).\nCRITICAL: You MUST NOT output any steps, headings (like '## Step'), reasoning, formulas, or conversational text.\nOutput EXACTLY the final answer(s) string and nothing else.\n\nExample 1:\nGiven Question - Does Amy ate the apple? A. Yes, B. No, C. Maybe. You can answer A & C\n\nExample 2:\nGiven Question - Whats the Integral of ln x? You answer 1/x\n\nRules:\n- Do not use MARKDOWN notation, only raw texts\n- Do only emit answers and no other else\n- For calculus problem, please just skip the step by step and straight to answer"

    from google.genai import types

    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt
        ]
    )
    return response.text.strip()

def notify(message):
    """Emits an Arch Linux desktop notification."""
    subprocess.run(["notify-send", "--", "pyCheat", message])

if __name__ == "__main__":
    try:
        image_bytes = capture_screen()
        answer = get_answer(image_bytes)
        notify(answer)
    except Exception as e:
        notify(f"Error: {str(e)}")
