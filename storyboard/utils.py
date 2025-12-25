"""
Utility functions for generating storyboard panels from text descriptions.
"""
import re
import os
import base64
import requests
from django.core.files.base import ContentFile
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
        
        # Generate image for the panel
        _generate_panel_image(panel, panel_desc)
    
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


def _generate_panel_image(panel, description):
    """
    Generate an image for a storyboard panel using Stability AI API.
    
    Args:
        panel: The StoryboardPanel model instance
        description: The panel description text
    
    Returns:
        Boolean indicating success or failure
    """
    # Get API key from environment variable
    api_key = os.environ.get('STABILITY_API_KEY')
    
    if not api_key:
        print("Warning: STABILITY_API_KEY not found in environment variables. Skipping image generation.")
        return False
    
    # Enhance the description with storyboard-specific artistic direction
    prompt = f"Cinematic storyboard sketch, black and white pencil drawing, {description}, professional film storyboard style, clear composition, dramatic lighting"
    
    # API endpoint
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    
    # API headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # API request body
    body = {
        "text_prompts": [
            {
                "text": prompt,
                "weight": 1
            },
            {
                "text": "blurry, bad anatomy, text, watermarks, signatures, low quality, color, colored",
                "weight": -1
            }
        ],
        "cfg_scale": 7,
        "height": 768,
        "width": 1344,
        "samples": 1,
        "steps": 30
    }
    
    try:
        # Make API request
        response = requests.post(url, headers=headers, json=body, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract the base64 image from the response
            if data.get('artifacts') and len(data['artifacts']) > 0:
                image_data = data['artifacts'][0].get('base64')
                
                if image_data:
                    # Decode base64 image
                    image_content = base64.b64decode(image_data)
                    
                    # Save image to the panel's image field
                    filename = f"panel_{panel.id}.png"
                    panel.image.save(filename, ContentFile(image_content), save=True)
                    
                    print(f"Successfully generated image for panel {panel.id}")
                    return True
                else:
                    print(f"Error: No image data in API response for panel {panel.id}")
                    return False
            else:
                print(f"Error: No artifacts in API response for panel {panel.id}")
                return False
        else:
            print(f"Error generating image for panel {panel.id}: API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"Error: API request timed out for panel {panel.id}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error generating image for panel {panel.id}: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error generating image for panel {panel.id}: {str(e)}")
        return False
