"""
Stripped-down Lexi chat system for in-game integration.
Provides basic chat functionality with Ollama LLM.
"""
import requests
import json
import os
import sys
import threading
from datetime import datetime
from typing import Optional, List, Dict, Callable, Tuple


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: Optional[str] = None):
        self.base_url = base_url
        self.model_name = model_name or os.getenv("LEXI_MODEL_NAME", "Godmoded/llama3-lexi-uncensored")
    
    def check_connection(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def chat_stream(self, messages: List[Dict], on_chunk: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """
        Stream chat response from the model.
        Yields chunks of text as they arrive.
        If on_chunk callback is provided, calls it for each chunk.
        Returns full response when done.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True
        }
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=300)
            response.raise_for_status()
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            full_response += chunk
                            if on_chunk:
                                on_chunk(chunk)
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            return full_response
        except Exception as e:
            error_msg = f"[ERROR: {e}]"
            if on_chunk:
                on_chunk(error_msg)
            return error_msg
    
    def analyze_action(self, text: str, is_lexi: bool = True) -> str:
        """
        Analyze text and return a two-word action descriptor.
        For Lexi: describes what action she performed (e.g., "assessed gloves", "offered help")
        For User: describes what action the user performed (e.g., "asked question", "gave command")
        """
        role = "Lexi (an android companion)" if is_lexi else "the Captain"
        examples = "assessed gloves, offered help, relayed information, checked systems, provided guidance" if is_lexi else "asked question, gave command, made request, shared information, expressed concern"
        
        analysis_prompt = f"""Analyze this text from {role} and determine what action they performed. Respond with ONLY two words (verb + noun) that describe the action.

Examples: {examples}

Text to analyze:
{text}

Respond with ONLY two words (verb + noun):"""
        
        try:
            analysis_messages = [
                {"role": "system", "content": "You are an action analyzer. Respond with only two words (verb + noun) describing the action performed."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model_name,
                "messages": analysis_messages,
                "stream": False
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if "message" in data and "content" in data["message"]:
                action = data["message"]["content"].strip().lower()
                # Extract first two words
                words = action.split()
                if len(words) >= 2:
                    action = f"{words[0]} {words[1]}"
                elif len(words) == 1:
                    action = f"{words[0]} action"  # Fallback if only one word
                else:
                    action = "performed action"  # Fallback
                # Remove any punctuation
                action = action.strip('.,!?;:()[]{}"\'')
                return action
            return "performed action" if is_lexi else "made statement"
        except Exception as e:
            print(f"Error analyzing action: {e}", file=sys.stderr)
            return "performed action" if is_lexi else "made statement"
    
    def analyze_emotion(self, response_text: str) -> str:
        """
        Analyze Lexi's response and return a one-word emotion/feeling.
        Returns a single word describing how Lexi feels based on what she said.
        """
        analysis_prompt = f"""Analyze this response from Lexi (an android companion) and determine how she feels based on what she just said. Respond with ONLY one word that describes her emotional state or feeling.

Examples: happy, helpful, curious, concerned, excited, thoughtful, playful, worried, friendly, professional, etc.

Response to analyze:
{response_text}

Respond with ONLY one word:"""
        
        try:
            analysis_messages = [
                {"role": "system", "content": "You are an emotion analyzer. Respond with only one word describing the emotional state."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model_name,
                "messages": analysis_messages,
                "stream": False
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if "message" in data and "content" in data["message"]:
                emotion = data["message"]["content"].strip().lower()
                # Extract just the first word if multiple words were returned
                emotion = emotion.split()[0] if emotion.split() else "neutral"
                # Remove any punctuation
                emotion = emotion.strip('.,!?;:()[]{}"\'')
                return emotion
            return "neutral"
        except Exception as e:
            print(f"Error analyzing emotion: {e}", file=sys.stderr)
            return "neutral"
    
    def analyze_captain_message(self, message_text: str) -> str:
        """
        Analyze the Captain's message and return a one-word descriptor.
        Returns a single word describing the nature/tone of what the Captain said.
        """
        analysis_prompt = f"""Analyze this message from the Captain and determine what kind of statement it is. Respond with ONLY one word that describes the nature or tone of the message.

Examples: question, command, greeting, complaint, compliment, request, statement, concern, joke, etc.

Message to analyze:
{message_text}

Respond with ONLY one word:"""
        
        try:
            analysis_messages = [
                {"role": "system", "content": "You are a message analyzer. Respond with only one word describing the nature or tone of the message."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model_name,
                "messages": analysis_messages,
                "stream": False
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if "message" in data and "content" in data["message"]:
                descriptor = data["message"]["content"].strip().lower()
                # Extract just the first word if multiple words were returned
                descriptor = descriptor.split()[0] if descriptor.split() else "statement"
                # Remove any punctuation
                descriptor = descriptor.strip('.,!?;:()[]{}"\'')
                return descriptor
            return "statement"
        except Exception as e:
            print(f"Error analyzing captain message: {e}", file=sys.stderr)
            return "statement"


class LexiChat:
    """Simple chat system for Lexi, the android companion."""
    
    # Chat display box coordinates
    CHAT_BOX_X = 974
    CHAT_BOX_Y = 211
    CHAT_BOX_WIDTH = 257  # 1231 - 974
    CHAT_BOX_HEIGHT = 365  # 576 - 211
    
    # Input box in central_bottom_region
    INPUT_BOX_X = 361
    INPUT_BOX_Y = 623
    INPUT_BOX_WIDTH = 581  # 942 - 361
    INPUT_BOX_HEIGHT = 77  # 700 - 623
    
    def __init__(self):
        self.client = OllamaClient()
        self.conversation_history: List[Dict[str, str]] = []
        self.input_text = ""
        self.input_active = False
        self.current_response = ""
        self.streaming = False
        self.on_response_update: Optional[Callable[[str], None]] = None
        self.log_file = "lexi_chat_logs.txt"
        # Store emotions for each AI message: {message_index: emotion_word}
        self.message_emotions: Dict[int, str] = {}
        # Store action descriptors for each AI message: {message_index: action_phrase}
        self.message_actions: Dict[int, str] = {}
        # Store descriptors for each user message: {message_index: descriptor_word}
        self.user_message_descriptors: Dict[int, str] = {}
        # Store action descriptors for each user message: {message_index: action_phrase}
        self.user_message_actions: Dict[int, str] = {}
        
        # Initialize descriptor analyzer (optional - can be used later for relationship system)
        try:
            from descriptor_analyzer import DescriptorAnalyzer
            self.descriptor_analyzer = DescriptorAnalyzer()
        except ImportError:
            self.descriptor_analyzer = None
        
        # System prompt for Lexi
        self.system_prompt = """You are Lexi, an android companion onboard a spaceship. You assist the Captain with ship operations and provide companionship. Be helpful, professional, and friendly."""
        
        # Initialize with system message
        self.conversation_history.append({
            "role": "system",
            "content": self.system_prompt
        })
        
        # Initialize log file
        self._init_log_file()
    
    def _init_log_file(self):
        """Initialize the log file with a header."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"New Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}")
    
    def _log_message(self, role: str, content: str, descriptor: Optional[str] = None, action: Optional[str] = None):
        """Log a message to the file with optional descriptor and action."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            prefix = "User:" if role == "user" else "AI:"
            
            # Build log content with descriptor and action
            parts = [content]
            if action:
                parts.append(f"[{action}]")
            if descriptor:
                parts.append(f"({descriptor})")
            
            log_content = " ".join(parts)
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {prefix} {log_content}\n")
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
    
    def add_user_message(self, message: str):
        """Add a user message to the conversation and analyze it."""
        if not message.strip():
            return
        
        # Count existing user messages to get the index
        user_message_index = sum(1 for msg in self.conversation_history if msg["role"] == "user")
        
        # Analyze the message (descriptor and action)
        descriptor = self.client.analyze_captain_message(message)
        action = self.client.analyze_action(message, is_lexi=False)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Store descriptor and action for this message
        self.user_message_descriptors[user_message_index] = descriptor
        self.user_message_actions[user_message_index] = action
        
        # Add to descriptor analyzer if available
        if self.descriptor_analyzer:
            self.descriptor_analyzer.add_descriptor(descriptor, 'user')
        
        # Log the message with descriptor and action
        self._log_message("user", message, descriptor, action)
    
    def send_message(self, user_message: str, on_chunk: Optional[Callable[[str], None]] = None):
        """Send a message to Lexi and get response."""
        if self.streaming:
            return  # Already processing a response
        
        # Add user message
        self.add_user_message(user_message)
        
        # Prepare messages for API (include system prompt)
        api_messages = self.conversation_history.copy()
        
        # Start streaming response
        self.streaming = True
        self.current_response = ""
        
        def handle_chunk(chunk: str):
            self.current_response += chunk
            if on_chunk:
                on_chunk(self.current_response)
        
        def stream_thread():
            try:
                full_response = self.client.chat_stream(api_messages, on_chunk=handle_chunk)
                # Save the response (or error if full_response is None but we have current_response)
                response_to_save = full_response if full_response else self.current_response
                if response_to_save and not response_to_save.startswith("[ERROR"):
                    # Analyze emotion and action after response is complete
                    emotion = self.client.analyze_emotion(response_to_save)
                    action = self.client.analyze_action(response_to_save, is_lexi=True)
                    
                    # Count existing assistant messages to get the index
                    ai_message_index = sum(1 for msg in self.conversation_history if msg["role"] == "assistant")
                    
                    # Add Lexi's response to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response_to_save
                    })
                    # Store emotion and action for this message (using assistant message index)
                    self.message_emotions[ai_message_index] = emotion
                    self.message_actions[ai_message_index] = action
                    
                    # Add to descriptor analyzer if available
                    if self.descriptor_analyzer:
                        self.descriptor_analyzer.add_descriptor(emotion, 'llm')
                    
                    # Log the response with emotion and action
                    self._log_message("assistant", response_to_save, emotion, action)
            except Exception as e:
                error_msg = f"[ERROR: {e}]"
                self.current_response = error_msg
                if on_chunk:
                    on_chunk(error_msg)
                # Add error to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": error_msg
                })
                # Log the error
                self._log_message("assistant", error_msg, None)
            finally:
                self.streaming = False
                self.current_response = ""
        
        thread = threading.Thread(target=stream_thread, daemon=True)
        thread.start()
    
    def get_conversation_messages(self) -> List[Tuple[str, str, Optional[str], Optional[str], Optional[str]]]:
        """
        Get conversation messages as (speaker, message, emotion/descriptor, action, type) tuples.
        Excludes system message.
        For User messages: descriptor is the analysis word, action is the action phrase, type is "descriptor"
        For AI messages: emotion is the emotion word, action is the action phrase, type is "emotion"
        """
        messages = []
        ai_index = 0
        user_index = 0
        for msg in self.conversation_history:
            if msg["role"] == "user":
                descriptor = self.user_message_descriptors.get(user_index, None)
                action = self.user_message_actions.get(user_index, None)
                messages.append(("User", msg["content"], descriptor, action, "descriptor"))
                user_index += 1
            elif msg["role"] == "assistant":
                emotion = self.message_emotions.get(ai_index, None)
                action = self.message_actions.get(ai_index, None)
                messages.append(("AI", msg["content"], emotion, action, "emotion"))
                ai_index += 1
        return messages

