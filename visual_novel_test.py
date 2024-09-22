import random
from typing import List, Dict

class MascotTeacher:
    def __init__(self):
        self.mood = "neutral"
        self.expressions = {
            "happy": "😊", "neutral": "😐", "angry": "😠",
            "excited": "😃", "disappointed": "😞"
        }
        self.dialogues = {
            "intro": ["Welcome to our educational journey! I'm your guide, Professor Tibby."],
            "correct_answer": ["Excellent work! You're really grasping the material."],
            "wrong_answer": ["Not quite right. Let's review that concept again."],
            "encouragement": ["Keep going! You're doing great."],
            "quiz_end": ["Congratulations on completing the quiz! Let's see how you did."]
        }

    def get_expression(self):
        return self.expressions[self.mood]

    def get_dialogue(self, dialogue_type):
        return random.choice(self.dialogues[dialogue_type])

    def update_mood(self, is_correct):
        self.mood = random.choice(["happy", "excited"]) if is_correct else random.choice(["angry", "disappointed"])

class VisualNovelQuiz:
    def __init__(self, topic: str):
        self.topic = topic
        self.questions = [
            {"question": "What was the capital of Ancient Egypt?", "choices": ["Memphis", "Thebes", "Alexandria", "Cairo"], "answer": "Memphis"},
            {"question": "Who was the sun god in Ancient Egyptian mythology?", "choices": ["Osiris", "Anubis", "Ra", "Horus"], "answer": "Ra"},
            {"question": "What is the name of the ancient Egyptian writing system?", "choices": ["Cuneiform", "Hieroglyphics", "Sanskrit", "Runes"], "answer": "Hieroglyphics"}
        ]
        self.current_question_index = 0
        self.user_answers: List[str] = []
        self.mascot = MascotTeacher()

    def start_quiz(self) -> Dict:
        return {
            "message": self.mascot.get_dialogue("intro"),
            "mascot_expression": self.mascot.get_expression(),
            "question": self.get_current_question()
        }

    def get_current_question(self) -> Dict:
        question = self.questions[self.current_question_index]
        return {
            "question": question["question"],
            "choices": question["choices"],
            "mascot_expression": self.mascot.get_expression()
        }

    def answer_question(self, answer: str) -> Dict:
        current_question = self.questions[self.current_question_index]
        is_correct = answer == current_question["answer"]
        self.user_answers.append(answer)
        self.mascot.update_mood(is_correct)
        
        return {
            "is_correct": is_correct,
            "feedback": self.mascot.get_dialogue("correct_answer" if is_correct else "wrong_answer"),
            "mascot_expression": self.mascot.get_expression(),
        }

    def next_question(self) -> Dict:
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            return self.get_current_question()
        else:
            return {
                "message": self.mascot.get_dialogue("quiz_end"),
                "mascot_expression": self.mascot.get_expression(),
                "final_score": self.get_score(),
                "total_questions": len(self.questions)
            }

    def get_score(self) -> int:
        return sum(1 for q, a in zip(self.questions, self.user_answers) if q["answer"] == a)

def main():
    topic = "Ancient Egypt"
    quiz = VisualNovelQuiz(topic)
    
    print("Welcome to TibbyClassroom!")
    print(quiz.start_quiz()["message"])
    
    for _ in range(len(quiz.questions)):
        question = quiz.get_current_question()
        print(f"\n{question['mascot_expression']} {question['question']}")
        for i, choice in enumerate(question['choices'], 1):
            print(f"{i}. {choice}")
        
        user_answer = input("Enter your answer (1-4): ")
        answer_index = int(user_answer) - 1
        result = quiz.answer_question(question['choices'][answer_index])
        
        print(f"{result['mascot_expression']} {result['feedback']}")
        
        if _ < len(quiz.questions) - 1:
            quiz.next_question()
    
    final_result = quiz.next_question()
    print(f"\n{final_result['mascot_expression']} {final_result['message']}")
    print(f"Your final score: {final_result['final_score']}/{final_result['total_questions']}")

if __name__ == "__main__":
    main()
