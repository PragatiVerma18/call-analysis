import re
import openai
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")


PROFANITY_WORDS = {
    "damn",
    "hell",
    "shit",
    "fuck",
    "asshole",
    "screw",
    "idiot",
    "bastard",
    "bitch",
    "douchebag",
    "jackass",
    "prick",
    "dick",
    "cunt",
    "wanker",
    "bollocks",
    "piss",
    "moron",
    "jerk",
    "dumbass",
    "son of a bitch",
    "motherfucker",
    "arsehole",
    "crap",
    "bugger",
    "twat",
    "slut",
    "whore",
    "dickhead",
    "tosser",
    "retard",
    "scumbag",
    "shithead",
    "numbnuts",
    "dipshit",
}


SENSITIVE_INFO_PATTERNS = [
    r"\b\d{10,16}\b",  # Detects potential account or credit card numbers (10-16 digits)
    r"\b(?:balance|account|SSN|social security number|routing number|card number|CVV|PIN|sort code|IFSC|IBAN)\b",  # Common sensitive financial terms
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN format (XXX-XX-XXXX)
    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card format XXXX-XXXX-XXXX-XXXX
    r"\b\d{9}\b",  # Generic 9-digit numbers (like some tax IDs)
    r"\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b",  # IBAN (common format)
    r"\b(?:dob|date of birth|address|phone number|email|security answer)\b",  # Other personal identifiers
]


def detect_profanity(conversation, method, call_id):
    """Detect profanity in calls using regex or LLM."""
    flagged_calls = []

    if method == "Regex":
        for utterance in conversation:
            words = set(utterance["text"].lower().split())
            if words & PROFANITY_WORDS:
                flagged_calls.append(
                    {
                        "call_id": call_id,  # Use the file name as the call_id
                        "speaker": utterance["speaker"],
                        "timestamp": f"{utterance['stime']} - {utterance['etime']}",
                        "flagged_utterance": utterance["text"],
                        "reason": "Contains profanity",
                    }
                )

    elif method == "LLM":
        flagged_calls = chatgpt_analyze(
            conversation,
            "Identify utterances where the speaker uses profanity. "
            "For each flagged utterance, provide the Call ID, Speaker, Timestamp, Text, and Reason.",
            call_id,
        )

    return flagged_calls


def detect_privacy_violation(conversation, method, call_id):
    """Detect privacy violations using regex or LLM."""
    flagged_calls = []

    if method == "Regex":
        for utterance in conversation:
            if (
                "date of birth" in utterance["text"].lower()
                or "address" in utterance["text"].lower()
            ):
                flagged_calls.append(
                    {
                        "call_id": call_id,  # Use the file name as the call_id
                        "speaker": utterance["speaker"],
                        "timestamp": f"{utterance['stime']} - {utterance['etime']}",
                        "flagged_utterance": utterance["text"],
                        "reason": "Mentions sensitive information (e.g., date of birth, address)",
                    }
                )
            elif any(
                re.search(pattern, utterance["text"], re.IGNORECASE)
                for pattern in SENSITIVE_INFO_PATTERNS
            ):
                flagged_calls.append(
                    {
                        "call_id": call_id,  # Use the file name as the call_id
                        "speaker": utterance["speaker"],
                        "timestamp": f"{utterance['stime']} - {utterance['etime']}",
                        "flagged_utterance": utterance["text"],
                        "reason": "Contains sensitive information (e.g., account number, SSN)",
                    }
                )

    elif method == "LLM":
        flagged_calls = chatgpt_analyze(
            conversation,
            "Identify utterances where sensitive information is shared without proper verification. "
            "For each flagged utterance, provide the Call ID, Speaker, Timestamp, Text, and Reason.",
            call_id,
        )

    return flagged_calls


def chatgpt_analyze(conversation, instruction, call_id):
    """Send conversation data to ChatGPT for analysis."""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # Prepare the conversation text
    conversation_text = "\n".join(
        f"{idx + 1}. {utt['speaker']}: {utt['text']} (Timestamp: {utt['stime']} - {utt['etime']})"
        for idx, utt in enumerate(conversation)
    )

    # Improved prompt
    prompt = f"""
    You are analyzing a debt collection call transcript. Your task is:
    {instruction}

    The transcript is provided below. Each utterance includes the speaker, the text, and the timestamp (start and end times). Identify and flag any utterances that meet the criteria specified in the task. For each flagged utterance, provide the following details:
    - Call ID: {call_id}  # Use the file name as the call_id
    - Speaker: [Speaker Name]
    - Timestamp: [Start Time - End Time]
    - Flagged Utterance: [Text of the utterance]
    - Reason: [Explanation of why it was flagged]

    Transcript:
    {conversation_text}

    Example Output:
    - Call ID: {call_id}
    - Speaker: Agent
    - Timestamp: 0.0 - 5.0
    - Flagged Utterance: "You are an idiot."
    - Reason: "Contains profanity."

    Ensure the output is a structured list of flagged utterances in the format specified above. Do not include any additional commentary or explanations.
    """

    # Send the request to ChatGPT
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI compliance expert."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )

    # Extract and parse the response
    flagged_results = response.choices[0].message.content.strip()

    # Parse the response into a structured format
    flagged_calls = []
    current_call = {}
    for line in flagged_results.split("\n"):
        try:
            if line.startswith("- Call ID:"):
                current_call["call_id"] = call_id
            elif line.startswith("- Speaker:"):
                current_call["speaker"] = line.split(":")[1].strip()
            elif line.startswith("- Timestamp:"):
                current_call["timestamp"] = line.split(":")[1].strip()
            elif line.startswith("- Flagged Utterance:"):
                current_call["flagged_utterance"] = line.split(":")[1].strip()
            elif line.startswith("- Reason:"):
                current_call["reason"] = line.split(":")[1].strip()
                flagged_calls.append(current_call)
                current_call = {}
        except Exception as e:
            print(f"Error parsing line: {line}. Error: {e}")

    return flagged_calls
