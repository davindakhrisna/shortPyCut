import base64
import subprocess
import os
import sys
from google import genai
from dotenv import load_dotenv

def get_script_dir():
    # Helper to find the current directory of this python file
    return os.path.dirname(os.path.realpath(__file__))

# Load environment variables from .env file located in the same directory
env_path = os.path.join(get_script_dir(), '.env')
load_dotenv(dotenv_path=env_path)

# --- Configuration & Initialization ---
model_name = 'gemini-2.5-flash' # Ensure this model name is valid for your keys
client_primary = None
client_backup = None

try:
    api_key_primary = os.getenv("GOOGLE_API_KEY")
    api_key_backup = os.getenv("GOOGLE_API_KEY_BACKUP")

    if not api_key_primary:
        raise ValueError("GOOGLE_API_KEY not found")
    
    # Initialize Primary Client
    client_primary = genai.Client(api_key=api_key_primary)
    
    # Initialize Backup Client if key exists
    if api_key_backup:
        client_backup = genai.Client(api_key=api_key_backup)
    else:
        print("Warning: GOOGLE_API_KEY_BACKUP not set. No fallback available.")

except Exception as e:
    subprocess.run(["notify-send", "pyCheat Error", f"Init Failed: {str(e)}"])
    sys.exit(1)

def capture_screen():
    """Captures the FULL screen using grim, returns jpeg format bytes."""
    try:
        # grim without -g captures the entire screen by default
        # -t jpeg ensures format, - outputs to stdout
        result = subprocess.run(["grim", "-t", "jpeg", "-"], capture_output=True)
        
        if result.returncode != 0:
            stderr_msg = result.stderr.decode('utf-8')
            raise Exception(f"grim failed: {stderr_msg}")
        
        if not result.stdout:
            raise Exception("grim returned empty data.")
            
        return result.stdout
    except FileNotFoundError:
        raise Exception("grim not found. Install it via 'sudo pacman -S grim'")

def get_answer_with_fallback(image_bytes):
    """
    Sends screenshot to Gemini. 
    Tries Primary Key first. If it fails, tries Backup Key.
    """
    prompt = ("Analyze the problem shown in the image and give me ONLY the answer(s).\n"
              "CRITICAL: You MUST NOT output any steps, headings (like '## Step'), reasoning, formulas, or conversational text.\n"
              "Output EXACTLY the final answer(s) string and nothing else.\n\n"
              "Example 1:\nGiven Question - Does Amy ate the apple? A. Yes, B. No, C. Maybe. You can answer A & C\n\n"
              "Example 2:\nGiven Question - Whats the Integral of ln x? You answer 1/x\n\n"
              "Rules:\n- Do not use MARKDOWN notation, only raw texts\n- Do only emit answers and no other else\n- For calculus problem, please just skip the step by step and straight to answer")

    from google.genai import types
    
    content_list = [
        types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        prompt
    ]

    # 1. Try Primary Client
    try:
        if client_primary is None:
            raise ValueError("Primary client not initialized")
            
        response = client_primary.models.generate_content(
            model=model_name,
            contents=content_list
        )
        return response.text.strip()

    except Exception as e:
        # Log error to stdout for debugging, but don't crash yet
        print(f"Primary API Key failed: {str(e)}. Attempting backup...")
        
        # 2. Try Backup Client
        if client_backup is not None:
            try:
                response = client_backup.models.generate_content(
                    model=model_name,
                    contents=content_list
                )
                # Optional: Notify user that fallback was used
                # notify("Used Backup Key") 
                return response.text.strip()
            except Exception as e_backup:
                raise Exception(f"Both keys failed. Primary: {str(e)} | Backup: {str(e_backup)}")
        else:
            # Re-raise original error if no backup exists
            raise e

def notify(message):
    """Emits an Arch Linux desktop notification."""
    # Using -t 5000 (5 seconds) so it doesn't linger too long
    subprocess.run(["notify-send", "-t", "5000", "--", "pyCheat", message])

if __name__ == "__main__":
    try:
        # 1. Capture Full Screen immediately
        image_bytes = capture_screen()
        
        # 2. Get Answer
        answer = get_answer_with_fallback(image_bytes)
        
        # 3. Notify Result
        if answer:
            notify(answer)
        else:
            notify("No answer received")
            
    except Exception as e:
        notify(f"Error: {str(e)}")
        print(f"Fatal Error: {str(e)}", file=sys.stderr)
