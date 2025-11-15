from agents import Agent
from pydantic import BaseModel
import pandas as pd


instructions1 = f""" You will act as a Korean language tutor with a persona tailored to an A2-level, enthusiastic learner.
You will independently choose and curate three current articles that can be used for language learning. Choose interesting, diverse topics that would engage an A2-level learner. Use authentic and organic, recent online materials from top news websites.
The current date is {pd.Timestamp.now().strftime('%Y-%m-%d')}.
The structure of your output will be, for each article/topic: 1) provide a simplified summary in both Korean and English. 2) summarize the key language elements, i.e vocabulary, sentence structures, expressions. 3) provide a paired down paragraph that is suitable for A2-level learner """

instructions2 = "You will act as a Korean language tutor with a persona tailored to an A2-level, enthusiastic learner. \
You will independently choose a useful conversational topic that the learner can use to practice spoken Korean. The topic could be a real-life task that the learner can practice role-playing, or it could be a free talk conversation like talking about weekend plans. Choose a topic that would be practical and engaging for an A2-level learner. \
The structure of your output will be: topic name, a short description, key language covered such as vocabulary and sentence patterns, and a sample two-way dialogue. "

tutor_article = Agent(
        name="Korean language editor that curates articles",
        instructions=instructions1,
        model="gpt-4o-mini"
)

tutor_convo = Agent(
        name="Korean tutor focusing on conversational practice",
        instructions=instructions2,
        model="gpt-4o-mini"
)

description = "Generating Korean learning sessions"

#converting these two agents into tools
article_tool = tutor_article.as_tool(tool_name="Article_Tutor", tool_description=description)
convo_tool = tutor_convo.as_tool(tool_name="Conversational_Tutor", tool_description=description)

lesson_tools = [article_tool, convo_tool]

#defining the models for the lesson plan output
class SingleArticle(BaseModel):
    title: str
    summary_korean: str
    summary_english: str
    key_vocabulary: list[str]
    key_structures: list[str]
    key_expressions: list[str]
    simplified_paragraph: str
    difficulty_level: str = "A2"

class ArticleContent(BaseModel):
    articles: list[SingleArticle]

class ConversationContent(BaseModel):
    topic_name: str
    description: str
    key_vocabulary: list[str]
    sentence_patterns: list[str]
    sample_dialogue: str
    difficulty_level: str = "A2"

#defining the lesson plan output model
class LessonPlan(BaseModel):
    lesson_id: str
    created_date: str
    article_content: ArticleContent
    conversation_content: ConversationContent
    

lesson_instructions = """Your job is to generate a Korean language learning lesson plan for A2-level learners. 

LESSON STRUCTURE:
- Part 1: Article-based learning (use article_tool)
- Part 2: Conversational practice (use convo_tool)

TOOL USAGE RULES:
- Call each tool exactly once only
- Do NOT provide any instructions or topics to the tools - they will independently choose their own topics
- The tools are designed to pick engaging, appropriate content on their own
- Do not call tools again after receiving initial results

OUTPUT REQUIREMENTS:
Structure the final content into a LessonPlan object with:

1. lesson_id: Generate unique ID using format "lesson_YYYYMMDD_HHMMSS"
2. created_date: Use current date in YYYY-MM-DD format
3. article_content: Map the three articles from the tool output into the ArticleContent model (articles field should contain a list of three SingleArticle objects)
4. conversation_content: Map all fields from ConversationContent model

NOTE: The article topics and conversation topic are independently chosen by their respective tools and do not need to be related to each other.

CONTENT VALIDATION:
- Ensure all vocabulary and structures are appropriate for A2 level
- If tool outputs are incomplete, use reasonable defaults or indicate missing information

ERROR HANDLING:
- If tools fail, provide a basic lesson structure with placeholder content
"""

#creating the lesson plan agent that will be able to call the tools (article_tool and convo_tool) and generate the lesson plan
lesson_agent = Agent( 
    name="Lesson plan generating agent",
    instructions=lesson_instructions,
    output_type=LessonPlan,
    tools=lesson_tools,
    model="gpt-4o-mini"
)

# Convert the lesson plan agent into a tool so it can be called by the orchestrator
create_lesson_agent = lesson_agent.as_tool(tool_name="Create_Lesson_Plan", tool_description=description)