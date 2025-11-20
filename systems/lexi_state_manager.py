"""
Lexi State Manager - Centralized state management for Lexi across all panels
Single source of truth for emotion, pose, and location context
"""
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
import time


class LexiStateManager:
    """Centralized state management for Lexi across all panels"""
    
    def __init__(self):
        # Core state
        self.current_emotion: str = "neutral"  # From chat analysis
        self.physical_pose: str = "sit"  # "sit" or "stand"
        self.location_context: str = "control_room"  # Which room/panel
        
        # State history & tracking
        self.emotion_history: List[Tuple[str, float]] = []  # (emotion, timestamp)
        self.pose_history: List[Tuple[str, float]] = []  # (pose, timestamp)
        self.state_change_callbacks: List[Callable[[str, str], None]] = []  # For panel subscriptions
        
        # State timers
        self.emotion_timer: float = 0.0
        self.emotion_timeout: float = 120.0  # 2 minutes default timeout
        
        # Last known values for change detection
        self.last_emotion: Optional[str] = None
        self.last_pose: Optional[str] = None
    
    def update_emotion(self, emotion: str, source: str = "chat"):
        """Update emotion from any source (chat, manual, event)"""
        if not emotion or emotion.strip() == "":
            emotion = "neutral"
        
        emotion = emotion.lower().strip()
        
        # Only update if emotion actually changed
        if emotion != self.current_emotion:
            self.last_emotion = self.current_emotion
            self.current_emotion = emotion
            self.emotion_timer = 0.0
            
            # Add to history
            timestamp = time.time()
            self.emotion_history.append((emotion, timestamp))
            
            # Keep only last 100 entries
            if len(self.emotion_history) > 100:
                self.emotion_history.pop(0)
            
            # Notify subscribers
            self._notify_state_change()
            
            print(f"LexiStateManager: Emotion updated to '{emotion}' (source: {source})")
    
    def update_pose(self, pose: str):
        """Update physical pose (sit/stand)"""
        if pose not in ["sit", "stand", "chair"]:
            print(f"Warning: Invalid pose '{pose}', defaulting to 'sit'")
            pose = "sit"
        
        # Normalize "chair" to "stand"
        if pose == "chair":
            pose = "stand"
        
        # Only update if pose actually changed
        if pose != self.physical_pose:
            self.last_pose = self.physical_pose
            self.physical_pose = pose
            
            # Add to history
            timestamp = time.time()
            self.pose_history.append((pose, timestamp))
            
            # Keep only last 100 entries
            if len(self.pose_history) > 100:
                self.pose_history.pop(0)
            
            # Notify subscribers
            self._notify_state_change()
            
            print(f"LexiStateManager: Pose updated to '{pose}'")
    
    def update_location_context(self, location: str):
        """Update location context (which room/panel)"""
        if location != self.location_context:
            self.location_context = location
            # Location changes don't trigger animation changes, but useful for logging
            print(f"LexiStateManager: Location context updated to '{location}'")
    
    def subscribe_state_change(self, callback: Callable[[str, str], None]):
        """Panels subscribe to state changes
        
        Args:
            callback: Function that takes (emotion: str, pose: str) as parameters
        """
        if callback not in self.state_change_callbacks:
            self.state_change_callbacks.append(callback)
            print(f"LexiStateManager: Subscribed callback {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def unsubscribe_state_change(self, callback: Callable[[str, str], None]):
        """Remove a state change callback"""
        if callback in self.state_change_callbacks:
            self.state_change_callbacks.remove(callback)
    
    def _notify_state_change(self):
        """Notify all subscribers of state change"""
        for callback in self.state_change_callbacks:
            try:
                callback(self.current_emotion, self.physical_pose)
            except Exception as e:
                print(f"Error in state change callback: {e}")
    
    def update(self, dt: float):
        """Update state manager (call each frame for timers)"""
        # Update emotion timer
        if self.current_emotion != "neutral":
            self.emotion_timer += dt
            if self.emotion_timer >= self.emotion_timeout:
                # Timeout: return to neutral
                self.update_emotion("neutral", source="timeout")
    
    def get_state(self) -> Dict[str, str]:
        """Get current state as dictionary"""
        return {
            "emotion": self.current_emotion,
            "pose": self.physical_pose,
            "location": self.location_context
        }
    
    def has_state_changed(self) -> bool:
        """Check if state has changed since last check"""
        changed = (
            self.current_emotion != self.last_emotion or
            self.physical_pose != self.last_pose
        )
        return changed

