from dotenv import load_dotenv
import asyncio
from agents import Agent, Runner, trace
from create_lesson import create_lesson_agent
from save_to_db import save_lesson_to_database
from send_digest import send_digest_agent
load_dotenv(override=True)

# ============================================================================
# AGENT ARCHITECTURE: Structured Object Passing Between Agents with Handoffs
# ============================================================================
# FLOW:
#   User Request → Orchestrator Agent
#                     ↓ (calls tool)
#                  Lesson Agent (generates LessonPlan object)
#                     ↓ (returns structured LessonPlan)
#                  Orchestrator Agent (receives LessonPlan)
#                     ↓ (passes LessonPlan object to function tool)
#                  save_lesson_to_database (@function_tool wrapper)
#                     ↓ (unpacks LessonPlan and formats for agent)
#                  Add Items Agent (processes formatted data)
#                     ↓ (calls database tools)
#                  Notion Database Updated
#                     ↓
#                  Orchestrator Agent (has LessonPlan)
#                     ↓ (HANDOFF with LessonPlan in context)
#                  Send Digest Agent (receives LessonPlan from context)
#                     ↓ (calls create_lesson_digest wrapper)
#                  create_lesson_digest (@function_tool wrapper)
#                     ↓ (unpacks LessonPlan → formats to readable string)
#                  Send Digest Agent (has digest string)
#                     ↓ (calls emailer_tool)
#                  Emailer Agent (creates subject, converts to HTML, sends)
#                     ↓
#                  Email Sent Successfully
#
# KEY CONCEPTS:
# - lesson_agent outputs a structured LessonPlan object (not a string)
# - @function_tool decorator handles Pydantic BaseModel parameters automatically
# - save_lesson_to_database accepts LessonPlan directly as a parameter
# - Orchestrator hands off to send_digest_agent (passes LessonPlan in context)
# - create_lesson_digest wrapper accepts LessonPlan and returns digest string
# - Type safety is maintained throughout the pipeline
# ============================================================================



orchestrator_instructions = """You are an orchestrator for a Korean language learning system.

Your job is to coordinate tasks and handoff to another agent.

WORKFLOW:
1. First, call the Create_Lesson_Plan tool to generate a complete lesson plan
   - This will return a structured LessonPlan object with articles and conversation content
   
2. Then, call the save_lesson_to_database tool and pass it the LessonPlan object you received
   - Pass the entire lesson_plan object as the parameter
   - This will automatically create a database and save the relevant items

3. Finally, handoff to the send_digest_agent:
   - Pass the LessonPlan object that you received from the Create_Lesson_Plan tool
   - The send_digest_agent will create a lesson digest and email it to the learner

Be efficient: call each tool once and handle any errors gracefully.
"""

# Create the orchestrator agent with access to both tools
orchestrator_agent = Agent(
    name="Orchestrator Agent",
    instructions=orchestrator_instructions,
    tools=[
        create_lesson_agent,           # ✅ Tool 1: Creates a LessonPlan object
        save_lesson_to_database        # ✅ Tool 2: Accepts LessonPlan object (via @function_tool)
    ],
    model="gpt-4o-mini",
    handoffs = [send_digest_agent]
)

async def main():
    """
    Main function that runs the full workflow:
    1. Orchestrator receives user request
    2. Orchestrator calls lesson_agent to create LessonPlan
    3. Orchestrator calls save_lesson_to_database with the LessonPlan
    4. Database items are created
    5. Orchestrator hands off to send_digest_agent with LessonPlan
    6. send_digest_agent formats digest and emails it
    """
    message = "Generate a Korean learning lesson with current topics, save items to my database, and email the lesson digest!"

    with trace("Korean Learning Orchestrator"):
        result = await Runner.run(orchestrator_agent, message)
        print("\n" + "="*80)
        print("ORCHESTRATOR RESULT:")
        print("="*80)
        print(result)
    
asyncio.run(main())