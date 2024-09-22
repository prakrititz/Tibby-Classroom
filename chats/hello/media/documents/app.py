from flask import Flask, render_template, request, Response, stream_with_context, jsonify, send_file, session
import time
import os
from werkzeug.utils import secure_filename
from populate_database import process_youtube_video, add_to_chroma, split_documents, extract_video_id
from query_data import query_rag
from langchain.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from get_embedding_function import get_embedding_function
from youtube_utils import get_video_info
from quiz_utils import generate_quiz, Quiz, MCQ
from query_data import query_rag
from mindmap_utils import generate_mindmap
import json, base64, io, uuid
from datetime import datetime
from urllib.parse import unquote
#from visual_novel_utils import create_visual_novel_quiz
app = Flask(__name__)

CHROMA_PATH = "chroma"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def initialize_database():
    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    return db

def process_pdf(file_path):
    chat_id = session['chat_id']
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    chunks = split_documents(documents)
    add_to_chroma(chunks, chat_id)

# Initialize chat session
@app.before_request
def before_request():
    if 'chat_id' not in session:
        session['chat_id'] = str(uuid.uuid4())
# Create chat directory
def create_chat_directory(chat_id):
    chat_dir = os.path.join('chats', chat_id)
    os.makedirs(chat_dir, exist_ok=True)
    os.makedirs(os.path.join(chat_dir, 'media', 'mindmaps'), exist_ok=True)
    os.makedirs(os.path.join(chat_dir, 'media', 'documents'), exist_ok=True)
    os.makedirs(os.path.join(chat_dir, 'media', 'youtube'), exist_ok=True)
    return chat_dir

# Save chat message
def save_chat_message(chat_id, message, is_user=True):
    chat_dir = create_chat_directory(chat_id)
    messages_file = os.path.join(chat_dir, 'messages.json')

    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            messages = json.load(f)
    else:
        messages = []

    messages.append({
        'content': message,
        'is_user': is_user,
        'timestamp': datetime.now().isoformat()
    })

    with open(messages_file, 'w') as f:
        json.dump(messages, f)

@app.route('/')
def index():
    chat_id = session.get('chat_id', str(uuid.uuid4()))
    media = get_media_list(chat_id)
    return render_template('chat.html', chat_id=chat_id, initial_media=json.dumps(media))

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    chat_id = session['chat_id']
    chat_dir = create_chat_directory(chat_id)
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(chat_dir, 'media', 'documents', filename)
        file.save(file_path)
        process_pdf(file_path)
        return jsonify({"message": "File uploaded and processed successfully"}), 200
    return jsonify({"error": "Invalid file type"}), 400

@app.route('/process_youtube', methods=['POST'])
def process_youtube():
    chat_id = session['chat_id']
    chat_dir = create_chat_directory(chat_id)
    url = request.json.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    video_info = get_video_info(video_id)
    if not video_info:
        return jsonify({"error": "Failed to fetch video information"}), 400

    chunks = process_youtube_video(url)
    add_to_chroma(chunks, chat_id)

    return jsonify({"message": f"YouTube video '{video_info['title']}' processed and indexed."}), 200

def update_chat_name(chat_id, message):
    chat_dir = create_chat_directory(chat_id)
    messages_file = os.path.join(chat_dir, 'messages.json')

    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            messages = json.load(f)
        if len(messages) == 1:  # If this is the first message
            chat_name = message[:50]  # Truncate to 50 characters
            with open(os.path.join(chat_dir, 'chat_name.txt'), 'w') as f:
                f.write(chat_name)

@app.route('/send', methods=["POST"])
def send():
    chat_id = request.form.get("chat_id")
    msg = request.form.get("msg", "")
    save_chat_message(chat_id, msg)

    # Update chat name if it's the first message
    update_chat_name(chat_id, msg)

    return "Message received"

@app.route('/stream', methods=["GET"])
def stream():
    chat_id = session['chat_id']

    def generate_response():
        message = request.args.get('msg', '')
        db = initialize_database()
        response, sources = query_rag(message, chat_id)

        for word in response.split():
            yield f"data: {word+' '}\n\n"
            time.sleep(0.05)
        yield f"data: [EOS]\n\n"

        for source in sources:
            yield f"data: SOURCE: {source+' '}\n\n"
        yield "data: [DONE]\n\n"
        save_chat_message(chat_id, response, is_user=False)

    return Response(stream_with_context(generate_response()), content_type='text/event-stream')

session = {}
@app.route('/generate_quiz', methods=['POST'])
def create_quiz():
    chat_id = session['chat_id']
    data = request.json
    topic = data.get('topic')
    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    quiz = generate_quiz(topic, chat_id)
    # Store the quiz in the session for later evaluation
    session['current_quiz'] = quiz.model_dump()

    # Return the quiz without the correct answers
    return jsonify({
        "topic": quiz.topic,
        "questions": [
            {
                "question": q.question,
                "choices": [c.choice for c in q.choices]
            } for q in quiz.multiple_choice_questions
        ]
    }), 200

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.json
    user_answers = data.get('answers')
    if not user_answers:
        return jsonify({"error": "No answers provided"}), 400

    current_quiz = session.get('current_quiz')
    if not current_quiz:
        return jsonify({"error": "No active quiz found"}), 400

    quiz = Quiz.model_validate(current_quiz)
    score = 0
    total = len(quiz.multiple_choice_questions)

    for i, question in enumerate(quiz.multiple_choice_questions):
        if i < len(user_answers):
            user_choice = user_answers[i]
            correct_choice = next(j for j, choice in enumerate(question.choices) if choice.isAnswer)
            if user_choice == correct_choice:
                score += 1

    # Clear the quiz from the session
    session.pop('current_quiz', None)

    return jsonify({
        "score": score,
        "total": total,
        "percentage": (score / total) * 100
    }), 200

@app.route('/create_mindmap', methods=['POST'])
def create_mindmap():
    chat_id = session['chat_id']
    chat_dir = create_chat_directory(chat_id)
    data = request.json
    topic = data.get('topic')
    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    mindmap_data = generate_mindmap(topic, chat_id)

    # Save the mindmap data as JSON
    filename = f"{topic.replace(' ', '_')}_mindmap.json"
    filename = filename.replace('_mindmap.json', '.json')
    filepath = os.path.join(chat_dir, 'media', 'mindmaps', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(mindmap_data, f)

    return jsonify({
        "message": "Mindmap created successfully",
        "filename": filename
    }), 200

@app.route('/save_mindmap', methods=['POST'])
def save_mindmap():
    data = request.json
    image_data = data.get('imageData')
    if not image_data:
        return jsonify({"error": "No image data provided"}), 400

    # Remove the data URL prefix
    image_data = image_data.split(',')[1]

    # Decode the base64 string
    image_bytes = base64.b64decode(image_data)

    # Create a file-like object
    image_file = io.BytesIO(image_bytes)

    # Send the file
    return send_file(image_file, mimetype='image/png', as_attachment=True, download_name='mindmap.png')


@app.route('/get_chat_history/<chat_id>')
def get_chat_history(chat_id):
    chat_dir = create_chat_directory(chat_id)
    messages_file = os.path.join(chat_dir, 'messages.json')

    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            messages = json.load(f)
    else:
        messages = []

    media = get_media_list(chat_id)

    return jsonify({
        'messages': messages,
        'media': media
    })

@app.route('/get_mindmap/<chat_id>/<filename>')
def get_mindmap(chat_id, filename):
    chat_dir = create_chat_directory(chat_id)
    filename = unquote(filename)  # Decode the URL-encoded filename
    filepath = os.path.join(chat_dir, 'media', 'mindmaps', filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return jsonify(json.load(f))
    else:
        return jsonify({"error": "Mindmap not found"}), 404

@app.route('/get_document/<chat_id>/<filename>')
def get_document(chat_id, filename):
    chat_dir = create_chat_directory(chat_id)
    filename = filename.replace(' ', '_')
    filepath = os.path.join(chat_dir, 'media', 'documents', filename)
    return send_file(filepath, as_attachment=True)


def get_media_list(chat_id):
    chat_dir = create_chat_directory(chat_id)
    media = []

    for media_type in ['mindmaps', 'documents', 'youtube']:
        media_dir = os.path.join(chat_dir, 'media', media_type)
        if os.path.exists(media_dir):
            for filename in os.listdir(media_dir):
                media.append({
                    'type': media_type,
                    'name': filename,
                    'path': os.path.join(media_dir, filename)
                })

    return media

@app.route('/get_chat_sessions')
def get_chat_sessions():
    chat_dirs = [d for d in os.listdir('chats') if os.path.isdir(os.path.join('chats', d))]
    sessions = []
    for chat_id in chat_dirs:
        chat_dir = os.path.join('chats', chat_id)
        chat_name_file = os.path.join(chat_dir, 'chat_name.txt')
        if os.path.exists(chat_name_file):
            with open(chat_name_file, 'r') as f:
                chat_name = f.read().strip()
        else:
            chat_name = "New Chat"
        sessions.append({
            'id': chat_id,
            'title': chat_name
        })
    return jsonify({'sessions': sessions})


@app.route('/load_chat_session/<chat_id>')
def load_chat_session(chat_id):
    messages_file = os.path.join('chats', chat_id, 'messages.json')
    if os.path.exists(messages_file):
        with open(messages_file, 'r') as f:
            messages = json.load(f)
    else:
        messages = []

    media = get_media_list(chat_id)

    session['chat_id'] = chat_id  # Update the current session

    return jsonify({
        'messages': messages,
        'media': media
    })

@app.route('/new_chat', methods=['POST'])
def new_chat():
    new_chat_id = str(uuid.uuid4())
    session['chat_id'] = new_chat_id
    create_chat_directory(new_chat_id)
    return jsonify({'chat_id': new_chat_id})

@app.route('/visual_novel_quiz', methods=['POST'])
def visual_novel_quiz():
    chat_id = session['chat_id']
    data = request.json
    action = data.get('action')
    topic = data.get('topic')

    if 'visual_novel_quiz' not in session:
        if not topic:
            return jsonify({"error": "Topic is required to start a new quiz"}), 400
        session['visual_novel_quiz'] = create_visual_novel_quiz(topic, chat_id)

    quiz = session['visual_novel_quiz']

    if action == 'start':
        return jsonify(quiz.start_quiz())
    elif action == 'answer':
        answer = data.get('answer')
        if not answer:
            return jsonify({"error": "Answer is required"}), 400
        return jsonify(quiz.answer_question(answer))
    elif action == 'next':
        return jsonify(quiz.next_question())
    elif action == 'previous':
        return jsonify(quiz.previous_question())
    elif action == 'stop':
        result = quiz.stop_quiz()
        session.pop('visual_novel_quiz', None)
        return jsonify(result)
    else:
        return jsonify({"error": "Invalid action"}), 400


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
