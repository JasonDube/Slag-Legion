"""
Lexi Animation Loader - Unified animation loading for all locations
Centralized animation loading with location-aware paths
"""
import os
import glob
import json
from typing import Dict, Optional, List
from modules.animation import Animation
import pygame


class LexiAnimationLoader:
    """Loads and manages Lexi animations for all locations"""
    
    # Animation paths by location
    ANIMATION_PATHS = {
        "right_panel": "animations/right",
        "control_room": "animations/central_middle/control_room/entities/lexi",
        # Future locations can be added here
    }
    
    def __init__(self, mapping_file: str = "systems/lexi_descriptor_animations.json"):
        """Initialize the animation loader
        
        Args:
            mapping_file: Path to emotion-to-animation mapping JSON file
        """
        self.mapping_file = mapping_file
        self.emotion_mappings: Dict = {}
        self.loaded_animations: Dict[str, Dict[str, Animation]] = {}  # location -> emotion -> Animation
        self.load_emotion_mapping()
    
    def load_emotion_mapping(self) -> Dict:
        """Load emotion→animation mapping from JSON"""
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    self.emotion_mappings = json.load(f)
                print(f"✓ Loaded emotion mappings from {self.mapping_file}")
            else:
                print(f"Warning: Mapping file not found: {self.mapping_file}, using defaults")
                self.emotion_mappings = self._get_default_mappings()
        except Exception as e:
            print(f"Error loading emotion mappings: {e}")
            self.emotion_mappings = self._get_default_mappings()
        
        return self.emotion_mappings
    
    def _get_default_mappings(self) -> Dict:
        """Get default emotion mappings if JSON file is missing"""
        return {
            "emotion_mappings": {
                "neutral": {
                    "primary": "lexi_neutral",
                    "fallbacks": ["lexi_professional"],
                    "locations": {
                        "right_panel": "lexi_neutral",
                        "control_room": None  # Uses default standing animation
                    }
                }
            }
        }
    
    def load_animations_for_location(self, location: str) -> Dict[str, Animation]:
        """Load all available animations for a location
        
        Args:
            location: Location identifier (e.g., "right_panel", "control_room")
            
        Returns:
            Dictionary mapping emotion names to Animation objects
        """
        if location not in self.ANIMATION_PATHS:
            print(f"Warning: Unknown location '{location}'")
            return {}
        
        if location in self.loaded_animations:
            return self.loaded_animations[location]
        
        base_path = self.ANIMATION_PATHS[location]
        animations = {}
        
        if location == "right_panel":
            animations = self._load_right_panel_animations(base_path)
        elif location == "control_room":
            animations = self._load_control_room_animations(base_path)
        
        self.loaded_animations[location] = animations
        return animations
    
    def _load_right_panel_animations(self, base_path: str) -> Dict[str, Animation]:
        """Load animations from right panel folder structure"""
        animations = {}
        
        if not os.path.exists(base_path):
            print(f"Warning: Right panel animation path not found: {base_path}")
            return animations
        
        # Find all lexi_* folders
        animation_folders = [
            d for d in os.listdir(base_path)
            if os.path.isdir(os.path.join(base_path, d)) and d.startswith("lexi_")
        ]
        
        for folder_name in animation_folders:
            animation_path = os.path.join(base_path, folder_name)
            config_file = os.path.join(animation_path, "animation_config.json")
            
            # Load config
            config = self._load_animation_config(config_file)
            
            # Load frames
            frame_files = sorted(glob.glob(os.path.join(animation_path, "frame_*.png")))
            if not frame_files:
                continue
            
            start_idx = config.get("start_frame", 0)
            if config.get("skip_first_frame", False):
                start_idx = max(1, start_idx)
            
            end_idx = config.get("end_frame")
            if end_idx is None:
                end_idx = len(frame_files)
            else:
                end_idx = min(end_idx + 1, len(frame_files))
            
            if start_idx >= len(frame_files) or start_idx >= end_idx:
                continue
            
            frames = []
            for frame_file in frame_files[start_idx:end_idx]:
                try:
                    frame = pygame.image.load(frame_file).convert_alpha()
                    frames.append(frame)
                except Exception as e:
                    print(f"Error loading frame {frame_file}: {e}")
                    continue
            
            if frames:
                fps = config.get("fps", 10)
                loop = config.get("loop", True)
                animation = Animation(folder_name, frames, fps=fps, loop=loop)
                animations[folder_name] = animation
        
        print(f"✓ Loaded {len(animations)} animations for right_panel")
        return animations
    
    def _load_control_room_animations(self, base_path: str) -> Dict[str, Animation]:
        """Load animations from control room folder structure"""
        animations = {}
        
        if not os.path.exists(base_path):
            print(f"Warning: Control room animation path not found: {base_path}")
            return animations
        
        # Load standing animation sequence (lexi_*.png files, excluding lexi_sit.png)
        all_files = glob.glob(os.path.join(base_path, "lexi_*.png"))
        frame_files = [
            f for f in all_files
            if not os.path.basename(f).lower() == "lexi_sit.png"
        ]
        frame_files = sorted(
            frame_files,
            key=lambda x: int(os.path.splitext(os.path.basename(x))[0].split('_')[1])
        )
        
        if frame_files:
            frames = []
            for frame_file in frame_files:
                try:
                    frame = pygame.image.load(frame_file).convert_alpha()
                    # Scale to 51.2% of original size
                    original_width = frame.get_width()
                    original_height = frame.get_height()
                    new_width = int(original_width * 0.512)
                    new_height = int(original_height * 0.512)
                    frame = pygame.transform.scale(frame, (new_width, new_height))
                    frames.append(frame)
                except Exception as e:
                    print(f"Error loading frame {frame_file}: {e}")
                    continue
            
            if frames:
                animation = Animation("lexi_control_room_standing", frames, fps=10, loop=True)
                animations["standing"] = animation
        
        # Load static poses
        sit_path = os.path.join(base_path, "lexi_sit.png")
        if os.path.exists(sit_path):
            try:
                sit_surface = pygame.image.load(sit_path).convert_alpha()
                # Scale to 52% of original size
                new_width = int(sit_surface.get_width() * 0.52)
                new_height = int(sit_surface.get_height() * 0.52)
                sit_surface = pygame.transform.scale(sit_surface, (new_width, new_height))
                sit_animation = Animation("lexi_sit_static", [sit_surface], fps=1, loop=True)
                animations["sit"] = sit_animation
            except Exception as e:
                print(f"Error loading sit pose: {e}")
        
        # Load chair pose (try multiple filename variations)
        chair_candidates = [
            os.path.join(base_path, "lexi_chair.pmg"),
            os.path.join(base_path, "lexi_chair.png"),
            os.path.join(base_path, "lexis_chair.png"),
        ]
        for chair_path in chair_candidates:
            if os.path.exists(chair_path):
                try:
                    chair_surface = pygame.image.load(chair_path).convert_alpha()
                    # Scale to 52% of original size
                    new_width = int(chair_surface.get_width() * 0.52)
                    new_height = int(chair_surface.get_height() * 0.52)
                    chair_surface = pygame.transform.scale(chair_surface, (new_width, new_height))
                    chair_animation = Animation("lexi_chair_static", [chair_surface], fps=1, loop=True)
                    animations["chair"] = chair_animation
                    break
                except Exception as e:
                    continue
        
        print(f"✓ Loaded {len(animations)} animations for control_room")
        return animations
    
    def _load_animation_config(self, config_file: str) -> Dict:
        """Load animation config from JSON file, return defaults if not found"""
        default_config = {
            "start_frame": 0,
            "end_frame": None,
            "fps": 10,
            "loop": True,
            "skip_first_frame": False,
            "sticky_frame": None
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                print(f"Warning: Could not load config from {config_file}: {e}")
                return default_config
        
        return default_config
    
    def get_animation(self, location: str, emotion: str, pose: str = None) -> Optional[Animation]:
        """Get specific animation by context
        
        Args:
            location: Location identifier (e.g., "right_panel", "control_room")
            emotion: Emotion name (e.g., "happy", "neutral")
            pose: Optional pose override (e.g., "sit", "stand")
            
        Returns:
            Animation object or None if not found
        """
        # Load animations for location if not already loaded
        if location not in self.loaded_animations:
            self.load_animations_for_location(location)
        
        location_animations = self.loaded_animations.get(location, {})
        
        # For control room, pose takes priority
        if location == "control_room" and pose:
            if pose == "sit" and "sit" in location_animations:
                return location_animations["sit"]
            elif pose == "stand" or pose == "chair":
                # Check for emotion-specific standing animation first
                emotion_anim = self._get_emotion_animation(location, emotion, location_animations)
                if emotion_anim:
                    return emotion_anim
                # Fall back to default standing animation
                if "standing" in location_animations:
                    return location_animations["standing"]
                # Or chair pose if available
                if "chair" in location_animations:
                    return location_animations["chair"]
        
        # For right panel, use emotion-based selection
        if location == "right_panel":
            return self._get_emotion_animation(location, emotion, location_animations)
        
        return None
    
    def _get_emotion_animation(self, location: str, emotion: str, location_animations: Dict) -> Optional[Animation]:
        """Get animation for specific emotion with fallback chain"""
        if not self.emotion_mappings or "emotion_mappings" not in self.emotion_mappings:
            # No mappings, try direct match
            animation_name = f"lexi_{emotion}"
            return location_animations.get(animation_name)
        
        emotion_mappings = self.emotion_mappings.get("emotion_mappings", {})
        
        # Check if emotion has mapping
        if emotion in emotion_mappings:
            mapping = emotion_mappings[emotion]
            primary = mapping.get("primary")
            
            # Try primary animation
            if primary and primary in location_animations:
                return location_animations[primary]
            
            # Try fallbacks
            fallbacks = mapping.get("fallbacks", [])
            for fallback in fallbacks:
                fallback_name = f"lexi_{fallback}" if not fallback.startswith("lexi_") else fallback
                if fallback_name in location_animations:
                    return location_animations[fallback_name]
        
        # Direct match as last resort
        animation_name = f"lexi_{emotion}"
        if animation_name in location_animations:
            return location_animations[animation_name]
        
        # Default to neutral if available
        if "lexi_neutral" in location_animations:
            return location_animations["lexi_neutral"]
        
        return None

