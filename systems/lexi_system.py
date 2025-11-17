"""
Lexi System - Handles all Lexi UI, state management, and animations
Separated from main game logic for better organization
"""
import pygame
import os
import glob
import json
from typing import Dict, Optional, List
from lexi_chat import LexiChat
from animation import Animation
import constants


class LexiSystem:
    """Manages all Lexi-related functionality: UI, animations, and state"""
    
    def __init__(self, screen: pygame.Surface, lexi_chat: LexiChat, show_debug_viewport_only: bool = False):
        self.screen = screen
        self.lexi_chat = lexi_chat
        self.show_debug_viewport_only = show_debug_viewport_only
        
        # UI state
        self.input_active = False
        self.chat_font = pygame.font.Font(None, 18)
        self.input_font = pygame.font.Font(None, 20)
        self.cursor_timer = 0
        self.cursor_visible = True
        self.chat_scroll_offset = 0
        self.scrollbar_dragging = False
        self.user_has_scrolled = False
        self.last_message_count = 0
        
        # Animation system
        self.animation_configs = {}
        self.animations_by_name = {}
        self.animation_position = (1046, 22)
        self.animations = []
        self.current_animation_index = 0
        self.animation_loops = 0
        self.animation_loops_per_animation = 5
        self.sticky_frame = None
        
        # State system
        self.current_state = "neutral"
        self.state_timer = 0.0
        self.state_animation = None
        self.state_animation_name = None
        self.state_timeout = 120.0  # 2 minutes
        self.last_descriptor = None
        
        # Load animations
        self.animations = self._load_all_animations()
        
        # Check Ollama connection
        if not self.lexi_chat.client.check_connection():
            print("Warning: Ollama server not running. Lexi chat will not work.")
            print(f"Make sure Ollama is running at {self.lexi_chat.client.base_url}")
        else:
            print("✓ Lexi chat system initialized")
    
    def _load_animation_config(self, animation_path: str) -> Dict:
        """Load animation config from JSON file, return defaults if not found"""
        config_file = os.path.join(animation_path, "animation_config.json")
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
    
    def _match_descriptor_to_animation(self, descriptor: str) -> Optional[str]:
        """Match a descriptor to an animation name with fuzzy matching"""
        if not descriptor:
            return None
        
        descriptor_lower = descriptor.lower().strip()
        
        # Direct match first
        animation_name = f"lexi_{descriptor_lower}"
        if animation_name in self.animations_by_name:
            return animation_name
        
        # Common variations and synonyms
        variations = {
            "happy": ["friendly", "sweet", "helpful"],
            "sad": ["detached", "ambivalent"],
            "excited": ["friendly", "helpful"],
            "calm": ["neutral", "professional", "diplomatic"],
            "playful": ["witty", "sarcastic", "flirtatious"],
            "serious": ["professional", "diplomatic", "neutral"],
            "surprised": ["shocked"],
            "thinking": ["thoughtful"],
            "curious": ["thoughtful", "helpful"],
            "worried": ["ambivalent", "detached"],
            "confused": ["ambivalent", "thoughtful"],
            "amused": ["witty", "sarcastic"],
            "flirty": ["flirtatious"],
            "sarcastic": ["sarcastic"],
            "witty": ["witty"],
            "helpful": ["helpful"],
            "friendly": ["friendly"],
            "professional": ["professional"],
            "diplomatic": ["diplomatic"],
            "sweet": ["sweet"],
            "shocked": ["shocked"],
            "thoughtful": ["thoughtful"],
            "ambivalent": ["ambivalent"],
            "detached": ["detached"],
            "neutral": ["neutral"]
        }
        
        # Check variations
        for key, anim_list in variations.items():
            if key in descriptor_lower or descriptor_lower in key:
                for anim_variant in anim_list:
                    animation_name = f"lexi_{anim_variant}"
                    if animation_name in self.animations_by_name:
                        return animation_name
        
        # Partial match
        for anim_name in self.animations_by_name.keys():
            anim_base = anim_name.replace("lexi_", "")
            if anim_base in descriptor_lower or descriptor_lower in anim_base:
                return anim_name
        
        return None
    
    def _load_all_animations(self) -> List[Animation]:
        """Load all Lexi animations from animations/right folders"""
        animations = []
        base_path = "animations/right"
        
        try:
            if not os.path.exists(base_path):
                print(f"Warning: Animation directory {base_path} not found")
                return []
            
            animation_folders = [d for d in os.listdir(base_path) 
                                if os.path.isdir(os.path.join(base_path, d)) and d.startswith("lexi_")]
            animation_folders.sort()
            
            if not animation_folders:
                print(f"Warning: No animation folders found in {base_path}")
                return []
            
            for folder_name in animation_folders:
                animation_path = os.path.join(base_path, folder_name)
                config = self._load_animation_config(animation_path)
                self.animation_configs[folder_name] = config
                
                frame_files = sorted(glob.glob(os.path.join(animation_path, "frame_*.png")))
                if not frame_files:
                    print(f"Warning: No frames found in {animation_path}")
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
                    print(f"Warning: Invalid frame range for {folder_name}")
                    continue
                
                frames = []
                for frame_file in frame_files[start_idx:end_idx]:
                    try:
                        frame = pygame.image.load(frame_file).convert_alpha()
                        frames.append(frame)
                    except Exception as e:
                        print(f"Error loading frame {frame_file}: {e}")
                        continue
                
                sticky_frame_idx = config.get("sticky_frame")
                sticky_frame_surface = None
                if sticky_frame_idx is not None:
                    if 0 <= sticky_frame_idx < len(frame_files):
                        try:
                            sticky_frame_surface = pygame.image.load(frame_files[sticky_frame_idx]).convert_alpha()
                            config['sticky_frame_surface'] = sticky_frame_surface
                            print(f"  Sticky frame loaded: {sticky_frame_idx}")
                        except Exception as e:
                            print(f"Warning: Could not load sticky frame {sticky_frame_idx} for {folder_name}: {e}")
                
                if frames:
                    fps = config.get("fps", 10)
                    loop = config.get("loop", True)
                    animation = Animation(folder_name, frames, fps=fps, loop=loop)
                    animations.append(animation)
                    self.animations_by_name[folder_name] = animation
                    print(f"Loaded {folder_name}: {len(frames)} frames (from {start_idx} to {end_idx-1}), fps={fps}, loop={loop}")
            
            # Start with neutral animation
            if animations:
                neutral_anim = self.animations_by_name.get("lexi_neutral")
                if neutral_anim:
                    neutral_anim.loop = True
                    neutral_anim.play()
                    self.current_animation_index = animations.index(neutral_anim)
                    self.current_state = "neutral"
                    self.sticky_frame = None
                    print(f"✓ Loaded {len(animations)} Lexi animations, starting with neutral")
                    print(f"  Neutral animation: {neutral_anim.name}, frames: {len(neutral_anim.frames)}, playing: {neutral_anim.playing}, loop: {neutral_anim.loop}")
                    print(f"  Animation index: {self.current_animation_index}, position: {self.animation_position}")
                else:
                    animations[0].loop = True
                    animations[0].play()
                    print(f"✓ Loaded {len(animations)} Lexi animations, starting with {animations[0].name}")
            
            return animations
            
        except Exception as e:
            print(f"Error loading Lexi animations: {e}")
            return []
    
    def handle_event(self, event) -> bool:
        """
        Handle events related to Lexi system.
        Returns True if event was handled, False otherwise.
        """
        if self.show_debug_viewport_only:
            return False
        
        if event.type == pygame.KEYDOWN:
            # Handle Lexi chat input - takes priority
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    if self.lexi_chat.input_text.strip():
                        self.lexi_chat.send_message(
                            self.lexi_chat.input_text,
                            on_chunk=lambda text: None
                        )
                        self.lexi_chat.input_text = ""
                        self.chat_scroll_offset = 999999
                        self.user_has_scrolled = False
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.lexi_chat.input_text = self.lexi_chat.input_text[:-1]
                    return True
                else:
                    if event.unicode and event.unicode.isprintable():
                        self.lexi_chat.input_text += event.unicode
                    return True
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Check if clicking on input box
                input_rect = pygame.Rect(
                    LexiChat.INPUT_BOX_X,
                    LexiChat.INPUT_BOX_Y,
                    LexiChat.INPUT_BOX_WIDTH,
                    LexiChat.INPUT_BOX_HEIGHT
                )
                if input_rect.collidepoint(event.pos):
                    self.input_active = True
                    return True
                else:
                    self.input_active = False
                
                # Check if clicking on scrollbar
                if self._check_scrollbar_click(event.pos):
                    self.scrollbar_dragging = True
                    self.user_has_scrolled = True
                    return True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.scrollbar_dragging = False
        
        elif event.type == pygame.MOUSEMOTION:
            if self.scrollbar_dragging:
                self._handle_scrollbar_drag(event.pos)
                return True
        
        elif event.type == pygame.MOUSEWHEEL:
            self.chat_scroll_offset = max(0, self.chat_scroll_offset - event.y * 3)
            if event.y != 0:
                self.user_has_scrolled = True
            return True
        
        return False
    
    def _check_scrollbar_click(self, mouse_pos: tuple) -> bool:
        """Check if mouse clicked on the Lexi chat scrollbar"""
        chat_box = pygame.Rect(
            LexiChat.CHAT_BOX_X,
            LexiChat.CHAT_BOX_Y,
            LexiChat.CHAT_BOX_WIDTH,
            LexiChat.CHAT_BOX_HEIGHT
        )
        scrollbar_x = chat_box.right - 4
        scrollbar_rect = pygame.Rect(scrollbar_x, chat_box.y, 4, chat_box.height)
        return scrollbar_rect.collidepoint(mouse_pos)
    
    def _handle_scrollbar_drag(self, mouse_pos: tuple):
        """Handle dragging the Lexi chat scrollbar"""
        chat_box = pygame.Rect(
            LexiChat.CHAT_BOX_X,
            LexiChat.CHAT_BOX_Y,
            LexiChat.CHAT_BOX_WIDTH - 4,
            LexiChat.CHAT_BOX_HEIGHT
        )
        
        messages = self.lexi_chat.get_conversation_messages()
        if self.lexi_chat.streaming and self.lexi_chat.current_response:
            messages = messages + [("AI", self.lexi_chat.current_response, None, None, "emotion")]
        
        padding = 10
        line_height = 20
        total_lines = []
        
        for message_data in messages:
            if len(message_data) == 5:
                speaker, message, descriptor_or_emotion, action, descriptor_type = message_data
            elif len(message_data) == 4:
                speaker, message, descriptor_or_emotion, descriptor_type = message_data
                action = None
            elif len(message_data) == 3:
                speaker, message, descriptor_or_emotion = message_data
                descriptor_type = "emotion" if speaker == "AI" else "descriptor"
                action = None
            else:
                speaker, message = message_data
                descriptor_or_emotion = None
                descriptor_type = None
                action = None
            
            prefix = "User: " if speaker == "User" else "AI: "
            parts = [prefix + message]
            if action:
                parts.append(f"[{action}]")
            if descriptor_or_emotion:
                parts.append(f"({descriptor_or_emotion})")
            full_text = " ".join(parts)
            
            words = full_text.split(' ')
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_surface = self.chat_font.render(test_line, True, constants.WHITE)
                if test_surface.get_width() <= chat_box.width - padding * 2:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append((speaker, current_line))
                    current_line = word
            
            if current_line:
                lines.append((speaker, current_line))
            
            total_lines.extend(lines)
            total_lines.append((None, ""))
        
        total_height = len(total_lines) * line_height
        visible_height = chat_box.height - padding * 2
        max_scroll = max(0, total_height - visible_height)
        
        if max_scroll > 0:
            relative_y = mouse_pos[1] - chat_box.y
            scroll_ratio = max(0, min(1, relative_y / chat_box.height))
            self.chat_scroll_offset = int(scroll_ratio * max_scroll)
            self.user_has_scrolled = True
    
    def update(self, dt: float):
        """Update Lexi system state"""
        # Update cursor blink
        if self.input_active:
            self.cursor_timer += dt
            if self.cursor_timer >= 0.5:
                self.cursor_timer = 0
                self.cursor_visible = not self.cursor_visible
        
        # Update state system - check for new descriptors
        if self.lexi_chat.message_emotions:
            latest_emotion_index = max(self.lexi_chat.message_emotions.keys())
            latest_descriptor = self.lexi_chat.message_emotions.get(latest_emotion_index)
            
            if latest_descriptor and latest_descriptor != self.last_descriptor:
                self.last_descriptor = latest_descriptor
                matched_animation = self._match_descriptor_to_animation(latest_descriptor)
                
                if matched_animation and matched_animation != self.state_animation_name:
                    state_anim = self.animations_by_name.get(matched_animation)
                    if state_anim:
                        if self.state_animation:
                            self.state_animation.stop()
                        
                        state_anim.loop = False
                        state_anim.play()
                        self.state_animation = state_anim
                        self.state_animation_name = matched_animation
                        self.current_state = matched_animation.replace("lexi_", "")
                        self.state_timer = 0.0
                        print(f"Lexi state changed to: {self.current_state} (animation: {matched_animation})")
        
        # Update state animation if playing
        if self.state_animation and self.state_animation.playing:
            self.state_animation.update(dt)
            
            if self.state_animation.finished:
                state_config = self.animation_configs.get(self.state_animation_name, {})
                
                if self.current_state == "neutral":
                    self.state_animation = None
                    self.state_animation_name = None
                    self.sticky_frame = None
                    neutral_anim = self.animations_by_name.get("lexi_neutral")
                    if neutral_anim:
                        neutral_anim.loop = True
                        neutral_anim.play()
                        self.current_animation_index = self.animations.index(neutral_anim) if neutral_anim in self.animations else 0
                    print("Returned to neutral, resuming animation cycling")
                else:
                    if 'sticky_frame_surface' in state_config:
                        self.sticky_frame = state_config['sticky_frame_surface']
                        self.state_animation.stop()
                        print(f"State animation finished, showing sticky frame for {self.current_state}")
                    else:
                        last_frame = self.state_animation.get_current_frame()
                        if last_frame:
                            self.sticky_frame = last_frame
                            self.state_animation.stop()
                            print(f"State animation finished, using last frame for {self.current_state}")
        
        # Update state timer (return to neutral after 2 minutes)
        if self.current_state != "neutral":
            self.state_timer += dt
            if self.state_timer >= self.state_timeout:
                neutral_anim = self.animations_by_name.get("lexi_neutral")
                if neutral_anim:
                    if self.state_animation:
                        self.state_animation.stop()
                    
                    neutral_anim.loop = False
                    neutral_anim.play()
                    self.state_animation = neutral_anim
                    self.state_animation_name = "lexi_neutral"
                    self.current_state = "neutral"
                    self.state_timer = 0.0
                    print("Lexi returning to neutral state (2 minute timeout)")
        
        # Update default neutral animation
        has_active_state = (self.state_animation is not None and 
                           (self.state_animation.playing or self.sticky_frame is not None))
        
        if not has_active_state:
            if self.animations and self.current_state == "neutral":
                neutral_anim = self.animations_by_name.get("lexi_neutral")
                if neutral_anim:
                    if not neutral_anim.playing:
                        neutral_anim.loop = True
                        neutral_anim.play()
                    neutral_anim.update(dt)
    
    def draw(self):
        """Draw all Lexi UI elements"""
        if self.show_debug_viewport_only:
            return
        
        self._draw_chat()
        self._draw_input()
        self._draw_animation()
    
    def _draw_chat(self):
        """Draw Lexi chat conversation"""
        chat_box = pygame.Rect(
            LexiChat.CHAT_BOX_X,
            LexiChat.CHAT_BOX_Y,
            LexiChat.CHAT_BOX_WIDTH - 4,
            LexiChat.CHAT_BOX_HEIGHT
        )
        
        chat_surface = pygame.Surface((chat_box.width, chat_box.height))
        chat_surface.set_alpha(200)
        chat_surface.fill(constants.BLACK)
        self.screen.blit(chat_surface, chat_box.topleft)
        
        messages = self.lexi_chat.get_conversation_messages()
        if self.lexi_chat.streaming and self.lexi_chat.current_response:
            messages = messages + [("AI", self.lexi_chat.current_response, None, None, "emotion")]
        
        padding = 10
        line_height = 20
        total_lines = []
        
        for message_data in messages:
            if len(message_data) == 5:
                speaker, message, descriptor_or_emotion, action, descriptor_type = message_data
            elif len(message_data) == 4:
                speaker, message, descriptor_or_emotion, descriptor_type = message_data
                action = None
            elif len(message_data) == 3:
                speaker, message, descriptor_or_emotion = message_data
                descriptor_type = "emotion" if speaker == "AI" else "descriptor"
                action = None
            else:
                speaker, message = message_data
                descriptor_or_emotion = None
                descriptor_type = None
                action = None
            
            prefix = "User: " if speaker == "User" else "AI: "
            parts = [prefix + message]
            if action:
                parts.append(f"[{action}]")
            if descriptor_or_emotion:
                parts.append(f"({descriptor_or_emotion})")
            full_text = " ".join(parts)
            
            words = full_text.split(' ')
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_surface = self.chat_font.render(test_line, True, constants.WHITE)
                if test_surface.get_width() <= chat_box.width - padding * 2:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append((speaker, current_line))
                    current_line = word
            
            if current_line:
                lines.append((speaker, current_line))
            
            total_lines.extend(lines)
            total_lines.append((None, ""))
        
        total_height = len(total_lines) * line_height
        visible_height = chat_box.height - padding * 2
        max_scroll = max(0, total_height - visible_height)
        
        current_message_count = len(messages)
        new_messages = current_message_count > self.last_message_count
        is_streaming = self.lexi_chat.streaming
        
        should_auto_scroll = False
        if is_streaming:
            should_auto_scroll = True
            self.user_has_scrolled = False
        elif new_messages and not self.user_has_scrolled:
            should_auto_scroll = True
        elif self.chat_scroll_offset >= max_scroll - (line_height * 2):
            should_auto_scroll = True
        
        if should_auto_scroll:
            self.chat_scroll_offset = max_scroll
        
        self.last_message_count = current_message_count
        self.chat_scroll_offset = max(0, min(self.chat_scroll_offset, max_scroll))
        
        start_line = int(self.chat_scroll_offset / line_height)
        y_offset = chat_box.y + padding - (self.chat_scroll_offset % line_height)
        
        for i in range(start_line, len(total_lines)):
            speaker, line = total_lines[i]
            if y_offset > chat_box.bottom:
                break
            
            if line:
                base_color = (0, 255, 0) if speaker == "User" else constants.WHITE
                x_offset = chat_box.x + padding
                
                if " [" in line and "]" in line:
                    bracket_start = line.find(" [")
                    bracket_end = line.find("]", bracket_start)
                    if bracket_start != -1 and bracket_end != -1:
                        before_action = line[:bracket_start]
                        if before_action:
                            text_surface = self.chat_font.render(before_action, True, base_color)
                            self.screen.blit(text_surface, (x_offset, y_offset))
                            x_offset += text_surface.get_width()
                        
                        action_text = line[bracket_start:bracket_end+1]
                        action_color = (255, 165, 0)
                        action_surface = self.chat_font.render(action_text, True, action_color)
                        self.screen.blit(action_surface, (x_offset, y_offset))
                        x_offset += action_surface.get_width()
                        
                        remaining = line[bracket_end+1:]
                        if remaining.strip():
                            if " (" in remaining and remaining.endswith(")"):
                                parts = remaining.rsplit(" (", 1)
                                if len(parts) == 2:
                                    if parts[0].strip():
                                        mid_surface = self.chat_font.render(parts[0], True, base_color)
                                        self.screen.blit(mid_surface, (x_offset, y_offset))
                                        x_offset += mid_surface.get_width()
                                    
                                    descriptor_part = "(" + parts[1]
                                    if speaker == "AI":
                                        descriptor_color = (255, 0, 0)
                                    else:
                                        descriptor_color = (100, 180, 255)
                                    descriptor_surface = self.chat_font.render(descriptor_part, True, descriptor_color)
                                    self.screen.blit(descriptor_surface, (x_offset, y_offset))
                                else:
                                    text_surface = self.chat_font.render(remaining, True, base_color)
                                    self.screen.blit(text_surface, (x_offset, y_offset))
                            else:
                                text_surface = self.chat_font.render(remaining, True, base_color)
                                self.screen.blit(text_surface, (x_offset, y_offset))
                    else:
                        text_surface = self.chat_font.render(line, True, base_color)
                        self.screen.blit(text_surface, (x_offset, y_offset))
                elif " (" in line and line.endswith(")"):
                    parts = line.rsplit(" (", 1)
                    if len(parts) == 2:
                        main_text = parts[0]
                        descriptor_part = "(" + parts[1]
                        
                        main_surface = self.chat_font.render(main_text, True, base_color)
                        self.screen.blit(main_surface, (x_offset, y_offset))
                        x_offset += main_surface.get_width()
                        
                        if speaker == "AI":
                            descriptor_color = (255, 0, 0)
                        else:
                            descriptor_color = (100, 180, 255)
                        descriptor_surface = self.chat_font.render(descriptor_part, True, descriptor_color)
                        self.screen.blit(descriptor_surface, (x_offset, y_offset))
                    else:
                        text_surface = self.chat_font.render(line, True, base_color)
                        self.screen.blit(text_surface, (x_offset, y_offset))
                else:
                    text_surface = self.chat_font.render(line, True, base_color)
                    self.screen.blit(text_surface, (x_offset, y_offset))
            
            y_offset += line_height
        
        # Draw scrollbar
        if total_height > visible_height:
            scrollbar_x = chat_box.right
            scrollbar_rect = pygame.Rect(scrollbar_x, chat_box.y, 4, chat_box.height)
            pygame.draw.rect(self.screen, (40, 40, 40), scrollbar_rect)
            
            thumb_height = max(20, int((visible_height / total_height) * chat_box.height))
            thumb_y = chat_box.y + int((self.chat_scroll_offset / max_scroll) * (chat_box.height - thumb_height)) if max_scroll > 0 else chat_box.y
            thumb_rect = pygame.Rect(scrollbar_x, thumb_y, 4, thumb_height)
            pygame.draw.rect(self.screen, (120, 120, 120), thumb_rect)
    
    def _draw_input(self):
        """Draw Lexi input box"""
        input_box = pygame.Rect(
            LexiChat.INPUT_BOX_X,
            LexiChat.INPUT_BOX_Y,
            LexiChat.INPUT_BOX_WIDTH,
            LexiChat.INPUT_BOX_HEIGHT
        )
        
        input_bg_color = (30, 30, 30) if self.input_active else (20, 20, 20)
        pygame.draw.rect(self.screen, input_bg_color, input_box)
        pygame.draw.rect(self.screen, (100, 100, 100), input_box, 2)
        
        padding = 10
        text_y = input_box.y + (input_box.height - self.input_font.get_height()) // 2
        
        text = self.lexi_chat.input_text
        if text:
            words = text.split(' ')
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                test_surface = self.input_font.render(test_line, True, constants.WHITE)
                if test_surface.get_width() <= input_box.width - padding * 2:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            for i, line in enumerate(lines[-3:]):  # Show last 3 lines max
                text_surface = self.input_font.render(line, True, constants.WHITE)
                self.screen.blit(text_surface, (input_box.x + padding, text_y + i * (self.input_font.get_height() + 2)))
        
        # Draw cursor
        if self.input_active and self.cursor_visible:
            cursor_x = input_box.x + padding
            if text:
                last_line = text.split('\n')[-1] if '\n' in text else text
                words = last_line.split(' ')
                if words:
                    last_word = words[-1]
                    test_surface = self.input_font.render(last_word, True, constants.WHITE)
                    cursor_x += test_surface.get_width()
            cursor_rect = pygame.Rect(cursor_x, text_y, 2, self.input_font.get_height())
            pygame.draw.rect(self.screen, constants.WHITE, cursor_rect)
    
    def _draw_animation(self):
        """Draw current Lexi animation"""
        if not self.animations:
            pygame.draw.rect(self.screen, (255, 0, 0), 
                           (self.animation_position[0], self.animation_position[1], 50, 50))
            return
        
        # Priority 1: State animation
        if self.state_animation and self.state_animation.playing:
            frame = self.state_animation.get_current_frame()
            if frame:
                self.screen.blit(frame, self.animation_position)
            return
        
        # Priority 2: Sticky frame
        if self.sticky_frame:
            self.screen.blit(self.sticky_frame, self.animation_position)
            return
        
        # Priority 3: Neutral animation
        if self.current_state == "neutral":
            neutral_anim = self.animations_by_name.get("lexi_neutral")
            if neutral_anim:
                if not neutral_anim.playing:
                    neutral_anim.loop = True
                    neutral_anim.play()
                
                if neutral_anim.playing:
                    frame = neutral_anim.get_current_frame()
                    if frame:
                        self.screen.blit(frame, self.animation_position)
    
    def set_debug_viewport_mode(self, enabled: bool):
        """Update debug viewport mode flag"""
        self.show_debug_viewport_only = enabled

