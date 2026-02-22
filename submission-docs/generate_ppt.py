"""
Healthcare Claim Validation & Analytics System — Presentation Generator
Generates a professional PPT for project evaluation/submission.
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Color Palette ──────────────────────────────────────────────────
BG_DARK = RGBColor(0x1B, 0x1F, 0x3B)       # Dark navy background
BG_MEDIUM = RGBColor(0x24, 0x2B, 0x4D)     # Slightly lighter navy
ACCENT_BLUE = RGBColor(0x38, 0x7A, 0xDF)   # Primary accent
ACCENT_TEAL = RGBColor(0x00, 0xC9, 0xA7)   # Secondary accent / success
ACCENT_ORANGE = RGBColor(0xFF, 0x8C, 0x42)  # Warning accent
ACCENT_RED = RGBColor(0xE8, 0x4D, 0x5B)    # Error accent
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xB0, 0xB8, 0xD1)
MID_GRAY = RGBColor(0x8A, 0x92, 0xAB)
DARK_TEXT = RGBColor(0x1B, 0x1F, 0x3B)


def set_slide_bg(slide, color):
    """Set solid background color for a slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_shape(slide, left, top, width, height, fill_color, border_color=None):
    """Add a rounded rectangle shape."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    return shape


def add_text_box(slide, left, top, width, height, text, font_size=14,
                 color=WHITE, bold=False, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    """Add a text box with formatted text."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_bullet_text(slide, left, top, width, height, items, font_size=13,
                    color=LIGHT_GRAY, bold_first=False):
    """Add a text box with bullet points."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.space_after = Pt(4)
        p.space_before = Pt(2)

        if isinstance(item, tuple):
            # (bold_part, normal_part)
            run1 = p.add_run()
            run1.text = item[0]
            run1.font.size = Pt(font_size)
            run1.font.color.rgb = WHITE
            run1.font.bold = True
            run1.font.name = "Calibri"
            run2 = p.add_run()
            run2.text = " — " + item[1]
            run2.font.size = Pt(font_size)
            run2.font.color.rgb = color
            run2.font.name = "Calibri"
        else:
            run = p.add_run()
            run.text = "  " + item
            run.font.size = Pt(font_size)
            run.font.color.rgb = color
            run.font.name = "Calibri"
            if bold_first and i == 0:
                run.font.bold = True
    return txBox


def add_card(slide, left, top, width, height, title, items,
             accent_color=ACCENT_BLUE, title_size=14, item_size=12):
    """Add a card-style box with title and bullet items."""
    shape = add_shape(slide, left, top, width, height, BG_MEDIUM, accent_color)

    # Accent bar at top
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, Pt(4)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_color
    bar.line.fill.background()

    # Title
    add_text_box(slide, left + Inches(0.15), top + Pt(10), width - Inches(0.3), Inches(0.4),
                 title, font_size=title_size, color=accent_color, bold=True)

    # Items
    if items:
        add_bullet_text(slide, left + Inches(0.15), top + Inches(0.45),
                        width - Inches(0.3), height - Inches(0.55),
                        items, font_size=item_size, color=LIGHT_GRAY)

    return shape


# ── SLIDE BUILDERS ─────────────────────────────────────────────────

def slide_title(prs):
    """Slide 1: Title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
    set_slide_bg(slide, BG_DARK)

    # Accent line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(1.5), Inches(2.8), Inches(7), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    add_text_box(slide, Inches(1.5), Inches(1.2), Inches(7), Inches(1.5),
                 "Healthcare Claim Validation\n& Analytics System",
                 font_size=36, color=WHITE, bold=True, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(1.5), Inches(3.0), Inches(7), Inches(0.5),
                 "AI-Powered CMS-1500 Claim Processing with HIPAA Compliance",
                 font_size=16, color=ACCENT_TEAL, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(1.5), Inches(4.0), Inches(7), Inches(1.0),
                 "Project Evaluation Submission\nFebruary 2026",
                 font_size=14, color=MID_GRAY, alignment=PP_ALIGN.CENTER)


def slide_problem(prs):
    """Slide 2: Problem Statement."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "The Problem", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_RED
    line.line.fill.background()

    stats = [
        ("$262 Billion", "lost annually to claim denials in US healthcare"),
        ("30%", "of claims are denied on first submission"),
        ("65%", "of denied claims are never resubmitted"),
        ("$25–$118", "average cost to rework a single denied claim"),
    ]

    y = Inches(1.3)
    for stat_val, stat_desc in stats:
        add_card(slide, Inches(0.5), y, Inches(4.2), Inches(0.7),
                 "", [], ACCENT_RED, item_size=11)
        add_text_box(slide, Inches(0.7), y + Pt(6), Inches(1.4), Inches(0.5),
                     stat_val, font_size=20, color=ACCENT_RED, bold=True)
        add_text_box(slide, Inches(2.2), y + Pt(10), Inches(2.4), Inches(0.5),
                     stat_desc, font_size=12, color=LIGHT_GRAY)
        y += Inches(0.85)

    # Right side - challenges
    add_card(slide, Inches(5.2), Inches(1.3), Inches(4.5), Inches(3.7),
             "Key Challenges", [
                 "Manual claim review is slow and error-prone",
                 "Coding errors (ICD-10 / CPT) are the #1 denial reason",
                 "HIPAA compliance makes AI integration complex",
                 "No unified validation + submission pipeline",
                 "Rejection patterns repeat but aren't learned from",
                 "Prior authorization requirements often missed",
             ], ACCENT_ORANGE, item_size=12)


def slide_solution(prs):
    """Slide 3: Solution Overview."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Our Solution", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    # Two components
    add_card(slide, Inches(0.5), Inches(1.3), Inches(4.3), Inches(2.0),
             "claim-validator (Python Library)", [
                 "Reusable, pip-installable validation engine",
                 "8 rule-based + 3 AI-powered validators",
                 "Multi-LLM support (Claude, GPT-4, Ollama)",
                 "HIPAA Safe Harbor de-identification",
                 "Zero-config defaults with full customizability",
             ], ACCENT_BLUE)

    add_card(slide, Inches(5.2), Inches(1.3), Inches(4.5), Inches(2.0),
             "healthcare-claim-analyzer (Django API)", [
                 "Production-ready REST API service",
                 "ClaimMD clearinghouse integration",
                 "Async processing (Celery + Redis)",
                 "Rejection analytics & pattern learning",
                 "MCP server for Claude Code integration",
             ], ACCENT_TEAL)

    # Bottom row - key differentiators
    add_text_box(slide, Inches(0.5), Inches(3.6), Inches(9), Inches(0.4),
                 "Key Differentiators", font_size=18, color=WHITE, bold=True)

    cards_data = [
        ("Dual-Phase\nValidation", "Rule-based + AI\nfor maximum\naccuracy", ACCENT_BLUE),
        ("HIPAA\nCompliant", "PHI encryption,\nde-identification,\naudit logging", ACCENT_TEAL),
        ("Multi-LLM\nSupport", "Anthropic, OpenAI,\nOllama, vLLM,\nLocalAI", ACCENT_ORANGE),
        ("End-to-End\nPipeline", "Validate → Submit\n→ Track → Analyze\n→ Learn", RGBColor(0x9B, 0x5D, 0xE5)),
    ]
    x = Inches(0.5)
    for title, desc, color in cards_data:
        add_card(slide, x, Inches(4.1), Inches(2.18), Inches(1.6),
                 title, [desc], color, title_size=13, item_size=11)
        x += Inches(2.4)


def slide_architecture(prs):
    """Slide 4: System Architecture."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "System Architecture", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_BLUE
    line.line.fill.background()

    # Layer 1 - Client
    add_shape(slide, Inches(0.5), Inches(1.2), Inches(9.2), Inches(0.7), BG_MEDIUM, ACCENT_BLUE)
    add_text_box(slide, Inches(0.7), Inches(1.25), Inches(1.5), Inches(0.3),
                 "CLIENT LAYER", font_size=11, color=ACCENT_BLUE, bold=True)
    add_text_box(slide, Inches(0.7), Inches(1.55), Inches(8.8), Inches(0.3),
                 "REST API Clients  |  MCP Server (Claude Code)  |  Django Admin",
                 font_size=10, color=LIGHT_GRAY)

    # Layer 2 - API
    add_shape(slide, Inches(0.5), Inches(2.05), Inches(9.2), Inches(0.7), BG_MEDIUM, ACCENT_TEAL)
    add_text_box(slide, Inches(0.7), Inches(2.1), Inches(1.5), Inches(0.3),
                 "API LAYER", font_size=11, color=ACCENT_TEAL, bold=True)
    add_text_box(slide, Inches(0.7), Inches(2.4), Inches(8.8), Inches(0.3),
                 "Django REST Framework  →  Claims CRUD  |  Validation  |  Submission  |  Eligibility  |  Analytics",
                 font_size=10, color=LIGHT_GRAY)

    # Layer 3 - Services
    add_shape(slide, Inches(0.5), Inches(2.9), Inches(9.2), Inches(0.7), BG_MEDIUM, ACCENT_ORANGE)
    add_text_box(slide, Inches(0.7), Inches(2.95), Inches(2), Inches(0.3),
                 "SERVICE LAYER", font_size=11, color=ACCENT_ORANGE, bold=True)
    add_text_box(slide, Inches(0.7), Inches(3.25), Inches(8.8), Inches(0.3),
                 "ValidationService  |  SubmissionService  |  EligibilityService  |  AnalyticsService",
                 font_size=10, color=LIGHT_GRAY)

    # Layer 4 - three boxes
    # Validation Pipeline
    add_shape(slide, Inches(0.5), Inches(3.8), Inches(3.2), Inches(1.7), BG_MEDIUM, ACCENT_BLUE)
    add_text_box(slide, Inches(0.7), Inches(3.85), Inches(3), Inches(0.3),
                 "VALIDATION PIPELINE", font_size=10, color=ACCENT_BLUE, bold=True)
    add_text_box(slide, Inches(0.7), Inches(4.15), Inches(2.8), Inches(1.2),
                 "Phase 1: 8 Rule Validators\n  Completeness, NPI, Coding,\n  Demographics, Monetary...\n\nPhase 2: 3 AI Validators\n  Code, Coverage, Prior Auth",
                 font_size=9, color=LIGHT_GRAY)

    # External Integrations
    add_shape(slide, Inches(3.9), Inches(3.8), Inches(2.8), Inches(1.7), BG_MEDIUM, ACCENT_TEAL)
    add_text_box(slide, Inches(4.1), Inches(3.85), Inches(2.6), Inches(0.3),
                 "INTEGRATIONS", font_size=10, color=ACCENT_TEAL, bold=True)
    add_text_box(slide, Inches(4.1), Inches(4.15), Inches(2.4), Inches(1.2),
                 "ClaimMD Clearinghouse\n  Upload, Poll, Eligibility\n\nLLM Providers\n  Anthropic, OpenAI, Ollama\n\nRate Limiter (100 req/min)",
                 font_size=9, color=LIGHT_GRAY)

    # Async Tasks
    add_shape(slide, Inches(6.9), Inches(3.8), Inches(2.8), Inches(1.7), BG_MEDIUM, ACCENT_ORANGE)
    add_text_box(slide, Inches(7.1), Inches(3.85), Inches(2.6), Inches(0.3),
                 "CELERY TASKS", font_size=10, color=ACCENT_ORANGE, bold=True)
    add_text_box(slide, Inches(7.1), Inches(4.15), Inches(2.4), Inches(1.2),
                 "validate_claim_task\nsubmit_claims_task\ncheck_eligibility_task\npoll_all_batches (5 min)\nanalyze_patterns (daily)",
                 font_size=9, color=LIGHT_GRAY)


def slide_tech_stack(prs):
    """Slide 5: Technology Stack."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Technology Stack", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    cards = [
        ("Backend", [
            ("Django 5.2", "Web framework"),
            ("DRF 3.16", "REST API"),
            ("Celery 5.6", "Task queue"),
            ("Redis", "Message broker"),
        ], ACCENT_BLUE),
        ("Data & Security", [
            ("PostgreSQL", "Production database"),
            ("Pydantic 2.x", "Data validation"),
            ("Fernet", "PHI encryption"),
            ("Audit Log", "HIPAA compliance"),
        ], ACCENT_TEAL),
        ("AI / LLM", [
            ("Anthropic SDK", "Claude integration"),
            ("OpenAI SDK", "GPT-4 support"),
            ("httpx", "OpenAI-compatible"),
            ("MCP 1.26", "Claude Code server"),
        ], ACCENT_ORANGE),
        ("Quality", [
            ("pytest 9.0", "Test framework"),
            ("mypy (strict)", "Type checking"),
            ("ruff", "Linting/formatting"),
            ("factory-boy", "Test factories"),
        ], RGBColor(0x9B, 0x5D, 0xE5)),
    ]

    x = Inches(0.3)
    for title, items, color in cards:
        add_card(slide, x, Inches(1.2), Inches(2.3), Inches(2.8),
                 title, [f"{name} — {desc}" for name, desc in items],
                 color, item_size=11)
        x += Inches(2.5)

    # Bottom - Python version note
    add_text_box(slide, Inches(0.5), Inches(4.3), Inches(9), Inches(0.8),
                 "Python 3.11+  |  ~1,050 lines (library) + ~3,000 lines (service)  |  50+ test files  |  Strict type checking",
                 font_size=12, color=MID_GRAY, alignment=PP_ALIGN.CENTER)


def slide_validation_pipeline(prs):
    """Slide 6: Validation Pipeline Deep Dive."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Two-Phase Validation Pipeline", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_BLUE
    line.line.fill.background()

    # Phase 1
    add_card(slide, Inches(0.3), Inches(1.2), Inches(4.6), Inches(4.0),
             "PHASE 1: Rule-Based (Deterministic)", [
                 ("Completeness", "Required fields, diagnosis, lines"),
                 ("NPI Validation", "Luhn check-digit algorithm"),
                 ("Subscriber ID", "Format & placeholder detection"),
                 ("Demographics", "DOB, gender, age consistency"),
                 ("Coding", "ICD-10, CPT/HCPCS format + pointers"),
                 ("Monetary", "Charges, totals, balance checks"),
                 ("Duplicate", "Cross-claim duplicate detection"),
                 ("Timely Filing", "Payer-specific deadline checks"),
             ], ACCENT_BLUE, item_size=11)

    # Arrow
    add_text_box(slide, Inches(4.9), Inches(2.8), Inches(0.5), Inches(0.5),
                 ">>", font_size=24, color=ACCENT_TEAL, bold=True)

    # De-identification
    add_shape(slide, Inches(5.2), Inches(1.2), Inches(4.5), Inches(1.2), BG_MEDIUM, ACCENT_TEAL)
    add_text_box(slide, Inches(5.4), Inches(1.25), Inches(4.1), Inches(0.3),
                 "HIPAA DE-IDENTIFICATION", font_size=11, color=ACCENT_TEAL, bold=True)
    add_text_box(slide, Inches(5.4), Inches(1.55), Inches(4.1), Inches(0.8),
                 "Safe Harbor: Strips all 18 HIPAA identifiers\nRetains: Codes, charges, age, gender, state\nRemoves: Names, DOB, SSN, member ID, address",
                 font_size=10, color=LIGHT_GRAY)

    # Phase 2
    add_card(slide, Inches(5.2), Inches(2.6), Inches(4.5), Inches(2.6),
             "PHASE 2: AI-Powered (LLM Analysis)", [
                 ("CodeValidationAI", "Diagnosis-procedure clinical plausibility"),
                 ("CoverageCheckAI", "Payer coverage likelihood analysis"),
                 ("PriorAuthAI", "Prior authorization requirement detection"),
                 "",
                 "Confidence scoring (>=70% threshold)",
                 "Errors downgraded to warnings if <90%",
                 "Skippable if Phase 1 has errors (configurable)",
             ], ACCENT_ORANGE, item_size=11)


def slide_rule_validators(prs):
    """Slide 7: Rule-Based Validators Detail."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Rule-Based Validators (8)", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_BLUE
    line.line.fill.background()

    validators = [
        ("Completeness", "Verifies all required CMS-1500 fields present\nMin 1 diagnosis, min 1 service line", ACCENT_BLUE),
        ("NPI", "10-digit format + Luhn check-digit validation\nBilling, rendering, and line-level NPIs", ACCENT_TEAL),
        ("Subscriber ID", "Format validation, min length 3\nPlaceholder detection (none/n-a/test)", ACCENT_ORANGE),
        ("Demographics", "DOB in past, age <=130, gender (M/F/U)\nPatient fields required if dependent", RGBColor(0x9B, 0x5D, 0xE5)),
        ("Coding", "ICD-10-CM + CPT/HCPCS format validation\nDiagnosis pointer integrity & bundled codes", ACCENT_BLUE),
        ("Monetary", "Charges > 0, unit count > 0\nLine total = claim total, patient paid <= total", ACCENT_TEAL),
        ("Duplicate", "Cross-claim detection: same subscriber +\nservice date + payer (WARNING level)", ACCENT_ORANGE),
        ("Timely Filing", "Payer-specific deadline enforcement\n30-day warning threshold", RGBColor(0x9B, 0x5D, 0xE5)),
    ]

    x_start = Inches(0.3)
    y_start = Inches(1.15)
    col_width = Inches(2.3)
    row_height = Inches(1.35)

    for i, (name, desc, color) in enumerate(validators):
        col = i % 4
        row = i // 4
        x = x_start + col * (col_width + Inches(0.12))
        y = y_start + row * (row_height + Inches(0.1))

        shape = add_shape(slide, x, y, col_width, row_height, BG_MEDIUM, color)

        # Title
        add_text_box(slide, x + Inches(0.1), y + Pt(6), col_width - Inches(0.2), Inches(0.3),
                     name, font_size=13, color=color, bold=True)

        # Description
        add_text_box(slide, x + Inches(0.1), y + Inches(0.4), col_width - Inches(0.2), Inches(0.9),
                     desc, font_size=9, color=LIGHT_GRAY)


def slide_ai_validators(prs):
    """Slide 8: AI-Powered Validators."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "AI-Powered Validators (3)", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_ORANGE
    line.line.fill.background()

    # Three AI validator cards
    ai_validators = [
        ("Code Validation AI", [
            "Checks clinical plausibility of",
            "diagnosis-procedure combinations",
            "",
            "Detects:",
            "  Gender-specific procedure mismatches",
            "  Age-inappropriate procedures",
            "  Implausible code combinations",
        ], ACCENT_BLUE),
        ("Coverage Check AI", [
            "Evaluates medical necessity and",
            "payer coverage concerns",
            "",
            "Detects:",
            "  Documentation-required procedures",
            "  Non-covered diagnosis codes",
            "  High-cost service flags",
        ], ACCENT_TEAL),
        ("Prior Auth AI", [
            "Identifies services requiring",
            "prior authorization",
            "",
            "Detects:",
            "  High-cost imaging (MRI, CT)",
            "  Surgical procedures",
            "  Specialty medications / DME",
        ], ACCENT_ORANGE),
    ]

    x = Inches(0.3)
    for title, items, color in ai_validators:
        add_card(slide, x, Inches(1.2), Inches(3.1), Inches(2.8),
                 title, items, color, title_size=14, item_size=11)
        x += Inches(3.3)

    # Bottom - LLM support note
    add_shape(slide, Inches(0.3), Inches(4.2), Inches(9.5), Inches(0.9), BG_MEDIUM, ACCENT_TEAL)
    add_text_box(slide, Inches(0.5), Inches(4.25), Inches(9), Inches(0.3),
                 "Multi-Provider LLM Support", font_size=13, color=ACCENT_TEAL, bold=True)
    add_text_box(slide, Inches(0.5), Inches(4.55), Inches(9), Inches(0.5),
                 "Anthropic Claude  |  OpenAI GPT-4  |  Ollama (local)  |  vLLM  |  LocalAI  |  Any OpenAI-compatible endpoint",
                 font_size=11, color=LIGHT_GRAY)


def slide_hipaa(prs):
    """Slide 9: HIPAA Compliance & Security."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "HIPAA Compliance & Security", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    layers = [
        ("Layer 1: Encryption at Rest", [
            "Fernet encryption for all PHI fields",
            "Subscriber name, ID, address encrypted",
            "Patient name, DOB encrypted",
            "django-encrypted-model-fields library",
        ], ACCENT_BLUE),
        ("Layer 2: De-identification Before AI", [
            "HIPAA Safe Harbor method (18 identifiers)",
            "Names, DOB, SSN, member ID removed",
            "Only codes, charges, age, gender retained",
            "Applied before every LLM API call",
        ], ACCENT_TEAL),
        ("Layer 3: Immutable Audit Logging", [
            "Every PHI access logged with timestamp",
            "User, IP address, resource tracked",
            "AuditLog.save() prevents modification",
            "Actions: CREATE, READ, UPDATE, DELETE...",
        ], ACCENT_ORANGE),
        ("Layer 4: Exception Scrubbing", [
            "PHIFilterMiddleware active in pipeline",
            "SSN/DOB patterns removed from errors",
            "No PHI leaks in exception messages",
            "Protects against accidental exposure",
        ], RGBColor(0x9B, 0x5D, 0xE5)),
    ]

    x = Inches(0.2)
    for title, items, color in layers:
        add_card(slide, x, Inches(1.2), Inches(2.35), Inches(2.6),
                 title, items, color, title_size=11, item_size=10)
        x += Inches(2.45)

    # Bottom highlight
    add_shape(slide, Inches(0.3), Inches(4.1), Inches(9.5), Inches(0.7), BG_MEDIUM, ACCENT_TEAL)
    add_text_box(slide, Inches(0.5), Inches(4.2), Inches(9), Inches(0.5),
                 "Zero PHI reaches external LLM providers. All patient data is de-identified using HIPAA\n"
                 "Safe Harbor method before any AI analysis. Complete audit trail for compliance verification.",
                 font_size=11, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)


def slide_django_api(prs):
    """Slide 10: Django REST API."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "REST API Endpoints", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_BLUE
    line.line.fill.background()

    groups = [
        ("Claims CRUD", [
            "GET    /api/v1/claims/",
            "POST  /api/v1/claims/",
            "GET    /api/v1/claims/{id}/",
            "PUT    /api/v1/claims/{id}/",
            "DELETE /api/v1/claims/{id}/",
        ], ACCENT_BLUE),
        ("Validation", [
            "POST /claims/{id}/validate/",
            "POST /claims/batch-validate/",
            "GET   /claims/{id}/validations/",
            "",
            "Sync & async modes supported",
        ], ACCENT_TEAL),
        ("Submission & Eligibility", [
            "POST /claims/{id}/submit/",
            "POST /claims/batch-submit/",
            "POST /claims/{id}/eligibility/",
            "",
            "ClaimMD clearinghouse integration",
        ], ACCENT_ORANGE),
        ("Analytics", [
            "GET /analytics/rejection-summary/",
            "GET /analytics/rejection-trends/",
            "GET /analytics/validator-effectiveness/",
            "GET /analytics/top-rejections/",
        ], RGBColor(0x9B, 0x5D, 0xE5)),
    ]

    x = Inches(0.2)
    for title, items, color in groups:
        add_card(slide, x, Inches(1.2), Inches(2.35), Inches(2.8),
                 title, items, color, title_size=12, item_size=10)
        x += Inches(2.45)

    add_text_box(slide, Inches(0.5), Inches(4.3), Inches(9), Inches(0.5),
                 "Django REST Framework  |  Pagination (50/page)  |  Filtering (status, payer, NPI, dates)  |  Nested serializers",
                 font_size=11, color=MID_GRAY, alignment=PP_ALIGN.CENTER)


def slide_claimmd(prs):
    """Slide 11: ClaimMD Integration & Rejection Analytics."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "ClaimMD Integration & Analytics", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_ORANGE
    line.line.fill.background()

    # ClaimMD integration
    add_card(slide, Inches(0.3), Inches(1.2), Inches(4.7), Inches(2.2),
             "ClaimMD Clearinghouse Integration", [
                 ("Batch Upload", "Submit validated claims to clearinghouse"),
                 ("Status Polling", "Auto-poll every 5 min via Celery beat"),
                 ("Eligibility", "Real-time insurance eligibility checks"),
                 ("Rate Limiting", "Sliding window, 100 req/min default"),
                 ("Error Handling", "Auth errors, rate limits, retry logic"),
             ], ACCENT_ORANGE, item_size=11)

    # Rejection Analytics
    add_card(slide, Inches(5.2), Inches(1.2), Inches(4.5), Inches(2.2),
             "Rejection Analytics Engine", [
                 ("Summary", "Total claims, rejections, rate by category"),
                 ("Trends", "Weekly rejection counts over 90 days"),
                 ("Effectiveness", "Which validators catch most issues"),
                 ("Top Rejections", "Ranked by frequency, actionable"),
                 ("Pattern Learning", "AI + manual pattern detection"),
             ], RGBColor(0x9B, 0x5D, 0xE5), item_size=11)

    # Claim lifecycle
    add_card(slide, Inches(0.3), Inches(3.6), Inches(9.4), Inches(1.4),
             "Claim Status Lifecycle", [
                 "DRAFT  →  VALIDATING  →  VALIDATED  →  SUBMITTING  →  SUBMITTED  →  ACKNOWLEDGED",
                 "                                                                          ↓",
                 "                                              PAID  |  REJECTED  →  APPEALING  |  DENIED",
             ], ACCENT_TEAL, item_size=10)


def slide_data_models(prs):
    """Slide 12: Data Models."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Data Models & Database", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    models = [
        ("Claim + ClaimLine", "CMS-1500 structure with encrypted PHI\nNested service lines, diagnosis codes\nUUID PK, timestamped, indexed", ACCENT_BLUE),
        ("ValidationResult\n+ Finding", "Validation run results with findings\nSeverity (error/warning/info)\nPipeline version tracking (SHA256)", ACCENT_TEAL),
        ("SubmissionBatch", "Batch submission tracking\nClaimMD batch ID, response data\nStatus: pending → submitted → done", ACCENT_ORANGE),
        ("RejectionHistory\n+ Pattern", "Rejection tracking with categorization\nPreventable flag, matched patterns\nAI + manual pattern learning", RGBColor(0x9B, 0x5D, 0xE5)),
        ("EligibilityCheck", "Real-time eligibility results\nEncrypted subscriber data\nPayer + provider + service date", ACCENT_BLUE),
        ("AuditLog", "IMMUTABLE audit trail (HIPAA)\nUser, IP, action, resource\nOverridden save() blocks updates", ACCENT_RED),
    ]

    x_start = Inches(0.2)
    for i, (name, desc, color) in enumerate(models):
        col = i % 3
        row = i // 3
        x = x_start + col * Inches(3.3)
        y = Inches(1.15) + row * Inches(1.85)
        shape = add_shape(slide, x, y, Inches(3.1), Inches(1.7), BG_MEDIUM, color)
        add_text_box(slide, x + Inches(0.1), y + Pt(6), Inches(2.9), Inches(0.4),
                     name, font_size=12, color=color, bold=True)
        add_text_box(slide, x + Inches(0.1), y + Inches(0.55), Inches(2.9), Inches(1.0),
                     desc, font_size=10, color=LIGHT_GRAY)


def slide_mcp_celery(prs):
    """Slide 13: MCP Server & Celery Tasks."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "MCP Server & Async Processing", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_BLUE
    line.line.fill.background()

    # MCP Server
    add_card(slide, Inches(0.3), Inches(1.2), Inches(4.7), Inches(3.0),
             "MCP Server (Claude Code Integration)", [
                 ("validate_claim", "Run full pipeline on claim JSON"),
                 ("lookup_icd10", "Validate ICD-10 code format"),
                 ("lookup_npi", "Validate NPI with Luhn check"),
                 ("analyze_rejection", "Explain rejection + corrective actions"),
                 ("get_rejection_stats", "Rejection rate statistics"),
                 ("list_validators", "List configured validators"),
                 ("check_eligibility", "Real-time eligibility verification"),
             ], ACCENT_BLUE, item_size=11)

    # Celery Tasks
    add_card(slide, Inches(5.2), Inches(1.2), Inches(4.5), Inches(3.0),
             "Celery Async Tasks (Redis Broker)", [
                 ("validate_claim_task", "Async claim validation"),
                 ("submit_claims_task", "Batch ClaimMD submission"),
                 ("check_eligibility_task", "Async eligibility check"),
                 ("poll_all_batches", "Every 5 min (Celery beat)"),
                 ("analyze_patterns", "Daily at 2:00 AM"),
                 "",
                 "acks_late=True for reliability",
                 "reject_on_worker_lost=True",
             ], ACCENT_ORANGE, item_size=11)

    # Bottom note
    add_text_box(slide, Inches(0.5), Inches(4.5), Inches(9), Inches(0.4),
                 "MCP enables AI-assisted billing workflows directly in Claude Code IDE",
                 font_size=12, color=MID_GRAY, alignment=PP_ALIGN.CENTER)


def slide_testing(prs):
    """Slide 14: Testing & Quality."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Testing & Code Quality", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    # Test coverage
    add_card(slide, Inches(0.3), Inches(1.2), Inches(4.7), Inches(2.0),
             "Test Coverage (50+ test files)", [
                 "Unit tests for all 8 rule-based validators",
                 "AI validator tests with mocked LLM responses",
                 "LLM provider tests (Anthropic, OpenAI, Compatible)",
                 "HIPAA de-identification compliance tests",
                 "Code table loading & lookup tests",
                 "Pipeline integration tests (end-to-end)",
                 "API endpoint tests (Django REST Framework)",
             ], ACCENT_TEAL, item_size=11)

    # Quality tools
    add_card(slide, Inches(5.2), Inches(1.2), Inches(4.5), Inches(2.0),
             "Quality Assurance Tools", [
                 ("pytest 9.0", "Test framework with fixtures"),
                 ("mypy (strict)", "Static type checking"),
                 ("ruff", "Fast Python linting & formatting"),
                 ("factory-boy", "Test data factories"),
                 ("pre-commit", "Automated quality hooks"),
                 ("pytest-cov", "Coverage reporting"),
             ], ACCENT_BLUE, item_size=11)

    # Design patterns
    add_card(slide, Inches(0.3), Inches(3.4), Inches(9.4), Inches(1.6),
             "Design Patterns & Best Practices", [
                 ("Abstract Base Classes", "BaseValidator, BaseLLMClient for extension"),
                 ("Factory Pattern", "LLM client factory, Validator registry"),
                 ("Strategy Pattern", "Swappable validators via dotted path config"),
                 ("Builder Pattern", "Fluent ValidationPipeline.builder()"),
                 ("Dependency Injection", "LLM client injected into AI validators"),
                 ("Immutable Models", "Frozen Pydantic models for data integrity"),
             ], ACCENT_ORANGE, item_size=10)


def slide_demo_flow(prs):
    """Slide 15: Prototype Demo Flow."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Prototype Demo Flow", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    steps = [
        ("1", "Create Claim", "POST /api/v1/claims/\nwith CMS-1500 data", ACCENT_BLUE),
        ("2", "Validate", "POST .../validate/\n8 rule + 3 AI checks", ACCENT_TEAL),
        ("3", "Review Findings", "GET .../validations/\nerrors & warnings", ACCENT_ORANGE),
        ("4", "Submit", "POST .../submit/\nto ClaimMD", RGBColor(0x9B, 0x5D, 0xE5)),
        ("5", "Track Status", "Auto-poll every 5m\nACK → PAID/REJ", ACCENT_BLUE),
        ("6", "Analytics", "GET /analytics/...\ntrends & patterns", ACCENT_TEAL),
    ]

    x = Inches(0.15)
    for num, title, desc, color in steps:
        # Circle with number
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, x + Inches(0.45), Inches(1.2), Inches(0.5), Inches(0.5)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = color
        circle.line.fill.background()
        tf = circle.text_frame
        tf.word_wrap = False
        p = tf.paragraphs[0]
        p.text = num
        p.font.size = Pt(18)
        p.font.color.rgb = WHITE
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

        # Card below
        add_shape(slide, x, Inches(1.85), Inches(1.55), Inches(1.3), BG_MEDIUM, color)
        add_text_box(slide, x + Inches(0.08), Inches(1.9), Inches(1.4), Inches(0.3),
                     title, font_size=12, color=color, bold=True)
        add_text_box(slide, x + Inches(0.08), Inches(2.25), Inches(1.4), Inches(0.8),
                     desc, font_size=9, color=LIGHT_GRAY)

        x += Inches(1.65)

    # Demo scenarios
    add_card(slide, Inches(0.3), Inches(3.4), Inches(9.4), Inches(1.6),
             "Demo Scenarios (demo_e2e.py)", [
                 ("Scenario 1: Clean Claim", "Valid CMS-1500 claim passes all rule-based validators"),
                 ("Scenario 2: Broken Claim", "Bad NPI, missing fields, negative charges, duplicates — multiple errors"),
                 ("Scenario 3: De-identification", "Shows PHI stripping: names/dates removed, age/codes retained"),
                 ("Scenario 4: AI Detection", "Male patient with female diagnosis + high-cost MRI → AI flags issues"),
             ], ACCENT_TEAL, item_size=10)


def slide_code_tables(prs):
    """Slide 16: Code Tables & Reference Data."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Healthcare Code Tables", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_ORANGE
    line.line.fill.background()

    tables = [
        ("ICD-10-CM", "Diagnosis code lookup\nFormat-aware (J069 ↔ J06.9)\nCompressed .json.gz", ACCENT_BLUE),
        ("HCPCS / CPT", "Procedure code lookup\n5-char alphanumeric codes\nCompressed .json.gz", ACCENT_TEAL),
        ("Taxonomy", "Provider specialty codes\nNPI taxonomy validation\nCompressed .json.gz", ACCENT_ORANGE),
        ("Place of Service", "POS code descriptions\nFacility type validation\nCompressed .json.gz", RGBColor(0x9B, 0x5D, 0xE5)),
        ("Timely Filing", "Payer-specific deadlines\nDays from service date\nJSON with _default fallback", ACCENT_BLUE),
    ]

    x = Inches(0.15)
    for name, desc, color in tables:
        add_shape(slide, x, Inches(1.2), Inches(1.9), Inches(1.5), BG_MEDIUM, color)
        add_text_box(slide, x + Inches(0.1), Inches(1.25), Inches(1.7), Inches(0.3),
                     name, font_size=12, color=color, bold=True)
        add_text_box(slide, x + Inches(0.1), Inches(1.6), Inches(1.7), Inches(1.0),
                     desc, font_size=10, color=LIGHT_GRAY)
        x += Inches(2.0)

    # Loading pattern
    add_card(slide, Inches(0.3), Inches(2.9), Inches(9.4), Inches(1.5),
             "Thread-Safe Lazy Loading Pattern", [
                 "Code tables loaded on first access, then cached as singletons",
                 "Double-check locking ensures thread safety in concurrent environments",
                 "gzip decompression + JSON parsing at load time",
                 "Format-aware normalization (e.g., ICD-10: J069 → J06.9 with fallback dot insertion)",
                 "CodeTableError exceptions on load/lookup failures with graceful handling",
             ], ACCENT_TEAL, item_size=11)


def slide_future(prs):
    """Slide 17: Future Scope."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Future Scope & Enhancements", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor(0x9B, 0x5D, 0xE5)
    line.line.fill.background()

    items = [
        ("Institutional Claims (UB-04)", "Extend validation pipeline for 837I institutional claims\nbeyond current CMS-1500 / 837P professional claims", ACCENT_BLUE),
        ("ML-Based Rejection Prediction", "Train models on historical rejection patterns to predict\ndenial probability before submission", ACCENT_TEAL),
        ("Real-Time Dashboard", "React/Next.js frontend with live claim status,\nanalytics charts, and validator performance metrics", ACCENT_ORANGE),
        ("Multi-Tenant Architecture", "Support multiple healthcare organizations with\nisolated data, billing, and configuration", RGBColor(0x9B, 0x5D, 0xE5)),
        ("EDI 835 Remittance Processing", "Parse and reconcile payment remittance advices\nwith submitted claims for revenue cycle management", ACCENT_BLUE),
        ("Appeal Automation", "AI-generated appeal letters for denied claims\nwith supporting documentation templates", ACCENT_TEAL),
    ]

    y = Inches(1.15)
    for i, (title, desc, color) in enumerate(items):
        col = i % 2
        row = i // 2
        x = Inches(0.3) + col * Inches(4.9)
        y_pos = Inches(1.15) + row * Inches(1.2)

        shape = add_shape(slide, x, y_pos, Inches(4.7), Inches(1.05), BG_MEDIUM, color)
        add_text_box(slide, x + Inches(0.1), y_pos + Pt(5), Inches(4.5), Inches(0.3),
                     title, font_size=12, color=color, bold=True)
        add_text_box(slide, x + Inches(0.1), y_pos + Inches(0.4), Inches(4.5), Inches(0.6),
                     desc, font_size=10, color=LIGHT_GRAY)


def slide_summary(prs):
    """Slide 18: Project Summary."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    add_text_box(slide, Inches(0.5), Inches(0.3), Inches(9), Inches(0.6),
                 "Project Summary", font_size=28, color=WHITE, bold=True)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(0.5), Inches(0.85), Inches(2), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    metrics = [
        ("11", "Validators\n(8 Rule + 3 AI)"),
        ("15+", "REST API\nEndpoints"),
        ("7", "MCP Server\nTools"),
        ("5", "Celery Async\nTasks"),
        ("50+", "Test Files\n(Comprehensive)"),
        ("6", "Data Models\n(Django ORM)"),
    ]

    x = Inches(0.15)
    for val, label in metrics:
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, x + Inches(0.2), Inches(1.2), Inches(1.0), Inches(1.0)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = BG_MEDIUM
        circle.line.color.rgb = ACCENT_TEAL
        circle.line.width = Pt(2)
        tf = circle.text_frame
        p = tf.paragraphs[0]
        p.text = val
        p.font.size = Pt(22)
        p.font.color.rgb = ACCENT_TEAL
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER

        add_text_box(slide, x, Inches(2.3), Inches(1.4), Inches(0.8),
                     label, font_size=10, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

        x += Inches(1.65)

    # Key accomplishments
    add_card(slide, Inches(0.3), Inches(3.0), Inches(9.4), Inches(2.0),
             "Key Accomplishments", [
                 "Built a production-ready dual-phase validation pipeline (rule-based + AI-powered)",
                 "Implemented full HIPAA compliance: PHI encryption, de-identification, immutable audit logs",
                 "Integrated with ClaimMD clearinghouse for real-time claim submission & status tracking",
                 "Created a multi-provider LLM abstraction (Anthropic, OpenAI, Ollama, vLLM)",
                 "Developed MCP server enabling AI-assisted healthcare billing workflows in Claude Code",
                 "Comprehensive test suite with 50+ test files and strict type checking (mypy)",
             ], ACCENT_TEAL, item_size=11)


def slide_thankyou(prs):
    """Slide 19: Thank You / Q&A."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)

    # Accent line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                  Inches(2), Inches(2.7), Inches(6), Pt(3))
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_TEAL
    line.line.fill.background()

    add_text_box(slide, Inches(1), Inches(1.5), Inches(8), Inches(1.2),
                 "Thank You", font_size=44, color=WHITE, bold=True,
                 alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(1), Inches(2.9), Inches(8), Inches(0.5),
                 "Healthcare Claim Validation & Analytics System",
                 font_size=16, color=ACCENT_TEAL, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(1), Inches(3.6), Inches(8), Inches(0.8),
                 "Questions & Discussion",
                 font_size=20, color=MID_GRAY, alignment=PP_ALIGN.CENTER)

    # Tech badges
    add_text_box(slide, Inches(1), Inches(4.5), Inches(8), Inches(0.4),
                 "Python  |  Django  |  Pydantic  |  Celery  |  Claude AI  |  HIPAA  |  CMS-1500",
                 font_size=12, color=MID_GRAY, alignment=PP_ALIGN.CENTER)


# ── MAIN ───────────────────────────────────────────────────────────

def main():
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)  # 16:9

    # Build all slides
    slide_title(prs)           # 1. Title
    slide_problem(prs)         # 2. Problem Statement
    slide_solution(prs)        # 3. Solution Overview
    slide_architecture(prs)    # 4. System Architecture
    slide_tech_stack(prs)      # 5. Technology Stack
    slide_validation_pipeline(prs)  # 6. Validation Pipeline
    slide_rule_validators(prs) # 7. Rule-Based Validators
    slide_ai_validators(prs)   # 8. AI Validators
    slide_hipaa(prs)           # 9. HIPAA Compliance
    slide_django_api(prs)      # 10. REST API Endpoints
    slide_claimmd(prs)         # 11. ClaimMD & Analytics
    slide_data_models(prs)     # 12. Data Models
    slide_mcp_celery(prs)      # 13. MCP & Celery
    slide_testing(prs)         # 14. Testing & Quality
    slide_demo_flow(prs)       # 15. Demo Flow
    slide_code_tables(prs)     # 16. Code Tables
    slide_future(prs)          # 17. Future Scope
    slide_summary(prs)         # 18. Summary
    slide_thankyou(prs)        # 19. Thank You

    output_path = "/home/lnv-20/Documents/claude/submission-docs/Healthcare_Claim_System_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved to: {output_path}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    main()
