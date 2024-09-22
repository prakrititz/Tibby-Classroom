from pydantic.v1 import BaseModel, Field
from typing import List
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from query_data import query_rag
from langchain_together import Together

together_api_key = "f79744841a9d211621a12f924b810dab2a71a48375b78a094372fb9ae3c9fbe6"

class MCQ(BaseModel):
    choice: str = Field(description="The text of the multiple-choice option")
    isAnswer: bool = Field(description="True if this choice is the correct answer, False otherwise")

class Question(BaseModel):
    question: str = Field(description="The text of the question")
    choices: List[MCQ] = Field(description="A list of multiple-choice options for this question")

class Quiz(BaseModel):
    topic: str = Field(description="The main topic of the quiz")
    multiple_choice_questions: List[Question] = Field(description="A list of multiple-choice questions for this quiz", min_items=1)

    class Config:
        schema_extra = {
            "example": {
                "topic": "Python Programming",
                "multiple_choice_questions": [
                    {
                        "question": "What is a variable in Python?",
                        "choices": [
                            {"choice": "A container for storing data values", "isAnswer": True},
                            {"choice": "A type of loop", "isAnswer": False},
                            {"choice": "A mathematical operation", "isAnswer": False},
                            {"choice": "A function definition", "isAnswer": False}
                        ]
                    }
                ]
            }
        }


def generate_quiz(topic: str, chat_id : str, numQuestion : int = 3) -> Quiz:
    context, sources = query_rag(f"Provide detailed information about {topic}", chat_id)
    model = Together(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        temperature=0.2,
        max_tokens=1024,
        top_k=50,
        together_api_key=together_api_key
    )

    parser = PydanticOutputParser(pydantic_object=Quiz)
    prompt = PromptTemplate(
    template="""Generate a quiz on the topic of {topic} based on the following information:

{context}

Provide ONLY a valid JSON object enclosed in triple backticks (```) with the following structure:
{{ "topic": "{topic}", "multiple_choice_questions": [ {{ "question": "Question text", "choices": [ {{"choice": "Option 1", "isAnswer": false}}, {{"choice": "Option 2", "isAnswer": false}}, {{"choice": "Option 3", "isAnswer": false}}, {{"choice": "Option 4", "isAnswer": true}} ] }} ] }}
Ensure the quiz has exactly {numQuestion} multiple-choice questions, each with 4 options. Do not include any text before or after the JSON object. The response should contain only the JSON object enclosed in triple backticks.""",
    input_variables=["topic", "context"]
)

    quiz_prompt = prompt.format(topic=topic, context=context, numQuestion = numQuestion)
    response = model.invoke(quiz_prompt)

    try:
        quiz = parser.parse(response)
        return quiz
    except Exception as e:
        print(f"Error parsing quiz: {e}")
        print(f"Raw response: {response}")
        raise

