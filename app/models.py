from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class FlashcardItem(BaseModel):
    question: str
    answer: str
    explanation: Optional[str] = ""
    tags: Optional[str] = ""

class QuizItem(BaseModel):
    question: str
    options: List[str]
    answer_index: int
    explanation: Optional[str] = ""

class GenerateRequest(BaseModel):
    text: str
    num_cards: Optional[int] = 4
    num_quizzes: Optional[int] = 2
    subject: Optional[str] = "General"
    target_language: Optional[str] = "auto" # 'auto', 'en', 'hi', 'ta', 'te', etc.

class SaveGeneratedRequest(BaseModel):
    title: str
    subject: str
    tags: Optional[str] = ""
    source_type: str = "text" # 'text' or 'image'
    image_path: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    ocr_blocks_json: Optional[str] = None
    content: str
    flashcards: List[FlashcardItem] = []
    quizzes: List[QuizItem] = []

class ReviewCardRequest(BaseModel):
    grade: str # 'again', 'hard', 'good', 'easy'

class QuizAttemptRequest(BaseModel):
    selected_index: int

class SettingsUpdateRequest(BaseModel):
    daily_goal: Optional[int] = None
    theme: Optional[str] = None
