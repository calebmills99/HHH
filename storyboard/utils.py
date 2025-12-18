"""
Utility functions for generating storyboard panels from text descriptions.
"""
import re
from .models import StoryboardPanel


def generate_storyboard_panels(storyboard):
    """
    Generate storyboard panels from the text description.
    
    This function analyzes the text description and breaks it down into
    logical panels/scenes. Each panel represents a key moment or shot.
    
    Args:
        storyboard: The Storyboard model instance
    
    Returns:
        List of created StoryboardPanel instances
    """
    description = storyboard.description
    
    # Split description into sentences
    sentences = re.split(r'[.!?]+', description)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Group sentences into logical panels (max 2-3 sentences per panel)
    panels = []
    current_panel = []
    
    for sentence in sentences:
        current_panel.append(sentence)
        
        # Create a panel every 2 sentences or if we detect a scene change
        if len(current_panel) >= 2 or _is_scene_change(sentence):
            panels.append(' '.join(current_panel) + '.')
            current_panel = []
    
    # Add any remaining sentences as the final panel
    if current_panel:
        panels.append(' '.join(current_panel) + '.')
    
    # Create StoryboardPanel instances
    created_panels = []
    for i, panel_desc in enumerate(panels, start=1):
        panel = StoryboardPanel.objects.create(
            storyboard=storyboard,
            panel_number=i,
            description=panel_desc,
            notes=_generate_panel_notes(panel_desc)
        )
        created_panels.append(panel)
    
    return created_panels


def _is_scene_change(sentence):
    """
    Detect if a sentence indicates a scene change.
    
    Args:
        sentence: The sentence to analyze
    
    Returns:
        Boolean indicating if this is likely a scene change
    """
    scene_indicators = [
        'meanwhile', 'later', 'suddenly', 'then', 'next',
        'cut to', 'fade to', 'transition', 'elsewhere',
        'back to', 'hours later', 'days later', 'the next'
    ]
    
    sentence_lower = sentence.lower()
    return any(indicator in sentence_lower for indicator in scene_indicators)


def _generate_panel_notes(description):
    """
    Generate directional notes for a panel based on its description.
    
    Args:
        description: The panel description text
    
    Returns:
        String with suggested camera angles, shots, or directions
    """
    notes = []
    desc_lower = description.lower()
    
    # Detect action words and suggest appropriate shots
    if any(word in desc_lower for word in ['runs', 'chases', 'fights', 'action']):
        notes.append("Dynamic shot with motion")
    
    if any(word in desc_lower for word in ['looks', 'sees', 'watches', 'observes']):
        notes.append("POV or close-up on eyes/face")
    
    if any(word in desc_lower for word in ['speaks', 'says', 'tells', 'whispers', 'shouts']):
        notes.append("Close-up or medium shot for dialogue")
    
    if any(word in desc_lower for word in ['enters', 'arrives', 'walks in']):
        notes.append("Establishing shot or wide angle")
    
    # Default note if nothing specific was detected
    if not notes:
        notes.append("Standard shot - adjust as needed")
    
    return ' | '.join(notes)
