from django.test import TestCase
from unittest.mock import patch, Mock
import os
import requests
from .models import Storyboard, StoryboardPanel
from .utils import generate_storyboard_panels, _generate_panel_image


# Test base64 image (1x1 transparent PNG)
TEST_BASE64_IMAGE = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='


class StoryboardPanelGenerationTestCase(TestCase):
    """Test storyboard panel generation with image generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.storyboard = Storyboard.objects.create(
            title="Test Storyboard",
            description="A detective enters a dimly lit office. He looks around suspiciously. Suddenly, a shadow moves behind the curtain."
        )
    
    def test_panels_generated_without_api_key(self):
        """Test that panels are created even without Stability AI API key."""
        # Ensure no API key is set
        with patch.dict(os.environ, {}, clear=True):
            panels = generate_storyboard_panels(self.storyboard)
            
            # Verify panels were created
            self.assertGreater(len(panels), 0)
            
            # Verify panel content
            for panel in panels:
                self.assertIsNotNone(panel.description)
                self.assertIsNotNone(panel.notes)
                self.assertIsNone(panel.image.name)  # No image should be generated
    
    def test_panels_generated_with_api_key_success(self):
        """Test successful image generation with valid API key."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'artifacts': [
                {
                    'base64': TEST_BASE64_IMAGE
                }
            ]
        }
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            with patch('storyboard.utils.requests.post', return_value=mock_response) as mock_post:
                panels = generate_storyboard_panels(self.storyboard)
                
                # Verify panels were created
                self.assertGreater(len(panels), 0)
                
                # Verify API was called for each panel
                self.assertEqual(mock_post.call_count, len(panels))
                
                # Verify images were saved
                for panel in panels:
                    self.assertIsNotNone(panel.image.name)
    
    def test_image_generation_api_failure(self):
        """Test graceful handling of API failures."""
        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        panel = StoryboardPanel.objects.create(
            storyboard=self.storyboard,
            panel_number=1,
            description="Test panel"
        )
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            with patch('storyboard.utils.requests.post', return_value=mock_response):
                result = _generate_panel_image(panel, "Test panel")
                
                # Should return False on failure
                self.assertFalse(result)
                
                # Panel should still exist without an image
                self.assertIsNone(panel.image.name)
    
    def test_image_generation_no_api_key(self):
        """Test that image generation is skipped when API key is missing."""
        panel = StoryboardPanel.objects.create(
            storyboard=self.storyboard,
            panel_number=1,
            description="Test panel"
        )
        
        with patch.dict(os.environ, {}, clear=True):
            result = _generate_panel_image(panel, "Test panel")
            
            # Should return False when no API key
            self.assertFalse(result)
            
            # No image should be generated
            self.assertIsNone(panel.image.name)
    
    def test_panel_description_enhancement(self):
        """Test that panel descriptions are enhanced with artistic direction."""
        panel = StoryboardPanel.objects.create(
            storyboard=self.storyboard,
            panel_number=1,
            description="A detective enters the room"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'artifacts': [
                {
                    'base64': TEST_BASE64_IMAGE
                }
            ]
        }
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            with patch('storyboard.utils.requests.post', return_value=mock_response) as mock_post:
                _generate_panel_image(panel, panel.description)
                
                # Verify API was called
                self.assertTrue(mock_post.called)
                
                # Verify the prompt includes artistic direction
                call_args = mock_post.call_args
                request_body = call_args[1]['json']
                prompt = request_body['text_prompts'][0]['text']
                
                self.assertIn('Cinematic storyboard sketch', prompt)
                self.assertIn('black and white pencil drawing', prompt)
                self.assertIn('professional film storyboard style', prompt)
    
    def test_image_generation_timeout(self):
        """Test that timeout scenario is handled correctly."""
        panel = StoryboardPanel.objects.create(
            storyboard=self.storyboard,
            panel_number=1,
            description="Test panel"
        )
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            with patch('storyboard.utils.requests.post', side_effect=requests.exceptions.Timeout):
                result = _generate_panel_image(panel, "Test panel")
                
                # Should return False on timeout
                self.assertFalse(result)
                
                # Panel should still exist without an image
                self.assertIsNone(panel.image.name)
