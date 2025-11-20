"""Room configuration data"""
import pygame
from typing import List, Dict, TYPE_CHECKING
from core import constants

if TYPE_CHECKING:
    from modules.room import Room


def create_room_with_transition(room_name: str, image_path: str, position: tuple, 
                                 transitions: List[Dict]) -> 'Room':
    """
    Helper function to create a room with transition elements.
    
    Args:
        room_name: Name of the room
        image_path: Path to the room background image
        position: (x, y) position to draw the room image
        transitions: List of dicts with keys:
            - 'rect' (pygame.Rect) or 'polygon' (List[tuple]): Shape definition
            - 'destination' (str): Destination room name
            - 'shape_type' (str, optional): 'rect' or 'polygon' (defaults to 'rect' if 'rect' key exists, 'polygon' if 'polygon' key exists)
    
    Returns:
        Room object with transitions configured
    """
    from modules.room import Room
    from modules.interactive import InteractiveElement
    
    room = Room(room_name, image_path, position)
    
    for transition in transitions:
        if 'polygon' in transition:
            # Polygon transition
            room.add_interactive_element(
                InteractiveElement(
                    transition['polygon'],
                    'room_transition',
                    shape_type='polygon',
                    destination=transition['destination']
                )
            )
        elif 'rect' in transition:
            # Rectangle transition
            room.add_interactive_element(
                InteractiveElement(
                    transition['rect'],
                    'room_transition',
                    shape_type='rect',
                    destination=transition['destination']
                )
            )
    
    return room


# Room definitions - data-driven approach
ROOM_DEFINITIONS = [
    {
        'name': 'Control Room',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_control_room_00001.png',
        'transitions': [
            {'rect': pygame.Rect(421, 551, 456, 26), 'destination': 'Hall 1'}
        ]
    },
    {
        'name': 'Hall 1',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_hall_1_00001.png',
        'transitions': [
            {'rect': pygame.Rect(508, 552, 291, 30), 'destination': 'Control Room'},
            {'polygon': [(815, 266), (854, 259), (852, 480), (821, 463)], 'destination': 'Airlock'},
            {'rect': pygame.Rect(616, 295, 68, 125), 'destination': 'Hall 2'}
        ]
    },
    {
        'name': 'Hall 2',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_hall_2_00001.png',
        'transitions': [
            {'rect': pygame.Rect(448, 562, 383, 18), 'destination': 'Hall 1'},
            {'rect': pygame.Rect(523, 224, 42, 212), 'destination': 'Hall 3'},
            {'rect': pygame.Rect(759, 288, 88, 107), 'destination': 'Cargo Room'}
        ]
    },
    {
        'name': 'Hall 3',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_hall_3_00001.png',
        'transitions': [
            {'polygon': [(492, 278), (515, 295), (514, 454), (497, 472)], 'destination': 'Android Charging Bay'},
            {'polygon': [(556, 310), (561, 315), (562, 418), (555, 422)], 'destination': "Captain's Quarters"},
            {'rect': pygame.Rect(619, 319, 68, 75), 'destination': 'Greenhouse'},
            {'rect': pygame.Rect(442, 550, 403, 35), 'destination': 'Hall 2'},
            {'polygon': [(770, 301), (803, 292), (804, 478), (775, 458)], 'destination': 'Mess Hall'}
        ]
    },
    {
        'name': 'Cargo Room',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_cargo_room_1_00001.png',
        'transitions': [
            {'polygon': [(514, 305), (541, 314), (540, 399), (516, 417)], 'destination': 'Engine Room'},
            {'rect': pygame.Rect(442, 548, 418, 39), 'destination': 'Hall 2'}
        ]
    },
    {
        'name': "Captain's Quarters",
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_captains_quarters_00001.png',
        'transitions': [
            {'rect': pygame.Rect(440, 543, 428, 38), 'destination': 'Hall 3'}
        ]
    },
    {
        'name': 'Android Charging Bay',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_android_charging_bay_00001.png',
        'transitions': [
            {'polygon': [(775, 176), (857, 176), (832, 400), (767, 368)], 'destination': 'Hall 3'}
        ]
    },
    {
        'name': 'Greenhouse',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_greenhouse_00001.png',
        'transitions': [
            {'rect': pygame.Rect(433, 547, 438, 36), 'destination': 'Hall 3'}
        ]
    },
    {
        'name': 'Mess Hall',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_mess_hall_00001.png',
        'transitions': [
            {'rect': pygame.Rect(421, 548, 455, 35), 'destination': 'Hall 3'}
        ]
    },
    {
        'name': 'Engine Room',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_engine_room_00001.png',
        'transitions': [
            {'rect': pygame.Rect(413, 569, 470, 19), 'destination': 'Cargo Room'}
        ]
    },
    {
        'name': 'Airlock',
        'image': f'{constants.ROOM_IMAGE_PATH}dagger_airlock_00001.png',
        'transitions': [
            {'rect': pygame.Rect(500, 558, 312, 24), 'destination': 'Hall 1'}
        ]
    },
]


def load_rooms() -> Dict[str, 'Room']:
    """Load all rooms from configuration"""
    from typing import Dict
    from modules.room import Room
    
    rooms: Dict[str, Room] = {}
    
    for room_def in ROOM_DEFINITIONS:
        room = create_room_with_transition(
            room_def['name'],
            room_def['image'],
            constants.ROOM_IMAGE_POSITION,
            room_def['transitions']
        )
        rooms[room_def['name']] = room
    
    return rooms

