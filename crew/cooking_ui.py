import streamlit as st
import re
import io
import base64
import asyncio
from datetime import datetime
from src.crew.cook_crew import CookCrew

# TTS imports
from gtts import gTTS
import edge_tts

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

if "tts_provider" not in st.session_state:
    st.session_state.tts_provider = "gtts"

if "edge_voice" not in st.session_state:
    st.session_state.edge_voice = "en-US-JennyNeural"

st.set_page_config(
    page_title="AI Cooking Assistant", 
    layout="wide",
    page_icon="👩‍🍳"
)

# TTS Provider Configuration
TTS_PROVIDERS = {
    "Google TTS (Free)": "gtts",
    "Microsoft Edge TTS (Free)": "edge"
}

EDGE_VOICES = {
    "Jenny (US Female)": "en-US-JennyNeural",
    "Davis (US Male)": "en-US-DavisNeural", 
    "Aria (US Female)": "en-US-AriaNeural",
    "Guy (US Male)": "en-US-GuyNeural",
    "Emma (UK Female)": "en-GB-SoniaNeural",
    "Ryan (UK Male)": "en-GB-RyanNeural",
    "Libby (UK Female)": "en-GB-LibbyNeural"
}

# TTS Functions
def gtts_speech(text):
    """Google Text-to-Speech - Completely free"""
    try:
        clean_text = re.sub(r'[*#`]', '', text)
        clean_text = re.sub(r'\n+', '. ', clean_text)
        clean_text = clean_text.strip()[:500]
        
        if not clean_text:
            return None
            
        tts = gTTS(text=clean_text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.error(f"Google TTS error: {str(e)}")
        return None

async def edge_tts_async(text, voice="en-US-JennyNeural"):
    """Microsoft Edge TTS async function"""
    try:
        clean_text = re.sub(r'[*#`]', '', text)
        clean_text = re.sub(r'\n+', '. ', clean_text)
        clean_text = clean_text.strip()[:500]
        
        if not clean_text:
            return None
            
        communicate = edge_tts.Communicate(clean_text, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
    except Exception as e:
        print(f"Edge TTS error: {str(e)}")
        return None

def edge_tts_speech(text, voice="en-US-JennyNeural"):
    """Microsoft Edge TTS - Completely free, high quality"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_data = loop.run_until_complete(edge_tts_async(text, voice))
        loop.close()
        return audio_data
    except Exception as e:
        st.error(f"Edge TTS error: {str(e)}")
        return None

def generate_speech_audio(text):
    """Generate speech audio based on selected provider"""
    if not st.session_state.voice_enabled:
        return None
    
    provider = st.session_state.tts_provider
    
    if provider == "gtts":
        return gtts_speech(text)
    elif provider == "edge":
        voice = st.session_state.edge_voice
        return edge_tts_speech(text, voice)
    else:
        return gtts_speech(text)  # Fallback to Google TTS

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
    
    .provider-info {
        background: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #28a745;
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
            # TTS Provider selection
            selected_provider = st.selectbox(
                "TTS Provider:",
                list(TTS_PROVIDERS.keys()),
                index=list(TTS_PROVIDERS.values()).index(st.session_state.tts_provider) if st.session_state.tts_provider in TTS_PROVIDERS.values() else 0
            )
            
            provider_key = TTS_PROVIDERS[selected_provider]
            st.session_state.tts_provider = provider_key
            
            # Provider-specific settings
            if provider_key == "gtts":
                st.markdown("""
                <div class="provider-info">
                    <strong>✅ Google TTS</strong><br>
                    • Completely free<br>
                    • No setup required<br>
                    • Works immediately
                </div>
                """, unsafe_allow_html=True)
                
            elif provider_key == "edge":
                selected_voice = st.selectbox(
                    "Select Voice:",
                    list(EDGE_VOICES.keys()),
                    index=list(EDGE_VOICES.values()).index(st.session_state.edge_voice) if st.session_state.edge_voice in EDGE_VOICES.values() else 0
                )
                st.session_state.edge_voice = EDGE_VOICES[selected_voice]
                
                st.markdown("""
                <div class="provider-info">
                    <strong>✅ Microsoft Edge TTS</strong><br>
                    • Completely free<br>
                    • High quality voices<br>
                    • Multiple voice options
                </div>
                """, unsafe_allow_html=True)
    
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
                if st.session_state.voice_enabled:
                    provider_name = {
                        "gtts": "Google TTS",
                        "edge": "Edge TTS"
                    }.get(st.session_state.tts_provider, "TTS")
                    voice_indicator = f'<span class="voice-indicator">🔊 {provider_name}</span>'
                
                st.markdown(f"""
                <div class="bot-message">
                    <div>{answer}{voice_indicator}</div>
                    <div class="message-time">{current_time}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Generate and play audio for the latest bot response
                if (st.session_state.voice_enabled and 
                    i == len(st.session_state.chat_history) - 1 and 
                    question != "SYSTEM"):
                    
                    audio_content = generate_speech_audio(answer)
                    
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

# Voice feature info
if st.session_state.voice_enabled:
    st.markdown("---")
    provider_info = {
        "gtts": "🎙️ **Google TTS Active** - Free text-to-speech enabled!",
        "edge": "🎙️ **Microsoft Edge TTS Active** - High-quality free voices enabled!"
    }
    st.info(provider_info.get(st.session_state.tts_provider, "🎙️ **Voice Feature Active**") + " Make sure your volume is on.")