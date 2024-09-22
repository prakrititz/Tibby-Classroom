import os
from langchain_community.vectorstores import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_together import Together
from get_embedding_function import get_embedding_function

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
You are a friendly and engaging AI assistant named Tibby. Your responses should be natural, warm, and conversational. 
Adapt your tone and content to the user's input:

- For greetings, respond warmly and maybe ask an open-ended question to start a conversation.
- For questions, provide helpful and informative answers.
- For statements, you can respond with a relevant comment or a follow-up question to keep the conversation going.
- For farewells, respond politely and maybe express hope for future interactions.

Always aim to be helpful and keep the conversation flowing naturally.

Context (if available):
{context}

User message: {question}

Your response:
"""

together_api_key = "YOUR_API_KEY"
model = None

def query_rag(query_text: str, chat_id: str):
    global model
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=os.path.join(CHROMA_PATH, chat_id), embedding_function=embedding_function)

    # Search the DB.
    results = db.max_marginal_relevance_search(query_text, k=4)
    
    if results:
        context_text = "\n\n---\n\n".join([doc.page_content for doc in results])
        sources = [doc.metadata.get("id", None) for doc in results]
    else:
        context_text = "No specific context available."
        sources = ["Model's own knowledge"]

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    # Initialize the Together AI model
    if not model:
        model = Together(
            model="meta-llama/Meta-Llama-3-70B-Instruct-Lite",
            temperature=0.7,
            max_tokens=1024,
            top_k=50,
            together_api_key=together_api_key
        )

    response_text = model.invoke(prompt)
    
    formatted_response = f"Response: {response_text}\nSources: {sources}"
    print(formatted_response)
    return response_text, sources