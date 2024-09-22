import json
from typing import Dict, List
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_together import Together
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from get_embedding_function import get_embedding_function

CHROMA_PATH = "chroma"
together_api_key = "f79744841a9d211621a12f924b810dab2a71a48375b78a094372fb9ae3c9fbe6"
model = None

PROMPT_TEMPLATE = """
Create an educational summary explaining the topic: {topic}. The summary should be presented as Professor Tibby's lecture, without any student interactions. Include:

1. A brief introduction to the topic by Professor Tibby
2. Professor Tibby's explanations of key concepts and principles, delivered with enthusiasm
3. Examples and practical applications provided by Professor Tibby
4. A brief conclusion by Professor Tibby, reinforcing the main points of the topic

Use the following context to inform the content:

{context}

Structure the summary as a monologue from Professor Tibby. Ensure the content is consistent with the given topic and context throughout.

Return the response in the following JSON format:
{{
    "topic": "The main topic of the summary",
    "lecture": [
        {{
            "section": "Introduction",
            "content": "Professor Tibby's introduction to the topic"
        }},
        {{
            "section": "Key Concepts",
            "content": "Professor Tibby's explanation of key concepts"
        }},
        {{
            "section": "Examples and Applications",
            "content": "Professor Tibby's examples and practical applications"
        }},
        {{
            "section": "Conclusion",
            "content": "Professor Tibby's conclusion and summary"
        }}
    ]
}}
"""

class LectureSection(BaseModel):
    section: str = Field(description="Section title of the lecture")
    content: str = Field(description="Content of the lecture section")

class EducationalSummary(BaseModel):
    topic: str = Field(description="The main topic of the summary")
    lecture: List[LectureSection] = Field(description="List of lecture sections")

def generate_additional_queries(topic: str) -> List[str]:
    prompt = f"Generate 3 related search queries to gather more information about '{topic}'. Each query should be on a new line."
    
    small_model = Together(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        temperature=0.7,
        max_tokens=100,
        top_k=50,
        together_api_key=together_api_key
    )
    
    response = small_model.invoke(prompt)
    queries = response.strip().split('\n')
    return queries[:3]  # Ensure we return at most 3 queries

def generate_educational_summary(topic: str, chat_id: str) -> Dict:
    global model
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=os.path.join(CHROMA_PATH, chat_id), embedding_function=embedding_function)

    results = db.max_marginal_relevance_search(topic, k=10)
    context_text = "\n\n---\n\n".join([doc.page_content for doc in results])

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, topic=topic)

    if not model:
        model = Together(
            model="meta-llama/Meta-Llama-3-70B-Instruct-Lite",
            temperature=0.7,
            max_tokens=1024,
            top_k=50,
            together_api_key=together_api_key
        )

    regeneration_count = 0
    while True:
        response = model.invoke(prompt)
        
        try:
            summary = EducationalSummary.parse_raw(response)
            return {
                "summary": summary,
                "sources": [doc.metadata.get("id", None) for doc in results]
            }
        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Error parsing LLM response: {e}")
            print("Raw response:")
            print(response)
            
            choice = input("Enter 'r' to regenerate, 'm' to manually input JSON, or 'q' to quit: ")
            if choice.lower() == 'r':
                regeneration_count += 1
                if regeneration_count <= 3:  # Limit the number of regenerations
                    additional_queries = generate_additional_queries(topic)
                    for query in additional_queries:
                        additional_results = db.max_marginal_relevance_search(query, k=2)
                        context_text += "\n\n---\n\n" + "\n\n---\n\n".join([doc.page_content for doc in additional_results])
                    prompt = prompt_template.format(context=context_text, topic=topic)
                continue
            elif choice.lower() == 'm':
                manual_json = input("Please enter the correct JSON:\n")
                try:
                    summary = EducationalSummary.parse_raw(manual_json)
                    return {
                        "summary": summary,
                        "sources": [doc.metadata.get("id", None) for doc in results]
                    }
                except (json.JSONDecodeError, ValidationError) as e:
                    print(f"Error parsing manual input: {e}")
                    continue
            else:
                raise ValueError("Summary generation failed")

def format_educational_summary(summary: EducationalSummary) -> str:
    output = f"# Professor Tibby's Lecture on: {summary.topic}\n\n"
    for section in summary.lecture:
        output += f"## {section.section}\n\n{section.content}\n\n"
    return output

def save_summary_to_json(summary: EducationalSummary, chat_id: str, filename: str):
    # Create the summaries folder if it doesn't exist
    summaries_dir = os.path.join("chats", chat_id, "summaries")
    os.makedirs(summaries_dir, exist_ok=True)

    # Save the JSON file in the summaries folder
    file_path = os.path.join(summaries_dir, filename)
    with open(file_path, 'w') as f:
        json.dump(summary.dict(), f, indent=2)

    return file_path

def main():
    topic = input("Enter an educational topic for Professor Tibby's lecture: ")
    chat_id = "71784266-1111-4c82-9e32-1d8cd48863ff"
    
    try:
        result = generate_educational_summary(topic, chat_id)
        
        print(f"Here's Professor Tibby's educational summary about {topic}:")
        print(format_educational_summary(result["summary"]))
        print("\nSources:", result["sources"])

        json_filename = f"{topic.replace(' ', '_').lower()}_summary.json"
        file_path = save_summary_to_json(result["summary"], chat_id, json_filename)
        print(f"\nSummary saved to {file_path}")
    except ValueError as e:
        print(f"Failed to generate summary: {e}")

if __name__ == "__main__":
    load_dotenv()
    main()
