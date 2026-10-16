import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (on pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "MemoryRecall — Gamified Active Recall App (Sarvam AI)")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
            
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_text)
        self.drawString(54, 40, "Confidential & Proprietary — Project Architecture & Guide")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 52, 558, 52)
        self.restoreState()

def create_project_pdf(output_filename="MemoryRecall_Project_Documentation.pdf"):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0F172A") # slate-900
    brand_emerald = colors.HexColor("#059669") # emerald-600
    brand_orange = colors.HexColor("#EA580C")  # sarvam orange
    text_dark = colors.HexColor("#1E293B")
    text_muted = colors.HexColor("#64748B")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=brand_emerald,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=brand_orange,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0F766E")
    )

    story = []

    # Title Banner
    story.append(Paragraph("MemoryRecall — Gamified Active Recall App", title_style))
    story.append(Paragraph("Full-Stack Architecture & Implementation Powered by Sarvam AI", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=brand_emerald, spaceBefore=0, spaceAfter=14))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary & Project Description", h1_style))
    summary_text = (
        "<b>MemoryRecall</b> is an interactive, gamified active recall and spaced repetition learning application. "
        "It empowers students, educators, and lifelong learners to transform raw learning materials—including "
        "<b>handwritten notes, textbook photos, screenshots, and typed summaries</b>—into durable, long-term memory. "
        "By integrating <b>Sarvam AI's Document Intelligence (Doc AI)</b> for handwriting OCR and the <b>sarvam-105b-conversations</b> "
        "large language model for pedagogical study material synthesis, the application creates a continuous learning loop: "
        "<b>Capture &rarr; Extract &rarr; Understand &rarr; Generate &rarr; Practice &rarr; Review &rarr; Retain</b>."
    )
    story.append(Paragraph(summary_text, body_style))

    # Callout Box
    callout_data = [[
        Paragraph("<b>Core Value Proposition:</b> Most flashcard apps require tedious manual data entry. MemoryRecall automates transcription using cutting-edge handwriting OCR, leverages AI to generate conceptual recall prompts rather than superficial flashcards, and reinforces learning with gamified XP, leveling, streaks, and Anki-style SM-2 spaced repetition.", callout_style)
    ]]
    callout_table = Table(callout_data, colWidths=[504])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ECFDF5")),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor("#A7F3D0")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 10))

    # 2. Technology Stack & System Architecture
    story.append(Paragraph("2. System Architecture & Tech Stack", h1_style))
    
    stack_data = [
        [Paragraph("<b>Layer</b>", body_style), Paragraph("<b>Technology</b>", body_style), Paragraph("<b>Key Responsibilities</b>", body_style)],
        [Paragraph("<b>Frontend UI</b>", body_style), Paragraph("HTML5, Tailwind CSS, Lucide Icons, Canvas Confetti", body_style), Paragraph("Responsive SPA (Desktop sidebar + Mobile bottom nav), 3D flip card animations, XP celebrations, Dark/Light modes.", body_style)],
        [Paragraph("<b>Backend API</b>", body_style), Paragraph("FastAPI, Uvicorn, Python 3.11", body_style), Paragraph("REST API endpoints, file uploads handling, business logic orchestration, spaced repetition computations.", body_style)],
        [Paragraph("<b>AI Services</b>", body_style), Paragraph("Sarvam AI Python SDK (<code>sarvamai</code>)", body_style), Paragraph("<b>Doc AI Digitise:</b> Handwriting and textbook OCR.<br/><b>sarvam-105b:</b> Conceptual flashcard and quiz generation.", body_style)],
        [Paragraph("<b>Persistence</b>", body_style), Paragraph("SQLite (<code>data/app.db</code>), Local File Storage", body_style), Paragraph("Zero-configuration local database saving notes, cards, quizzes, streaks, XP, logs, and uploaded image buffers.", body_style)]
    ]
    t_stack = Table(stack_data, colWidths=[100, 160, 244])
    t_stack.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_stack)
    story.append(Spacer(1, 12))

    # 3. Sarvam AI Deep Dive
    story.append(Paragraph("3. Sarvam AI Integration Deep Dive", h1_style))
    
    story.append(Paragraph("A. Document Intelligence & Handwriting OCR (<code>client.doc_ai.digitise</code>)", h2_style))
    ocr_desc = (
        "Users can upload photos of handwritten notebooks, lecture whiteboard slides, or textbook pages. "
        "The system dispatches the image to Sarvam's asynchronous Doc AI digitise pipeline. "
        "The engine identifies document layout structures including paragraphs, headings, lists, tables, and formulas. "
        "The application polls for completion, receives structured JSON coordinates and normalized bounding boxes (<code>bbox_norm</code>), "
        "and presents the extracted text in an editable verification workspace alongside the uploaded image so users can review before generating cards."
    )
    story.append(Paragraph(ocr_desc, body_style))

    story.append(Paragraph("B. Multilingual Cognitive Material Generation (<code>sarvam-105b-conversations</code>)", h2_style))
    llm_desc = (
        "Once verified text is ready, Sarvam's 105B parameter conversational model processes the text through a specialized educational prompt. "
        "Rather than producing rote trivia, it creates conceptual question-and-answer flashcards and 4-option multiple-choice quizzes with detailed rationales. "
        "<b>Multilingual Adaptability:</b> Sarvam AI natively understands English, 11+ Indian languages (Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, etc.), "
        "and code-mixed bilingual inputs (such as Hinglish). When study notes contain non-English or mixed text, the generated questions and explanations "
        "naturally adopt that same language style."
    )
    story.append(Paragraph(llm_desc, body_style))
    story.append(Spacer(1, 8))

    # 4. Core Features & Learning Mechanics
    story.append(Paragraph("4. Core Features & Learning Mechanics", h1_style))
    
    features = [
        ("Daily Home Dashboard", "Presents today's study plan at a glance: flashcards due, new cards, daily goal progress, streak flames, weekly study activity chart, and weak topics diagnostics."),
        ("SuperMemo (SM-2) Spaced Repetition", "Implements the proven SM-2 memory retention algorithm. Each flashcard tracks repetition count, ease factor (1.3 to 3.0), and interval days. Rating cards as Again (&lt;1d), Hard (~1-2d), Good (~4-6d), or Easy (~8-12d) dynamically recalculates optimal review intervals."),
        ("Interactive 3D Flashcards", "Full 3D card flip animation on click or Spacebar. Back of card displays the verified answer, deep explanation, subject tags, and source note reference. Rating buttons are mapped to keyboard shortcuts 1, 2, 3, 4."),
        ("Gamified Interactive Quizzes", "Dynamic multiple-choice questions with instantaneous visual state change upon selection (green for correct, red for incorrect), followed by clear conceptual explanations and XP awards."),
        ("Gamification & Progression System", "Features XP accumulation, level progression (Level 1 Novice &rarr; Level 5 Mind Architect), streak counters, and an unlockable achievement badges shelf (e.g. First Step, Sharp Mind, Flame Keeper, Visionary)."),
        ("Local Persistence & Privacy", "All notes, flashcards, quizzes, study logs, and images are stored locally in SQLite (<code>data/app.db</code>) and <code>data/uploads/</code>, ensuring context is never lost across sessions without requiring mandatory logins.")
    ]

    for title, desc in features:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", bullet_style))

    story.append(Spacer(1, 8))

    # 5. Database Schema & Data Portability
    story.append(Paragraph("5. Database Schema & Storage Model", h1_style))
    schema_desc = (
        "The application utilizes SQLite with 5 primary tables: "
        "<b>notes</b> (source text, image paths, OCR blocks), "
        "<b>flashcards</b> (note relation, Q&A, ease factor, repetition count, due dates), "
        "<b>quizzes</b> (question, JSON options array, correct index, historical accuracy), "
        "<b>user_stats</b> (total XP, current level, daily streaks, unlocked badge IDs, weekly counts), and "
        "<b>study_logs</b> (audit history of every review and quiz attempt for telemetry). "
        "Users can export the complete database as a portable JSON backup at any time from the Settings view."
    )
    story.append(Paragraph(schema_desc, body_style))
    story.append(Spacer(1, 8))

    # 6. How to Run & Quickstart
    story.append(Paragraph("6. Setup & Execution Instructions", h1_style))
    instructions = [
        ("Step 1 — Environment Configuration", "Place your unified Sarvam API key in <code>.env</code> as <code>SARVAM_API_KEY=your_key_here</code> (already protected via <code>.gitignore</code>)."),
        ("Step 2 — Launch Application", "Run <code>python run.py</code> in the terminal. The server starts instantly on <code>http://127.0.0.1:8000</code>."),
        ("Step 3 — Access Web UI", "Open <code>http://127.0.0.1:8000</code> in your browser. You can start reviewing pre-seeded demo decks or click <b>Add Knowledge</b> to digitize notes.")
    ]
    for step, desc in instructions:
        story.append(Paragraph(f"• <b>{step}:</b> {desc}", bullet_style))

    # Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generated successfully: {output_filename}")

if __name__ == "__main__":
    create_project_pdf()
