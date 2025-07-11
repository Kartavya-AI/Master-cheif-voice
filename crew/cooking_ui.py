__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
sys.modules["sqlite3.dbapi2"] = sys.modules["pysqlite3.dbapi2"]
import streamlit as st
import re
import json
from datetime import datetime
from src.crew.cook_crew import CookCrew
import fal_client
import base64
from dotenv import load_dotenv
import os
import asyncio
import tempfile
import edge_tts
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Crew and session state once
load_dotenv()
os.getenv("FAL_KEY")

def init_session_state():
    """Initialize all session state variables with defaults"""
    defaults = {
        "crew_instance": None,
        "chat_history": [],
        "recipe_notes": [],
        "current_topic": None,
        "memory_active": True,
        "current_recipe_step": None,
        "tts_enabled": False,
        "tts_service": "Edge TTS",
        "edge_voice": "en-US-AriaNeural",
        "audio_playing": False,
        "processing": False,
        "stt_enabled": False,
        "listening": False,
        "debug": False,
        "nav_command": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize crew instance if not exists
    if st.session_state.crew_instance is None:
        try:
            st.session_state.crew_instance = CookCrew()
            logger.info("✅ Crew instance initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize crew: {str(e)}")
            st.error(f"Failed to initialize AI crew: {str(e)}")

# Initialize session state
init_session_state()

st.set_page_config(
    page_title="AI Cooking Assistant", 
    layout="wide",
    page_icon="👩‍🍳"
)

# Custom CSS for chat interface and speech controls
st.markdown("""
<style>
    .chat-container {
        height: 1px;
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
        background: #1a1a2e;
        color: white;
        padding: 10px 15px;
        border-radius: 15px 15px 15px 5px;
        margin: 10px auto 10px 0;
        max-width: 70%;
        border: 1px solid #333;
    }
    
    .recipe-step {
        background: #2d3748;
        color: white;
        border-left: 4px solid #4299e1;
        padding: 20px;
        margin: 15px 0;
        border-radius: 8px;
        line-height: 1.6;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .recipe-step h3 {
        color: #4299e1;
        margin: 0 0 15px 0;
        font-size: 1.2em;
        font-weight: 600;
    }
    
    .recipe-step .step-instruction {
        font-size: 1.1em;
        font-weight: 600;
        margin-bottom: 10px;
        color: #fff;
    }
    
    .recipe-step .step-details {
        font-style: italic;
        color: #cbd5e0;
        margin-bottom: 15px;
        font-size: 0.95em;
    }
    
    .recipe-step .step-prompt {
        color: #81c784;
        font-weight: 500;
        margin-bottom: 15px;
        padding: 8px 12px;
        background: rgba(129, 199, 132, 0.1);
        border-radius: 4px;
        border-left: 3px solid #81c784;
    }
    
    .recipe-step .progress-info {
        color: #ffd54f;
        font-weight: 500;
        font-size: 0.9em;
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid #475569;
    }
    
    .message-time {
        font-size: 0.8em;
        opacity: 0.7;
        margin-top: 5px;
    }
    
    .welcome-message {
        text-align: center;
        color: #666;
        padding: 1rem;
        font-style: italic;
        background: transparent;
        border: 1px dashed #ccc;
        margin: 10px 0;
        border-radius: 8px;
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
    
    .notes-section {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    
    .tts-controls {
        background: #f0f8ff;
        border: 1px solid #b0d4f1;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .speech-controls {
        background: #f0fff0;
        border: 1px solid #90ee90;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .listening-indicator {
        background: #ff6b6b;
        color: white;
        padding: 10px;
        border-radius: 20px;
        text-align: center;
        font-weight: bold;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    .speech-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
        padding: 12px 24px;
        border-radius: 25px;
        cursor: pointer;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    
    .speech-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .debug-panel {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 8px;
        font-family: monospace;
        font-size: 0.9rem;
        margin: 10px 0;
        max-height: 300px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Speech-to-Text functionality using browser's Web Speech API
def add_speech_to_text_js():
    """Add JavaScript for speech-to-text functionality"""
    st.markdown("""
    <script>
        let recognition;
        let isListening = false;
        
        function initSpeechRecognition() {
            try {
                if ('webkitSpeechRecognition' in window) {
                    recognition = new webkitSpeechRecognition();
                } else if ('SpeechRecognition' in window) {
                    recognition = new SpeechRecognition();
                } else {
                    console.error('Speech recognition not supported in this browser');
                    showStatus('❌ Speech recognition not supported in this browser', 'error');
                    return false;
                }
                
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-US';
                recognition.maxAlternatives = 1;
                
                recognition.onstart = function() {
                    console.log('Speech recognition started');
                    isListening = true;
                    showStatus('🎤 Listening... Speak now!', 'listening');
                };
                
                recognition.onresult = function(event) {
                    if (event.results.length > 0) {
                        const transcript = event.results[0][0].transcript;
                        console.log('Speech result:', transcript);
                        
                        // Try multiple ways to find and update the text input
                        const selectors = [
                            'input[data-testid="stTextInput-input"]',
                            'input[aria-label*="Message Chef AI"]',
                            'input[placeholder*="Type or use voice"]',
                            'input[type="text"]',
                            '.stTextInput input',
                            'input[data-baseweb="input"]'
                        ];
                        
                        let textInput = null;
                        for (const selector of selectors) {
                            textInput = document.querySelector(selector);
                            if (textInput) {
                                console.log('Found input with selector:', selector);
                                break;
                            }
                        }
                        
                        if (textInput) {
                            // Clear existing value first
                            textInput.value = '';
                            textInput.focus();
                            
                            // Set new value
                            textInput.value = transcript;
                            
                            // Trigger comprehensive events to ensure Streamlit updates
                            const events = ['input', 'change', 'keyup', 'keydown', 'blur', 'focus'];
                            events.forEach(eventType => {
                                const event = new Event(eventType, { 
                                    bubbles: true, 
                                    cancelable: true 
                                });
                                textInput.dispatchEvent(event);
                            });
                            
                            // Also try React-style events
                            const reactEvent = new Event('input', { bubbles: true });
                            Object.defineProperty(reactEvent, 'target', { 
                                writable: false, 
                                value: textInput 
                            });
                            textInput.dispatchEvent(reactEvent);
                            
                            // Force a final focus
                            setTimeout(() => {
                                textInput.focus();
                                textInput.setSelectionRange(textInput.value.length, textInput.value.length);
                            }, 100);
                            
                            showStatus('✅ Speech captured: "' + transcript + '"', 'success');
                        } else {
                            console.error('Text input not found with any selector');
                            showStatus('❌ Could not find text input field', 'error');
                            
                            // Debug: show available inputs
                            const allInputs = document.querySelectorAll('input');
                            console.log('Available inputs:', allInputs);
                        }
                    }
                };
                
                recognition.onerror = function(event) {
                    console.error('Speech recognition error:', event.error);
                    let errorMsg = 'Speech recognition error: ' + event.error;
                    if (event.error === 'not-allowed') {
                        errorMsg = 'Microphone access denied. Please allow microphone access.';
                    } else if (event.error === 'no-speech') {
                        errorMsg = 'No speech detected. Please try again.';
                    }
                    showStatus('❌ ' + errorMsg, 'error');
                    isListening = false;
                };
                
                recognition.onend = function() {
                    console.log('Speech recognition ended');
                    isListening = false;
                    setTimeout(() => {
                        const statusEl = document.getElementById('listening-status');
                        if (statusEl) {
                            statusEl.innerHTML = '';
                        }
                    }, 3000);
                };
                
                return true;
            } catch (error) {
                console.error('Error initializing speech recognition:', error);
                showStatus('❌ Error initializing speech recognition', 'error');
                return false;
            }
        }
        
        function showStatus(message, type) {
            const statusEl = document.getElementById('listening-status');
            if (statusEl) {
                let className = 'listening-indicator';
                if (type === 'success') className = 'success-indicator';
                if (type === 'error') className = 'error-indicator';
                
                statusEl.innerHTML = '<div class="' + className + '">' + message + '</div>';
            }
        }
        
        function debugInputs() {
            console.log('=== Debugging Input Elements ===');
            const allInputs = document.querySelectorAll('input');
            allInputs.forEach((input, index) => {
                console.log(`Input ${index}:`, {
                    element: input,
                    type: input.type,
                    placeholder: input.placeholder,
                    'data-testid': input.getAttribute('data-testid'),
                    'aria-label': input.getAttribute('aria-label'),
                    className: input.className,
                    id: input.id
                });
            });
        }
        
        function startListening() {
            console.log('Starting speech recognition...');
            debugInputs(); // Debug available inputs
            
            if (!recognition) {
                console.log('Recognition not initialized, attempting to initialize...');
                if (!initSpeechRecognition()) {
                    return;
                }
            }
            
            if (recognition && !isListening) {
                try {
                    recognition.start();
                    console.log('Speech recognition started successfully');
                } catch (error) {
                    console.error('Error starting recognition:', error);
                    showStatus('❌ Error starting speech recognition: ' + error.message, 'error');
                }
            } else if (isListening) {
                showStatus('⚠️ Already listening...', 'warning');
            } else {
                showStatus('❌ Speech recognition not available', 'error');
            }
        }
        
        function stopListening() {
            if (recognition && isListening) {
                try {
                    recognition.stop();
                    showStatus('⏹️ Stopped listening', 'info');
                } catch (error) {
                    console.error('Error stopping recognition:', error);
                }
            }
        }
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded, initializing speech recognition');
            setTimeout(() => initSpeechRecognition(), 500);
        });
        
        // Re-initialize multiple times to ensure Streamlit is ready
        const initDelays = [1000, 2000, 3000];
        initDelays.forEach(delay => {
            setTimeout(function() {
                console.log(`Re-initializing speech recognition after ${delay}ms`);
                initSpeechRecognition();
            }, delay);
        });
        
        // Also try when the page becomes visible (in case of tab switching)
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden) {
                setTimeout(() => initSpeechRecognition(), 500);
            }
        });
        
        // Add CSS for status indicators
        const style = document.createElement('style');
        style.textContent = `
            .success-indicator {
                background: #10b981;
                color: white;
                padding: 10px;
                border-radius: 20px;
                text-align: center;
                font-weight: bold;
                margin: 10px 0;
            }
            .error-indicator {
                background: #ef4444;
                color: white;
                padding: 10px;
                border-radius: 20px;
                text-align: center;
                font-weight: bold;
                margin: 10px 0;
            }
            .warning-indicator {
                background: #f59e0b;
                color: white;
                padding: 10px;
                border-radius: 20px;
                text-align: center;
                font-weight: bold;
                margin: 10px 0;
            }
        `;
        document.head.appendChild(style);
    </script>
    """, unsafe_allow_html=True)

async def generate_edge_speech(text, voice="en-US-AriaNeural"):
    """Generate speech using Edge TTS"""
    try:
        # Clean text for TTS
        clean_text = re.sub(r'[*#`]', '', text)  # Remove markdown
        clean_text = re.sub(r'\n+', ' ', clean_text)  # Replace newlines with spaces
        clean_text = clean_text.strip()
        
        if not clean_text:
            return None
            
        # Limit text length for TTS
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + "..."
        
        # Create Edge TTS communicator
        communicate = edge_tts.Communicate(clean_text, voice)
        
        # Generate audio to bytes
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Edge TTS Error: {str(e)}")
        st.error(f"Edge TTS Error: {str(e)}")
        return None

def generate_fal_speech(text):
    """Generate speech using fal.ai TTS"""
    try:
        # Clean text for TTS
        clean_text = re.sub(r'[*#`]', '', text)  # Remove markdown
        clean_text = re.sub(r'\n+', ' ', clean_text)  # Replace newlines with spaces
        clean_text = clean_text.strip()
        
        if not clean_text:
            return None
            
        # Limit text length for TTS
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."
        
        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    logger.info(log["message"])
        
        result = fal_client.subscribe(
            "fal-ai/kokoro/american-english",
            arguments={"text": clean_text},
            with_logs=True,
            on_queue_update=on_queue_update,
        )
        
        if result and 'audio_url' in result:
            return result['audio_url']
        return None
        
    except Exception as e:
        logger.error(f"FAL TTS Error: {str(e)}")
        st.error(f"FAL TTS Error: {str(e)}")
        return None

def generate_speech_with_fallback(text):
    """Generate speech using selected TTS service with fallback"""
    if st.session_state.tts_service == "Edge TTS":
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_bytes = loop.run_until_complete(
                generate_edge_speech(text, st.session_state.edge_voice)
            )
            loop.close()
            return audio_bytes
        except Exception as e:
            logger.warning(f"Edge TTS failed, trying FAL.ai: {str(e)}")
            return generate_fal_speech(text)
    else:
        try:
            return generate_fal_speech(text)
        except Exception as e:
            logger.warning(f"FAL TTS failed, trying Edge TTS: {str(e)}")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_bytes = loop.run_until_complete(
                    generate_edge_speech(text, st.session_state.edge_voice)
                )
                loop.close()
                return audio_bytes
            except Exception as e2:
                logger.error(f"All TTS services failed: {str(e2)}")
                return None

def validate_api_keys():
    """Validate that all required API keys are present"""
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        st.warning("⚠️ FAL_KEY not found in environment variables")
        return False
    return True

def format_recipe_step(recipe_text):
    """Format recipe step for display with proper styling"""
    if not recipe_text:
        return ""
    
    # Clean up the recipe text
    recipe_text = recipe_text.replace('\\n', '\n').replace('\n\n', '\n').strip()
    
    # Parse different parts of the recipe step
    html_parts = []
    
    # Split by lines to process each part
    lines = recipe_text.split('\n')
    current_section = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for step header (### Current Step: Step X)
        if line.startswith('### Current Step:') or line.startswith('## Current Step:'):
            step_title = line.replace('###', '').replace('##', '').strip()
            html_parts.append(f'<h3>{step_title}</h3>')
            
        # Check for main instruction (usually in **bold**)
        elif line.startswith('**') and line.endswith('**'):
            instruction = line.replace('**', '').strip()
            html_parts.append(f'<div class="step-instruction">{instruction}</div>')
            
        # Check for details/tips (usually in *italics* or contains parentheses/details)
        elif line.startswith('*') and line.endswith('*'):
            details = line.replace('*', '').strip()
            if details.lower().startswith('let me know when'):
                html_parts.append(f'<div class="step-prompt">{details}</div>')
            else:
                html_parts.append(f'<div class="step-details">{details}</div>')
                
        # Check for progress info (usually starts with **Progress:**)
        elif line.startswith('**Progress:**'):
            progress = line.replace('**Progress:**', '').replace('**', '').strip()
            html_parts.append(f'<div class="progress-info"><strong>Progress:</strong> {progress}</div>')
            
        # Handle mixed formatting lines
        else:
            # Clean up mixed bold/italic formatting
            formatted_line = line
            
            # Convert **text** to bold
            formatted_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_line)
            
            # Convert *text* to italic (but not if it's already in strong tags)
            formatted_line = re.sub(r'(?<!<strong>)\*([^*]+)\*(?!</strong>)', r'<em>\1</em>', formatted_line)
            
            # Determine the type based on content
            if 'let me know when' in formatted_line.lower() or 'say "done"' in formatted_line.lower():
                html_parts.append(f'<div class="step-prompt">{formatted_line}</div>')
            elif 'progress:' in formatted_line.lower():
                html_parts.append(f'<div class="progress-info">{formatted_line}</div>')
            elif formatted_line.startswith('<strong>') or 'Step' in formatted_line:
                html_parts.append(f'<div class="step-instruction">{formatted_line}</div>')
            else:
                html_parts.append(f'<div class="step-details">{formatted_line}</div>')
    
    # Join all parts
    formatted_content = ''.join(html_parts)
    
    return f'<div class="recipe-step">{formatted_content}</div>'

def parse_json_response(response_text):
    """Parse JSON response and extract recipe and notes"""
    try:
        # Look for JSON in the response
        json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            parsed_data = json.loads(json_str)
            return parsed_data
        else:
            # Try to parse the entire response as JSON
            return json.loads(response_text)
    except (json.JSONDecodeError, AttributeError):
        return None

def build_context_with_notes():
    """Build context including recipe notes for better continuity"""
    context_parts = []
    
    # Add recent recipe notes
    if st.session_state.recipe_notes:
        recent_notes = st.session_state.recipe_notes[-5:]  # Last 5 notes
        notes_text = "\n".join([f"Note {i+1}: {note}" for i, note in enumerate(recent_notes)])
        context_parts.append(f"Previous recipe steps and notes:\n{notes_text}")
    
    # Add recent chat history
    if st.session_state.chat_history:
        recent_chat = st.session_state.chat_history[-3:]  # Last 3 exchanges
        chat_text = "\n".join([f"User: {q}\nChef: {a[:100]}..." if len(a) > 100 else f"User: {q}\nChef: {a}" 
                              for q, a in recent_chat if q != "SYSTEM"])
        if chat_text:
            context_parts.append(f"Recent conversation:\n{chat_text}")
    
    return "\n\n".join(context_parts)

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

def cleanup_session_state():
    """Clean up old temporary data from session state"""
    temp_keys = [k for k in st.session_state.keys() if k.startswith('temp_')]
    for key in temp_keys:
        del st.session_state[key]
    
    # Limit chat history to prevent memory issues
    if len(st.session_state.chat_history) > 50:
        st.session_state.chat_history = st.session_state.chat_history[-25:]
        logger.info("Cleaned up old chat history")

# Available Edge TTS voices
EDGE_VOICES = {
    # English voices
    "Aria (US Female)": "en-US-AriaNeural",
    "Jenny (US Female)": "en-US-JennyNeural", 
    "Guy (US Male)": "en-US-GuyNeural",
    "Davis (US Male)": "en-US-DavisNeural",
    "Jane (US Female)": "en-US-JaneNeural",
    "Jason (US Male)": "en-US-JasonNeural",
    "Sara (US Female)": "en-US-SaraNeural",
    "Tony (US Male)": "en-US-TonyNeural",
    
    # British voices
    "Libby (UK Female)": "en-GB-LibbyNeural",
    "Maisie (UK Female)": "en-GB-MaisieNeural", 
    "Ryan (UK Male)": "en-GB-RyanNeural",
    "Sonia (UK Female)": "en-GB-SoniaNeural",
    "Thomas (UK Male)": "en-GB-ThomasNeural",
    
    # Australian voices
    "Natasha (AU Female)": "en-AU-NatashaNeural",
    "William (AU Male)": "en-AU-WilliamNeural",
}

# Header
st.markdown("# 👩‍🍳 Chef AI")
st.markdown("*Your personal cooking assistant with voice interaction*")

# Add Speech-to-Text JavaScript
add_speech_to_text_js()

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Debug mode
    debug_enabled = st.toggle("🐛 Debug Mode", value=st.session_state.debug)
    st.session_state.debug = debug_enabled
    
    memory_enabled = st.toggle("🧠 Memory", value=st.session_state.memory_active)
    st.session_state.memory_active = memory_enabled
    
    # Validate API keys
    if st.button("🔑 Validate API Keys"):
        if validate_api_keys():
            st.success("✅ All API keys valid")
        else:
            st.error("❌ Missing API keys")
    
    st.markdown("### 🎤 Speech-to-Text Settings")
    with st.expander("STT Configuration", expanded=st.session_state.stt_enabled):
        stt_enabled = st.toggle("Enable Speech-to-Text", value=st.session_state.stt_enabled)
        st.session_state.stt_enabled = stt_enabled
        
        if stt_enabled:
            st.info("🎤 Uses your browser's built-in speech recognition")
            st.markdown("**How to use:**")
            st.markdown("1. Click the microphone button below")
            st.markdown("2. Speak clearly when prompted")
            st.markdown("3. Your speech will appear in the text box")
    
    st.markdown("### 🔊 Text-to-Speech Settings")
    with st.expander("TTS Configuration", expanded=st.session_state.tts_enabled):
        tts_enabled = st.toggle("Enable Text-to-Speech", value=st.session_state.tts_enabled)
        st.session_state.tts_enabled = tts_enabled
        
        if tts_enabled:
            # TTS Service Selection
            tts_service = st.selectbox(
                "TTS Service:",
                ["Edge TTS", "FAL.ai TTS"],
                index=0 if st.session_state.tts_service == "Edge TTS" else 1
            )
            st.session_state.tts_service = tts_service
            
            # Voice selection for Edge TTS
            if tts_service == "Edge TTS":
                current_voice_name = next(
                    (name for name, code in EDGE_VOICES.items() if code == st.session_state.edge_voice),
                    "Aria (US Female)"
                )
                
                selected_voice_name = st.selectbox(
                    "Voice:",
                    list(EDGE_VOICES.keys()),
                    index=list(EDGE_VOICES.keys()).index(current_voice_name)
                )
                st.session_state.edge_voice = EDGE_VOICES[selected_voice_name]
                
                # Voice preview
                if st.button("🎵 Test Voice"):
                    test_text = "Hello! I'm your cooking assistant. Let me help you create delicious meals!"
                    with st.spinner("Generating voice sample..."):
                        audio_data = generate_speech_with_fallback(test_text)
                        if audio_data:
                            st.audio(audio_data, format='audio/wav')
                        else:
                            st.error("Could not generate voice sample")
            
            elif tts_service == "FAL.ai TTS":
                st.info("🎯 FAL.ai uses Kokoro American English voice")
                if st.button("🎵 Test Voice"):
                    test_text = "Hello! I'm your cooking assistant. Let me help you create delicious meals!"
                    with st.spinner("Generating voice sample..."):
                        audio_url = generate_speech_with_fallback(test_text)
                        if audio_url:
                            st.audio(audio_url, format='audio/wav')
                        else:
                            st.error("Could not generate voice sample")
    
    # Status indicators
    if st.session_state.current_topic:
        st.info(f"📝 Current Topic: {st.session_state.current_topic.title()}")
    
    if st.session_state.current_recipe_step:
        st.success(f"🍳 Current Step: {st.session_state.current_recipe_step}")
    
    st.metric("💬 Messages", len(st.session_state.chat_history))
    st.metric("📝 Recipe Notes", len(st.session_state.recipe_notes))
    
    # Show recent notes
    if st.session_state.recipe_notes:
        st.markdown("### 📋 Recent Notes")
        for i, note in enumerate(st.session_state.recipe_notes[-3:], 1):
            st.text_area(f"Note {len(st.session_state.recipe_notes)-3+i}", 
                        note[:100] + "..." if len(note) > 100 else note, 
                        height=68, disabled=True)
    
    # Maintenance buttons
    if st.button("🧹 Cleanup Memory"):
        cleanup_session_state()
        st.success("✅ Memory cleaned up")
    
    if st.button("🗑️ Clear Chat"):
        if st.session_state.crew_instance:
            try:
                crew = st.session_state.crew_instance.cooking_crew()
                for agent in crew.agents:
                    if hasattr(agent, 'reset'):
                        agent.reset()
            except Exception as e:
                logger.error(f"Error resetting crew: {str(e)}")
        
        st.session_state.chat_history = []
        st.session_state.recipe_notes = []
        st.session_state.current_topic = None
        st.session_state.current_recipe_step = None
        st.rerun()

# Debug panel
if st.session_state.debug:
    with st.expander("🐛 Debug Information", expanded=False):
        st.markdown("#### Session State")
        debug_state = {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                      for k, v in st.session_state.items() 
                      if not k.startswith('crew_instance')}
        st.json(debug_state)
        
        st.markdown("#### Environment")
        st.write(f"FAL_KEY present: {'✅' if os.getenv('FAL_KEY') else '❌'}")
        st.write(f"Chat history length: {len(st.session_state.chat_history)}")
        st.write(f"Recipe notes length: {len(st.session_state.recipe_notes)}")

# Chat container
chat_container = st.container()

with chat_container:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    if not st.session_state.chat_history:
        st.markdown("""
        <div class="welcome-message">
            <h4>👋 Welcome to Chef AI!</h4>
            <p>Ask me about recipes, cooking techniques, ingredient substitutions, and more!</p>
            <p><strong>🎤 New: Voice input available!</strong></p>
            <p><strong>Try asking:</strong></p>
            <p>• "How do I make pasta carbonara?"</p>
            <p>• "What can I substitute for eggs in baking?"</p>
            <p>• "Give me a quick dinner recipe"</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for question, answer in st.session_state.chat_history:
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
                
                # Bot message - enhanced JSON parsing and display
                recipe_data = None
                is_recipe_step = False
                
                # Try multiple methods to extract recipe data
                try:
                    # Method 1: Use existing parse_json_response function
                    parsed_data = parse_json_response(answer)
                    if parsed_data and 'cook_recipe' in parsed_data:
                        recipe_data = parsed_data['cook_recipe']
                        is_recipe_step = True
                    else:
                        # Method 2: Check if answer starts with { (raw JSON)
                        if answer.strip().startswith('{'):
                            json_data = json.loads(answer.strip())
                            if 'cook_recipe' in json_data:
                                recipe_data = json_data['cook_recipe']
                                is_recipe_step = True
                        
                        # Method 3: Look for JSON patterns anywhere in the text
                        elif '{' in answer and '}' in answer:
                            # Find JSON object in the text - improved pattern for nested objects
                            try:
                                # Find the start and end of JSON object
                                start_idx = answer.find('{')
                                if start_idx != -1:
                                    # Find matching closing brace
                                    brace_count = 0
                                    end_idx = start_idx
                                    for i, char in enumerate(answer[start_idx:], start_idx):
                                        if char == '{':
                                            brace_count += 1
                                        elif char == '}':
                                            brace_count -= 1
                                            if brace_count == 0:
                                                end_idx = i
                                                break
                                    
                                    if end_idx > start_idx:
                                        json_str = answer[start_idx:end_idx + 1]
                                        json_data = json.loads(json_str)
                                        if 'cook_recipe' in json_data:
                                            recipe_data = json_data['cook_recipe']
                                            is_recipe_step = True
                            except (json.JSONDecodeError, ValueError):
                                pass
                        
                        # Method 4: Check for markdown code blocks with JSON
                        elif '```json' in answer or '```' in answer:
                            code_blocks = re.findall(r'```(?:json)?\s*({.*?})\s*```', answer, re.DOTALL)
                            for block in code_blocks:
                                try:
                                    json_data = json.loads(block)
                                    if 'cook_recipe' in json_data:
                                        recipe_data = json_data['cook_recipe']
                                        is_recipe_step = True
                                        break
                                except json.JSONDecodeError:
                                    continue
                
                except (json.JSONDecodeError, AttributeError, TypeError) as e:
                    # If all parsing fails, treat as regular message
                    is_recipe_step = False
                    recipe_data = None
                    # Debug: log parsing error if debug mode is on
                    if st.session_state.debug:
                        st.warning(f"🐛 JSON parsing failed: {str(e)[:100]}...")
                        st.text_area("Raw response for debugging:", answer[:500], height=100)
                
                # Display the message
                if is_recipe_step and recipe_data:
                    # Display formatted recipe step
                    recipe_html = format_recipe_step(recipe_data)
                    st.markdown(recipe_html, unsafe_allow_html=True)
                    
                    # Auto-generate TTS for recipe steps
                    if st.session_state.tts_enabled:
                        with st.spinner(f"🔊 Generating speech using {st.session_state.tts_service}..."):
                            audio_data = generate_speech_with_fallback(recipe_data)
                            if audio_data:
                                st.audio(audio_data, format='audio/wav', autoplay=True)
                                st.success(f"🎵 Recipe step audio ready! ({st.session_state.tts_service})")
                            else:
                                st.warning(f"⚠️ Could not generate audio")
                else:
                    # Display as regular message, but format JSON nicely if detected
                    display_text = answer
                    
                    # If the response looks like JSON but wasn't a recipe, format it nicely
                    try:
                        if answer.strip().startswith('{') and answer.strip().endswith('}'):
                            # Try to parse and format the JSON for better readability
                            json_data = json.loads(answer.strip())
                            display_text = json.dumps(json_data, indent=2)
                        elif '```json' in answer:
                            # Extract and format JSON from code blocks
                            json_match = re.search(r'```json\s*({.*?})\s*```', answer, re.DOTALL)
                            if json_match:
                                json_data = json.loads(json_match.group(1))
                                formatted_json = json.dumps(json_data, indent=2)
                                display_text = answer.replace(json_match.group(0), f'```json\n{formatted_json}\n```')
                    except (json.JSONDecodeError, AttributeError):
                        # If formatting fails, use original text
                        pass
                    
                    st.markdown(f"""
                    <div class="bot-message">
                        <div><pre style="white-space: pre-wrap; font-family: inherit;">{display_text}</pre></div>
                        <div class="message-time">{current_time}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Manual TTS for regular messages
                    if st.session_state.tts_enabled:
                        col1, col2 = st.columns([1, 6])
                        with col1:
                            tts_key = f"tts_regular_{len(st.session_state.chat_history)}_{hash(answer)}"
                            if st.button("🔊", key=tts_key, help=f"Play with {st.session_state.tts_service}"):
                                with st.spinner(f"Generating speech using {st.session_state.tts_service}..."):
                                    audio_data = generate_speech_with_fallback(answer)
                                    if audio_data:
                                        st.audio(audio_data, format='audio/wav')
                                        st.success(f"🎵 Audio ready! ({st.session_state.tts_service})")
                                    else:
                                        st.warning(f"⚠️ Could not generate audio")
    
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

# Speech-to-Text controls
if st.session_state.stt_enabled:
    st.markdown("### 🎤 Voice Input")
    
    col1, col2, col3 = st.columns([2, 2, 4])
    
    with col1:
        if st.button("🎤 Start Listening", key="start_listening"):
            st.markdown("""
            <script>
                startListening();
            </script>
            """, unsafe_allow_html=True)
    
    with col2:
        if st.button("⏹️ Stop Listening", key="stop_listening"):
            st.markdown("""
            <script>
                stopListening();
            </script>
            """, unsafe_allow_html=True)
    
    # Listening status display
    st.markdown('<div id="listening-status"></div>', unsafe_allow_html=True)
    st.markdown("---")

# Quick recipe navigation buttons
if st.session_state.current_recipe_step:
    st.markdown("### 🍳 Recipe Navigation")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Done with this step"):
            st.session_state.nav_command = "done"
    
    with col2:
        if st.button("➡️ Next step"):
            st.session_state.nav_command = "next"
    
    with col3:
        if st.button("🔄 Repeat step"):
            st.session_state.nav_command = "repeat this step"

# Text input with enhanced functionality
user_input = st.text_input("💬 Message Chef AI:", placeholder="Type or use voice input above!", key="main_input")

col1, col2 = st.columns([1, 4])
with col1:
    send_clicked = st.button("📤 Send", use_container_width=True)

# Process input function
def process_user_input(input_text):
    """Process user input and get response from crew"""
    if not input_text.strip():
        return
    
    st.session_state.processing = True
    
    try:
        if not st.session_state.crew_instance:
            st.error("❌ AI crew not initialized. Please refresh the page.")
            return
        
        crew = st.session_state.crew_instance.cooking_crew()
        
        # Topic detection
        new_topic = detect_recipe_topic(input_text)
        topic_changed = False
        
        if st.session_state.memory_active and new_topic:
            if new_topic != st.session_state.current_topic:
                topic_changed = True
                
                if st.session_state.current_topic:
                    st.session_state.chat_history.append(("SYSTEM", f"🔄 Switched topic from {st.session_state.current_topic} to {new_topic}"))
                
                # Reset memory but keep some context
                for agent in crew.agents:
                    if hasattr(agent, 'reset'):
                        agent.reset()
                
                st.session_state.current_topic = new_topic
                st.session_state.current_recipe_step = None
                
                # Keep limited history
                if len(st.session_state.chat_history) > 4:
                    st.session_state.chat_history = st.session_state.chat_history[-2:]
            elif not st.session_state.current_topic:
                st.session_state.current_topic = new_topic
        
        # Build context with notes
        context_query = input_text
        if st.session_state.memory_active:
            context = build_context_with_notes()
            if context:
                context_query = f"""
Current question: "{input_text}"

Context:
{context}

Please respond to the current question considering the context and previous steps.
"""
        
        # Get response
        logger.info(f"Processing query: {input_text[:50]}...")
        result = crew.kickoff(inputs={"user_query": context_query})
        result_str = str(result)
        
        # Parse JSON response
        parsed_data = parse_json_response(result_str)
        if parsed_data:
            # Save notes to history
            if 'notes_making' in parsed_data:
                st.session_state.recipe_notes.append(parsed_data['notes_making'])
            
            # Update current step info
            if 'cook_recipe' in parsed_data:
                recipe_text = parsed_data['cook_recipe']
                # Extract step number if present
                step_match = re.search(r'Step (\d+)', recipe_text)
                if step_match:
                    st.session_state.current_recipe_step = f"Step {step_match.group(1)}"
            
            # Store the original response for display
            st.session_state.chat_history.append((input_text, result_str))
        else:
            # Regular response without JSON
            st.session_state.chat_history.append((input_text, result_str))
        
        logger.info("✅ Query processed successfully")
        
    except Exception as e:
        error_msg = f"🚫 Sorry, I encountered an error: {str(e)}. Please try again!"
        st.session_state.chat_history.append((input_text, error_msg))
        logger.error(f"Error processing query: {str(e)}")
    
    finally:
        st.session_state.processing = False

# Process input
if send_clicked and user_input.strip():
    process_user_input(user_input)
    st.rerun()

elif send_clicked and not user_input.strip():
    st.warning("Please enter a message or use voice input!")

# Process navigation commands from buttons
if st.session_state.nav_command:
    command = st.session_state.nav_command
    st.session_state.nav_command = None  # Clear the command immediately
    process_user_input(command)
    st.rerun()  # Refresh the page to show the new step immediately
