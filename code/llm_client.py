"""
LLM client: abstraction over Groq API for structured output generation.
"""

import json
import time
import logging
from groq import Groq

from config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE, LLM_SEED, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger("triage_agent.llm")

client = None


def init_llm():
    global client
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set. Please set it in your .env file or environment variables."
        )
    client = Groq(api_key=GROQ_API_KEY)
    logger.info(f"Groq API configured with model: {GROQ_MODEL}")


def call_llm(system_prompt: str, user_prompt: str) -> dict:
    global client
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=LLM_TEMPERATURE,
                seed=LLM_SEED,
                max_tokens=2048,
            )
            
            text = response.choices[0].message.content
            if not text:
                logger.warning(f"Empty response on attempt {attempt}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                    continue
                return _fallback_response("LLM returned empty response")
            
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            
            text = text.replace("\\", "/")
            
            result = json.loads(text)
            
            required = {"status", "product_area", "response", "justification", "request_type"}
            if not required.issubset(result.keys()):
                missing = required - result.keys()
                logger.warning(f"Response missing fields: {missing}")
                for field in missing:
                    result[field] = ""
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            return _fallback_response(f"Failed to parse LLM response as JSON: {e}")
            
        except Exception as e:
            logger.error(f"LLM call failed on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
                continue
            return _fallback_response(f"LLM call failed after {MAX_RETRIES} attempts: {e}")
    
    return _fallback_response("Exhausted all retries")


def _fallback_response(reason: str) -> dict:
    logger.error(f"Falling back to escalation: {reason}")
    return {
        "status": "escalated",
        "product_area": "",
        "response": "This request requires human assistance. A support specialist will review your case.",
        "justification": f"Escalated due to processing error: {reason}",
        "request_type": "product_issue",
    }
