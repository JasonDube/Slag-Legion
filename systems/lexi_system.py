"""
Lexi System - Handles all Lexi UI, state management, and animations
Separated from main game logic for better organization
Refactored to use centralized state management and animation loading
"""
import pygame
import os
import sys
import json
from typing import Dict, Optional, List, Tuple

# Add parent directory to path so we can import from modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.lexi_chat import LexiChat
from modules.animation import Animation
from modules.vi_text_editor import ViTextEditor
from core import constants
from systems.lexi_state_manager import LexiStateManager
from systems.lexi_animation_loader import LexiAnimationLoader


class LexiSystem:
    """Manages all Lexi-related functionality: UI, animations, and state"""
    
    def __init__(self, screen: pygame.Surface, lexi_chat: LexiChat, 
                 state_manager: LexiStateManager, animation_loader: LexiAnimationLoader,
                 show_debug_viewport_only: bool = False):
        self.screen = screen
        self.lexi_chat = lexi_chat
        self.state_manager = state_manager
        self.animation_loader = animation_loader
        self.show_debug_viewport_only = show_debug_viewport_only
        
        # UI state
        self.input_active = False
        self.chat_font = pygame.font.Font(None, 18)
        self.input_font = pygame.font.Font(None, 14)  # Smaller font size
        self.cursor_timer = 0
        self.cursor_visible = True
        
        # Vi-like text editor
        self.vi_editor: Optional[ViTextEditor] = None
        self.chat_scroll_offset = 0
        self.scrollbar_dragging = False
        self.user_has_scrolled = False
        self.last_message_count = 0
        
        # Animation system
        self.animation_position = (1046, 22)
        self.animations_by_name = {}
        self.sticky_frame = None
        
        # State system (for UI rendering)
        self.state_animation = None
        self.state_animation_name = None
        self.animation_configs = {}
        
        # Subscribe to state changes
        self.state_manager.subscribe_state_change(self._on_state_change)
        
        # Load animations for right panel
        self.animations_by_name = self.animation_loader.load_animations_for_location("right_panel")
        
        # Start with neutral animation
        neutral_anim = self.animations_by_name.get("lexi_neutral")
        if neutral_anim:
            neutral_anim.loop = True
            neutral_anim.play()
            print(f"✓ Lexi right panel initialized with {len(self.animations_by_name)} animations")
        else:
            print("Warning: No neutral animation found for right panel")
        
        # Monitor chat for emotion updates
        self.last_emotion_index = -1
        
        # Check Ollama connection
        if not self.lexi_chat.client.check_connection():
            print("Warning: Ollama server not running. Lexi chat will not work.")
            print(f"Make sure Ollama is running at {self.lexi_chat.client.base_url}")
        else:
            print("✓ Lexi chat system initialized")
    
    def _on_state_change(self, emotion: str, pose: str):
        """React to state changes from central manager"""
        # Update animation based on emotion
        animation = self.animation_loader.get_animation("right_panel", emotion, pose)
        
        if animation and animation.name != self.state_animation_name:
            # Stop current state animation
            if self.state_animation:
                self.state_animation.stop()
            
            # Start new animation
            animation.loop = False
            animation.play()
            self.state_animation = animation
            self.state_animation_name = animation.name
            
            # Load config for sticky frame if available
            animation_path = f"animations/right/{animation.name}"
            self.animation_configs[animation.name] = self.animation_loader._load_animation_config(
                os.path.join(animation_path, "animation_config.json")
            )
            
            print(f"LexiSystem: Animation changed to {animation.name} (emotion: {emotion})")
    
    
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
                # Initialize vi editor if needed
                if self.vi_editor is None:
                    self.vi_editor = ViTextEditor(
                        self.input_font,
                        LexiChat.INPUT_BOX_WIDTH,
                        LexiChat.INPUT_BOX_HEIGHT,
                        padding=5
                    )
                    self.vi_editor.set_text(self.lexi_chat.input_text)
                    # Set command callback for :send and :help
                    self.vi_editor.set_command_callback(self._handle_vi_command)
                
                # Handle Ctrl+Enter to send message
                mods = pygame.key.get_mods()
                if event.key == pygame.K_RETURN and (mods & pygame.KMOD_CTRL):
                    # Ctrl+Enter sends message regardless of mode
                    text = self.vi_editor.get_text()
                    if text.strip():
                        self.lexi_chat.send_message(
                            text,
                            on_chunk=lambda text: None
                        )
                        self.lexi_chat.input_text = ""
                        self.vi_editor.set_text("")
                        self.chat_scroll_offset = 999999
                        self.user_has_scrolled = False
                    return True
                
                # Let vi editor handle the key (including regular Enter for new lines)
                handled = self.vi_editor.handle_key(event)
                
                # Update lexi_chat.input_text to match vi editor
                self.lexi_chat.input_text = self.vi_editor.get_text()
                
                return handled
        
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
                    # Initialize vi editor when clicking input box
                    if self.vi_editor is None:
                        self.vi_editor = ViTextEditor(
                            self.input_font,
                            LexiChat.INPUT_BOX_WIDTH,
                            LexiChat.INPUT_BOX_HEIGHT,
                            padding=5
                        )
                        self.vi_editor.set_text(self.lexi_chat.input_text)
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
            self.chat_scroll_offset = max(0, self.chat_scroll_offset - event.y * 10)
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
        
        # Monitor chat for new emotions and update state manager
        if self.lexi_chat.message_emotions:
            latest_emotion_index = max(self.lexi_chat.message_emotions.keys())
            if latest_emotion_index > self.last_emotion_index:
                latest_emotion = self.lexi_chat.message_emotions.get(latest_emotion_index)
                if latest_emotion:
                    self.state_manager.update_emotion(latest_emotion, source="chat")
                self.last_emotion_index = latest_emotion_index
        
        # Update state animation if playing
        if self.state_animation and self.state_animation.playing:
            self.state_animation.update(dt)
            
            if self.state_animation.finished:
                state_config = self.animation_configs.get(self.state_animation_name, {})
                current_emotion = self.state_manager.current_emotion
                
                if current_emotion == "neutral":
                    self.state_animation = None
                    self.state_animation_name = None
                    self.sticky_frame = None
                    neutral_anim = self.animations_by_name.get("lexi_neutral")
                    if neutral_anim:
                        neutral_anim.loop = True
                        neutral_anim.play()
                    print("Returned to neutral, resuming animation cycling")
                else:
                    if 'sticky_frame_surface' in state_config:
                        self.sticky_frame = state_config['sticky_frame_surface']
                        self.state_animation.stop()
                        print(f"State animation finished, showing sticky frame for {current_emotion}")
                    else:
                        last_frame = self.state_animation.get_current_frame()
                        if last_frame:
                            self.sticky_frame = last_frame
                            self.state_animation.stop()
                            print(f"State animation finished, using last frame for {current_emotion}")
        
        # Update default neutral animation if no state animation
        has_active_state = (self.state_animation is not None and 
                           (self.state_animation.playing or self.sticky_frame is not None))
        
        if not has_active_state:
            if self.state_manager.current_emotion == "neutral":
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
    
    def _handle_vi_command(self, command: str, args):
        """Handle commands from vi editor command mode"""
        if command == "send":
            # Send message to Lexi
            text = args if isinstance(args, str) else self.vi_editor.get_text()
            if text.strip():
                self.lexi_chat.send_message(
                    text,
                    on_chunk=lambda text: None
                )
                self.lexi_chat.input_text = ""
                self.vi_editor.set_text("")
                self.chat_scroll_offset = 999999
                self.user_has_scrolled = False
        elif command == "help":
            # Show help message (print to console for now)
            help_text = """
Vi Editor Commands:
  :send          - Send message to Lexi
  :help          - Show this help message
  :clear         - Clear input buffer (coming soon)
  
Navigation (Normal Mode):
  h, j, k, l     - Move left, down, up, right
  Arrow keys     - Move cursor
  0, $           - Start/end of line
  
Insert Mode:
  i              - Enter insert mode at cursor
  a              - Append after cursor
  A              - Append to end of line
  o, O           - Open new line below/above
  Esc            - Exit insert mode
  
Editing:
  x              - Delete character under cursor
  dd             - Delete current line
  Backspace      - Delete before cursor (insert mode)
  
Other:
  Ctrl+Enter     - Send message to Lexi
  Esc            - Exit insert/command mode
  :              - Enter command mode
            """
            print(help_text)
    
    def _draw_input(self):
        """Draw Lexi input box with vi-like editor"""
        input_box = pygame.Rect(
            LexiChat.INPUT_BOX_X,
            LexiChat.INPUT_BOX_Y,
            LexiChat.INPUT_BOX_WIDTH,
            LexiChat.INPUT_BOX_HEIGHT
        )
        
        input_bg_color = constants.BLACK  # Black fill color
        pygame.draw.rect(self.screen, input_bg_color, input_box)
        pygame.draw.rect(self.screen, (53, 62, 78), input_box, 2)  # Outline color
        
        padding = 5
        text_y = input_box.y + padding
        
        # Use vi editor if available, otherwise fall back to old system
        if self.vi_editor is not None:
            # Draw visible lines from vi editor
            visible_lines = self.vi_editor.get_visible_lines()
            line_height = self.input_font.get_height() + 1
            
            for i, (line_idx, line_text) in enumerate(visible_lines):
                line_surface = self.input_font.render(line_text, True, constants.WHITE)
                self.screen.blit(line_surface, (input_box.x + padding, text_y + i * line_height))
            
            # Draw cursor at vi editor position (only in insert/normal mode, not command mode)
            if self.input_active and self.cursor_visible and self.vi_editor.mode != 'command':
                cursor_x, cursor_y = self.vi_editor.get_cursor_screen_pos(
                    input_box.x, input_box.y
                )
                cursor_width = 6
                cursor_height = 12
                cursor_rect = pygame.Rect(cursor_x, cursor_y, cursor_width, cursor_height)
                pygame.draw.rect(self.screen, constants.WHITE, cursor_rect)
            
            # Draw mode indicator or command prompt
            if self.vi_editor.mode == 'command':
                # Draw command prompt at bottom of input box
                command_text = f":{self.vi_editor.get_command_buffer()}"
                if self.cursor_visible:  # Blinking cursor in command mode
                    command_text += "_"
                command_surface = self.input_font.render(command_text, True, constants.WHITE)
                cmd_y = input_box.bottom - command_surface.get_height() - padding
                self.screen.blit(command_surface, (input_box.x + padding, cmd_y))
            else:
                # Draw mode indicator (INSERT mode)
                mode_text = self.vi_editor.get_mode_display()
                if mode_text:
                    mode_surface = self.input_font.render(mode_text, True, (100, 100, 100))
                    mode_x = input_box.right - mode_surface.get_width() - padding
                    mode_y = input_box.bottom - mode_surface.get_height() - padding
                    self.screen.blit(mode_surface, (mode_x, mode_y))
            
            # Draw command prompt at bottom if in command mode
            if self.vi_editor.mode == 'command':
                command_text = f":{self.vi_editor.get_command_buffer()}_"
                command_surface = self.input_font.render(command_text, True, constants.WHITE)
                # Draw at bottom of input box
                cmd_y = input_box.bottom - command_surface.get_height() - padding
                self.screen.blit(command_surface, (input_box.x + padding, cmd_y))
        else:
            # Fallback to old system if vi editor not initialized
            text = self.lexi_chat.input_text
            if text:
                line_surface = self.input_font.render(text, True, constants.WHITE)
                self.screen.blit(line_surface, (input_box.x + padding, text_y))
            
            # Simple cursor
            if self.input_active and self.cursor_visible:
                text_width = 0
                if text:
                    text_surface = self.input_font.render(text, True, constants.WHITE)
                    text_width = text_surface.get_width()
                cursor_x = input_box.x + padding + text_width
                cursor_y = input_box.y + padding
                cursor_rect = pygame.Rect(cursor_x, cursor_y, 6, 12)
                pygame.draw.rect(self.screen, constants.WHITE, cursor_rect)
    
    def _draw_animation(self):
        """Draw current Lexi animation"""
        if not self.animations_by_name:
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
        if self.state_manager.current_emotion == "neutral":
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

