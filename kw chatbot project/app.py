from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
import os
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Gemini setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Chat model
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    full_conversation = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@app.before_request
def set_session():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

@app.route("/")
def index():
    session_id = session["session_id"]
    chat = Chat.query.filter_by(session_id=session_id).order_by(Chat.timestamp.desc()).first()
    history = Chat.query.order_by(Chat.timestamp.desc()).all()
    conversation = chat.full_conversation if chat else ""
    return render_template("index.html", conversation=conversation, history=history)

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    if not user_input:
        return jsonify({"response": "No input received."})

    response = model.generate_content(user_input)
    bot_response = response.text
    session_id = session["session_id"]

    chat = Chat.query.filter_by(session_id=session_id).first()
    if chat:
        chat.full_conversation += f"\n👩 You: {user_input}\n🤖 Bot: {bot_response}"
    else:
        chat = Chat(session_id=session_id, full_conversation=f"👩 You: {user_input}\n🤖 Bot: {bot_response}")
        db.session.add(chat)

    db.session.commit()
    return jsonify({"response": bot_response})

@app.route("/chat/<session_id>")
def view_chat(session_id):
    chat = Chat.query.filter_by(session_id=session_id).first()
    history = Chat.query.order_by(Chat.timestamp.desc()).all()
    conversation = chat.full_conversation if chat else ""
    session["session_id"] = session_id  # Switch to clicked session
    return render_template("index.html", conversation=conversation, history=history)


@app.route("/reset", methods=["POST"])
def reset():
    session["session_id"] = str(uuid.uuid4())
    return ("", 204)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
