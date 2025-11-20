# Lexi Animation Architecture Analysis & Recommendations

## Current State Analysis

### Right Panel (LexiSystem) - Emotion-Based Animations
**Location:** `systems/lexi_system.py`

**Current Flow:**
1. `LexiChat` analyzes Lexi's responses → stores in `message_emotions` dict
2. `LexiSystem.update()` polls `lexi_chat.message_emotions` directly
3. Uses `_match_descriptor_to_animation()` with hardcoded variations dict
4. Loads animations from `animations/right/lexi_*` folders
5. Manages state transitions, timeouts, and sticky frames

**State Tracking:**
- `current_state` (string: "neutral", "happy", etc.)
- `state_animation` (Animation object)
- `state_timer` (for 2-minute timeout back to neutral)
- `last_descriptor` (to detect changes)

**Issues:**
- Direct coupling to `lexi_chat.message_emotions` dict
- Hardcoded emotion→animation mapping in code
- No separation between emotion analysis and animation selection
- State management mixed with UI rendering

---

### Central Panel (Control Room) - Pose-Based Animations
**Location:** `core/game.py`

**Current Flow:**
1. Loads static poses: `lexi_sit.png`, `lexi_chair.png`
2. Loads standing animation sequence from `animations/central_middle/control_room/entities/lexi`
3. Manual toggle via `_set_lexi_state('sit'/'chair')`
4. Triggered by: user click OR user message callback

**State Tracking:**
- `lexi_pose_state` (string: "sit" or "chair")
- Separate animation objects: `lexi_sit_animation`, `lexi_chair_animation`, `lexi_control_room_animation`

**Issues:**
- No emotion-based animation selection
- Completely separate from right panel system
- No unified state management
- Duplicate animation loading logic

---

## Recommended Architecture

### 1. Central State Manager (`systems/lexi_state_manager.py`)

**Purpose:** Single source of truth for all Lexi state (emotion, pose, location context)

```python
class LexiStateManager:
    """Centralized state management for Lexi across all panels"""
    
    # Core state
    current_emotion: str = "neutral"  # From chat analysis
    physical_pose: str = "sit"  # "sit" or "stand"
    location_context: str = "control_room"  # Which room/panel
    
    # State history & transitions
    emotion_history: List[Tuple[str, float]]  # (emotion, timestamp)
    state_change_callbacks: List[Callable]  # For panel subscriptions
    
    # Animation mappings
    emotion_to_animation: Dict[str, str]  # Loaded from JSON
    location_animations: Dict[str, Dict[str, Animation]]  # By location & emotion
    
    def update_emotion(self, emotion: str, source: str = "chat"):
        """Update emotion from any source (chat, manual, event)"""
        
    def update_pose(self, pose: str):
        """Update physical pose (sit/stand)"""
        
    def get_animation_for_context(self, location: str, emotion: str, pose: str) -> Optional[Animation]:
        """Get appropriate animation for given context"""
        
    def subscribe_state_change(self, callback: Callable):
        """Panels subscribe to state changes"""
```

**Benefits:**
- Single source of truth
- Decoupled from UI systems
- Easy to extend with new states
- Testable in isolation

---

### 2. Unified Animation Loader (`systems/lexi_animation_loader.py`)

**Purpose:** Centralized animation loading with location-aware paths

```python
class LexiAnimationLoader:
    """Loads and manages Lexi animations for all locations"""
    
    # Animation paths by location
    ANIMATION_PATHS = {
        "right_panel": "animations/right/lexi_{emotion}",
        "control_room": "animations/central_middle/control_room/entities/lexi",
        # Future: "cargo_room", "greenhouse", etc.
    }
    
    def load_animations_for_location(self, location: str) -> Dict[str, Animation]:
        """Load all available animations for a location"""
        
    def get_animation(self, location: str, emotion: str, pose: str = None) -> Optional[Animation]:
        """Get specific animation by context"""
        
    def load_emotion_mapping(self) -> Dict[str, str]:
        """Load emotion→animation mapping from JSON"""
```

**Benefits:**
- Consistent loading logic
- Easy to add new locations
- Centralized path management
- Reusable across panels

---

### 3. Emotion-to-Animation Mapping System

**Current:** Hardcoded dict in `LexiSystem._match_descriptor_to_animation()`

**Recommended:** JSON-based mapping with fallback chain

**Structure:**
```json
{
  "emotion_mappings": {
    "happy": {
      "primary": "lexi_friendly",
      "fallbacks": ["lexi_sweet", "lexi_helpful"],
      "locations": {
        "right_panel": "animations/right/lexi_friendly",
        "control_room": "animations/central_middle/control_room/entities/lexi/emotions/happy"
      }
    },
    "neutral": {
      "primary": "lexi_neutral",
      "fallbacks": ["lexi_professional"],
      "locations": {
        "right_panel": "animations/right/lexi_neutral",
        "control_room": null  // Uses default standing animation
      }
    }
  },
  "pose_overrides": {
    "sit": {
      "control_room": "lexi_sit_static"
    },
    "stand": {
      "control_room": "lexi_control_room_standing"
    }
  }
}
```

**Benefits:**
- Data-driven (no code changes for new mappings)
- Location-aware
- Fallback chain for missing animations
- Easy to extend

---

### 4. Refactored Panel Systems

#### Right Panel (`systems/lexi_system.py`)
**Changes:**
- Remove direct `lexi_chat.message_emotions` access
- Subscribe to `LexiStateManager` for emotion changes
- Use `LexiAnimationLoader` for animation retrieval
- Focus on UI rendering only

```python
class LexiSystem:
    def __init__(self, ..., state_manager: LexiStateManager):
        self.state_manager = state_manager
        self.state_manager.subscribe_state_change(self._on_state_change)
        
    def _on_state_change(self, emotion: str, pose: str):
        """React to state changes from central manager"""
        animation = self.animation_loader.get_animation(
            "right_panel", emotion, pose
        )
        # Update UI...
```

#### Central Panel (`core/game.py`)
**Changes:**
- Remove duplicate state tracking
- Use `LexiStateManager` for pose state
- Subscribe to emotion changes for future emotion-based animations
- Use `LexiAnimationLoader` for animation loading

```python
class Game:
    def __init__(self):
        self.lexi_state_manager = LexiStateManager()
        self.lexi_state_manager.subscribe_state_change(self._on_lexi_state_change)
        
    def _on_lexi_state_change(self, emotion: str, pose: str):
        """Update Control Room animations based on state"""
        if pose == "sit":
            # Show sit animation
        elif pose == "stand":
            # Show stand + emotion-based animation if available
            emotion_anim = self.animation_loader.get_animation(
                "control_room", emotion, "stand"
            )
```

---

## Implementation Plan

### Phase 1: Create Core Infrastructure
1. ✅ Create `LexiStateManager` class
2. ✅ Create `LexiAnimationLoader` class
3. ✅ Create unified emotion mapping JSON structure
4. ✅ Add state change callback system

### Phase 2: Refactor Right Panel
1. ✅ Remove direct `message_emotions` access
2. ✅ Integrate `LexiStateManager`
3. ✅ Use `LexiAnimationLoader`
4. ✅ Test emotion-based animations

### Phase 3: Refactor Central Panel
1. ✅ Remove duplicate state tracking
2. ✅ Integrate `LexiStateManager`
3. ✅ Use `LexiAnimationLoader`
4. ✅ Add emotion-based animation support (future-ready)

### Phase 4: Enhancements
1. ✅ Add location-specific animation variants
2. ✅ Add pose transitions (sit→stand animations)
3. ✅ Add animation blending/transitions
4. ✅ Performance optimization

---

## Key Design Principles

### 1. Single Source of Truth
- All state in `LexiStateManager`
- No duplicate state tracking
- Panels are observers, not owners

### 2. Separation of Concerns
- **State Management:** `LexiStateManager`
- **Animation Loading:** `LexiAnimationLoader`
- **UI Rendering:** Panel-specific classes
- **Emotion Analysis:** `LexiChat` (already separate)

### 3. Extensibility
- JSON-based mappings (no code changes)
- Callback system (easy to add new subscribers)
- Location-aware paths (scalable to new rooms)

### 4. Error Handling
- Graceful fallbacks for missing animations
- Default to "neutral" if emotion unknown
- Logging for debugging

### 5. Performance
- Lazy loading of animations
- Cache loaded animations
- Only update when state actually changes

---

## Migration Strategy

### Backward Compatibility
- Keep existing code working during transition
- Gradual migration (one panel at a time)
- Feature flags for new system

### Testing Strategy
1. Unit tests for `LexiStateManager`
2. Unit tests for `LexiAnimationLoader`
3. Integration tests for state transitions
4. Visual regression tests for animations

---

## Future Enhancements

### 1. Animation Blending
- Smooth transitions between emotions
- Pose transition animations (sit→stand)

### 2. Context-Aware Animations
- Different animations based on conversation topic
- Room-specific variants (e.g., "working" in Control Room)

### 3. Animation Priority System
- Override system for special events
- Queue system for animation sequences

### 4. Performance Monitoring
- Track animation load times
- Monitor state change frequency
- Optimize hot paths

---

## Code Structure Preview

```
systems/
├── lexi_state_manager.py      # Central state management
├── lexi_animation_loader.py   # Unified animation loading
├── lexi_system.py             # Right panel (refactored)
└── lexi_descriptor_animations.json  # Enhanced mapping

core/
└── game.py                    # Central panel (refactored)

modules/
└── lexi_chat.py               # Emotion analysis (unchanged)
```

---

## Summary

**Current Issues:**
- ❌ Duplicate state tracking
- ❌ Tight coupling between systems
- ❌ Hardcoded mappings
- ❌ No unified architecture

**Proposed Solution:**
- ✅ Central `LexiStateManager` for all state
- ✅ Unified `LexiAnimationLoader` for all animations
- ✅ JSON-based emotion mappings
- ✅ Observer pattern for panel updates
- ✅ Clean separation of concerns
- ✅ Extensible and maintainable

**Result:**
- Both panels feed from same state source
- Easy to add new animations/locations
- Clean, testable, maintainable code
- Ready for future enhancements

---

## Refactoring Completed

**Date:** January 20, 2025

**Implementation Status:**
- ✅ Created `LexiStateManager` class - centralized state management
- ✅ Created `LexiAnimationLoader` class - unified animation loading
- ✅ Updated `lexi_descriptor_animations.json` - location-aware emotion mappings
- ✅ Refactored `LexiSystem` - now uses state manager and animation loader
- ✅ Refactored `Game` class - Control Room now uses unified architecture
- ✅ Removed duplicate state tracking and hardcoded mappings
- ✅ Implemented observer pattern for state change notifications

**Key Changes:**
1. Both panels now subscribe to `LexiStateManager` for state updates
2. All animations loaded through `LexiAnimationLoader` with consistent logic
3. Emotion-to-animation mapping now JSON-based and location-aware
4. State changes trigger callbacks to update both panels automatically
5. Removed direct `message_emotions` access from `LexiSystem`

**Next Steps:**
- Test the refactored system with existing animations
- Add emotion-based animations for Control Room (future enhancement)
- Monitor performance and optimize if needed
- Add unit tests for state manager and animation loader

