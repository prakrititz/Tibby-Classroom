import json
from typing import List, Dict
from langchain_together import Together
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field, ValidationError
import random
import os
from query_data import query_rag

CHROMA_PATH = "chats"
together_api_key = "f79744841a9d211621a12f924b810dab2a71a48375b78a094372fb9ae3c9fbe6"

class Choice(BaseModel):
    choice: str
    isAnswer: bool

class Question(BaseModel):
    question: str
    choices: List[Choice]

class Quiz(BaseModel):
    topic: str
    questions: List[Question]

class TibbyResponse(BaseModel):
    text: str
    mood: str

class QuizGenerator:
    def __init__(self, topic: str, chat_id: str, num_questions: int):
        self.topic = topic
        self.chat_id = chat_id
        self.num_questions = num_questions
        self.quiz_path = os.path.join(CHROMA_PATH, chat_id, "quiz")
        os.makedirs(self.quiz_path, exist_ok=True)
        self.model = Together(
            model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
            temperature=0.7,
            max_tokens=1024,
            top_k=50,
            together_api_key=together_api_key
        )

    def generate_quiz(self) -> Quiz:
        prompt = PromptTemplate(
            template="""Generate a quiz about {topic} with {num_questions} multiple-choice questions. 
            Each question should have 4 choices, with one correct answer. 
            Provide the output as a JSON object with the following structure:
            {{
                "topic": "The quiz topic",
                "questions": [
                    {{
                        "question": "The question text",
                        "choices": [
                            {{"choice": "Choice 1", "isAnswer": false}},
                            {{"choice": "Choice 2", "isAnswer": false}},
                            {{"choice": "Choice 3", "isAnswer": true}},
                            {{"choice": "Choice 4", "isAnswer": false}}
                        ]
                    }},
                    // ... more questions ...
                ]
            }}
            
            Do not include any text before or after the JSON object.""",
            input_variables=["topic", "num_questions"]
        )

        while True:
            quiz_output = self.model.invoke(prompt.format(topic=self.topic, num_questions=self.num_questions))
            
            json_start = quiz_output.find('{')
            json_end = quiz_output.rfind('}') + 1
            json_content = quiz_output[json_start:json_end]
            
            try:
                quiz = Quiz.parse_raw(json_content)
                self.validate_quiz(quiz)
                return quiz
            except (json.JSONDecodeError, ValidationError) as e:
                print("Validation error occurred. Here's the received JSON:")
                print(json_content)
                print("\nPlease enter the correct JSON data:")
                user_input = input()
                try:
                    quiz = Quiz.parse_raw(user_input)
                    self.validate_quiz(quiz)
                    return quiz
                except ValidationError:
                    print("Invalid input. Trying again...")

    def validate_quiz(self, quiz: Quiz):
        #assert quiz.topic.lower() == self.topic.lower(), "Quiz topic doesn't match the requested topic"
        #assert len(quiz.questions) == self.num_questions, f"Expected {self.num_questions} questions, got {len(quiz.questions)}"
        
        for i, question in enumerate(quiz.questions):
            assert len(question.choices) == 4, f"Question {i+1} doesn't have exactly 4 choices"
            assert sum(choice.isAnswer for choice in question.choices) == 1, f"Question {i+1} doesn't have exactly one correct answer"
            assert len(set(choice.choice for choice in question.choices)) == 4, f"Question {i+1} has duplicate choices"

    def save_quiz(self, quiz: Quiz):
        with open(os.path.join(self.quiz_path, f"{self.topic.replace(' ', '_')}_quiz.json"), "w") as f:
            json.dump(quiz.dict(), f)

    def generate_tibby_response(self, question: str, user_answer: str, correct_answer: str) -> TibbyResponse:
        is_correct = user_answer == correct_answer
        rag_response, sources = query_rag(f"{self.topic} {question}", self.chat_id)
        
        if is_correct:
            mood = "happy"
            response = f"Excellent job! You're correct. {user_answer} is indeed the right answer. Let's move on to the next question!"
        else:
            mood = "thinking"
            response = f"Not quite right. The correct answer is {correct_answer}. Let me explain: {rag_response}"
        
        tibby_response = TibbyResponse(
            text=f"{response}\n\nSources: {', '.join(sources)}",
            mood=mood
        )
        return tibby_response


def create_interactive_quiz(topic: str, chat_id: str, num_questions: int) -> Dict:
    quiz_generator = QuizGenerator(topic, chat_id, num_questions)
    quiz = quiz_generator.generate_quiz()
    quiz_generator.save_quiz(quiz)
    
    return {
        "quiz": quiz.dict(),
        "generate_tibby_response": quiz_generator.generate_tibby_response
    }

if __name__ == "__main__":
    topic = input("Enter a topic for the quiz: ")
    chat_id = input("Enter the chat ID: ")
    num_questions = int(input("Enter the number of questions: "))
    
    quiz_data = create_interactive_quiz(topic, chat_id, num_questions)
    print(json.dumps(quiz_data["quiz"], indent=2))

    play_quiz = input("Would you like to play through the quiz with Tibby? (y/n): ").lower()
    if play_quiz == 'y':
        quiz = Quiz(**quiz_data["quiz"])
        generate_tibby_response = quiz_data["generate_tibby_response"]
        score = 0

        for i, question in enumerate(quiz.questions):
            print(f"\nQuestion {i+1}: {question.question}")
            for j, choice in enumerate(question.choices):
                print(f"{j+1}. {choice.choice}")
            
            user_answer = int(input("Enter your answer (1-4): ")) - 1
            correct_answer = next(i for i, choice in enumerate(question.choices) if choice.isAnswer)
            is_correct = user_answer == correct_answer
            score += is_correct

            tibby_response = generate_tibby_response(question.question, question.choices[user_answer].choice, question.choices[correct_answer].choice)
            print(f"\nProfessor Tibby ({tibby_response.mood}): {tibby_response.text}")

        print(f"\nQuiz completed! Your score: {score}/{len(quiz.questions)}")
