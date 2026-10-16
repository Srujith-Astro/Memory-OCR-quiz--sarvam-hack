import os
import json
import time
import re
from typing import Optional, Dict, Any, List
from sarvamai import SarvamAI
from app.config import SARVAM_API_KEY, SARVAM_LLM_MODEL

def get_sarvam_client() -> SarvamAI:
    key = os.getenv("SARVAM_API_KEY") or SARVAM_API_KEY
    if not key:
        raise ValueError("SARVAM_API_KEY is not set. Please add it to your .env file.")
    return SarvamAI(api_subscription_key=key)

def perform_ocr(
    file_bytes: bytes,
    filename: str,
    content_type: str = "handwritten",
    language: str = "en-IN"
) -> Dict[str, Any]:
    """
    Submits an image/document to Sarvam Doc AI digitise endpoint,
    polls for completion, and returns extracted text and layout blocks.
    Supports English (en-IN) and 11+ Indian languages (hi-IN, ta-IN, te-IN, bn-IN, etc.).
    """
    client = get_sarvam_client()

    ext = filename.lower().split(".")[-1]
    mime_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "pdf": "application/pdf"
    }
    mime = mime_map.get(ext, "image/jpeg")

    if content_type not in ["printed", "handwritten", "mixed"]:
        content_type = "handwritten"

    # Start digitise job
    job = client.doc_ai.digitise(
        file=[(filename, file_bytes, mime)],
        content_type=content_type,
        language=language
    )
    job_id = job.job_id

    # Poll job status
    max_wait_seconds = 60
    start_time = time.time()
    completed = False

    while time.time() - start_time < max_wait_seconds:
        status_resp = client.doc_ai.get_status(job_id=job_id)
        current_status = status_resp.status
        if current_status == "completed":
            completed = True
            break
        elif current_status in ["failed", "rejected"]:
            raise RuntimeError(f"Sarvam OCR job {job_id} ended with status: {current_status}")
        time.sleep(1.5)

    if not completed:
        raise TimeoutError(f"Sarvam OCR job {job_id} timed out after {max_wait_seconds} seconds.")

    # Fetch structured JSON results
    results = client.doc_ai.get_results(job_id=job_id, format="json")

    extracted_lines: List[str] = []
    blocks_list: List[Dict[str, Any]] = []

    if hasattr(results, "documents") and results.documents:
        for doc in results.documents:
            for page in (doc.pages or []):
                for b in (page.blocks or []):
                    b_dict = b if isinstance(b, dict) else b.__dict__
                    text = b_dict.get("text", "").strip()
                    if text:
                        extracted_lines.append(text)
                        blocks_list.append({
                            "block_id": b_dict.get("block_id", ""),
                            "layout_tag": b_dict.get("layout_tag", "paragraph"),
                            "reading_order": b_dict.get("reading_order", 0),
                            "text": text,
                            "bbox_norm": b_dict.get("bbox_norm", []),
                            "coordinates": b_dict.get("coordinates", {})
                        })

    full_text = "\n\n".join(extracted_lines) if extracted_lines else ""

    return {
        "job_id": job_id,
        "full_text": full_text,
        "blocks": blocks_list,
        "page_count": len(results.documents[0].pages) if (hasattr(results, "documents") and results.documents and results.documents[0].pages) else 1
    }

def generate_study_materials(
    study_text: str,
    num_cards: int = 4,
    num_quizzes: int = 2,
    subject: Optional[str] = None,
    target_language: Optional[str] = "auto"
) -> Dict[str, Any]:
    """
    Uses Sarvam's sarvam-105b-conversations to generate active-recall flashcards
    and multiple-choice quizzes with explanations.
    Features native multi-language and code-mixed (Indic + English) comprehension.
    """
    client = get_sarvam_client()

    subject_prompt = f"Subject: {subject}\n" if subject else ""

    lang_instruction = ""
    if target_language and target_language != "auto":
        lang_instruction = f"""
LANGUAGE REQUIREMENT:
Generate all questions, answers, and explanations strictly in {target_language}.
"""
    else:
        lang_instruction = """
MULTILINGUAL & ADAPTABILITY INSTRUCTION:
- If the study material is written in an Indian language (e.g., Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati, etc.), or is bilingual/code-mixed with English (e.g., Hinglish/Tanglish), preserve and adapt to that exact language style in the generated flashcards and quizzes!
- The student should be able to actively recall and practice concepts in the same language or bilingual style they took notes in.
- The JSON keys MUST ALWAYS remain strictly in standard English ('flashcards', 'question', 'answer', 'explanation', 'tags', 'quizzes', 'options', 'answer_index') while values match the study language.
"""

    prompt = f"""You are an elite cognitive learning specialist and educator.
Analyze the following study material and generate:
1. Exactly {num_cards} high-quality Active Recall Flashcards. Focus on core concepts, definitions, cause-and-effect relationships, mechanisms, and key distinctions. Every card must have a clear recall prompt question, an accurate answer, and a helpful explanation.
2. Exactly {num_quizzes} interactive Multiple-Choice Quiz questions. Each question must have 4 plausible choices, specify the 0-based index of the correct answer, and provide a clear explanation for why the answer is correct.

{subject_prompt}
{lang_instruction}

Study Material:
\"\"\"
{study_text}
\"\"\"

Output MUST be strictly valid JSON without any markdown formatting, backticks, or preamble:
{{
  "flashcards": [
    {{
      "question": "Clear recall prompt or question",
      "answer": "Concise, precise answer",
      "explanation": "Why this is true / deeper conceptual context",
      "tags": "relevant, comma, separated, tags"
    }}
  ],
  "quizzes": [
    {{
      "question": "Engaging multiple-choice question",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer_index": 0,
      "explanation": "Explanation of the correct option and why others are incorrect"
    }}
  ]
}}
"""

    response = client.chat.completions(
        model=SARVAM_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw_text = response.choices[0].message.content.strip()

    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError(f"Could not parse valid JSON from Sarvam response: {raw_text[:200]}")

    flashcards = data.get("flashcards", [])
    quizzes = data.get("quizzes", [])

    return {
        "flashcards": flashcards,
        "quizzes": quizzes
    }
