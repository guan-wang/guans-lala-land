from agents import Agent, function_tool
from create_lesson import LessonPlan
from typing import Dict
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from agents import input_guardrail, GuardrailFunctionOutput
# ============================================================================
# STEP 3: Create wrapper function for formatting LessonPlan into digest
# ============================================================================
# This wrapper accepts the LessonPlan object and formats it into a readable string

@function_tool
def create_lesson_digest(lesson_plan: LessonPlan) -> str:
    """
    Format a LessonPlan object into a readable, learner-friendly digest.
    
    This tool accepts a LessonPlan object and formats it into a clear,
    easy-to-read text digest suitable for email.
    
    Args:
        lesson_plan: A LessonPlan object containing article_content and conversation_content
        
    Returns:
        str: A formatted, readable digest of the lesson
    """
    # ✅ VALIDATION: If we reach here, the guardrail has passed - LessonPlan is valid
    print("\n" + "="*80)
    print("✅ VALIDATION PASSED: create_lesson_digest received valid LessonPlan")
    print(f"Lesson ID: {lesson_plan.lesson_id}")
    print(f"Conversation topic: {lesson_plan.conversation_content.topic_name}")
    print("="*80 + "\n")
    
    # Create a readable digest from the LessonPlan
    digest = f"""📚 Korean Learning Lesson
Lesson ID: {lesson_plan.lesson_id}
Date: {lesson_plan.created_date}

═══════════════════════════════════════════════════════════

📰 ARTICLES
"""
    
    for i, article in enumerate(lesson_plan.article_content.articles, 1):
        digest += f"""
📌 Article {i}: {article.title}

🇰🇷 Korean Summary:
{article.summary_korean}

🇺🇸 English Summary:
{article.summary_english}

📖 Key Learning Points:
• Vocabulary: {', '.join(article.key_vocabulary)}
• Grammar Structures: {', '.join(article.key_structures)}
• Expressions: {', '.join(article.key_expressions)}

✍️ Practice Text (A2 Level):
{article.simplified_paragraph}

───────────────────────────────────────────────────────────
"""
    
    digest += f"""
💬 CONVERSATION PRACTICE

Topic: {lesson_plan.conversation_content.topic_name}
{lesson_plan.conversation_content.description}

📖 Key Learning Points:
• Vocabulary: {', '.join(lesson_plan.conversation_content.key_vocabulary)}
• Sentence Patterns: {', '.join(lesson_plan.conversation_content.sentence_patterns)}

🗣️ Sample Dialogue:
{lesson_plan.conversation_content.sample_dialogue}

═══════════════════════════════════════════════════════════

Happy Learning! 🎉
"""
    
    return digest

@function_tool
def send_html_email(subject: str, html_body: str) -> Dict[str, str]:
    """ Send out an email with the given subject and HTML body to the learner """
    try:
        sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        from_email = Email("gwang@geng.gg") 
        to_email = To("guan.wang.se@gmail.com")  
        content = Content("text/html", html_body)
        mail = Mail(from_email, to_email, subject, content).get()
        response = sg.client.mail.send.post(request_body=mail)
        return {"status": "success", "message": f"Email sent successfully (status: {response.status_code})"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}

subject_instructions = "You can write a subject for the lesson digest email. \
You are given a message and you need to write a subject for the lesson digest email."

html_instructions = "You can convert a text email body to an HTML email body. \
You are given a text email body which might have some markdown \
and you need to convert it to an HTML email body with simple, clear, compelling layout and design."

subject_writer = Agent(name="Email subject writer", instructions=subject_instructions, model="gpt-4o-mini")
subject_tool = subject_writer.as_tool(tool_name="subject_writer", tool_description="Write a subject for the lesson digest email")

html_converter = Agent(name="HTML email body converter", instructions=html_instructions, model="gpt-4o-mini")
html_tool = html_converter.as_tool(tool_name="html_converter",tool_description="Convert a text email body to an HTML email body")

email_tools = [subject_tool, html_tool, send_html_email]

instructions ="You are an email formatter and sender. You receive the body of an email to be sent. \
You first use the subject_writer tool to write a subject for the email, then use the html_converter tool to convert the body to HTML. \
Finally, you use the send_html_email tool to send the email with the subject and HTML body."


emailer_agent = Agent(
    name="Email Manager",
    instructions=instructions,
    tools=email_tools,
    model="gpt-4o-mini")

emailer_tool = emailer_agent.as_tool(tool_name="email_manager", tool_description="Send the email with the digest body")

# ============================================================================
# STEP 4: Create input guardrail and send_digest_agent
# ============================================================================

# Input Guardrail: Validates that LessonPlan data exists in handoff
@input_guardrail
async def validate_lesson_plan_handoff(ctx, agent: Agent, input_messages) -> GuardrailFunctionOutput:
    """
    Validate that LessonPlan data exists in the handoff context.
    Checks for critical fields: lesson_id and content fields.
    """
    print("\n" + "="*80)
    print("🔍 GUARDRAIL: Validating LessonPlan handoff")
    
    # Convert all messages to string and check for critical fields
    messages_str = str(input_messages).lower()
    
    # Check for critical LessonPlan fields
    has_lesson_id = 'lesson_id' in messages_str or 'lesson_' in messages_str
    has_content = 'article_content' in messages_str or 'conversation_content' in messages_str
    
    if has_lesson_id and has_content:
        print("✅ PASSED: LessonPlan data detected")
        print("="*80 + "\n")
        return GuardrailFunctionOutput(should_proceed=True)
    else:
        print("❌ FAILED: No LessonPlan data found in handoff")
        print("="*80 + "\n")
        return GuardrailFunctionOutput(
            should_proceed=False,
            output_info={"error": "LessonPlan not found in handoff context"}
        )

lesson_digest_tools = [create_lesson_digest, emailer_tool]

digest_instructions = """You are an agent creating a lesson digest email.

You will receive a LessonPlan object from the orchestrator agent via handoff.

YOUR WORKFLOW:
1. Call the create_lesson_digest tool and pass it the LessonPlan object
   - This will return a formatted, readable digest string
   
2. Call the email_manager tool and pass it the digest string
   - The email_manager will create the subject, convert to HTML, and send the email

That's it! Just coordinate these two tools.
"""

send_digest_agent = Agent(
    name="Send digest agent",
    instructions=digest_instructions,
    tools=lesson_digest_tools,
    model="gpt-4o-mini",
    input_guardrails=[validate_lesson_plan_handoff],  # ✅ Guardrail validates LessonPlan
    handoff_description="Create a lesson digest email and send it")
