import json
import openai
from pydantic import BaseModel, Field
from typing import List, Optional

# Create client
client = openai.OpenAI(
    base_url="https://api.together.xyz/v1",
    api_key="f79744841a9d211621a12f924b810dab2a71a48375b78a094372fb9ae3c9fbe6",
)

class Option(BaseModel):
    text: str
    is_correct: bool

class Question(BaseModel):
    question_text: str
    options: List[Option]
    explanation: str

class Quiz(BaseModel):
    topic: str
    questions: List[Question]

def generate_quiz(topic: str, num_questions: int = 2) -> Optional[Quiz]:
    num_questions = 10
    prompt = f"""Create a quiz on the topic of {topic} with {num_questions} multiple-choice questions. 
    Each question should have 4 options, with only one correct answer. 
    Provide a detailed explanation for why the correct answer is right and why the others are wrong.
    
    Format the response as a JSON object with the following structure:
    {{
      "topic": "string",
      "questions": [
        {{
          "question_text": "string",
          "options": [
            {{"text": "string", "is_correct": boolean}},
            ...
          ],
          "explanation": "string"
        }},
        ...
      ]
    }}
    
    Ensure that the response is valid JSON. Do not include any text before or after the JSON object.
    """

    messages = [
        {"role": "system", "content": "You are an AI specialized in creating educational quizzes. Always respond with valid JSON."},
        {"role": "user", "content": prompt}
    ]

    try:
        response = client.chat.completions.create(
            model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
            messages=messages,
        )

        response_content = response.choices[0].message.content.strip()
        
        # Try to parse the JSON response
        try:
            quiz_data = json.loads(response_content)
        except json.JSONDecodeError as json_error:
            print(f"Error decoding JSON: {json_error}")
            print("Raw response content:")
            print(response_content)
            return None

        # Validate the structure of the parsed data
        if "topic" not in quiz_data or "questions" not in quiz_data:
            print("Error: Invalid quiz structure. Missing 'topic' or 'questions'.")
            return None

        # Create the Quiz object
        quiz = Quiz(**quiz_data)
        return quiz

    except Exception as e:
        print(f"Error generating quiz: {e}")
        return None

def save_quiz_to_json(quiz: Quiz, filename: str):
    with open(filename, 'w') as json_file:
        json.dump(quiz.model_dump(), json_file, indent=2)

def print_quiz(quiz: Quiz):
    print(f"Quiz on: {quiz.topic}\n")
    for i, question in enumerate(quiz.questions, 1):
        print(f"Question {i}: {question.question_text}")
        for j, option in enumerate(question.options, 1):
            print(f"  {j}. {option.text}")
        print(f"\nExplanation: {question.explanation}\n")

if __name__ == '__main__':
    topic = input("Enter the topic for the quiz: ")
    num_questions = int(input("Enter the number of questions: "))
    
    quiz = generate_quiz(topic, num_questions)
    
    if quiz:
        print_quiz(quiz)
        save_quiz_to_json(quiz, 'quiz.json')
        print("Quiz generated successfully and saved to quiz.json!")
    else:
        print("Failed to generate the quiz. Please try again with a different topic or number of questions.")