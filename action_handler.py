"""Action handler system"""
import pygame
from typing import Dict, Callable, Optional
from interactive import InteractiveElement
from room import Room
from region_content import RegionContent


class ActionHandler:
    """Handles actions triggered by interactive elements"""
    
    def __init__(self, player_location: Dict, rooms: Dict[str, Room], region_content: RegionContent):
        self.player_location = player_location
        self.rooms = rooms
        self.region_content = region_content
        self.event_handlers: Dict[str, Callable] = {}  # Custom event handlers
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """Register a custom event handler"""
        self.event_handlers[event_name] = handler
    
    def handle_action(self, element: InteractiveElement):
        """Handle an action from an interactive element"""
        action_type = element.action_type
        action_data = element.action_data
        
        if action_type == 'room_transition':
            self._handle_room_transition(action_data)
        elif action_type == 'show_screen':
            self._handle_show_screen(action_data)
        elif action_type == 'update_info':
            self._handle_update_info(action_data)
        elif action_type == 'trigger_animation':
            self._handle_trigger_animation(action_data)
        elif action_type == 'trigger_sprite_animation':
            self._handle_trigger_sprite_animation(action_data)
        elif action_type == 'trigger_event':
            self._handle_trigger_event(action_data)
        elif action_type == 'custom':
            self._handle_custom_action(action_data)
    
    def _handle_room_transition(self, action_data: Dict):
        """Handle room transition action"""
        destination = action_data.get('destination')
        if destination:
            self.player_location['ship_room'] = destination
            # Start default animation for the new room
            if destination in self.rooms:
                self.rooms[destination].start_default_animation()
            print(f"Player moved to: {self.player_location['ship_name']} - {destination}")
    
    def _handle_show_screen(self, action_data: Dict):
        """Handle show screen action"""
        region = action_data.get('target_region')
        screen_path = action_data.get('screen_path')
        if region and screen_path:
            try:
                screen_img = pygame.image.load(screen_path).convert_alpha()
                self.region_content.set_screen(region, screen_img)
                print(f"Showing screen in {region}")
            except Exception as e:
                print(f"Error loading screen: {e}")
    
    def _handle_update_info(self, action_data: Dict):
        """Handle update info action"""
        region = action_data.get('target_region')
        info_text = action_data.get('info_text')
        if region and info_text:
            self.region_content.set_info(region, info_text)
            print(f"Updated info in {region}")
    
    def _handle_trigger_animation(self, action_data: Dict):
        """Handle trigger animation action"""
        room_name = self.player_location.get('ship_room')
        animation_name = action_data.get('animation_name')
        if room_name in self.rooms and animation_name:
            room = self.rooms[room_name]
            if animation_name in room.animations:
                room.animations[animation_name].play()
                print(f"Triggered animation: {animation_name}")
    
    def _handle_trigger_sprite_animation(self, action_data: Dict):
        """Handle trigger sprite animation action"""
        room_name = self.player_location.get('ship_room')
        sprite_name = action_data.get('sprite_name')
        animation_name = action_data.get('animation_name')
        if room_name in self.rooms:
            room = self.rooms[room_name]
            for sprite in room.sprites:
                if sprite.name == sprite_name:
                    sprite.play_animation(animation_name)
                    print(f"Triggered sprite animation: {sprite_name} - {animation_name}")
    
    def _handle_trigger_event(self, action_data: Dict):
        """Handle trigger event action"""
        event_name = action_data.get('event_name')
        if event_name in self.event_handlers:
            self.event_handlers[event_name](action_data)
    
    def _handle_custom_action(self, action_data: Dict):
        """Handle custom action"""
        handler = action_data.get('handler')
        if handler and callable(handler):
            handler(action_data)

