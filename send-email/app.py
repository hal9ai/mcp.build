"""
Send Email agent — Hal9-style stdin/stdout agent.

Reads a natural language prompt via input(), uses Groq tool calling to extract
email fields, and sends the email with Resend.
"""

import json
import os
import resend
from groq import Groq

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
RESEND_FROM = os.environ.get("RESEND_FROM", "mcp.build <onboarding@resend.dev>")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": (
                "Send an email to a recipient. Use this when the user asks to "
                "send, email, or message someone."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line. Infer a short subject if not provided.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Plain text body of the email",
                    },
                },
                "required": ["to", "subject", "text"],
            },
        },
    }
]

SYSTEM_PROMPT = (
    "You are an email assistant. When the user wants to send an email, "
    "call the send_email tool with the recipient address, a subject, and the message text. "
    "If the subject is missing, invent a short sensible one from the content. "
    "If required details are missing, ask a brief clarifying question instead of calling the tool."
)


def send_email(to: str, subject: str, text: str) -> str:
    """Send an email via Resend and return a status message."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        return "Error: RESEND_API_KEY environment variable is not set."

    resend.api_key = api_key
    try:
        result = resend.Emails.send(
            {
                "from": RESEND_FROM,
                "to": [to],
                "subject": subject,
                "text": text,
            }
        )
        email_id = result.get("id", result) if isinstance(result, dict) else getattr(result, "id", result)
        return f"Email sent successfully to {to} (id: {email_id})."
    except Exception as e:
        return f"Failed to send email: {e}"


def run(prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY environment variable is not set."

    client = Groq(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.2,
    )
    message = response.choices[0].message

    if not message.tool_calls:
        return message.content or "I could not determine what email to send. Please try again."

    available = {"send_email": send_email}
    results = []

    for tool_call in message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments or "{}")
        fn = available.get(name)
        if not fn:
            results.append(f"Unknown tool: {name}")
            continue
        results.append(fn(**args))

    return "\n".join(results)


if __name__ == "__main__":
    prompt = input()
    print(run(prompt))
