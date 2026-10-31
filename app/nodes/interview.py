"""Dynamic Interview Generation and Answer Validation Node.

Dynamically inspects extracted conditions, detects missing fields in the user profile,
and generates minimal targeted interview questions with type and range validation.
"""

from typing import Any, Dict, List, Optional, Tuple
from app.schemas import Field_, InterviewQuestion, Scheme, UserProfile

# Controlled label, question prompt, and validation specification for each field
FIELD_SPEC: Dict[Field_, dict] = {
    Field_.AGE: {
        "question_text": "What is your age in years?",
        "question_text_hi": "आपकी आयु (उम्र) कितने वर्ष है?",
        "input_type": "number",
        "unit": "years",
        "min": 0,
        "max": 125,
    },
    Field_.ANNUAL_INCOME: {
        "question_text": "What is your total annual household income in INR?",
        "question_text_hi": "आपकी कुल वार्षिक पारिवारिक आय (रुपये में) कितनी है?",
        "input_type": "number",
        "unit": "INR",
        "min": 0,
        "max": 100_000_000_000,
    },
    Field_.LAND_HECTARES: {
        "question_text": "How many hectares of cultivable land do you own?",
        "question_text_hi": "आपके पास कितनी हेक्टेयर कृषि भूमि है? (1 हेक्टेयर = 2.47 एकड़)",
        "input_type": "number",
        "unit": "hectares",
        "min": 0.0,
        "max": 100_000.0,
    },
    Field_.STATE: {
        "question_text": "Which state or union territory do you reside in?",
        "question_text_hi": "आप किस राज्य या केंद्र शासित प्रदेश के निवासी हैं?",
        "input_type": "choice",
        "options": [
            "All India", "Andhra Pradesh", "Assam", "Bihar", "Delhi", "Gujarat",
            "Haryana", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
            "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
            "Uttar Pradesh", "West Bengal", "Other"
        ],
    },
    Field_.CATEGORY: {
        "question_text": "Which social/economic category do you belong to?",
        "question_text_hi": "आप किस सामाजिक/आर्थिक वर्ग से संबंधित हैं?",
        "input_type": "choice",
        "options": ["General", "OBC", "SC", "ST", "EWS"],
    },
    Field_.GENDER: {
        "question_text": "What is your gender?",
        "question_text_hi": "आपका लिंग क्या है?",
        "input_type": "choice",
        "options": ["Male", "Female", "Other"],
    },
    Field_.OCCUPATION: {
        "question_text": "What is your primary occupation?",
        "question_text_hi": "आपका मुख्य व्यवसाय क्या है?",
        "input_type": "text",
        "options": ["Farmer", "Artisan", "Small Business Owner", "Student", "Daily Wage Worker", "Other"],
    },
    Field_.IS_FARMER: {
        "question_text": "Are you or your family actively engaged in farming/agriculture?",
        "question_text_hi": "क्या आप या आपका परिवार कृषि/खेती से जुड़े हैं?",
        "input_type": "boolean",
        "options": ["True", "False"],
    },
    Field_.IS_STUDENT: {
        "question_text": "Are you currently enrolled as a student?",
        "question_text_hi": "क्या आप वर्तमान में एक छात्र/विद्यार्थी हैं?",
        "input_type": "boolean",
        "options": ["True", "False"],
    },
    Field_.HAS_DISABILITY: {
        "question_text": "Do you have a certified disability (Divyangjan)?",
        "question_text_hi": "क्या आपके पास दिव्यांगता प्रमाण पत्र है?",
        "input_type": "boolean",
        "options": ["True", "False"],
    },
    Field_.BUSINESS_TYPE: {
        "question_text": "What is your enterprise classification?",
        "question_text_hi": "आपके व्यवसाय/उद्यम का प्रकार क्या है?",
        "input_type": "choice",
        "options": ["Micro", "Small", "Medium", "Proprietorship", "Partnership", "Other"],
    },
    Field_.ANNUAL_TURNOVER: {
        "question_text": "What is your business annual turnover in INR?",
        "question_text_hi": "आपके व्यवसाय का वार्षिक टर्नओवर (रुपये में) कितना है?",
        "input_type": "number",
        "unit": "INR",
        "min": 0,
        "max": 100_000_000_000,
    },
    Field_.EMPLOYEES: {
        "question_text": "How many full-time employees are in your business?",
        "question_text_hi": "आपके व्यवसाय में कुल कितने कर्मचारी हैं?",
        "input_type": "number",
        "unit": "count",
        "min": 0,
        "max": 1_000_000,
    },
}


def generate_interview_questions(
    scheme: Scheme,
    user_profile: Optional[UserProfile] = None,
    language: str = "en",
) -> List[InterviewQuestion]:
    """Generate minimal interview questions only for fields present in scheme conditions.

    Skips fields that are already answered in the user profile.
    """
    profile_answers = user_profile.answers if user_profile else {}
    needed_fields: list[Field_] = []

    # Identify distinct fields required by conditions
    for cond in scheme.conditions:
        if cond.field not in needed_fields and cond.field not in profile_answers:
            needed_fields.append(cond.field)

    questions: List[InterviewQuestion] = []
    for field in needed_fields:
        spec = FIELD_SPEC.get(
            field,
            {
                "question_text": f"Please provide your value for {field.value.replace('_', ' ')}",
                "question_text_hi": f"कृपया {field.value} का विवरण दें",
                "input_type": "text",
            },
        )

        q_text = spec.get("question_text_hi") if language == "hi" else spec.get("question_text")

        questions.append(
            InterviewQuestion(
                field=field,
                question_text=q_text or spec["question_text"],
                input_type=spec.get("input_type", "text"),
                options=spec.get("options"),
                unit=spec.get("unit"),
            )
        )

    return questions


def validate_answer(field: Field_, raw_value: Any) -> Tuple[bool, Any, Optional[str]]:
    """Validate and cast a raw user answer against the field's schema and bounds.

    Returns:
        (is_valid, cast_value, error_message)
    """
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        return False, None, "Answer cannot be empty."

    spec = FIELD_SPEC.get(field, {})
    input_type = spec.get("input_type", "text")

    try:
        if input_type == "number":
            # Strip commas and currency symbols if user typed '1,50,000' or '₹6000'
            clean_str = str(raw_value).replace(",", "").replace("₹", "").replace("Rs.", "").strip()
            val = float(clean_str)

            min_val = spec.get("min")
            max_val = spec.get("max")
            if min_val is not None and val < min_val:
                return False, None, f"Value must be at least {min_val}."
            if max_val is not None and val > max_val:
                return False, None, f"Value must be at most {max_val}."

            return True, val, None

        if input_type == "boolean":
            if isinstance(raw_value, bool):
                return True, raw_value, None
            s = str(raw_value).strip().lower()
            if s in ["true", "yes", "y", "1", "हाँ", "ha"]:
                return True, True, None
            if s in ["false", "no", "n", "0", "नहीं", "nahi"]:
                return True, False, None
            return False, None, "Please answer with Yes/True or No/False."

        if input_type == "choice":
            val_str = str(raw_value).strip()
            options = spec.get("options", [])
            # Case-insensitive match against allowed options
            for opt in options:
                if opt.lower() == val_str.lower():
                    return True, opt, None
            return False, None, f"Please select one of the allowed options: {', '.join(options)}."

        # Default text
        return True, str(raw_value).strip(), None

    except ValueError:
        return False, None, f"Invalid format for {field.value}. Please enter a valid {input_type}."

