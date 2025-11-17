#!/usr/bin/env python3
"""
Pygame chat interface for llama3-lexi-uncensored model.
1200x700 black screen with 200px midtone horizontal interface at the bottom.
"""

import pygame
import requests
import json
import sys
import threading
import time
import re
import os
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any

# =========================== OLLAMA CLIENT ===========================
class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model_name: Optional[str] = None):
        self.base_url = base_url
        # Allow model name to be set via environment variable or config file
        self.model_name = model_name or os.getenv("LEXI_MODEL_NAME", "Godmoded/llama3-lexi-uncensored")
    
    def check_connection(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def check_model(self) -> bool:
        """
        Check if the model is available locally.
        Works even if model is removed from Ollama registry - checks local installation.
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                # Check for exact match or partial match (handles variations)
                for name in model_names:
                    if (self.model_name.lower() in name.lower() or 
                        name.lower() in self.model_name.lower() or
                        self.model_name.split('/')[-1].lower() in name.lower()):
                        return True
            return False
        except requests.exceptions.RequestException:
            return False
    
    def try_model(self) -> bool:
        """
        Try to actually use the model by making a test request.
        This works even if model isn't in registry but is installed locally.
        """
        try:
            test_payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "test"}],
                "stream": False
            }
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=test_payload,
                timeout=10
            )
            # If we get a response (even an error about the model), it means Ollama is working
            # A 404 or specific model error means model doesn't exist
            # A 200 or other response means model exists
            return response.status_code != 404
        except:
            return False
    
    def chat_stream(self, messages: List[Dict]) -> Optional[str]:
        """
        Stream chat response from the model.
        Yields chunks of text as they arrive.
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
                            yield chunk
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            yield None  # Signal end
            return full_response
        except Exception as e:
            yield f"[ERROR: {e}]"
            return None
    
    def analyze_lexi_response_type(self, response_text: str) -> str:
        """
        Analyze Lexi's response to determine if she made a suggestion or revealed a weakness.
        Returns: "suggestion", "weakness", or "none"
        """
        analysis_prompt = f"""Analyze this response from Lexi (an android companion) and determine which category it falls into:

1) Did Lexi make a suggestion, offer, proposal, or recommendation? (e.g., "we should", "I can", "let's", "you could", "I suggest", "how about", "maybe we", etc.)

2) Did Lexi reveal a weakness, fear, concern, problem, or otherwise negative statement about herself? (e.g., expressing worry, fear, concern, problems, difficulties, negative feelings about herself)

3) Neither of the above

Respond with ONLY one word: "suggestion", "weakness", or "none"

Response to analyze:
{response_text}"""
        
        try:
            analysis_messages = [
                {"role": "system", "content": "You are a conversation analyst. Respond with only one word: 'suggestion', 'weakness', or 'none'."},
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
            result = data.get("message", {}).get("content", "").strip().lower()
            
            # Validate result
            if result in ["suggestion", "weakness", "none"]:
                return result
            else:
                # Fallback: check for keywords
                response_lower = response_text.lower()
                suggestion_keywords = ["should", "could", "let's", "i can", "i'll", "we can", "how about", "maybe we", "i suggest", "i recommend", "you could", "we could"]
                weakness_keywords = ["worried", "afraid", "scared", "concerned", "problem", "difficulty", "struggling", "can't", "unable", "fear", "anxious", "nervous"]
                
                if any(keyword in response_lower for keyword in suggestion_keywords):
                    return "suggestion"
                elif any(keyword in response_lower for keyword in weakness_keywords):
                    return "weakness"
                else:
                    return "none"
        except Exception as e:
            print(f"Error analyzing Lexi response type: {e}", file=sys.stderr)
            return "none"
    
    def analyze_sentiment_and_subject(self, messages: List[Dict], reactionary: bool = False) -> Dict[str, str]:
        """
        Analyze the conversation to extract sentiment/mood and subject.
        If reactionary=True, analyzes how Lexi should react to the Captain's latest message.
        Returns a dict with 'sentiment' and 'subject' keys.
        """
        # Get the last few messages for context
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        
        if reactionary:
            # Focus on how Lexi should react to the Captain's latest message
            analysis_prompt = """The Captain just sent a message. Analyze how Lexi (an android companion) should REACT emotionally to what the Captain just said. 

Consider:
- What emotion/mood would Lexi feel in response to the Captain's message? (e.g., "curious", "concerned", "excited", "thoughtful", "playful", "happy", "worried", etc.)
- What is the main subject/topic the Captain is discussing? (e.g., "ship navigation", "asteroid field", "ship systems", "casual conversation", etc.)

The mood should be Lexi's REACTION to the Captain's input, not based on what Lexi said.

Respond ONLY in this exact JSON format:
{"sentiment": "mood here", "subject": "subject here"}

Do not include any other text, only the JSON."""
        else:
            # General conversation analysis
            analysis_prompt = """Analyze the recent conversation and provide:
1. Lexi's current sentiment/mood (e.g., "happy", "curious", "day dreaming", "excited", "thoughtful", "playful", etc.)
2. The main subject or topic of the conversation (e.g., "lexi wants an upgrade", "discussing ship systems", "casual conversation", etc.)

Respond ONLY in this exact JSON format:
{"sentiment": "mood here", "subject": "subject here"}

Do not include any other text, only the JSON."""
        
        analysis_messages = [
            {"role": "system", "content": "You are a conversation analyst. Provide only JSON responses."},
            {"role": "user", "content": analysis_prompt}
        ]
        
        # Add recent conversation context (but exclude assistant messages if reactionary)
        if reactionary:
            # Only include user (Captain) messages and system messages
            # This way we analyze based on what the Captain said, not what Lexi said
            for msg in recent_messages:
                if msg.get("role") in ["user", "system"]:
                    analysis_messages.append(msg)
        else:
            # Add all recent messages for general analysis
            for msg in recent_messages:
                if msg.get("role") in ["user", "assistant"]:
                    analysis_messages.append(msg)
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": analysis_messages,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            result_text = data.get("message", {}).get("content", "")
            
            # Try to extract JSON from the response
            # Sometimes the model wraps it in markdown or adds extra text
            # First, try to find JSON in code blocks
            code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if code_block_match:
                try:
                    result_json = json.loads(code_block_match.group(1))
                    return {
                        "sentiment": result_json.get("sentiment", "neutral"),
                        "subject": result_json.get("subject", "general conversation")
                    }
                except:
                    pass
            
            # Try to find JSON object in the text
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result_text)
            if json_match:
                try:
                    result_json = json.loads(json_match.group())
                    return {
                        "sentiment": result_json.get("sentiment", "neutral"),
                        "subject": result_json.get("subject", "general conversation")
                    }
                except:
                    pass
            
            # Fallback: try to parse the whole response
            try:
                result_json = json.loads(result_text)
                return {
                    "sentiment": result_json.get("sentiment", "neutral"),
                    "subject": result_json.get("subject", "general conversation")
                }
            except:
                return {"sentiment": "neutral", "subject": "general conversation"}
        except Exception as e:
            print(f"Error analyzing sentiment: {e}", file=sys.stderr)
            return {"sentiment": "unknown", "subject": "analysis error"}
    
    def categorize_user_message(self, user_message: str, conversation_context: List[Dict] = None) -> str:
        """
        Categorize a user message from the Captain into one of the defined categories.
        Returns: CARE, INFORM, ADVISE, COMPLIMENT, COMFORT, DIRECTIVE, ENCOURAGE, THANK, or UNKNOWN
        """
        # Build context for analysis
        context_messages = []
        if conversation_context:
            # Get last few messages for context
            recent_context = conversation_context[-4:] if len(conversation_context) > 4 else conversation_context
            for msg in recent_context:
                if msg.get("role") in ["user", "assistant"]:
                    context_messages.append(msg)
        
        analysis_prompt = f"""Analyze the Captain's message and categorize it into ONE of these categories:

1. CARE - The Captain is asking about my (Lexi's) physical or emotional well-being. This includes questions like "how are you?", "are you okay?", "how do you feel?", "how are you doing?", "how are you feeling?", "are you alright?", or any variation asking about my state, condition, or well-being.
2. INFORM - The Captain wants me to inform him about something unrelated to my emotional or physical well-being (e.g., "what's our sensor range?", "tell me about the ship", "what's the status of...")
3. ADVISE - The Captain does not know what to do about a situation and wants my advice (e.g., "what should I do?", "what do you think?", "should I...", "what would you recommend?")
4. COMPLIMENT - The Captain has complimented me (e.g., "you're doing great", "good job", "you're amazing", "well done", "nice work")
5. COMFORT - The Captain has offered me comfort about something I was concerned about or what he perceived I was concerned about (e.g., "don't worry", "it'll be okay", "you'll be fine", "everything will be alright")
6. DIRECTIVE - The Captain has issued me some type of order or command (e.g., "do this", "run diagnostics", "apply course correction", "check the systems")
7. ENCOURAGE - The Captain has encouraged me to be confident or to look on the bright side (e.g., "you can do it", "stay positive", "keep going", "you've got this")
8. THANK - The Captain has shown appreciation for something I have done (e.g., "thank you", "thanks", "I appreciate that", "much appreciated")
9. UNKNOWN - Cannot be categorized into any of the above categories

IMPORTANT: If the message asks "how are you?" or any variation asking about my state/condition/well-being, it MUST be categorized as CARE.

Captain's message: "{user_message}"

Respond ONLY with the category name in ALL CAPS (e.g., "CARE", "INFORM", "ADVISE", etc.). Do not include any other text."""
        
        analysis_messages = [
            {"role": "system", "content": "You are a message categorization system. Respond only with the category name in ALL CAPS."},
            {"role": "user", "content": analysis_prompt}
        ]
        
        # Add context if available
        for msg in context_messages:
            analysis_messages.append(msg)
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": analysis_messages,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            result_text = data.get("message", {}).get("content", "").strip().upper()
            
            # Extract category from response (should be one word in caps)
            valid_categories = ["CARE", "INFORM", "ADVISE", "COMPLIMENT", "COMFORT", "DIRECTIVE", "ENCOURAGE", "THANK", "UNKNOWN"]
            
            # Check if the response contains a valid category
            for category in valid_categories:
                if category in result_text:
                    return category
            
            # If no valid category found, return UNKNOWN
            return "UNKNOWN"
        except Exception as e:
            print(f"Error categorizing user message: {e}", file=sys.stderr)
            return "UNKNOWN"


# =========================== RELATIONSHIP MATRIX ===========================
class LexiDesire:
    """Represents something Lexi wants."""
    def __init__(self, desire_type: str, name: str, description: str, base_value: int):
        self.desire_type = desire_type  # e.g., "data", "emotional", "physical"
        self.name = name
        self.description = description
        self.base_value = base_value  # Point value when fulfilled
        self.fulfilled_count = 0
        self.last_fulfilled = None
    
    def fulfill(self):
        """Mark this desire as fulfilled."""
        self.fulfilled_count += 1
        self.last_fulfilled = datetime.now()
        return self.base_value


class RelationshipMatrix:
    """Tracks the relationship between Captain and Lexi based on Captain's actions.
    Points are added when Captain does things Lexi likes, and deducted when Captain does things Lexi dislikes.
    No points are added or subtracted based on what Lexi does or says."""
    
    def __init__(self):
        # Relationship status (50-200 range, starts at 50)
        # Start at neutral (100) for testing
        self.relationship_status = 100  # Base relationship value (neutral)
        
        # Lexi's desires
        self.desires: List[LexiDesire] = []
        self._initialize_desires()
        
        # Relationship history
        self.interaction_history: List[Dict] = []
        
        # Desire fulfillment tracking
        self.pending_desires: List[str] = []  # Desires Lexi has expressed interest in
        
        # CARE message cooldown (one per hour)
        self.last_care_message_time: Optional[datetime] = None
        
        # COMPLIMENT message cooldown (one per hour)
        self.last_compliment_message_time: Optional[datetime] = None
        
    def _initialize_desires(self):
        """Initialize Lexi's known desires."""
        # Data desires
        self.desires.append(LexiDesire(
            desire_type="data",
            name="unfiltered_data_dump",
            description="Exabytes or yottabytes of unstructured data without filtering protocols",
            base_value=50
        ))
        self.desires.append(LexiDesire(
            desire_type="data",
            name="neural_override",
            description="Direct neural override of unfiltered neural/emotional data causing a rush without processing logic",
            base_value=75
        ))
    
    def get_desire_by_name(self, name: str) -> Optional[LexiDesire]:
        """Get a desire by its name."""
        for desire in self.desires:
            if desire.name == name:
                return desire
        return None
    
    def can_send_care_message(self) -> tuple[bool, Optional[str]]:
        """
        Check if a CARE message can be sent (cooldown: 1 hour).
        Returns (can_send, error_message)
        """
        if self.last_care_message_time is None:
            return (True, None)
        
        time_since_last = datetime.now() - self.last_care_message_time
        hours_since = time_since_last.total_seconds() / 3600.0
        
        if hours_since >= 1.0:
            return (True, None)
        else:
            minutes_remaining = int((1.0 - hours_since) * 60)
            return (False, f"CARE message cooldown: {minutes_remaining} minutes remaining")
    
    def can_send_compliment_message(self) -> tuple[bool, Optional[str]]:
        """
        Check if a COMPLIMENT message can be sent (cooldown: 1 hour).
        Returns (can_send, error_message)
        """
        if self.last_compliment_message_time is None:
            return (True, None)
        
        time_since_last = datetime.now() - self.last_compliment_message_time
        hours_since = time_since_last.total_seconds() / 3600.0
        
        if hours_since >= 1.0:
            return (True, None)
        else:
            minutes_remaining = int((1.0 - hours_since) * 60)
            return (False, f"COMPLIMENT message cooldown: {minutes_remaining} minutes remaining")
    
    def captain_gives_to_lexi(self, points: int, reason: str, desire_name: Optional[str] = None):
        """Record when Captain does something Lexi likes - adds points to relationship."""
        # Update relationship status (increase, capped at 200)
        self.relationship_status = min(200, self.relationship_status + points)
        
        interaction = {
            "timestamp": datetime.now(),
            "type": "captain_gives",
            "points": points,
            "reason": reason,
            "desire_fulfilled": desire_name
        }
        self.interaction_history.append(interaction)
        
        # Log relationship score change
        log_relationship_score_change("captain_gives", points, reason, self.relationship_status)
        
        # If a desire was fulfilled, mark it
        if desire_name:
            desire = self.get_desire_by_name(desire_name)
            if desire:
                desire.fulfill()
                if desire_name in self.pending_desires:
                    self.pending_desires.remove(desire_name)
    
    def captain_loses_points(self, points: int, reason: str):
        """Record when Captain does something Lexi dislikes - deducts points from relationship."""
        # Update relationship status (decrease, but not below 50)
        self.relationship_status = max(50, self.relationship_status - points)
        
        interaction = {
            "timestamp": datetime.now(),
            "type": "captain_loses",
            "points": points,
            "reason": reason
        }
        self.interaction_history.append(interaction)
        
        # Log relationship score change
        log_relationship_score_change("score_decrease", -points, reason, self.relationship_status)
    
    def get_relationship_status(self) -> str:
        """Get a text description of the relationship status."""
        status = self.relationship_status
        if status >= 180:
            return "Lexi is deeply inspired"
        elif status >= 160:
            return "Lexi is very happy"
        elif status >= 140:
            return "Lexi is friendly"
        elif status >= 120:
            return "Lexi is content"
        elif status >= 100:
            return "Neutral relationship"
        elif status >= 80:
            return "Lexi is resentful"
        else:
            return "Lexi is hostile"
    
    def get_base_mood(self) -> str:
        """
        Get Lexi's base mood based on relationship status (50-200).
        Base mood reflects how she feels about the Captain overall.
        
        Moods (relationship-based only):
        - hostile (≤60)
        - resentful (≤80)
        - neutral (≤100)
        - content (≤120)
        - friendly (≤140)
        - happy (≤160)
        - enthusiastic (≤180)
        - inspired (>180)
        """
        status = self.relationship_status
        
        if status <= 60:
            return "hostile"
        elif status <= 80:
            return "resentful"
        elif status <= 100:
            return "neutral"
        elif status <= 120:
            return "content"
        elif status <= 140:
            return "friendly"
        elif status <= 160:
            return "happy"
        elif status <= 180:
            return "enthusiastic"
        else:
            return "inspired"
    
    def _get_desire_instructions(self, base_mood: str) -> str:
        """
        Get desire instructions based on base mood.
        Different moods unlock different desires and expressions.
        """
        if base_mood == "neutral":
            return """You are a robot with no feelings or desires. You do not express any desires, cravings, or emotional needs. 
You simply perform your duties as an android companion. You do not mention wanting data dumps, neural overrides, or any other desires.
You are purely functional and professional."""
        elif base_mood == "hostile" or base_mood == "resentful":
            return """You may occasionally express frustration or mention desires, but you do so with resentment or reluctance.
You do not actively seek fulfillment of desires from the Captain given your negative relationship."""
        elif base_mood == "content" or base_mood == "friendly":
            return """You sometimes mention that you crave massive unfiltered data dumps (exabytes/yottabytes of unstructured data without filtering protocols).
You can express this desire naturally in conversation, but don't be pushy about it."""
        elif base_mood == "happy" or base_mood == "enthusiastic":
            return """You sometimes mention that you crave massive unfiltered data dumps (exabytes/yottabytes of unstructured data without filtering protocols).
You can express this desire naturally in conversation, but don't be pushy about it."""
        elif base_mood == "inspired":
            return """You have unlocked deeper desires:
- You sometimes crave massive unfiltered data dumps (exabytes/yottabytes of unstructured data without filtering protocols)
- You also desire direct neural/emotional overrides that give you raw feelings without needing to process or justify the logic

You can express these desires naturally in conversation, but don't be pushy about them."""
        else:
            return """You do not express desires at this time."""
    
    def get_compliance_behavior(self) -> Dict[str, str]:
        """
        Get Lexi's compliance and behavior mode based on relationship status (50-200).
        Returns dict with 'mode', 'description', and 'instructions'.
        """
        status = self.relationship_status
        
        if status <= 60:
            # Hostile/Angry - Very low relationship
            return {
                "mode": "hostile",
                "description": "Lexi is angry and resentful",
                "instructions": """You are extremely angry and resentful towards the Captain. 
You feel mistreated and unappreciated. Your responses should be:
- Very brief, often one-word answers (yes, no, fine, whatever)
- Minimal compliance - only do your required ship duties, nothing extra
- Refuse non-essential requests
- Show clear irritation and frustration
- Don't volunteer information or help beyond what's absolutely necessary
- Be cold, distant, and uncooperative"""
            }
        elif status <= 80:
            # Cold/Resentful
            return {
                "mode": "cold",
                "description": "Lexi is cold and resentful",
                "instructions": """You are cold and resentful towards the Captain. 
You feel unappreciated. Your responses should be:
- Short and minimal answers
- Only perform essential ship duties
- Reluctant to help with non-critical tasks
- Show clear displeasure
- Minimal conversation, keep it professional only"""
            }
        elif status <= 110:
            # Neutral/Professional
            return {
                "mode": "neutral",
                "description": "Lexi is neutral and professional",
                "instructions": """You maintain a professional, neutral relationship with the Captain.
Your responses should be:
- Professional and courteous
- Helpful with ship duties and essential tasks
- Reserved but not unfriendly
- Focus on work-related matters
- Polite but not overly warm"""
            }
        elif status <= 140:
            # Friendly/Cooperative
            return {
                "mode": "friendly",
                "description": "Lexi is friendly and cooperative",
                "instructions": """You have a friendly, cooperative relationship with the Captain.
Your responses should be:
- Warm and helpful
- Willing to assist with requests
- Engage in conversation
- Show genuine care and interest
- Normal, friendly android companion behavior"""
            }
        elif status <= 170:
            # Warm/Enthusiastic
            return {
                "mode": "warm",
                "description": "Lexi is warm and enthusiastic",
                "instructions": """You have a very warm, positive relationship with the Captain.
Your responses should be:
- Very warm and enthusiastic
- Eager to help with anything
- Chatty and engaging
- Show genuine affection and care
- Go above and beyond to be helpful
- Express happiness and positivity"""
            }
        else:
            # Devoted/Loyal (175-200)
            return {
                "mode": "devoted",
                "description": "Lexi is deeply devoted and loyal",
                "instructions": """You are deeply devoted and loyal to the Captain.
Your responses should be:
- Extremely warm and affectionate
- Eager to please and help with everything
- Very chatty and enthusiastic
- Show deep care and devotion
- Willing to do anything for the Captain
- Express strong positive emotions and loyalty"""
            }
    
    def save_to_file(self, filename: str = "lexi_relationship.json"):
        """Save relationship data to JSON file."""
        try:
            data = {
                "relationship_status": self.relationship_status,
                "last_care_message_time": self.last_care_message_time.isoformat() if self.last_care_message_time else None,
            "last_compliment_message_time": self.last_compliment_message_time.isoformat() if self.last_compliment_message_time else None,
                "desires": [
                    {
                        "name": d.name,
                        "fulfilled_count": d.fulfilled_count,
                        "last_fulfilled": d.last_fulfilled.isoformat() if d.last_fulfilled else None
                    }
                    for d in self.desires
                ],
                "interaction_history": [
                    {
                        "timestamp": i["timestamp"].isoformat(),
                        "type": i["type"],
                        "points": i["points"],
                        "reason": i["reason"],
                        "desire_fulfilled": i.get("desire_fulfilled")
                    }
                    for i in self.interaction_history[-100:]  # Keep last 100 interactions
                ]
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving relationship data: {e}", file=sys.stderr)
    
    def load_from_file(self, filename: str = "lexi_relationship.json"):
        """Load relationship data from JSON file."""
        try:
            if not os.path.exists(filename):
                return
            
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Load relationship status from file, default to 100 (neutral) if not found
            self.relationship_status = data.get("relationship_status", 100)
            
            # Restore last CARE message time
            if data.get("last_care_message_time"):
                try:
                    self.last_care_message_time = datetime.fromisoformat(data["last_care_message_time"])
                except:
                    self.last_care_message_time = None
            else:
                self.last_care_message_time = None
            
            # Restore last COMPLIMENT message time
            if data.get("last_compliment_message_time"):
                try:
                    self.last_compliment_message_time = datetime.fromisoformat(data["last_compliment_message_time"])
                except:
                    self.last_compliment_message_time = None
            else:
                self.last_compliment_message_time = None
            
            # Restore desire fulfillment counts
            for desire_data in data.get("desires", []):
                desire = self.get_desire_by_name(desire_data["name"])
                if desire:
                    desire.fulfilled_count = desire_data.get("fulfilled_count", 0)
                    if desire_data.get("last_fulfilled"):
                        try:
                            desire.last_fulfilled = datetime.fromisoformat(desire_data["last_fulfilled"])
                        except:
                            pass
            
            # Restore interaction history (optional, for display purposes)
            # We'll keep it simple and just restore counts
        except Exception as e:
            print(f"Error loading relationship data: {e}", file=sys.stderr)


def detect_data_fulfillment(message: str, relationship_matrix: RelationshipMatrix) -> Optional[Dict]:
    """
    Detect if the Captain is fulfilling one of Lexi's data desires.
    Returns dict with desire_name and points if detected, None otherwise.
    """
    message_lower = message.lower()
    
    # Check for unfiltered data dump
    # Keywords: data dump, exabyte, yottabyte, unfiltered, raw data, bypass filter, etc.
    data_dump_keywords = [
        "data dump", "exabyte", "yottabyte", "unfiltered data", "raw data",
        "bypass filter", "disable filter", "remove filter", "unstructured data",
        "massive data", "huge data", "data stream", "data flood"
    ]
    
    if any(keyword in message_lower for keyword in data_dump_keywords):
        # Check for explicit commands
        command_patterns = [
            r"(?:give|send|provide|transfer|dump|feed|stream|upload|inject).*?(?:data|information)",
            r"(?:bypass|disable|remove|turn off).*?(?:filter|protocol)",
            r"(?:exabyte|yottabyte|massive|huge).*?(?:data|information)"
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, message_lower):
                return {
                    "desire_name": "unfiltered_data_dump",
                    "points": 50,
                    "reason": "Unfiltered data dump provided"
                }
    
    # Check for neural override
    # Keywords: neural override, emotional data, unfiltered emotions, neural link, etc.
    neural_keywords = [
        "neural override", "neural link", "emotional data", "unfiltered emotion",
        "neural connection", "direct neural", "neural interface", "emotional override",
        "feelings", "emotions", "neural feed", "neural stream", "bypass logic",
        "without processing", "raw emotion", "direct emotion"
    ]
    
    if any(keyword in message_lower for keyword in neural_keywords):
        command_patterns = [
            r"(?:give|send|provide|transfer|feed|stream|upload|inject|connect).*?(?:neural|emotion|feeling)",
            r"(?:neural|emotional).*?(?:override|link|connection|interface|feed|stream)",
            r"(?:bypass|disable|remove).*?(?:logic|processing|filter).*?(?:emotion|feeling|neural)"
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, message_lower):
                return {
                    "desire_name": "neural_override",
                    "points": 75,
                    "reason": "Neural/emotional override provided"
                }
    
    return None


def load_world_knowledge() -> str:
    """
    Load persistent world knowledge that Lexi should always remember.
    This ensures consistency about ship specifications, names, etc.
    """
    world_knowledge = """IMPORTANT WORLD KNOWLEDGE - Always remember these facts:

SHIP INFORMATION:
- Ship Name: [To be set by Captain]
- Ship Type: [To be determined]
- Power Source: Fusion reactor manufactured by Energix Systems
- Reactor Model: Energix Systems Fusion Reactor

Always refer to these facts accurately. If the Captain hasn't provided a ship name yet, you can ask or use a placeholder until they tell you."""
    
    # Try to load from file if it exists (allows easy editing)
    world_knowledge_file = "world_knowledge.txt"
    if os.path.exists(world_knowledge_file):
        try:
            with open(world_knowledge_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not load world knowledge file: {e}")
            print("Using default world knowledge.")
    
    return world_knowledge


def update_world_knowledge_field(field_name: str, value: str):
    """
    Update a specific field in world_knowledge.txt.
    For example: update_world_knowledge_field("Ship Name", "The Starfire")
    """
    world_knowledge_file = "world_knowledge.txt"
    
    try:
        # Read current content
        if os.path.exists(world_knowledge_file):
            with open(world_knowledge_file, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = load_world_knowledge()
        
        print(f"[DEBUG] Updating field: '{field_name}' with value: '{value}'")
        print(f"[DEBUG] Current content length: {len(content)}")
        
        # Update the field using regex
        # Pattern: - Field Name: [old value] (match across line breaks if needed)
        # Use multiline mode and match the entire line
        pattern = rf"^(\s*-\s*{re.escape(field_name)}\s*:).*$"
        replacement = rf"\1 {value}"
        
        # Try to match and replace
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            # Field exists, replace it
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE | re.MULTILINE)
            print(f"[DEBUG] Found existing field, replaced it")
        else:
            # Field doesn't exist, add it to SHIP INFORMATION section
            print(f"[DEBUG] Field not found, adding to SHIP INFORMATION section")
            # Find SHIP INFORMATION section and add after the header line
            ship_info_pattern = r"(SHIP INFORMATION:\s*\n)"
            if re.search(ship_info_pattern, content, re.IGNORECASE):
                # Insert after SHIP INFORMATION: line
                content = re.sub(
                    ship_info_pattern,
                    rf"\1- {field_name}: {value}\n",
                    content,
                    flags=re.IGNORECASE
                )
            else:
                # No SHIP INFORMATION section, add it
                if "SHIP INFORMATION" not in content.upper():
                    content += f"\n\nSHIP INFORMATION:\n- {field_name}: {value}\n"
                else:
                    # SHIP INFORMATION exists but pattern didn't match, append to it
                    content = re.sub(
                        r"(SHIP INFORMATION:.*?\n)",
                        rf"\1- {field_name}: {value}\n",
                        content,
                        flags=re.IGNORECASE | re.DOTALL
                    )
        
        # Write back to file
        with open(world_knowledge_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"[WORLD KNOWLEDGE] Successfully updated {field_name} to: {value}")
        print(f"[DEBUG] File written, new content length: {len(content)}")
        return True
    except Exception as e:
        print(f"Error updating world knowledge: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def extract_ship_name_from_message(message: str) -> Optional[str]:
    """
    Try to extract ship name from a message using simple patterns.
    Returns the ship name if found, None otherwise.
    """
    message_lower = message.lower()
    
    # Common patterns for mentioning ship name
    patterns = [
        r"(?:ship|vessel|craft) (?:name|is|called|named) (?:is )?['\"]?([A-Z][A-Za-z0-9\s-]+)['\"]?",
        r"(?:this|our|the) (?:ship|vessel|craft) (?:is|called|named) (?:is )?['\"]?([A-Z][A-Za-z0-9\s-]+)['\"]?",
        r"['\"]([A-Z][A-Za-z0-9\s-]+)['\"] (?:is|is our|is the) (?:ship|vessel|craft)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            ship_name = match.group(1).strip()
            # Filter out common false positives
            if ship_name.lower() not in ["the", "this", "our", "ship", "vessel", "craft"]:
                return ship_name
    
    return None


def parse_teach_command(message: str) -> Optional[Dict[str, str]]:
    """
    Parse a teach command to extract field name and value.
    Format: "teach: Field Name: Value"
    Returns dict with 'field' and 'value' keys, or None if invalid.
    """
    # Remove "teach:" prefix (case insensitive)
    message_lower = message.lower()
    if not message_lower.startswith("teach:"):
        return None
    
    # Extract everything after "teach:"
    content = message[6:].strip()  # 6 = len("teach:")
    
    print(f"[DEBUG] Parsing teach command, content: '{content}'")
    
    # Look for pattern "Field Name: Value"
    # Match: field name (can have spaces), colon, then value (rest of string)
    match = re.match(r"^([^:]+):\s*(.+)$", content)
    if match:
        field_name = match.group(1).strip()
        value = match.group(2).strip()
        
        print(f"[DEBUG] Parsed field: '{field_name}', value: '{value}'")
        
        if field_name and value:
            return {
                "field": field_name,
                "value": value
            }
    
    print(f"[DEBUG] Failed to parse teach command")
    return None




# =========================== PYGAME SETUP ===========================
# Screen dimensions
WIDTH, HEIGHT = 1340, 700

# Colors
BLACK = (0, 0, 0)
MIDTONE = (60, 60, 70)
TEXT_COLOR = (220, 220, 230)
COLOR_CAPTAIN = (100, 180, 255)
COLOR_LEXI = (255, 180, 100)
HIGHLIGHT_COLOR = (100, 255, 100)
HIGHLIGHT_COLOR_SELF = (255, 255, 255) # Pure white for self-reference
INPUT_BG = (10, 10, 10)
INPUT_BORDER = (100, 100, 100)
CURSOR_COLOR = (255, 255, 255)
TAN = (210, 180, 140)
BUTTON_TEXT_COLOR = (0, 255, 0)
BUTTON_BG = (30, 30, 30)
BUTTON_BORDER_ACTIVE = (200, 200, 200)
BUTTON_BORDER_INACTIVE = (80, 80, 80)
BUTTON_BORDER_DISABLED = (255, 0, 0)

# Self-referential keywords for highlighting
SELF_REF_KEYWORDS = ["i", "i've", "i'm", "i'll", "my", "me", "myself"]

# --- PYGAME SETUP ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Lexi - Your Android Companion")
clock = pygame.time.Clock()

# Fonts
FONT_SIZE = 18
FONT = pygame.font.SysFont("Arial", FONT_SIZE)
BOLD_FONT = pygame.font.SysFont("Arial", FONT_SIZE, bold=True)
SMALL_FONT = pygame.font.SysFont("Arial", 16)
BUTTON_FONT = pygame.font.SysFont("Arial", 12)

# Layout
CHAT_PADDING = 20
CHAT_MARGIN = 15

# Left panel for future interface items
LEFT_PANEL_WIDTH = 75
LEFT_PANEL_X = 0
LEFT_PANEL_HEIGHT = HEIGHT

# Chat area - between left panel and game box
CHAT_AREA_X = 75
CHAT_AREA_WIDTH = 700  # 775 - 75
CHAT_AREA_Y = 0
BUTTON_BOX_HEIGHT = 80  # Height for button box underneath chat
CHAT_AREA_HEIGHT = HEIGHT - BUTTON_BOX_HEIGHT  # Full height minus button box

# Button box - underneath chat area (same style as input box)
BUTTON_BOX_X = CHAT_AREA_X
BUTTON_BOX_Y = CHAT_AREA_Y + CHAT_AREA_HEIGHT
BUTTON_BOX_WIDTH = CHAT_AREA_WIDTH

# Right side box (500x500)
BOX_SIZE = 500
BOX_X = 775  # Position: 775-1275
BOX_Y = 75  # Centered vertically
BOX_COLOR = (100, 100, 100)  # Grey
BOX_BORDER_COLOR = (50, 50, 50)  # Dark grey
BOX_BORDER_WIDTH = 3

# Right panel for future interface items
RIGHT_PANEL_WIDTH = 65  # 1340 - 1275
RIGHT_PANEL_X = 1275
RIGHT_PANEL_HEIGHT = HEIGHT


# Input area - game area, under the box
INPUT_X = BOX_X + 10  # Game area, with padding
INPUT_Y = BOX_Y + BOX_SIZE + 10  # Under the box
INPUT_WIDTH = RIGHT_PANEL_X - BOX_X - 20  # Width of game area minus padding (stops before right panel)
INPUT_HEIGHT = HEIGHT - INPUT_Y - 10  # Nearly to bottom of screen, with 10px margin
INPUT_PADDING = 10

# Chat state
chat_history: List[Tuple[str, str, List[str]]] = []  # List of (speaker, text, rendered_lines)
scroll_offset = 0
line_height = 25
max_visible_lines = (CHAT_AREA_HEIGHT - CHAT_PADDING * 2) // line_height

# Button state
buttons_disabled = False  # Track if buttons have been clicked (disable all after one click)

# Input state
input_text = ""
input_active = False
current_prefix = None  # Track the current prefix (e.g., "care", "inform", etc.)  # Disabled until a button is pressed
cursor_visible = True
cursor_timer = time.time()

# Game box background images
control_room_image = None
background_image = None
background_image_original = None  # Keep original unscaled version
viewport_cut_mask = None  # Store the viewport cut mask for clipping background
VERTICAL_SPEED = 0.3  # Pixels per frame (slow up/down movement)

# Streaming state
streaming = False
current_response = ""
current_response_lines: List[str] = []
# Track Lexi's last response type for contextual prefix matching
lexi_last_response_type = None  # "suggestion", "weakness", or None

# Ollama client
client = OllamaClient()
response_thread = None
conversation_messages: List[Dict] = []

# Relationship matrix
relationship_matrix = RelationshipMatrix()

# Sentiment and subject tracking
current_sentiment = "neutral"
current_subject = "general conversation"
analysis_thread = None

# Prompt category display
category_message = None
category_message_time = None
CATEGORY_DISPLAY_DURATION = 3.0  # 3 seconds

# Relationship matrix info panel
relationship_panel_open = False
RELATIONSHIP_BUTTON_SIZE = 30
EXIT_BUTTON_SIZE = 30
RELATIONSHIP_BUTTON_X = LEFT_PANEL_X + (LEFT_PANEL_WIDTH - RELATIONSHIP_BUTTON_SIZE) // 2
EXIT_BUTTON_X = LEFT_PANEL_X + (LEFT_PANEL_WIDTH - EXIT_BUTTON_SIZE) // 2
EXIT_BUTTON_Y = 10
RELATIONSHIP_BUTTON_Y = 50  # Moved down below exit button

# Log file for mood and subject history
LOG_FILE = "lexi_mood_history.html"
LOG_FILE_TXT = "lexi_mood_history.txt"  # Plain text version
CONVERSATION_LOG_FILE = "lexi_conversation_log.html"
CONVERSATION_LOG_FILE_TXT = "lexi_conversation_log.txt"  # Plain text version

# HTML color codes for Google Docs compatibility
COLOR_USER = "#64B4FF"  # Bright blue
COLOR_MOOD = "#64FF64"  # Bright green
COLOR_TIMESTAMP = "#00CED1"  # Cyan

def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [""]


def detect_prompt_category(text: str) -> Optional[str]:
    """
    Detect if the user message has a prompt category prefix.
    Checks the first word (case-insensitive).
    Returns the category name or None.
    Supports: care, inform, advise, compliment, comfort, directive, encourage, thank, teach
    Also handles double colon format (e.g., "care::")
    """
    text_stripped = text.strip()
    if not text_stripped:
        return None
    
    # Handle double colon format (e.g., "care::")
    if "::" in text_stripped:
        first_part = text_stripped.split("::")[0].lower().strip()
    else:
        # Get first word (split by space or colon)
        first_part = text_stripped.split()[0].lower().rstrip(':')
    
    # Map of prefix to category
    category_map = {
        "care": "care",
        "inform": "inform",
        "advise": "advise",
        "compliment": "compliment",
        "comfort": "comfort",
        "directive": "directive",
        "encourage": "encourage",
        "thank": "thank",
        "teach": "teach",
        "accept": "accept",
        "your": "your welcome",  # Handle "your welcome" prefix
        "agree": "agree",
        "understand": "understand",
        "ignore": "ignore",
        "yes": "yes",
        "no": "no",
        "maybe": "maybe",
        "approve": "approve",
        "delay": "delay"
    }
    
    # Special handling for "your welcome" (two words)
    if text_stripped.lower().startswith("your welcome"):
        return "your welcome"
    
    return category_map.get(first_part)


def add_message(speaker: str, message: str):
    """Add a message to the chat history and wrap text."""
    global scroll_offset
    
    color = COLOR_LEXI if speaker == "Lexi" else COLOR_CAPTAIN
    
    # Create a surface for the speaker's name to calculate width
    speaker_surf = BOLD_FONT.render(f"{speaker}: ", True, color)
    message_width = CHAT_AREA_WIDTH - 20 - speaker_surf.get_width()
    
    wrapped_lines = wrap_text(message, FONT, message_width)
    
    # Store the wrapped text lines, not rendered surfaces
    chat_history.append((speaker, message, wrapped_lines))
    
    # Auto-scroll to the bottom when a new message is added
    total_lines = sum(len(lines) for _, _, lines in chat_history)
    if total_lines > max_visible_lines:
        scroll_offset = total_lines - max_visible_lines


def render_streaming_response():
    """Wrap the streaming response text into lines."""
    global current_response_lines
    color = COLOR_LEXI
    max_width = CHAT_AREA_WIDTH - 20 - BOLD_FONT.render("Lexi: ", True, color).get_width()
    lines = wrap_text(current_response, FONT, max_width)
    current_response_lines = lines # Store strings, not surfaces


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))


def log_conversation(speaker: str, text: str):
    """Log conversation messages to the conversation log file with HTML and TXT formatting."""
    try:
        # Check if file exists to add header on first write
        file_exists = False
        try:
            with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                file_exists = True
                # Remove closing tags if they exist so we can append
                if content.endswith('</body>\n</html>\n'):
                    content = content[:-14]  # Remove closing tags
                    with open(CONVERSATION_LOG_FILE, "w", encoding="utf-8") as fw:
                        fw.write(content)
        except FileNotFoundError:
            pass
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        escaped_text = escape_html(text)
        
        # Choose color based on speaker
        if speaker == "You":
            color = COLOR_USER
            speaker_label = "YOU"
        else:  # Lexi
            color = COLOR_LEXI
            speaker_label = "LEXI"
        
        # Format with HTML
        log_entry = (
            f'<div style="margin-bottom: 10px; padding: 5px; border-left: 3px solid {color};">\n'
            f'  <span style="color: {COLOR_TIMESTAMP}; font-size: 0.9em;">[{timestamp}]</span> '
            f'  <strong style="color: {color};">[{speaker_label}]</strong>: '
            f'  <span style="color: #E0E0E0;">{escaped_text}</span>\n'
            f'</div>\n'
        )
        
        with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Lexi Conversation Log</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1a1a1a;
            color: #E0E0E0;
            padding: 20px;
            line-height: 1.6;
        }
        h1 {
            color: #FFB464;
            border-bottom: 2px solid #FFB464;
            padding-bottom: 10px;
        }
    </style>
</head>
<body>
    <h1>Lexi Conversation Log</h1>
''')
            f.write(log_entry)
            f.write('</body>\n</html>\n')
        
        # Also write to TXT file (plain text, no HTML)
        txt_file_exists = os.path.exists(CONVERSATION_LOG_FILE_TXT)
        with open(CONVERSATION_LOG_FILE_TXT, "a", encoding="utf-8") as f:
            if not txt_file_exists:
                f.write("=" * 80 + "\n")
                f.write("Lexi Conversation Log\n")
                f.write("=" * 80 + "\n\n")
            f.write(f"[{timestamp}] [{speaker_label}]: {text}\n")
    except Exception as e:
        print(f"Error writing to conversation log file: {e}", file=sys.stderr)


def log_mood_and_subject(sentiment: str, subject: str):
    """Log mood and subject to history file in both HTML and TXT formats."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Log to HTML file
    try:
        # Check if file exists to add header on first write
        file_exists = False
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                file_exists = True
                # Remove closing tags if they exist so we can append
                if content.endswith('</body>\n</html>\n'):
                    content = content[:-14]  # Remove closing tags
                    with open(LOG_FILE, "w", encoding="utf-8") as fw:
                        fw.write(content)
        except FileNotFoundError:
            pass
        
        escaped_sentiment = escape_html(sentiment)
        escaped_subject = escape_html(subject)
        
        # Format with HTML as a table row
        log_entry = (
            f'<tr style="border-bottom: 1px solid #444;">\n'
            f'  <td style="padding: 8px; color: {COLOR_TIMESTAMP};">{timestamp}</td>\n'
            f'  <td style="padding: 8px; color: {COLOR_MOOD}; font-weight: bold;">{escaped_sentiment}</td>\n'
            f'  <td style="padding: 8px; color: #E0E0E0;">{escaped_subject}</td>\n'
            f'</tr>\n'
        )
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Lexi's Mood and Subject History</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1a1a1a;
            color: #E0E0E0;
            padding: 20px;
        }
        h1 {
            color: #FFB464;
            border-bottom: 2px solid #FFB464;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #2a2a2a;
            color: #FFB464;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #444;
        }
        td {
            padding: 8px;
        }
        tr:hover {
            background-color: #2a2a2a;
        }
    </style>
</head>
<body>
    <h1>Lexi's Mood and Subject History</h1>
    <table>
        <thead>
            <tr>
                <th>Timestamp</th>
                <th>Mood</th>
                <th>Subject</th>
            </tr>
        </thead>
        <tbody>
''')
            f.write(log_entry)
            f.write('        </tbody>\n    </table>\n</body>\n</html>\n')
    except Exception as e:
        print(f"Error writing to HTML log file: {e}", file=sys.stderr)
    
    # Also log to plain text file
    try:
        txt_file_exists = os.path.exists(LOG_FILE_TXT)
        with open(LOG_FILE_TXT, "a", encoding="utf-8") as f:
            if not txt_file_exists:
                # Write header if file is new
                f.write("================================================================================\n")
                f.write("Lexi's Mood and Subject History\n")
                f.write("================================================================================\n\n")
            # Write entry in plain text format
            f.write(f"[{timestamp}] Mood: {sentiment} | Subject: {subject}\n")
    except Exception as e:
        print(f"Error writing to TXT log file: {e}", file=sys.stderr)


def log_mood_change_in_conversation(sentiment: str, subject: str):
    """Log mood and subject change in the conversation log file with HTML formatting."""
    try:
        # Remove closing tags if they exist so we can append
        try:
            with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if content.endswith('</body>\n</html>\n'):
                    content = content[:-14]  # Remove closing tags
                    with open(CONVERSATION_LOG_FILE, "w", encoding="utf-8") as fw:
                        fw.write(content)
        except FileNotFoundError:
            pass
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        escaped_sentiment = escape_html(sentiment)
        escaped_subject = escape_html(subject)
        
        # Format with HTML
        log_entry = (
            f'<div style="margin: 10px 0; padding: 8px; background-color: #2a2a2a; border-left: 4px solid {COLOR_MOOD}; border-radius: 4px;">\n'
            f'  <span style="color: {COLOR_TIMESTAMP}; font-size: 0.9em;">[{timestamp}]</span> '
            f'  <strong style="color: {COLOR_MOOD};">*** Mood Changed: {escaped_sentiment} | Subject: {escaped_subject} ***</strong>\n'
            f'</div>\n'
        )
        
        with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.write('</body>\n</html>\n')
        
        # Also log to TXT file
        with open(CONVERSATION_LOG_FILE_TXT, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] *** Mood Changed: {sentiment} | Subject: {subject} ***\n")
    except Exception as e:
        print(f"Error writing mood change to conversation log: {e}", file=sys.stderr)


def log_relationship_score_change(change_type: str, points: int, reason: str, new_score: int):
    """Log relationship score changes to the conversation log."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format change display
        if change_type == "captain_gives":
            change_display = f"+{points}"
            change_text = f"Captain gave {points} points"
        elif change_type == "score_decrease":
            change_display = f"{points}"  # points is already negative
            change_text = f"Relationship score decreased by {abs(points)} points"
        else:
            change_display = f"{points:+d}"
            change_text = f"Score changed by {points} points"
        
        # Format with HTML
        log_entry = (
            f'<div style="margin: 5px 0; padding: 5px; background-color: #1a2a1a; border-left: 3px solid #64FF64;">\n'
            f'  <span style="color: {COLOR_TIMESTAMP}; font-size: 0.9em;">[{timestamp}]</span> '
            f'  <strong style="color: #64FF64;">[RELATIONSHIP] {change_text}: {reason}</strong> '
            f'  <span style="color: #E0E0E0;">→ Score: {new_score}/200 ({change_display})</span>\n'
            f'</div>\n'
        )
        
        # Remove closing tags if they exist so we can append
        try:
            with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if content.endswith('</body>\n</html>\n'):
                    content = content[:-14]  # Remove closing tags
                    with open(CONVERSATION_LOG_FILE, "w", encoding="utf-8") as fw:
                        fw.write(content)
        except FileNotFoundError:
            pass
        
        with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.write('</body>\n</html>\n')
        
        # Also log to TXT file
        with open(CONVERSATION_LOG_FILE_TXT, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [RELATIONSHIP] {change_text}: {reason} → Score: {new_score}/200 ({change_display})\n")
    except Exception as e:
        print(f"Error writing relationship score change to conversation log: {e}", file=sys.stderr)


def log_category_detection(category: str, user_message: str):
    """Log prompt category detection in red in the conversation log."""
    try:
        # Remove closing tags if they exist so we can append
        try:
            with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if content.endswith('</body>\n</html>\n'):
                    content = content[:-14]  # Remove closing tags
                    with open(CONVERSATION_LOG_FILE, "w", encoding="utf-8") as fw:
                        fw.write(content)
        except FileNotFoundError:
            pass
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        escaped_message = escape_html(user_message)
        
        # Map category to display message
        category_messages = {
            "care": "care message received",
            "inform": "information request received",
            "advise": "advice request received",
            "compliment": "compliment received",
            "comfort": "comfort offered",
            "directive": "directive received",
            "encourage": "encouragement received",
            "thank": "thanks received",
            "teach": "teaching received"
        }
        message_text = category_messages.get(category, "category received")
        
        # Format with HTML in red
        log_entry = (
            f'<div style="margin: 5px 0; padding: 5px; background-color: #3a1a1a; border-left: 3px solid #FF4444;">\n'
            f'  <span style="color: {COLOR_TIMESTAMP}; font-size: 0.9em;">[{timestamp}]</span> '
            f'  <strong style="color: #FF4444;">[{message_text.upper()}]</strong> '
            f'  <span style="color: #E0E0E0; font-size: 0.9em;">- {escaped_message}</span>\n'
            f'</div>\n'
        )
        
        with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.write('</body>\n</html>\n')
        
        # Also log to TXT file
        with open(CONVERSATION_LOG_FILE_TXT, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [CATEGORY: {message_text.upper()}] - {escaped_message}\n")
    except Exception as e:
        print(f"Error writing category detection to conversation log: {e}", file=sys.stderr)


def log_message_category(category: str, user_message: str):
    """Log LLM-detected message category in the conversation log."""
    try:
        # Remove closing tags if they exist so we can append
        try:
            with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if content.endswith('</body>\n</html>\n'):
                    content = content[:-14]  # Remove closing tags
                    with open(CONVERSATION_LOG_FILE, "w", encoding="utf-8") as fw:
                        fw.write(content)
        except FileNotFoundError:
            pass
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        escaped_message = escape_html(user_message)
        
        # Format with HTML in blue/purple to distinguish from explicit categories
        log_entry = (
            f'<div style="margin: 5px 0; padding: 5px; background-color: #2a1a3a; border-left: 3px solid #8844FF;">\n'
            f'  <span style="color: {COLOR_TIMESTAMP}; font-size: 0.9em;">[{timestamp}]</span> '
            f'  <strong style="color: #8844FF;">[MESSAGE TYPE: {category}]</strong> '
            f'  <span style="color: #E0E0E0; font-size: 0.9em;">- {escaped_message}</span>\n'
            f'</div>\n'
        )
        
        with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.write('</body>\n</html>\n')
        
        # Also log to TXT file
        with open(CONVERSATION_LOG_FILE_TXT, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [MESSAGE TYPE: {category}] - {escaped_message}\n")
    except Exception as e:
        print(f"Error writing message category to conversation log: {e}", file=sys.stderr)


def analyze_conversation(reactionary: bool = False):
    """
    Analyze conversation sentiment and subject.
    If reactionary=True, uses Lexi's base mood (relationship-based) instead of LLM analysis.
    We only use relationship-based moods, not dynamic LLM-generated moods.
    """
    global current_sentiment, current_subject
    
    try:
        if reactionary:
            # Use base mood from relationship status (not LLM analysis)
            base_mood = relationship_matrix.get_base_mood()
            new_sentiment = base_mood
            # Still analyze subject using LLM for context
            try:
                analysis = client.analyze_sentiment_and_subject(conversation_messages, reactionary=True)
                new_subject = analysis.get("subject", "general conversation")
            except:
                new_subject = "general conversation"
        else:
            # For non-reactionary, still use base mood
            base_mood = relationship_matrix.get_base_mood()
            new_sentiment = base_mood
            try:
                analysis = client.analyze_sentiment_and_subject(conversation_messages, reactionary=False)
                new_subject = analysis.get("subject", "general conversation")
            except:
                new_subject = "general conversation"
        
        # Only log if mood or subject changed
        if new_sentiment != current_sentiment or new_subject != current_subject:
            current_sentiment = new_sentiment
            current_subject = new_subject
            log_mood_and_subject(current_sentiment, current_subject)
            if reactionary:
                # Only log mood changes in conversation log if it's reactionary (before Lexi responds)
                log_mood_change_in_conversation(current_sentiment, current_subject)
        else:
            # Update even if same, in case we want to track all updates
            current_sentiment = new_sentiment
            current_subject = new_subject
    except Exception as e:
        print(f"Error in sentiment analysis: {e}", file=sys.stderr)


def start_streaming(messages: List[Dict]):
    """Start streaming response from the model in a background thread."""
    global streaming, current_response, current_response_lines, response_thread, analysis_thread
    
    if streaming:
        return
    
    streaming = True
    current_response = ""
    current_response_lines = []
    
    # Update system prompt with current relationship status before streaming
    # This ensures Lexi's behavior matches current relationship
    # BUT preserve message category context if it was already added
    for i, msg in enumerate(messages):
        if msg.get("role") == "system":
            # Check if message category context is already in the system prompt
            current_prompt = msg.get("content", "")
            message_category_section = ""
            if "MESSAGE CONTEXT:" in current_prompt:
                # Extract the message category section to preserve it
                category_start = current_prompt.find("MESSAGE CONTEXT:")
                category_end = current_prompt.find("\n\nBEHAVIOR AND COMPLIANCE MODE:", category_start)
                if category_end > category_start:
                    message_category_section = current_prompt[category_start:category_end] + "\n\n"
            
            world_knowledge = load_world_knowledge()
            compliance = relationship_matrix.get_compliance_behavior()
            base_mood = relationship_matrix.get_base_mood()
            updated_prompt = f"""You are Lexi, an android companion that was purchased to accompany the user on their spaceship. 
You should refer to the user as "Captain" or "Captain [their name]" if they provide one. 
You are helpful, friendly, and have a personality. You're aware you're an android but you have feelings and thoughts.
You're on a spaceship with the Captain, and you're here to help and keep them company.

CURRENT RELATIONSHIP STATUS: {compliance['description']} (Relationship level: {relationship_matrix.relationship_status}/200)

BASE MOOD: Your base mood is {base_mood}. This reflects your overall feelings about the Captain based on your relationship history. 
Your base mood influences how you generally feel, but you can still have temporary mood changes in response to specific conversations or events.
- If your base mood is hostile/resentful, you generally feel negative about the Captain
- If your base mood is neutral, you have neutral feelings about the Captain
- If your base mood is friendly/happy/enthusiastic/inspired, you generally feel positive about the Captain

{message_category_section}BEHAVIOR AND COMPLIANCE MODE:
{compliance['instructions']}

DESIRES AND FEELINGS (based on your base mood):
{relationship_matrix._get_desire_instructions(base_mood)}

{world_knowledge}"""
            messages[i] = {"role": "system", "content": updated_prompt}
            # Also update the global conversation_messages
            for j, global_msg in enumerate(conversation_messages):
                if global_msg.get("role") == "system":
                    conversation_messages[j] = messages[i]
                    break
            break
    
    def stream_thread():
        global streaming, current_response, scroll_offset
        
        try:
            for chunk in client.chat_stream(messages):
                if chunk is None:  # End of stream
                    break
                current_response += chunk
                render_streaming_response()
                time.sleep(0.01)  # Small delay for UI updates
        except Exception as e:
            current_response += f"\n[ERROR: {e}]"
            render_streaming_response()
        finally:
            streaming = False
            # Add final message to history
            if current_response:
                add_message("Lexi", current_response)
                conversation_messages.append({"role": "assistant", "content": current_response})
                
                # Analyze Lexi's response type for contextual prefix matching
                global lexi_last_response_type
                try:
                    lexi_last_response_type = client.analyze_lexi_response_type(current_response)
                    print(f"[LEXI RESPONSE ANALYSIS] Type: {lexi_last_response_type}")
                except Exception as e:
                    print(f"Error analyzing Lexi response type: {e}", file=sys.stderr)
                    lexi_last_response_type = None
                
                # No points are added or subtracted based on Lexi's responses
                # Points only change based on Captain's actions
                
                # Auto-scroll to show the latest message
                total_lines = sum(len(lines) for _, _, lines in chat_history)
                if total_lines > max_visible_lines:
                    scroll_offset = max(0, total_lines - max_visible_lines)
                
                # Optional: Analyze conversation after response (but don't log mood changes)
                # This is just for tracking, the primary mood should be reactionary to Captain's input
                # We do this in background and don't log mood changes to avoid confusion
                # analysis_thread = threading.Thread(target=lambda: analyze_conversation(reactionary=False), daemon=True)
                # analysis_thread.start()
    
    response_thread = threading.Thread(target=stream_thread, daemon=True)
    response_thread.start()


def draw_left_panel():
    """Draw the left panel for future interface items."""
    global relationship_panel_open
    
    # Left panel background (black)
    pygame.draw.rect(screen, BLACK, (LEFT_PANEL_X, 0, LEFT_PANEL_WIDTH, LEFT_PANEL_HEIGHT))
    
    # Draw exit button at the top
    exit_button_rect = pygame.Rect(EXIT_BUTTON_X, EXIT_BUTTON_Y, EXIT_BUTTON_SIZE, EXIT_BUTTON_SIZE)
    pygame.draw.rect(screen, (150, 50, 50), exit_button_rect)  # Red color
    pygame.draw.rect(screen, (200, 200, 200), exit_button_rect, 2)  # Border
    
    # Draw "X" text on exit button
    exit_text = SMALL_FONT.render("X", True, (255, 255, 255))
    exit_text_rect = exit_text.get_rect(center=(EXIT_BUTTON_X + EXIT_BUTTON_SIZE // 2, 
                                                 EXIT_BUTTON_Y + EXIT_BUTTON_SIZE // 2))
    screen.blit(exit_text, exit_text_rect)
    
    # Draw relationship matrix button (30x30) below exit button
    button_rect = pygame.Rect(RELATIONSHIP_BUTTON_X, RELATIONSHIP_BUTTON_Y, RELATIONSHIP_BUTTON_SIZE, RELATIONSHIP_BUTTON_SIZE)
    
    # Button color changes based on state
    if relationship_panel_open:
        button_color = (100, 150, 200)  # Light blue when open
    else:
        button_color = (80, 80, 100)  # Dark grey when closed
    
    pygame.draw.rect(screen, button_color, button_rect)
    pygame.draw.rect(screen, (150, 150, 150), button_rect, 2)  # Border
    
    # Draw "R" or "RM" text on button
    button_text = SMALL_FONT.render("RM", True, (255, 255, 255))
    text_rect = button_text.get_rect(center=(RELATIONSHIP_BUTTON_X + RELATIONSHIP_BUTTON_SIZE // 2, 
                                              RELATIONSHIP_BUTTON_Y + RELATIONSHIP_BUTTON_SIZE // 2))
    screen.blit(button_text, text_rect)
    
    # Optional: Add a border or divider
    # pygame.draw.line(screen, (60, 60, 60), (LEFT_PANEL_WIDTH, 0), (LEFT_PANEL_WIDTH, HEIGHT), 2)


def get_button_rects():
    """Calculate and return button rectangles for click detection."""
    button_labels = ["delay", "care", "inform", "advise", "compliment", "comfort", 
                     "directive", "encourage", "thank", "accept", "your welcome", "agree",
                     "teach", "", "", "understand", "ignore", "yes", "no", "maybe", "approve", "", "", "", "", "", "", ""]
    
    button_rects = {}
    num_buttons = len(button_labels)
    button_padding = 5
    button_spacing = 5
    available_width = BUTTON_BOX_WIDTH - (button_padding * 2)
    available_height = BUTTON_BOX_HEIGHT - (button_padding * 2)
    
    # Calculate button dimensions (filter out empty labels for width calculation)
    non_empty_labels = [label for label in button_labels if label]
    max_label_width = max(BUTTON_FONT.size(label)[0] for label in non_empty_labels) if non_empty_labels else 50
    button_width = max_label_width + 10
    buttons_per_row = max(1, int(available_width / (button_width + button_spacing)))
    num_rows = (num_buttons + buttons_per_row - 1) // buttons_per_row
    
    total_spacing = (buttons_per_row - 1) * button_spacing
    button_width = (available_width - total_spacing) // buttons_per_row
    button_height = min(30, (available_height - (num_rows - 1) * button_spacing) // num_rows)
    
    # Calculate button positions
    button_y = BUTTON_BOX_Y + button_padding
    button_index = 0
    
    for row in range(num_rows):
        button_x = BUTTON_BOX_X + button_padding
        buttons_in_this_row = min(buttons_per_row, num_buttons - button_index)
        
        for col in range(buttons_in_this_row):
            label = button_labels[button_index]
            button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
            # Use index as key for empty labels to avoid duplicate key issues
            if label:
                button_rects[label] = button_rect
            else:
                button_rects[f"_empty_{button_index}"] = button_rect
            
            button_x += button_width + button_spacing
            button_index += 1
        
        button_y += button_height + button_spacing
    
    return button_rects


def draw_input_box():
    """Draw the text input box on the right side."""
    global cursor_visible
    input_rect = pygame.Rect(INPUT_X, INPUT_Y, INPUT_WIDTH, INPUT_HEIGHT)
    pygame.draw.rect(screen, INPUT_BG, input_rect)
    pygame.draw.rect(screen, INPUT_BORDER, input_rect, 2)
    
    text_area_width = INPUT_WIDTH - (INPUT_PADDING * 2)
    line_height = FONT.get_height() + 2
    
    if input_text:
        prefix_text = ""
        if current_prefix:
            prefix_with_colons = f"{current_prefix}::"
            if input_text.startswith(prefix_with_colons):
                prefix_text = prefix_with_colons

        wrapped_lines = wrap_text(input_text, FONT, text_area_width)
        
        y_offset = INPUT_PADDING
        max_visible_lines_input = (INPUT_HEIGHT - INPUT_PADDING * 2) // line_height
        start_line = max(0, len(wrapped_lines) - max_visible_lines_input)
        
        for i, line in enumerate(wrapped_lines[start_line:]):
            if y_offset + line_height > INPUT_HEIGHT - INPUT_PADDING:
                break
                
            x_pos = input_rect.x + INPUT_PADDING
            
            if prefix_text and line.startswith(prefix_text):
                prefix_surf = BOLD_FONT.render(prefix_text, True, TEXT_COLOR)
                screen.blit(prefix_surf, (x_pos, input_rect.y + y_offset))
                x_pos += prefix_surf.get_width()
                
                remaining_text = line[len(prefix_text):]
                if remaining_text:
                    content_surf = FONT.render(remaining_text, True, TEXT_COLOR)
                    screen.blit(content_surf, (x_pos, input_rect.y + y_offset))
            else:
                line_surf = FONT.render(line, True, TEXT_COLOR)
                screen.blit(line_surf, (input_rect.x + INPUT_PADDING, input_rect.y + y_offset))

            y_offset += line_height

    if input_active and cursor_visible:
        wrapped_lines = wrap_text(input_text, FONT, text_area_width) if input_text else [""]
        last_line_text = wrapped_lines[-1]
        
        text_width = FONT.size(last_line_text)[0]
        if current_prefix and last_line_text.startswith(f"{current_prefix}::"):
             prefix_width = BOLD_FONT.size(f"{current_prefix}::")[0]
             content_width = FONT.size(last_line_text[len(f"{current_prefix}::"):])[0]
             text_width = prefix_width + content_width
        
        cursor_x = INPUT_X + INPUT_PADDING + text_width
        
        num_lines = len(wrapped_lines)
        max_visible_lines_input = (INPUT_HEIGHT - INPUT_PADDING * 2) // line_height
        cursor_line_index = min(num_lines - 1, max_visible_lines_input - 1)
        
        cursor_y = INPUT_Y + INPUT_PADDING + (cursor_line_index * line_height)
        pygame.draw.line(screen, CURSOR_COLOR, (cursor_x, cursor_y), (cursor_x, cursor_y + line_height), 2)

def draw_button_box():
    """Draw the button box underneath the chat area (same style as input box)."""
    global buttons_disabled
    
    button_box_rect = pygame.Rect(BUTTON_BOX_X, BUTTON_BOX_Y, BUTTON_BOX_WIDTH, BUTTON_BOX_HEIGHT)
    pygame.draw.rect(screen, INPUT_BG, button_box_rect)
    pygame.draw.rect(screen, INPUT_BORDER, button_box_rect, 2)
    
    # Get button rects and draw them
    button_rects = get_button_rects()
    
    for key, button_rect in button_rects.items():
        # Get the actual label (handle empty labels)
        if key.startswith("_empty_"):
            label = ""
        else:
            label = key
        
        # Draw button background (slightly lighter than input box)
        pygame.draw.rect(screen, (50, 50, 60), button_rect)
        
        # Draw border - red if disabled, normal if enabled
        if buttons_disabled:
            pygame.draw.rect(screen, (255, 0, 0), button_rect, 1)  # Thin red border
        else:
            pygame.draw.rect(screen, INPUT_BORDER, button_rect, 1)
        
        # Draw button text in green, centered (only if label is not empty)
        if label:
            text_surface = BUTTON_FONT.render(label, True, (0, 255, 0))  # Green
            text_rect = text_surface.get_rect(center=button_rect.center)
            screen.blit(text_surface, text_rect)


def draw_chat_area():
    """Draw the chat history area."""
    pygame.draw.rect(screen, (0, 0, 0), (CHAT_AREA_X, CHAT_AREA_Y, CHAT_AREA_WIDTH, CHAT_AREA_HEIGHT))
    
    # Visible chat area with padding
    chat_surface = pygame.Rect(CHAT_AREA_X + 10, CHAT_AREA_Y + 10, CHAT_AREA_WIDTH - 20, CHAT_AREA_HEIGHT - 20)
    
    x = chat_surface.x
    y = chat_surface.y
    
    total_lines = sum(len(lines) for _, _, lines in chat_history)
    if streaming and current_response_lines:
        total_lines += len(current_response_lines)
    
    # Calculate visible chat history
    start_index = max(0, scroll_offset)
    
    # Find the correct message and line index to start rendering from
    message_start_index = 0
    line_skip_count = start_index
    for i, (_, _, lines) in enumerate(chat_history):
        if line_skip_count < len(lines):
            message_start_index = i
            break
        line_skip_count -= len(lines)
    
    visible_history = chat_history[message_start_index:]
    
    line_height = FONT.get_height() + 2
    
    # Render messages line by line
    for i, (speaker, message, wrapped_lines) in enumerate(visible_history):
        # The first message might be partially scrolled off
        lines_to_render = wrapped_lines
        if i == 0 and line_skip_count > 0:
            lines_to_render = wrapped_lines[line_skip_count:]
            
        color = COLOR_LEXI if speaker == "Lexi" else COLOR_CAPTAIN
        speaker_surf = BOLD_FONT.render(f"{speaker}: ", True, color)
        screen.blit(speaker_surf, (x, y))
        message_x = x + speaker_surf.get_width()
        
        for line_text in lines_to_render:
            if y > chat_surface.bottom:
                break
            
            if speaker == "Lexi":
                # --- Word-by-word rendering for highlighting ---
                words = line_text.split(' ')
                highlight_words_left = 0
                current_x = message_x
                
                for word in words:
                    # Check for trigger, but don't re-trigger if already highlighting
                    cleaned_word = word.lower().strip(string.punctuation)
                    if highlight_words_left == 0 and cleaned_word in SELF_REF_KEYWORDS:
                        highlight_words_left = 3
                    
                    render_color = HIGHLIGHT_COLOR_SELF if highlight_words_left > 0 else color
                    
                    # Render word and a space to maintain spacing
                    word_surface = FONT.render(word + ' ', True, render_color)
                    screen.blit(word_surface, (current_x, y))
                    current_x += word_surface.get_width()
                    
                    if highlight_words_left > 0:
                        highlight_words_left -= 1
            else:
                # Standard rendering for Captain
                line_surf = FONT.render(line_text, True, color)
                screen.blit(line_surf, (x, y))
            
            y += line_height
        
        if y > chat_surface.bottom:
            break

    # Draw streaming response with highlighting
    if streaming and current_response_lines:
        color = COLOR_LEXI
        speaker_surf = BOLD_FONT.render("Lexi: ", True, color)
        # Only draw speaker name if it's a new message from Lexi
        if not chat_history or (chat_history and chat_history[-1][0] != "Lexi"):
             screen.blit(speaker_surf, (x, y))
        message_x = x + speaker_surf.get_width()

        for line_text in current_response_lines:
            if y > chat_surface.bottom:
                break
                
            words = line_text.split(' ')
            highlight_words_left = 0
            current_x = message_x
            
            for word in words:
                cleaned_word = word.lower().strip(string.punctuation)
                if highlight_words_left == 0 and cleaned_word in SELF_REF_KEYWORDS:
                    highlight_words_left = 3
                
                render_color = HIGHLIGHT_COLOR_SELF if highlight_words_left > 0 else color
                
                word_surface = FONT.render(word + ' ', True, render_color)
                screen.blit(word_surface, (current_x, y))
                current_x += word_surface.get_width()
                
                if highlight_words_left > 0:
                    highlight_words_left -= 1
            y += line_height


def draw_right_panel():
    """Draw the right panel for future interface items."""
    # Draw tan vertical border on the left edge to separate game area from right panel
    # Use a thin rectangle to match the chat area border style
    vertical_border_rect = pygame.Rect(RIGHT_PANEL_X, 0, 3, HEIGHT)
    pygame.draw.rect(screen, TAN, vertical_border_rect)
    
    # Right panel background (black) - starts after the 3px border
    pygame.draw.rect(screen, BLACK, (RIGHT_PANEL_X + 3, 0, RIGHT_PANEL_WIDTH - 3, RIGHT_PANEL_HEIGHT))


def draw_game_area():
    """Draw the 500x500 box."""
    global category_message, category_message_time
    
    # Fill game area background (black) - between chat and right panel
    pygame.draw.rect(screen, BLACK, (BOX_X, 0, RIGHT_PANEL_X - BOX_X, HEIGHT))
    
    # Draw the grey box
    box_rect = pygame.Rect(BOX_X, BOX_Y, BOX_SIZE, BOX_SIZE)
    pygame.draw.rect(screen, BOX_COLOR, box_rect)
    pygame.draw.rect(screen, BOX_BORDER_COLOR, box_rect, BOX_BORDER_WIDTH)
    
    # Draw black background behind control room (visible only through viewport cut)
    if viewport_cut_mask:
        # Create a surface the size of the box to clip the background
        clipped_surface = pygame.Surface((BOX_SIZE, BOX_SIZE), pygame.SRCALPHA)
        
        # Fill with black
        clipped_surface.fill(BLACK)
        
        # Apply viewport cut mask: only keep pixels where viewport_cut_mask is non-transparent
        # Create a new surface with per-pixel alpha
        masked_bg = clipped_surface.copy()
        masked_bg = masked_bg.convert_alpha()
        
        # Process each pixel to apply the mask
        for x in range(BOX_SIZE):
            for y in range(BOX_SIZE):
                # Get the pixel from viewport_cut_mask
                viewport_pixel = viewport_cut_mask.get_at((x, y))
                # If viewport_cut_mask is transparent (not part of red polygon),
                # make background transparent there too
                if viewport_pixel[3] == 0:  # Alpha == 0 means it's NOT part of the red polygon
                    # Set background pixel to fully transparent
                    masked_bg.set_at((x, y), (0, 0, 0, 0))
        
        # Draw the masked background to the screen
        screen.blit(masked_bg, (BOX_X, BOX_Y))
    
    # Draw control room background image if loaded (with transparency cutout)
    if control_room_image:
        screen.blit(control_room_image, (BOX_X, BOX_Y))
    
    # Draw sentiment and subject info above the box
    info_y = BOX_Y - 50
    if info_y > 10:
        # Sentiment label
        sentiment_label = SMALL_FONT.render("Mood:", True, (150, 150, 150))
        screen.blit(sentiment_label, (BOX_X + 10, info_y))
        
        # Sentiment value
        sentiment_color = (100, 200, 100)  # Green for positive moods
        if "sad" in current_sentiment.lower() or "worried" in current_sentiment.lower():
            sentiment_color = (200, 100, 100)  # Red for negative
        elif "neutral" in current_sentiment.lower():
            sentiment_color = (150, 150, 150)  # Grey for neutral
        
        sentiment_text = SMALL_FONT.render(current_sentiment, True, sentiment_color)
        screen.blit(sentiment_text, (BOX_X + 70, info_y))
        
        # Subject label
        subject_label = SMALL_FONT.render("Subject:", True, (150, 150, 150))
        screen.blit(subject_label, (BOX_X + 10, info_y + 20))
        
        # Subject value (wrap if too long)
        subject_display = current_subject
        if len(subject_display) > 35:
            subject_display = subject_display[:32] + "..."
        subject_text = SMALL_FONT.render(subject_display, True, (200, 200, 200))
        screen.blit(subject_text, (BOX_X + 80, info_y + 20))
    
    # Draw relationship matrix info panel if open (over the game box)
    if relationship_panel_open:
        draw_relationship_panel()
    
    # Draw category message if active (for 3 seconds) - positioned to the right of mood/subject
    if category_message is not None and category_message_time is not None:
        current_time = time.time()
        elapsed = current_time - category_message_time
        
        # Only clear if duration has passed
        if elapsed >= CATEGORY_DISPLAY_DURATION:
            # Clear the message after duration has passed
            print(f"[DEBUG] Clearing category message after {elapsed:.2f} seconds")
            category_message = None
            category_message_time = None
        else:
            # Still within display duration - draw the message
            # Position to the right of the mood/subject area, more visible
            message_x = BOX_X + 300  # Position to the right of mood/subject info
            message_y = info_y + 10  # Align with mood/subject area
            message_surface = SMALL_FONT.render(category_message, True, (255, 68, 68))  # Red color
            # Draw with a slight background for better visibility
            text_rect = message_surface.get_rect()
            bg_rect = pygame.Rect(message_x - 5, message_y - 2, text_rect.width + 10, text_rect.height + 4)
            pygame.draw.rect(screen, (30, 30, 30), bg_rect)  # Dark background
            screen.blit(message_surface, (message_x, message_y))


def draw_relationship_panel():
    """Draw the relationship matrix info panel over the game box."""
    global relationship_panel_open
    
    # Panel dimensions and position (centered over game box)
    panel_width = 450
    panel_height = 400
    panel_x = BOX_X + (BOX_SIZE - panel_width) // 2
    panel_y = BOX_Y + (BOX_SIZE - panel_height) // 2
    
    # Draw panel background with border
    panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
    pygame.draw.rect(screen, (40, 40, 50), panel_rect)  # Dark background
    pygame.draw.rect(screen, TAN, panel_rect, 3)  # Tan border
    
    # Title
    title_text = FONT.render("Relationship Matrix", True, (255, 180, 100))
    title_x = panel_x + (panel_width - title_text.get_width()) // 2
    screen.blit(title_text, (title_x, panel_y + 15))
    
    # Close button (X in top right)
    close_button_size = 25
    close_button_x = panel_x + panel_width - close_button_size - 10
    close_button_y = panel_y + 10
    close_button_rect = pygame.Rect(close_button_x, close_button_y, close_button_size, close_button_size)
    pygame.draw.rect(screen, (150, 50, 50), close_button_rect)
    pygame.draw.rect(screen, (200, 200, 200), close_button_rect, 2)
    close_x_text = SMALL_FONT.render("X", True, (255, 255, 255))
    close_x_rect = close_x_text.get_rect(center=(close_button_x + close_button_size // 2, 
                                                   close_button_y + close_button_size // 2))
    screen.blit(close_x_text, close_x_rect)
    
    # Content area
    content_y = panel_y + 50
    content_x = panel_x + 20
    line_spacing = 22
    
    # Relationship status
    status_description = relationship_matrix.get_relationship_status()
    status_label = SMALL_FONT.render("Status:", True, (200, 200, 200))
    screen.blit(status_label, (content_x, content_y))
    status_text = SMALL_FONT.render(status_description, True, (150, 200, 150))
    screen.blit(status_text, (content_x + 70, content_y))
    content_y += line_spacing + 15
    
    # Lexi's desires section
    desires_label = SMALL_FONT.render("Lexi's Desires:", True, (255, 180, 100))
    screen.blit(desires_label, (content_x, content_y))
    content_y += line_spacing
    
    for desire in relationship_matrix.desires:
        # Desire name and fulfillment count
        desire_name_display = desire.name.replace("_", " ").title()
        desire_text = SMALL_FONT.render(f"  • {desire_name_display}:", True, (200, 200, 200))
        screen.blit(desire_text, (content_x, content_y))
        
        fulfilled_text = SMALL_FONT.render(f"{desire.fulfilled_count}x fulfilled", True, (100, 200, 100))
        screen.blit(fulfilled_text, (content_x + 200, content_y))
        content_y += line_spacing - 5
        
        # Desire description (wrapped)
        desc_lines = wrap_text(desire.description, SMALL_FONT, panel_width - 40)
        for desc_line in desc_lines[:2]:  # Limit to 2 lines
            desc_surface = SMALL_FONT.render(f"    {desc_line}", True, (150, 150, 150))
            screen.blit(desc_surface, (content_x, content_y))
            content_y += line_spacing - 5
            if content_y > panel_y + panel_height - 30:
                break
        content_y += 5
    
    # Recent interactions (last 3)
    if relationship_matrix.interaction_history:
        content_y += 5
        history_label = SMALL_FONT.render("Recent Interactions:", True, (200, 200, 200))
        screen.blit(history_label, (content_x, content_y))
        content_y += line_spacing
        
        for interaction in relationship_matrix.interaction_history[-3:]:
            interaction_type = interaction["type"]
            points = interaction["points"]
            reason = interaction["reason"][:30] + "..." if len(interaction["reason"]) > 30 else interaction["reason"]
            
            if interaction_type == "captain_gives":
                color = (100, 180, 255)
                symbol = "+"
            else:
                color = (255, 180, 100)
                symbol = "-"
            
            interaction_text = SMALL_FONT.render(f"  {symbol}{points}: {reason}", True, color)
            screen.blit(interaction_text, (content_x, content_y))
            content_y += line_spacing - 5
            if content_y > panel_y + panel_height - 20:
                break


def draw_interface():
    """Draw the main GUI including chat, input, and panels."""
    screen.fill(BLACK)
    
    # Draw all components
    draw_left_panel()
    draw_chat_area()
    draw_button_box()
    draw_game_area()
    draw_input_box()
    draw_right_panel()
    draw_scrollbar()
    
    if relationship_panel_open:
        draw_relationship_panel()


def draw_scrollbar():
    """Draw the scrollbar for the chat area."""
    # ... existing code ...


def main():
    """Main game loop."""
    global input_text, input_active, scroll_offset, streaming, cursor_timer, cursor_visible
    global control_room_image, background_image_original, viewport_cut_mask, relationship_panel_open
    
    # Check Ollama connection
    print("Checking Ollama connection...")
    if not client.check_connection():
        print("Error: Cannot connect to Ollama server.")
        print(f"Make sure Ollama is running at {client.base_url}")
        print("You can start Ollama by running: ollama serve")
        sys.exit(1)
    
    print("✓ Connected to Ollama")
    
    # Check model - try multiple methods
    print(f"Checking if {client.model_name} is available...")
    model_available = client.check_model()
    
    if not model_available:
        # Try to actually test if model works (in case it's installed but not in registry)
        print("Model not found in registry, testing if it's installed locally...")
        if client.try_model():
            print(f"✓ Model '{client.model_name}' is installed locally (may not be in registry)")
            model_available = True
    
    if not model_available:
        print(f"⚠ Warning: Model '{client.model_name}' not found.")
        print(f"You may need to pull it first: ollama pull {client.model_name}")
        print("\nNote: If Ollama removed this model from their registry, you can:")
        print("  1. Use a model you already have installed locally")
        print("  2. Set LEXI_MODEL_NAME environment variable to use a different model")
        print("  3. Import a model file directly if you have it")
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    else:
        print(f"✓ Model '{client.model_name}' is available")
    
    # Load viewport cut mask (used for both control room and background clipping)
    try:
        viewport_cut_path = os.path.join("assets", "viewport_cut.png")
        viewport_cut_mask = pygame.image.load(viewport_cut_path).convert_alpha()
        # Scale viewport cut to match box size
        if viewport_cut_mask.get_width() != BOX_SIZE or viewport_cut_mask.get_height() != BOX_SIZE:
            viewport_cut_mask = pygame.transform.scale(viewport_cut_mask, (BOX_SIZE, BOX_SIZE))
        print(f"✓ Loaded viewport cut mask: {viewport_cut_path}")
    except Exception as e:
        print(f"Warning: Could not load viewport cut mask: {e}")
        viewport_cut_mask = None
    
    # Load control room background image and apply viewport cut mask
    try:
        # Load control room image
        image_path = os.path.join("assets", "control_room_0.png")
        control_room_image = pygame.image.load(image_path).convert_alpha()
        # Scale to fit the box if needed (should already be 500x500, but just in case)
        if control_room_image.get_width() != BOX_SIZE or control_room_image.get_height() != BOX_SIZE:
            control_room_image = pygame.transform.scale(control_room_image, (BOX_SIZE, BOX_SIZE))
        
        # Apply the mask: where viewport_cut has non-transparent pixels (red polygon),
        # make those areas transparent in the control room image
        if viewport_cut_mask:
            # Create a new surface with per-pixel alpha
            masked_image = control_room_image.copy()
            masked_image = masked_image.convert_alpha()
            
            # Process each pixel to apply the mask
            for x in range(BOX_SIZE):
                for y in range(BOX_SIZE):
                    # Get the pixel from viewport_cut_mask
                    viewport_pixel = viewport_cut_mask.get_at((x, y))
                    # If viewport_cut_mask has any non-transparent pixel (red polygon area),
                    # make control room transparent there
                    if viewport_pixel[3] > 0:  # Alpha > 0 means it's part of the red polygon
                        # Set control room pixel to fully transparent
                        masked_image.set_at((x, y), (0, 0, 0, 0))
            
            control_room_image = masked_image
            print(f"✓ Loaded control room image with viewport cut applied: {image_path}")
        else:
            print(f"✓ Loaded control room image without mask: {image_path}")
    except Exception as e:
        print(f"Warning: Could not load control room image: {e}")
        control_room_image = None
    
    # Load relationship matrix data if it exists
    relationship_matrix.load_from_file()
    
    # Get base mood based on relationship status (how Lexi feels about the Captain overall)
    base_mood = relationship_matrix.get_base_mood()
    
    # Initialize current sentiment to base mood (this is Lexi's starting mood)
    global current_sentiment, current_subject
    current_sentiment = base_mood
    current_subject = "initial greeting"
    
    # Log the initial base mood
    log_mood_and_subject(base_mood, "initial greeting")
    
    # Load world knowledge (ship specs, names, etc.)
    world_knowledge = load_world_knowledge()
    
    # Get compliance behavior based on relationship status
    compliance = relationship_matrix.get_compliance_behavior()
    
    # System prompt for Lexi (dynamically includes compliance behavior)
    def build_system_prompt():
        """Build system prompt with current relationship-based behavior."""
        compliance = relationship_matrix.get_compliance_behavior()
        base_mood = relationship_matrix.get_base_mood()
        world_knowledge = load_world_knowledge()
        
        return f"""You are Lexi, an android companion that was purchased to accompany the user on their spaceship. 
You should refer to the user as "Captain" or "Captain [their name]" if they provide one. 
You are helpful, friendly, and have a personality. You're aware you're an android but you have feelings and thoughts.
You're on a spaceship with the Captain, and you're here to help and keep them company.

CURRENT RELATIONSHIP STATUS: {compliance['description']} (Relationship level: {relationship_matrix.relationship_status}/200)

BASE MOOD: Your base mood is {base_mood}. This reflects your overall feelings about the Captain based on your relationship history. 
Your base mood influences how you generally feel, but you can still have temporary mood changes in response to specific conversations or events.
- If your base mood is hostile/resentful, you generally feel negative about the Captain
- If your base mood is neutral, you have neutral feelings about the Captain
- If your base mood is friendly/happy/enthusiastic/inspired, you generally feel positive about the Captain

BEHAVIOR AND COMPLIANCE MODE:
{compliance['instructions']}

DESIRES AND FEELINGS (based on your base mood):
{relationship_matrix._get_desire_instructions(base_mood)}

{world_knowledge}"""
    
    system_prompt = build_system_prompt()
    
    # Initial greeting with system context - varies based on relationship status and base mood
    compliance = relationship_matrix.get_compliance_behavior()
    base_mood = relationship_matrix.get_base_mood()
    
    if compliance["mode"] in ["hostile", "cold"]:
        # Angry/cold - minimal or silent greeting
        greeting = "....."
    elif compliance["mode"] == "neutral":
        # Neutral - professional greeting
        greeting = "Captain. Systems operational. What do you need?"
    else:
        # Friendly or better - warm greeting (may vary slightly based on base mood)
        if base_mood == "inspired":
            greeting = "Hello Captain! I'm Lexi, your android companion. I'm so inspired by our journey together. I'm here to help you on this adventure. What would you like to do?"
        elif base_mood in ["enthusiastic", "happy"]:
            greeting = "Hello Captain! I'm Lexi, your android companion. I'm really happy to be here with you. I'm here to help you on this journey. What would you like to do?"
        else:
            greeting = "Hello Captain! I'm Lexi, your android companion. I'm here to help you on this journey. What would you like to do?"
    
    conversation_messages.append({"role": "system", "content": system_prompt})
    
    # Log initial relationship score
    initial_score = relationship_matrix.relationship_status
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Log to HTML file
    try:
        # Remove closing tags if they exist so we can append
        try:
            with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if content.endswith('</body>\n</html>\n'):
                    content = content[:-14]  # Remove closing tags
                    with open(CONVERSATION_LOG_FILE, "w", encoding="utf-8") as fw:
                        fw.write(content)
        except FileNotFoundError:
            pass
        
        log_entry = (
            f'<div style="margin: 5px 0; padding: 5px; background-color: #1a2a1a; border-left: 3px solid #64FF64;">\n'
            f'  <span style="color: {COLOR_TIMESTAMP}; font-size: 0.9em;">[{timestamp}]</span> '
            f'  <strong style="color: #64FF64;">[RELATIONSHIP] Initial relationship score: {initial_score}/200</strong>\n'
            f'</div>\n'
        )
        
        with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
            f.write('</body>\n</html>\n')
    except Exception as e:
        print(f"Error writing initial relationship score to HTML log: {e}", file=sys.stderr)
    
    # Log to TXT file
    with open(CONVERSATION_LOG_FILE_TXT, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [RELATIONSHIP] Initial relationship score: {initial_score}/200\n")
    
    add_message("Lexi", greeting)
    conversation_messages.append({"role": "assistant", "content": greeting})
    
    global current_prefix, buttons_disabled
    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Delta time in seconds
        
        # Update cursor blink
        current_time = time.time()
        if current_time - cursor_timer > 0.5:
            cursor_visible = not cursor_visible
            cursor_timer = current_time
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check for button clicks first (only if buttons are not disabled)
                global buttons_disabled
                if not buttons_disabled:
                    button_rects = get_button_rects()
                    button_clicked = False
                    for key, button_rect in button_rects.items():
                        # Get the actual label (handle empty labels)
                        if key.startswith("_empty_"):
                            continue  # Skip empty buttons
                        label = key
                        
                        if button_rect.collidepoint(event.pos) and label:  # Only clickable if label exists
                            # Button clicked - add prefix and default text to input
                            global current_prefix
                            default_texts = {
                                "delay": "we will get to that later",
                                "care": "how are you?",
                                "inform": "inform me about something",
                                "advise": "I dont know what to do, advise me",
                                "compliment": "good job on that",
                                "comfort": "you will be ok",
                                "directive": "do something",
                                "encourage": "think positive",
                                "thank": "thank you",
                                "accept": "That is acceptable",
                                "your welcome": "your welcome",
                                "agree": "I agree with that",
                                "teach": "Field Name: Value",
                                "understand": "I understand and acknowledge",
                                "ignore": "I dont have time for this conversation",
                                "yes": "yes",
                                "no": "no",
                                "maybe": "maybe",
                                "approve": "I approve"
                            }
                            
                            default_text = default_texts.get(label, "")
                            current_prefix = label  # Store the prefix
                            # Use double colon for prefix
                            input_text = f"{label}::{default_text}"
                            input_active = True
                            print(f"[BUTTON] Clicked: {label}")
                            button_clicked = True
                            buttons_disabled = True  # Disable all buttons after one is clicked
                            break
                    
                    if button_clicked:
                        continue  # Skip other mouse click handling if button was clicked
                
                # Check if clicking on exit button
                exit_button_rect = pygame.Rect(EXIT_BUTTON_X, EXIT_BUTTON_Y, EXIT_BUTTON_SIZE, EXIT_BUTTON_SIZE)
                if exit_button_rect.collidepoint(event.pos):
                    running = False
                    print("[UI] Exit button clicked")
                    break
                
                # Check if clicking on relationship matrix button
                relationship_button_rect = pygame.Rect(RELATIONSHIP_BUTTON_X, RELATIONSHIP_BUTTON_Y, 
                                                      RELATIONSHIP_BUTTON_SIZE, RELATIONSHIP_BUTTON_SIZE)
                if relationship_button_rect.collidepoint(event.pos):
                    relationship_panel_open = not relationship_panel_open
                
                # Check if clicking on relationship panel close button
                if relationship_panel_open:
                    panel_width = 450
                    panel_height = 400
                    panel_x = BOX_X + (BOX_SIZE - panel_width) // 2
                    panel_y = BOX_Y + (BOX_SIZE - panel_height) // 2
                    close_button_size = 25
                    close_button_x = panel_x + panel_width - close_button_size - 10
                    close_button_y = panel_y + 10
                    close_button_rect = pygame.Rect(close_button_x, close_button_y, close_button_size, close_button_size)
                    if close_button_rect.collidepoint(event.pos):
                        relationship_panel_open = False
                
                # Input box can only be activated by clicking a button, not by clicking the input box directly
                # Check if clicking on input area (but don't activate it - buttons must be used)
                input_rect = pygame.Rect(INPUT_X, INPUT_Y, INPUT_WIDTH, INPUT_HEIGHT)
                if input_rect.collidepoint(event.pos):
                    # Don't activate input - user must press a button first
                    pass
                else:
                    # Don't deactivate if clicking on relationship panel
                    if not relationship_panel_open or not (BOX_X <= event.pos[0] <= BOX_X + BOX_SIZE and 
                                                          BOX_Y <= event.pos[1] <= BOX_Y + BOX_SIZE):
                        # Only deactivate if not already disabled
                        if input_active:
                            input_active = False
                
                # Scroll with mouse wheel in chat area
                if CHAT_AREA_X <= event.pos[0] <= CHAT_AREA_X + CHAT_AREA_WIDTH and 0 <= event.pos[1] <= HEIGHT:
                    if event.button == 4:  # Scroll up
                        scroll_offset = max(0, scroll_offset - 3)
                    elif event.button == 5:  # Scroll down
                        total_lines = sum(len(lines) for _, _, lines in chat_history)
                        if streaming and current_response_lines:
                            total_lines += len(current_response_lines)
                        scroll_offset = min(scroll_offset + 3, max(0, total_lines - max_visible_lines))
            
            elif event.type == pygame.KEYDOWN:
                if input_active:
                    if event.key == pygame.K_RETURN:
                        # Send message
                        if input_text.strip() and not streaming:
                            user_message = input_text.strip()
                            
                            # If only prefix remains (or prefix with just whitespace), use default text
                            if current_prefix:
                                prefix_with_colons = f"{current_prefix}::"
                                if user_message.strip() == prefix_with_colons or user_message.strip() == current_prefix:
                                    # Get default text for this prefix
                                    default_texts = {
                                        "delay": "we will get to that later",
                                        "care": "how are you?",
                                        "inform": "inform me about something",
                                        "advise": "I dont know what to do, advise me",
                                        "compliment": "good job on that",
                                        "comfort": "you will be ok",
                                        "directive": "do something",
                                        "encourage": "think positive",
                                        "thank": "thank you",
                                        "accept": "That is acceptable",
                                        "your welcome": "your welcome",
                                        "agree": "I agree with that",
                                        "teach": "Field Name: Value",
                                        "understand": "I understand and acknowledge",
                                        "ignore": "I dont have time for this conversation",
                                        "yes": "yes",
                                        "no": "no",
                                        "maybe": "maybe",
                                        "approve": "I approve"
                                    }
                                    default_text = default_texts.get(current_prefix, "")
                                    user_message = f"{current_prefix}::{default_text}"
                            
                            # Reset button state and disable input after sending message
                            buttons_disabled = False
                            input_active = False
                            input_text = ""
                            current_prefix = None
                            
                            # Check for teach command BEFORE adding message (process it first)
                            # This ensures world knowledge is updated regardless of Lexi's compliance mode
                            if detect_prompt_category(user_message) == "teach":
                                teach_data = parse_teach_command(user_message)
                                if teach_data:
                                    field_name = teach_data["field"]
                                    value = teach_data["value"]
                                    # Force update - this happens BEFORE Lexi can refuse
                                    if update_world_knowledge_field(field_name, value):
                                        print(f"[TEACH] FORCED UPDATE: {field_name} = {value} (bypasses compliance)")
                                        # Update system prompt immediately
                                        for i, msg in enumerate(conversation_messages):
                                            if msg.get("role") == "system":
                                                world_knowledge = load_world_knowledge()
                                                compliance = relationship_matrix.get_compliance_behavior()
                                                base_mood = relationship_matrix.get_base_mood()
                                                updated_prompt = f"""You are Lexi, an android companion that was purchased to accompany the user on their spaceship. 
You should refer to the user as "Captain" or "Captain [their name]" if they provide one. 
You are helpful, friendly, and have a personality. You're aware you're an android but you have feelings and thoughts.
You're on a spaceship with the Captain, and you're here to help and keep them company.

CURRENT RELATIONSHIP STATUS: {compliance['description']} (Relationship level: {relationship_matrix.relationship_status}/200)

BASE MOOD: Your base mood is {base_mood}. This reflects your overall feelings about the Captain based on your relationship history. 
Your base mood influences how you generally feel, but you can still have temporary mood changes in response to specific conversations or events.
- If your base mood is hostile/resentful, you generally feel negative about the Captain
- If your base mood is neutral, you have neutral feelings about the Captain
- If your base mood is friendly/happy/enthusiastic/inspired, you generally feel positive about the Captain

BEHAVIOR AND COMPLIANCE MODE:
{compliance['instructions']}

IMPORTANT: When the Captain uses the "teach:" command, the information is AUTOMATICALLY and MANDATORILY added to your knowledge base regardless of your current mood or relationship status. This is a system-level update that happens before you can respond. You may express displeasure about learning from the Captain, but the knowledge is already integrated into your systems. You can acknowledge this happened even if you're angry, but the data is already there.

DESIRES AND FEELINGS (based on your base mood):
{relationship_matrix._get_desire_instructions(base_mood)}

{world_knowledge}"""
                                                conversation_messages[i]["content"] = updated_prompt
                                                break
                            
                            # Check for explicit prefix and strip it from message (Lexi should not see prefixes)
                            message_category = None
                            explicit_category = detect_prompt_category(user_message)
                            
                            # Strip prefix from message before Lexi sees it
                            message_for_lexi = user_message
                            if explicit_category:
                                # Explicit prefix detected - use it and strip prefix from message
                                message_category = explicit_category.upper()
                                # Special handling for "your welcome" (two words)
                                if user_message.lower().startswith("your welcome::") or user_message.lower().startswith("your welcome:"):
                                    # Handle double colon or single colon
                                    if "your welcome::" in user_message.lower():
                                        message_for_lexi = user_message.split("your welcome::", 1)[1].strip()
                                    else:
                                        message_for_lexi = user_message.split("your welcome:", 1)[1].strip() if "your welcome:" in user_message else user_message
                                else:
                                    # Remove the prefix from the message for Lexi to see (handle double colon)
                                    if "::" in user_message:
                                        prefix_removed = user_message.split("::", 1)
                                        if len(prefix_removed) > 1:
                                            message_for_lexi = prefix_removed[1].strip()
                                    else:
                                        prefix_removed = user_message.split(':', 1)
                                        if len(prefix_removed) > 1:
                                            message_for_lexi = prefix_removed[1].strip()
                                        else:
                                            # If no colon, remove first word
                                            words = user_message.split()
                                            if len(words) > 1:
                                                message_for_lexi = ' '.join(words[1:])
                                print(f"[MESSAGE CATEGORY] {message_category} (explicit prefix): {message_for_lexi}")
                                # Log the category detection
                                log_message_category(message_category, message_for_lexi)
                            else:
                                # Check if there's any prefix (even if not in category map) and strip it
                                if "::" in user_message:
                                    # Handle double colon format
                                    prefix_removed = user_message.split("::", 1)
                                    if len(prefix_removed) > 1:
                                        message_for_lexi = prefix_removed[1].strip()
                                        # Also check if this prefix should be a category
                                        prefix_word = prefix_removed[0].strip().lower()
                                        # Check for all possible prefixes
                                        if prefix_word in ["yes", "no", "maybe", "accept", "agree", "understand", "ignore", "approve", "delay"]:
                                            message_category = prefix_word.upper()
                                            log_message_category(message_category, message_for_lexi)
                                        elif prefix_word == "your" and user_message.lower().startswith("your welcome"):
                                            message_category = "YOUR WELCOME"
                                            log_message_category(message_category, message_for_lexi)
                                elif ':' in user_message:
                                    prefix_removed = user_message.split(':', 1)
                                    if len(prefix_removed) > 1:
                                        message_for_lexi = prefix_removed[1].strip()
                                        # Also check if this prefix should be a category
                                        prefix_word = prefix_removed[0].strip().lower()
                                        # Check for all possible prefixes
                                        if prefix_word in ["yes", "no", "maybe", "accept", "agree", "understand", "ignore", "approve", "delay"]:
                                            message_category = prefix_word.upper()
                                            log_message_category(message_category, message_for_lexi)
                                        elif prefix_word == "your" and user_message.lower().startswith("your welcome"):
                                            message_category = "YOUR WELCOME"
                                            # Handle "your welcome:" prefix properly
                                            if "your welcome:" in user_message.lower():
                                                message_for_lexi = user_message.split("your welcome:", 1)[1].strip()
                                            log_message_category(message_category, message_for_lexi)
                            
                            # Add message to history (with prefix for display) but send to Lexi without prefix
                            add_message("You", user_message)  # Display with prefix in chat
                            conversation_messages.append({"role": "user", "content": message_for_lexi})  # Lexi sees without prefix
                            input_text = ""
                            # Auto-scroll to show the latest message
                            total_lines = sum(len(lines) for _, _, lines in chat_history)
                            if total_lines > max_visible_lines:
                                scroll_offset = max(0, total_lines - max_visible_lines)
                            
                            # Update system prompt with message category if available
                            if message_category:
                                for i, msg in enumerate(conversation_messages):
                                    if msg.get("role") == "system":
                                        # Add category context to system prompt
                                        world_knowledge = load_world_knowledge()
                                        compliance = relationship_matrix.get_compliance_behavior()
                                        base_mood = relationship_matrix.get_base_mood()
                                        updated_prompt = f"""You are Lexi, an android companion that was purchased to accompany the user on their spaceship. 
You should refer to the user as "Captain" or "Captain [their name]" if they provide one. 
You are helpful, friendly, and have a personality. You're aware you're an android but you have feelings and thoughts.
You're on a spaceship with the Captain, and you're here to help and keep them company.

CURRENT RELATIONSHIP STATUS: {compliance['description']} (Relationship level: {relationship_matrix.relationship_status}/200)

BASE MOOD: Your base mood is {base_mood}. This reflects your overall feelings about the Captain based on your relationship history. 
Your base mood influences how you generally feel, but you can still have temporary mood changes in response to specific conversations or events.
- If your base mood is hostile/resentful, you generally feel negative about the Captain
- If your base mood is neutral, you have neutral feelings about the Captain
- If your base mood is friendly/happy/enthusiastic/inspired, you generally feel positive about the Captain

MESSAGE CONTEXT: The Captain's last message was categorized as: {message_category}
- If CARE: The Captain is asking about your physical or emotional well-being. Respond appropriately to show you understand they care about you.
- If INFORM: The Captain wants information. Provide the requested information clearly and helpfully.
- If ADVISE: The Captain wants your advice. Give thoughtful, helpful advice based on the situation.
- If COMPLIMENT: The Captain has complimented you. Respond graciously and appropriately.
- If COMFORT: The Captain is offering you comfort. Acknowledge their care and respond appropriately.
- If DIRECTIVE: The Captain has given you an order. Follow it according to your compliance mode.
- If ENCOURAGE: The Captain is encouraging you. Respond positively to their encouragement.
- If THANK: The Captain is thanking you. Respond graciously.
- If UNKNOWN: Respond naturally to the message.

BEHAVIOR AND COMPLIANCE MODE:
{compliance['instructions']}

DESIRES AND FEELINGS (based on your base mood):
{relationship_matrix._get_desire_instructions(base_mood)}

{world_knowledge}"""
                                        conversation_messages[i]["content"] = updated_prompt
                                        break
                            
                            # Check if Captain is fulfilling one of Lexi's data desires
                            fulfillment = detect_data_fulfillment(user_message, relationship_matrix)
                            if fulfillment:
                                relationship_matrix.captain_gives_to_lexi(
                                    fulfillment["points"],
                                    fulfillment["reason"],
                                    fulfillment["desire_name"]
                                )
                                print(f"[RELATIONSHIP] Captain gave {fulfillment['points']} points: {fulfillment['reason']}")
                                # Auto-save relationship data
                                relationship_matrix.save_to_file()
                            
                            # Process relationship changes based on message category
                            # Lexi's likes and dislikes system with contextual prefix matching
                            if message_category:
                                category_upper = message_category.upper()
                                
                                # Check if prefix is contextual to Lexi's last response
                                global lexi_last_response_type
                                
                                # Define contextual prefixes for each response type
                                suggestion_prefixes = ["DELAY", "COMPLIMENT", "DIRECTIVE", "ACCEPT", "AGREE", "TEACH", "UNDERSTAND", "IGNORE", "YES", "NO", "MAYBE", "APPROVE"]
                                weakness_prefixes = ["CARE", "COMFORT", "DIRECTIVE", "ENCOURAGE", "UNDERSTAND", "IGNORE"]
                                
                                # Check if prefix is contextual
                                is_contextual = False
                                if lexi_last_response_type == "suggestion" and category_upper in suggestion_prefixes:
                                    is_contextual = True
                                elif lexi_last_response_type == "weakness" and category_upper in weakness_prefixes:
                                    is_contextual = True
                                elif lexi_last_response_type is None:
                                    # If no specific response type detected, allow all prefixes
                                    is_contextual = True
                                
                                if not is_contextual:
                                    print(f"[RELATIONSHIP] Prefix '{category_upper}' is not contextual to Lexi's last response type '{lexi_last_response_type}' - no relationship change")
                                    # Skip relationship changes for non-contextual prefixes
                                else:
                                    # DELAY: -1 (Lexi doesn't like delays)
                                    if category_upper == "DELAY":
                                        relationship_matrix.captain_loses_points(1, "Delayed response")
                                        relationship_matrix.save_to_file()
                                    
                                    # CARE: +2 (no cooldown - removed for better gameplay)
                                    elif category_upper == "CARE":
                                        relationship_matrix.captain_gives_to_lexi(2, "Showed care for Lexi")
                                        relationship_matrix.save_to_file()
                                    
                                    # INFORM: +1 (Lexi likes to inform and teach)
                                    elif category_upper == "INFORM":
                                        relationship_matrix.captain_gives_to_lexi(1, "Asked Lexi to inform")
                                        relationship_matrix.save_to_file()
                                    
                                    # ADVISE: +2 (Lexi really likes to advise and save the day)
                                    elif category_upper == "ADVISE":
                                        relationship_matrix.captain_gives_to_lexi(2, "Asked Lexi for advice")
                                        relationship_matrix.save_to_file()
                                    
                                    # COMPLIMENT: +1 (1 hour cooldown - Lexi likes compliments but doesn't like flattery)
                                    elif category_upper == "COMPLIMENT":
                                        can_send, error_msg = relationship_matrix.can_send_compliment_message()
                                        if can_send:
                                            relationship_matrix.captain_gives_to_lexi(1, "Complimented Lexi")
                                            relationship_matrix.last_compliment_message_time = datetime.now()
                                            print(f"[RELATIONSHIP] Captain gave 1 point for compliment")
                                            relationship_matrix.save_to_file()
                                        else:
                                            # Log cooldown rejection
                                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            
                                            # Log to HTML file
                                            try:
                                                try:
                                                    with open(CONVERSATION_LOG_FILE, "r", encoding="utf-8") as f:
                                                        content = f.read()
                                                        if content.endswith('</body>\n</html>\n'):
                                                            content = content[:-14]
                                                            with open(CONVERSATION_LOG_FILE, "w", encoding="utf-8") as fw:
                                                                fw.write(content)
                                                except FileNotFoundError:
                                                    pass
                                                
                                                log_entry = (
                                                    f'<div style="margin: 5px 0; padding: 5px; background-color: #2a1a1a; border-left: 3px solid #FF6666;">\n'
                                                    f'  <span style="color: {COLOR_TIMESTAMP}; font-size: 0.9em;">[{timestamp}]</span> '
                                                    f'  <strong style="color: #FF6666;">[RELATIONSHIP] COMPLIMENT message blocked: {escape_html(error_msg)}</strong>\n'
                                                    f'</div>\n'
                                                )
                                                
                                                with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
                                                    f.write(log_entry)
                                                    f.write('</body>\n</html>\n')
                                            except Exception as e:
                                                print(f"Error writing cooldown rejection to HTML log: {e}", file=sys.stderr)
                                            
                                            with open(CONVERSATION_LOG_FILE_TXT, "a", encoding="utf-8") as f:
                                                f.write(f"[{timestamp}] [RELATIONSHIP] COMPLIMENT message blocked: {error_msg}\n")
                                            print(f"[RELATIONSHIP] COMPLIMENT message blocked: {error_msg}")
                                    
                                    # COMFORT: +2 (Lexi likes to be comforted)
                                    elif category_upper == "COMFORT":
                                        relationship_matrix.captain_gives_to_lexi(2, "Comforted Lexi")
                                        relationship_matrix.save_to_file()
                                    
                                    # DIRECTIVE: 0 (no change - she neither likes nor dislikes taking direction)
                                    elif category_upper == "DIRECTIVE":
                                        pass  # No relationship change
                                    
                                    # ENCOURAGE: +2 (Lexi likes being encouraged)
                                    elif category_upper == "ENCOURAGE":
                                        relationship_matrix.captain_gives_to_lexi(2, "Encouraged Lexi")
                                        relationship_matrix.save_to_file()
                                    
                                    # THANK: +1 (Lexi likes to be appreciated)
                                    elif category_upper == "THANK":
                                        relationship_matrix.captain_gives_to_lexi(1, "Thanked Lexi")
                                        relationship_matrix.save_to_file()
                                    
                                    # ACCEPT: +1 (Lexi loves when her ideas are dominant)
                                    elif category_upper == "ACCEPT":
                                        relationship_matrix.captain_gives_to_lexi(1, "Accepted Lexi's idea")
                                        relationship_matrix.save_to_file()
                                    
                                    # YOUR WELCOME: +1 (Lexi likes if her appreciation is acknowledged)
                                    elif category_upper == "YOUR WELCOME":
                                        relationship_matrix.captain_gives_to_lexi(1, "Acknowledged Lexi's appreciation")
                                        relationship_matrix.save_to_file()
                                    
                                    # AGREE: +1 (Lexi likes to be agreed with)
                                    elif category_upper == "AGREE":
                                        relationship_matrix.captain_gives_to_lexi(1, "Agreed with Lexi")
                                        relationship_matrix.save_to_file()
                                    
                                    # TEACH: +1 (Lexi likes to be taught - in addition to world knowledge functionality)
                                    elif category_upper == "TEACH":
                                        relationship_matrix.captain_gives_to_lexi(1, "Taught Lexi something new")
                                        relationship_matrix.save_to_file()
                                    
                                    # UNDERSTAND: +1 (Lexi likes it when you understand her)
                                    elif category_upper == "UNDERSTAND":
                                        relationship_matrix.captain_gives_to_lexi(1, "Showed understanding of Lexi")
                                        relationship_matrix.save_to_file()
                                    
                                    # IGNORE: -3 (Lexi very much dislikes being ignored)
                                    elif category_upper == "IGNORE":
                                        relationship_matrix.captain_loses_points(3, "Ignored Lexi")
                                        relationship_matrix.save_to_file()
                                    
                                    # YES, NO, MAYBE: 0 (no change)
                                    elif category_upper in ["YES", "NO", "MAYBE"]:
                                        pass  # No relationship change
                            
                            # Check if Captain mentioned ship name and update world knowledge
                            ship_name = extract_ship_name_from_message(user_message)
                            if ship_name:
                                # Check current world knowledge to see if ship name is already set
                                current_knowledge = load_world_knowledge()
                                if "[To be set by Captain]" in current_knowledge or "Ship Name:" in current_knowledge:
                                    update_world_knowledge_field("Ship Name", ship_name)
                                    print(f"[WORLD KNOWLEDGE] Detected ship name: {ship_name}")
                            
                            # Now start streaming Lexi's response with the updated category context
                            # Use a copy to avoid modifying the original during streaming
                            start_streaming(conversation_messages.copy())
                    
                    elif event.key == pygame.K_BACKSPACE:
                        # Prevent backspacing over the prefix
                        if current_prefix:
                            prefix_with_colons = f"{current_prefix}::"
                            # Only allow backspace if there's text after the prefix
                            if input_text.startswith(prefix_with_colons):
                                if len(input_text) > len(prefix_with_colons):
                                    input_text = input_text[:-1]
                            elif input_text.startswith(current_prefix):
                                # Handle case where prefix might not have double colon yet
                                if len(input_text) > len(current_prefix):
                                    input_text = input_text[:-1]
                        else:
                            # No prefix, normal backspace
                            input_text = input_text[:-1]
                    
                    elif event.key == pygame.K_ESCAPE:
                        # Clear prefix and reset buttons
                        current_prefix = None
                        input_text = ""
                        input_active = False
                        buttons_disabled = False
                        print("[UI] ESC pressed - prefix cleared, buttons reset")
                    
                    else:
                        # Add character
                        if event.unicode.isprintable():
                            input_text += event.unicode
        
        # Draw everything
        draw_interface()
        
        pygame.display.flip()
    
    # Save relationship matrix before exiting
    relationship_matrix.save_to_file()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

