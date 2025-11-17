from agents import Agent, function_tool
from notion_client import Client
import os
from create_lesson import LessonPlan
from agents import Runner
from dotenv import load_dotenv
load_dotenv(override=True)
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
print (f"NOTION_TOKEN: {NOTION_TOKEN}")

#now let's create a new agent that can create database and add items into the database
parent_page_id = "29664f58e96c80039c9dca04384d1a69"
notion = Client(auth=NOTION_TOKEN)

# tool for creating a new database

@function_tool
def create_database(parent_page_id: str) -> str:
    """
    Create a new Notion database under a given parent page ID.

    Args:
        parent_page_id (str): The Notion page ID under which to create the database.

    Returns:
        str: The ID of the newly created database.
        
    """
    database = notion.databases.create(
        parent={"page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Language Learning Database"}}],
        properties={
            "Item": {"title": {}},
            "Meaning": {"rich_text": {}},
            "Item Type": {
                "select": {
                    "options": [
                        {"name": "Vocabulary", "color": "blue"},
                        {"name": "Sentence Pattern", "color": "orange"},
                        {"name": "Dialogue", "color": "green"},
                    ]
                }
            },
            "Mastery Level": {"number": {"format": "number"}},
        },
    )
    return database["id"]  # ✅ Return the database ID so agent can use it

# tool for adding a new language item to the database
@function_tool
def add_language_item(
    database_id: str,
    item: str,
    meaning: str,
    item_type: str,
    mastery_level: int
) -> str:
    """
    Add a new language item to the database.
    """
    new_page = notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "Item": {"title": [{"type": "text", "text": {"content": item}}]},
            "Meaning": {"rich_text": [{"type": "text", "text": {"content": meaning}}]},
            "Item Type": {"select": {"name": item_type}},
            "Mastery Level": {"number": mastery_level},
        },
    )
    return new_page["id"]

db_tools = [create_database, add_language_item]

# ============================================================================
# STEP 1: Create the add_items_agent (works with string messages)
# ============================================================================
# This agent processes lesson plan information and saves items to the database

add_items_instructions = f"""Your job is to save new language items from a lesson plan to a Notion database.

You will receive information about a lesson plan containing:
- lesson_id: The unique ID of the lesson
- created_date: When the lesson was created
- article_content: Contains a list of articles with vocabulary, structures, and expressions
- conversation_content: Contains a conversation topic with vocabulary and sentence patterns

YOUR WORKFLOW:
1. First, create ONE new database/table using the create_database tool under parent page ID {parent_page_id}
   - Do NOT create more than one table
   - The tool will RETURN a database_id - remember this ID for the next step
   
2. Then, extract language items from the lesson plan information provided:
   - From articles: Extract key_vocabulary, key_structures, and key_expressions
   - From conversation content: Extract key_vocabulary and sentence_patterns
   - From conversation content: Extract sample_dialogue
   
3. Add items to the database using add_language_item tool:
   - Use the database_id returned from step 1 as the database_id parameter
   - This tool accepts ONE ITEM AT A TIME, so call it once per item
   - Choose 10 most relevant/useful items for the learner
   - Aim for a good mix: some vocabulary, some sentence patterns, and maybe two dialogues
   - For vocabulary: item_type="Vocabulary", provide the Korean term and English meaning
   - For sentence patterns: item_type="Sentence Pattern", provide the pattern and explanation
   - For dialogues: item_type="Dialogue", provide a short dialogue excerpt and its context
   - Set mastery_level to 0 for all new items (learner hasn't practiced yet)

IMPORTANT:
- Do not add more than 10 items in total
- Choose items that complement each other and provide good learning value
"""

# Create the agent
add_items_agent = Agent(
    name="Add items to database agent",
    instructions=add_items_instructions,
    tools=db_tools,
    model="gpt-4o-mini"
)

# ============================================================================
# STEP 2: Create a wrapper function tool that accepts structured LessonPlan
# ============================================================================
# ✅ KEY: @function_tool decorator automatically handles Pydantic BaseModel parameters!
# This function acts as a bridge: it accepts a LessonPlan object and passes
# it to the add_items_agent in a format it can understand

@function_tool
async def save_lesson_to_database(lesson_plan: LessonPlan) -> str:
    """
    Save language learning items from a lesson plan to a Notion database.
    
    This tool accepts a complete LessonPlan object and extracts relevant items
    to save to the database (vocabulary, sentence patterns, dialogues).
    
    Args:
        lesson_plan: A LessonPlan object containing article_content and conversation_content
        
    Returns:
        str: Confirmation message about items saved
    """
    # Convert the structured LessonPlan object into a detailed message
    # that the add_items_agent can work with
    message = f"""Here is the lesson plan data to process:

Lesson ID: {lesson_plan.lesson_id}
Created Date: {lesson_plan.created_date}

ARTICLE CONTENT:
"""
    
    # Add details from each article
    for i, article in enumerate(lesson_plan.article_content.articles, 1):
        message += f"\nArticle {i}: {article.title}\n"
        message += f"  Vocabulary: {', '.join(article.key_vocabulary)}\n"
        message += f"  Structures: {', '.join(article.key_structures)}\n"
        message += f"  Expressions: {', '.join(article.key_expressions)}\n"
    
    # Add conversation content
    message += f"\nCONVERSATION CONTENT:\n"
    message += f"Topic: {lesson_plan.conversation_content.topic_name}\n"
    message += f"Vocabulary: {', '.join(lesson_plan.conversation_content.key_vocabulary)}\n"
    message += f"Sentence Patterns: {', '.join(lesson_plan.conversation_content.sentence_patterns)}\n"
    message += f"Sample Dialogue:\n{lesson_plan.conversation_content.sample_dialogue}\n"
    
    # Run the add_items_agent with this detailed message
    result = await Runner.run(add_items_agent, message)
    
    return f"Successfully processed lesson {lesson_plan.lesson_id}. Database items have been created."


# ============================================================================
# STEP 3: Create wrapper function for formatting LessonPlan into digest
# ============================================================================
# This wrapper accepts the LessonPlan object and formats it into a readable string
