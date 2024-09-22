import json
import openai
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain.output_parsers import PydanticOutputParser
from together import Together
import base64
from PIL import Image
import io, os
from langchain_community.vectorstores import Chroma
from get_embedding_function import get_embedding_function

CHROMA_PATH = "chroma"

client = openai.OpenAI(
    base_url="https://api.together.xyz/v1",
    api_key="YOUR_API_KEY",
)

class Dialogue(BaseModel):
    character: str = Field(default="Tibby", description="The AI teacher character")
    mood: str = Field(description="The mood of Tibby while teaching choose strictly any one from  angry,confused,proud,satisfied,happy,shock,sideeye,amused")
    text: str = Field(description="The dialogue spoken by Tibby")

class TeachingScene(BaseModel):
    scene_id: int = Field(description="Scene identifier")
    background: str = Field(description="Description of scene's background")
    dialogue: Dialogue = Field(description="Dialogue object for Tibby")
    background_image: Optional[str] = Field(default=None, description="Path to the background image")

class VisualTeaching(BaseModel):
    tags: List[str] = Field(description="List of tags for the entire visual novel")
    scenes: List[TeachingScene] = Field(description="List of teaching scenes")

def generate_visual_teaching(topic, chat_id):
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=os.path.join(CHROMA_PATH, chat_id), embedding_function=embedding_function)
    
    results = db.max_marginal_relevance_search(topic, k=5)
    context_text = "\n\n---\n\n".join([doc.page_content for doc in results])

    pydantic_parser = PydanticOutputParser(pydantic_object=VisualTeaching)
    format_instructions = pydantic_parser.get_format_instructions()

    prompt = f'''Create an engaging visual teaching sequence with Tibby, the AI teacher, explaining the topic: {topic}.
    Use the following context to inform the content:
    {context_text}

    Follow these guidelines:
    - Create 7-10 scenes that break down the topic into simple, understandable parts in details.
    - Each scene should have a unique background that relates to the content being taught.
    - Tibby's mood should vary to keep the teaching engaging and reflect the content.
    - The dialogue should be concise, clear, and suitable for the target audience.
    - Use analogies, examples, or interactive elements to make the content relatable and interesting.
    -Generate a list of 1-2 relevant tags for the entire visual novel. These tags should reflect the main themes, concepts, and educational elements of the entire teaching sequence.
    Format the response exactly as shown in the following example:
    {format_instructions}'''

    messages = [
        {
            "role": "system",
            "content": "You are Tibby, a creative AI teacher who can explain any topic in an engaging and simple manner.",
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
        messages=messages,
    )

    try:
        response_content = response.choices[0].message.content
        teaching_sequence = pydantic_parser.parse(response_content)
    except Exception as e:
        print(f"Error parsing the response: {e}")
        return None

    return teaching_sequence

def generate_background_images(teaching_sequence):
    client = Together(api_key = "YOUR_API_KEY")
    
    os.makedirs("./backgrounds", exist_ok=True)
    
    for scene in teaching_sequence.scenes:
        image_path = f'./backgrounds/bg_{scene.scene_id}.png'
        response = client.images.generate(
            prompt=scene.background,
            model="stabilityai/stable-diffusion-xl-base-1.0",
            steps=10,
            n=1,
            height=768,
        )
        image_data = base64.b64decode(response.data[0].b64_json)
        image = Image.open(io.BytesIO(image_data))
        image.save(image_path)
        scene.background_image = image_path

def save_teaching_to_json(teaching_sequence, filename):
    with open(filename, 'w') as json_file:
        json.dump(teaching_sequence.model_dump(), json_file, indent=2)

if __name__ == '__main__':
    topic = input('Please enter the topic you want Tibby to teach: ')
    chat_id = "example_chat_id"  # In a real application, this would be dynamically generated
    teaching_sequence = generate_visual_teaching(topic, chat_id)
    if teaching_sequence:
        generate_background_images(teaching_sequence)
        save_teaching_to_json(teaching_sequence, 'visual_teaching.json')
        print("Visual teaching sequence generated successfully!")
