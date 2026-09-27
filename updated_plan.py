import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Models to try in order — if primary is overloaded, fallback to next
FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
]


import time

def _generate_text(model_name_ignored, prompt):
    """Generate text using Gemini API with fallback models and retries."""
    last_error = None
    
    for model_name in FALLBACK_MODELS:
        for attempt in range(2):  # 2 retries per model
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return getattr(response, "text", str(response))
            except Exception as e:
                last_error = e
                error_str = str(e)
                # If model not found (404), skip to next model immediately
                if "404" in error_str or "NOT_FOUND" in error_str:
                    break
                # If overloaded (503), wait and retry
                if "503" in error_str or "UNAVAILABLE" in error_str:
                    time.sleep(2 * (attempt + 1))
                    continue
                # For other errors, retry once
                if attempt == 0:
                    time.sleep(1)
                    continue
                break  # Move to next model
    
    raise last_error


def generate_workout_plan(age, weight, goal, intensity):
    prompt = f"""
    Create a 7-day workout plan for a user with the following details:
    Age: {age}, Weight: {weight}, Goal: {goal}, Preferred Intensity: {intensity}.
    Provide a day-by-day schedule tailored to this objective.
    """
    return _generate_text(None, prompt)


def update_workout_plan(existing_plan, feedback):
    prompt = f"""
    Here is an existing 7-day workout plan:
    {existing_plan}
    
    The user has provided the following feedback/changes: "{feedback}".
    Please regenerate and refine the 7-day workout plan based on this feedback.
    """
    return _generate_text(None, prompt)


def generate_nutrition_tip(goal):
    prompt = f"""
    Provide a single, short, and highly relevant nutrition or recovery tip 
    for someone whose fitness goal is "{goal}".
    """
    return _generate_text(None, prompt)