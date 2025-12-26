"""
Utility functions for generating storyboard panels from text descriptions.
"""
import re
import os
import base64
import json
import logging
import requests
from django.core.files.base import ContentFile
from .models import StoryboardPanel


logger = logging.getLogger(__name__)

# Stability AI API Configuration
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
STABILITY_CFG_SCALE = 7
STABILITY_HEIGHT = 768
STABILITY_WIDTH = 1344
STABILITY_SAMPLES = 1
STABILITY_STEPS = 30
STABILITY_TIMEOUT = 60

# Prompt templates
PROMPT_TEMPLATE = "Cinematic storyboard sketch, black and white pencil drawing, {description}, professional film storyboard style, clear composition, dramatic lighting"
NEGATIVE_PROMPT = "blurry, bad anatomy, text, watermarks, signatures, low quality, color, colored"

# Sanitization and logging limits
MAX_DESCRIPTION_LENGTH = 500
MAX_LOG_LENGTH = 500


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
        # NOTE: Image generation is performed synchronously for each panel.
        # For storyboards with multiple panels, this could result in long request times
        # (e.g., 5 panels = up to 5 minutes worst case with 60-second timeout per panel).
        # Consider implementing asynchronous task processing (e.g., using Celery) or
        # providing user feedback that image generation is in progress.
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


def _sanitize_description(description):
    """
    Sanitize panel description to prevent prompt injection attacks.
    
    Args:
        description: The raw panel description text
    
    Returns:
        Sanitized description limited to safe characters and length
    """
    # Limit length to prevent excessively long prompts
    sanitized = description[:MAX_DESCRIPTION_LENGTH] if len(description) > MAX_DESCRIPTION_LENGTH else description
    
    # Remove potentially problematic characters that could manipulate prompts
    # Keep alphanumeric, spaces, and common punctuation used in narrative descriptions
    sanitized = re.sub(r'[^\w\s.,!?\-():\"\']', '', sanitized)
    
    return sanitized.strip()


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
        logger.warning("STABILITY_API_KEY not found in environment variables. Skipping image generation.")
        return False
    
    # Sanitize the description to prevent prompt injection
    safe_description = _sanitize_description(description)
    
    # Enhance the description with storyboard-specific artistic direction
    prompt = PROMPT_TEMPLATE.format(description=safe_description)
    
    # API endpoint
    url = STABILITY_API_URL
    
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
                "text": NEGATIVE_PROMPT,
                "weight": -1
            }
        ],
        "cfg_scale": STABILITY_CFG_SCALE,
        "height": STABILITY_HEIGHT,
        "width": STABILITY_WIDTH,
        "samples": STABILITY_SAMPLES,
        "steps": STABILITY_STEPS
    }
    
    try:
        # Make API request
        response = requests.post(url, headers=headers, json=body, timeout=STABILITY_TIMEOUT)
        
        if response.status_code == 200:
            try:
                data = response.json()
            except json.JSONDecodeError as json_error:
                logger.error(f"Failed to parse JSON response for panel {panel.id}: {str(json_error)}")
                return False
            
            # Extract the base64 image from the response
            if data.get('artifacts') and len(data['artifacts']) > 0:
                image_data = data['artifacts'][0].get('base64')
                
                if image_data:
                    # Decode base64 image
                    image_content = base64.b64decode(image_data)
                    
                    # Save image to the panel's image field
                    filename = f"panel_{panel.id}.png"
                    panel.image.save(filename, ContentFile(image_content), save=True)
                    
                    logger.info(f"Successfully generated image for panel {panel.id}")
                    return True
                else:
                    logger.error(f"No image data in API response for panel {panel.id}")
                    return False
            else:
                logger.error(f"No artifacts in API response for panel {panel.id}")
                return False
        else:
            # Log additional response details to aid debugging, while avoiding overly large log entries
            response_details = None
            try:
                # Try to extract a useful error message from JSON, if available
                error_json = response.json()
                if isinstance(error_json, dict):
                    # Common fields used by APIs for error messages
                    response_details = error_json.get("error") or error_json.get("message") or str(error_json)
                else:
                    response_details = str(error_json)
            except json.JSONDecodeError:
                # Fallback to text content if response is not JSON
                response_details = response.text
            # Truncate response details to avoid logging excessively large payloads
            if response_details is not None:
                if len(response_details) > MAX_LOG_LENGTH:
                    response_details = response_details[:MAX_LOG_LENGTH] + " ...[truncated]"
            logger.error(
                f"Image generation failed for panel {panel.id}: "
                f"API returned status {response.status_code}"
                f"{' with response: ' + response_details if response_details else ''}"
            )
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"API request timed out for panel {panel.id}")
        return False
    except requests.exceptions.RequestException:
        logger.error(f"Error generating image for panel {panel.id}")
        return False
    except Exception:
        logger.exception(f"Unexpected error generating image for panel {panel.id}")
        return False
