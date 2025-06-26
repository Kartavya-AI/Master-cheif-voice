import streamlit as st
import re
import io
import base64
from datetime import datetime
from src.crew.cook_crew import CookCrew
import requests
import json

# Initialize Crew and session state once
if "crew_instance" not in st.session_state:
    st.session_state.crew_instance = CookCrew()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "current_topic" not in st.session_state:
    st.session_state.current_topic = None

if "memory_active" not in st.session_state:
    st.session_state.memory_active = True

if "processing" not in st.session_state:
    st.session_state.processing = False

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False

if "elevenlabs_api_key" not in st.session_state:
    st.session_state.elevenlabs_api_key = ""

if "selected_voice" not in st.session_state:
    st.session_state.selected_voice = "Rachel"

st.set_page_config(
    page_title="AI Cooking Assistant", 
    layout="wide",
    page_icon="👩‍🍳"
)

# ElevenLabs Configuration
ELEVENLABS_VOICES = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Drew": "29vD33N1CtxCmqQRPOHJ", 
    "Clyde": "2EiwWnXFnvU5JabPnv8n",
    "Paul": "5Q0t7uMcjvnagumLfvZi",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Dave": "CYw3kZ02Hs0563khs1Fj",
    "Fin": "D38z5RcWu1voky8WS1ja",
    "Sarah": "EXAVITQu4vr4xnSDxMaL",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Thomas": "GBv7mTt0atIp3Br8iCZE"
}

def text_to_speech(text, api_key, voice_id="21m00Tcm4TlvDq8ikWAM"):
    """Convert text to speech using ElevenLabs API"""
    if not api_key:
        return None
        
    # Clean text for better speech synthesis
    clean_text = re.sub(r'[*#`]', '', text)  # Remove markdown symbols
    clean_text = re.sub(r'\n+', '. ', clean_text)  # Replace newlines with periods
    clean_text = clean_text.strip()
    
    # Limit text length to avoid very long audio
    if len(clean_text) > 500:
        clean_text = clean_text[:500] + "..."
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": clean_text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"ElevenLabs API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Voice synthesis error: {str(e)}")
        return None

def create_audio_player(audio_content):
    """Create an HTML audio player from audio content"""
    if audio_content:
        audio_base64 = base64.b64encode(audio_content).decode()
        audio_html = f"""
        <audio controls autoplay style="width: 100%; margin: 10px 0;">
            <source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
        """
        return audio_html
    return ""

# Custom CSS for chat interface
st.markdown("""
<style>
    .chat-container {
        height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #ddd;
        border-radius: 10px;
        background-color: #f8f9fa;
        margin-bottom: 1rem;
    }
    
    .user-message {
        background: #007bff;
        color: white;
        padding: 10px 15px;
        border-radius: 15px 15px 5px 15px;
        margin: 10px 0 10px auto;
        max-width: 70%;
        text-align: right;
    }
    
    .bot-message {
        background: white;
        color: #333;
        padding: 10px 15px;
        border-radius: 15px 15px 15px 5px;
        margin: 10px auto 10px 0;
        max-width: 70%;
        border: 1px solid #ddd;
    }
    
    .message-time {
        font-size: 0.8em;
        opacity: 0.7;
        margin-top: 5px;
    }
    
    .welcome-message {
        text-align: center;
        color: #666;
        padding: 2rem;
        font-style: italic;
    }
    
    .system-message {
        text-align: center;
        color: #666;
        font-style: italic;
        margin: 1rem 0;
        padding: 8px;
        background: #e9ecef;
        border-radius: 20px;
        font-size: 0.9em;
    }
    
    .voice-controls {
        background: #f0f8ff;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 1px solid #d0e7ff;
    }
    
    .voice-indicator {
        display: inline-block;
        margin-left: 10px;
        padding: 2px 8px;
        background: #28a745;
        color: white;
        border-radius: 12px;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)

def detect_recipe_topic(query):
    """Extract recipe/cooking topic from user query"""
    patterns = [
        r'\b(?:recipe|cook|make|prepare)\s+(?:for\s+)?(?:a\s+)?(\w+(?:\s+\w+)?)',
        r'\b(?:how to (?:make|cook|prepare))\s+(\w+(?:\s+\w+)?)',
        r'\b(\w+(?:\s+\w+)?)\s+recipe\b',
        r'\bwant\s+(?:a\s+)?(\w+(?:\s+\w+)?)\s+recipe\b'
    ]
    
    query_lower = query.lower()
    for pattern in patterns:
        matches = re.findall(pattern, query_lower)
        if matches:
            topic = matches[0].strip()
            stop_words = {'the', 'a', 'an', 'some', 'good', 'best', 'easy', 'quick'}
            topic_words = [word for word in topic.split() if word not in stop_words]
            if topic_words:
                return ' '.join(topic_words)
    return None

# Header
st.markdown("# 👩‍🍳 Chef AI")
st.markdown("*Your personal cooking assistant with voice*")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Voice Settings
    with st.expander("🎙️ Voice Settings", expanded=True):
        voice_enabled = st.toggle("🔊 Enable Voice", value=st.session_state.voice_enabled)
        st.session_state.voice_enabled = voice_enabled
        
        if voice_enabled:
            # API Key input
            api_key = st.text_input(
                "ElevenLabs API Key:", 
                value=st.session_state.elevenlabs_api_key,
                type="password",
                help="Get your API key from https://elevenlabs.io"
            )
            st.session_state.elevenlabs_api_key = api_key
            
            # Voice selection
            selected_voice = st.selectbox(
                "Select Voice:",
                options=list(ELEVENLABS_VOICES.keys()),
                index=list(ELEVENLABS_VOICES.keys()).index(st.session_state.selected_voice)
            )
            st.session_state.selected_voice = selected_voice
            
            if not api_key:
                st.warning("⚠️ Please enter your ElevenLabs API key to enable voice")
    
    # Other Settings
    memory_enabled = st.toggle("🧠 Memory", value=st.session_state.memory_active)
    st.session_state.memory_active = memory_enabled
    
    if st.session_state.current_topic:
        st.info(f"📝 Current Topic: {st.session_state.current_topic.title()}")
    
    st.metric("💬 Messages", len(st.session_state.chat_history))
    
    if st.button("🗑️ Clear Chat"):
        crew = st.session_state.crew_instance.cooking_crew()
        for agent in crew.agents:
            if hasattr(agent, 'reset'):
                agent.reset()
        st.session_state.chat_history = []
        st.session_state.current_topic = None
        st.rerun()

# Chat container
chat_container = st.container()

with chat_container:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    if not st.session_state.chat_history:
        st.markdown("""
        <div class="welcome-message">
            <h4>👋 Welcome to Chef AI!</h4>
            <p>Ask me about recipes, cooking techniques, ingredient substitutions, and more!</p>
            <p><strong>Try asking:</strong></p>
            <p>• "How do I make pasta carbonara?"</p>
            <p>• "What can I substitute for eggs in baking?"</p>
            <p>• "Give me a quick dinner recipe"</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for i, (question, answer) in enumerate(st.session_state.chat_history):
            if question == "SYSTEM":
                st.markdown(f'<div class="system-message">{answer}</div>', unsafe_allow_html=True)
            else:
                # User message
                current_time = datetime.now().strftime('%H:%M')
                st.markdown(f"""
                <div class="user-message">
                    <div>{question}</div>
                    <div class="message-time">{current_time}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Bot message with voice
                voice_indicator = ""
                if st.session_state.voice_enabled and st.session_state.elevenlabs_api_key:
                    voice_indicator = '<span class="voice-indicator">🔊 Voice</span>'
                
                st.markdown(f"""
                <div class="bot-message">
                    <div>{answer}{voice_indicator}</div>
                    <div class="message-time">{current_time}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Generate and play audio for the latest bot response
                if (st.session_state.voice_enabled and 
                    st.session_state.elevenlabs_api_key and 
                    i == len(st.session_state.chat_history) - 1 and 
                    question != "SYSTEM"):
                    
                    voice_id = ELEVENLABS_VOICES.get(st.session_state.selected_voice, "21m00Tcm4TlvDq8ikWAM")
                    audio_content = text_to_speech(answer, st.session_state.elevenlabs_api_key, voice_id)
                    
                    if audio_content:
                        audio_player = create_audio_player(audio_content)
                        st.markdown(audio_player, unsafe_allow_html=True)
    
    # Show processing indicator
    if st.session_state.processing:
        st.markdown("""
        <div class="system-message">
            🤔 Chef is thinking...
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Input area
st.markdown("---")
user_input = st.text_input("💬 Message Chef AI:", placeholder="Ask me anything about cooking!")

col1, col2 = st.columns([1, 4])
with col1:
    send_clicked = st.button("📤 Send", use_container_width=True)

# Process input
if send_clicked and user_input.strip():
    st.session_state.processing = True
    st.rerun()

if st.session_state.processing and user_input.strip():
    try:
        crew = st.session_state.crew_instance.cooking_crew()
        
        # Topic detection
        new_topic = detect_recipe_topic(user_input)
        topic_changed = False
        
        if st.session_state.memory_active and new_topic:
            if new_topic != st.session_state.current_topic:
                topic_changed = True
                
                if st.session_state.current_topic:
                    st.session_state.chat_history.append(("SYSTEM", f"🔄 Switched topic from {st.session_state.current_topic} to {new_topic}"))
                
                # Reset memory
                for agent in crew.agents:
                    if hasattr(agent, 'reset'):
                        agent.reset()
                
                st.session_state.current_topic = new_topic
                
                # Keep limited history
                if len(st.session_state.chat_history) > 4:
                    st.session_state.chat_history = st.session_state.chat_history[-2:]
            elif not st.session_state.current_topic:
                st.session_state.current_topic = new_topic
        
        # Build context
        context_query = user_input
        if st.session_state.memory_active and st.session_state.chat_history and not topic_changed:
            recent_history = [(q, a) for q, a in st.session_state.chat_history[-3:] if q != "SYSTEM"]
            
            if recent_history:
                history_context = "\n".join(
                    f"User: {q}\nChef: {a[:100]}..." if len(a) > 100 else f"User: {q}\nChef: {a}"
                    for q, a in recent_history
                )
                
                context_query = f"""
Current question: "{user_input}"

Recent conversation:
{history_context}

Please respond to the current question considering the context.
"""
        
        # Get response
        result = crew.kickoff(inputs={"user_query": context_query})
        
        # Add to history
        st.session_state.chat_history.append((user_input, str(result)))
        
        # Reset processing state
        st.session_state.processing = False
        st.rerun()
        
    except Exception as e:
        st.session_state.chat_history.append((user_input, f"🚫 Sorry, I encountered an error: {str(e)}. Please try again!"))
        st.session_state.processing = False
        st.rerun()

elif send_clicked and not user_input.strip():
    st.warning("Please enter a message!")

# Quick actions
if st.session_state.chat_history:
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    quick_actions = [
        ("🍝 Pasta", "Show me pasta recipes"),
        ("🥗 Healthy", "Give me healthy meal ideas"), 
        ("⚡ Quick", "What can I cook quickly?"),
        ("🔄 Substitute", "Help with substitutions")
    ]
    
    for i, (col, (label, message)) in enumerate(zip([col1, col2, col3, col4], quick_actions)):
        with col:
            if st.button(label, key=f"quick_{i}"):
                st.session_state.processing = True
                # Simulate user input
                try:
                    crew = st.session_state.crew_instance.cooking_crew()
                    result = crew.kickoff(inputs={"user_query": message})
                    st.session_state.chat_history.append((message, str(result)))
                    st.session_state.processing = False
                    st.rerun()
                except Exception as e:
                    st.session_state.chat_history.append((message, f"Error: {str(e)}"))
                    st.session_state.processing = False
                    st.rerun()

# Voice feature info
if st.session_state.voice_enabled:
    st.markdown("---")
    st.info("🎙️ **Voice Feature Active** - Chef AI responses will be spoken aloud! Make sure your volume is on.")