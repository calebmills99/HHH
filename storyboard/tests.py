from django.test import TestCase
from unittest.mock import patch, Mock
import os
from .models import Storyboard, StoryboardPanel
from .utils import generate_storyboard_panels, generate_panel_image


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
                self.assertIsNotNone(panel.image_prompt)
                self.assertFalse(panel.prompt_approved)
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
            with patch('requests.post', return_value=mock_response) as mock_post:
                panels = generate_storyboard_panels(self.storyboard)
                self.assertGreater(len(panels), 0)

                # Capture prompts before any image generation
                original_prompts = [panel.image_prompt for panel in panels]

                # Approve only the first panel
                first_panel = panels[0]
                first_panel.prompt_approved = True
                first_panel.save(update_fields=['prompt_approved'])

                # Generate image for the approved panel
                result = generate_panel_image(first_panel)

                # First (approved) panel: image generated, approval maintained, prompt unchanged
                first_panel.refresh_from_db()
                self.assertTrue(first_panel.prompt_approved)
                self.assertIsNotNone(first_panel.image.name)
                self.assertEqual(first_panel.image_prompt, original_prompts[0])
                self.assertTrue(result)

                # Non-approved panels: remain unapproved, no image, prompt unchanged
                for index, panel in enumerate(panels[1:], start=1):
                    panel.refresh_from_db()
                    self.assertFalse(panel.prompt_approved)
                    self.assertFalse(panel.image.name)  # Empty string or None evaluates to False
                    self.assertEqual(panel.image_prompt, original_prompts[index])

                # Stability API is called exactly once and uses the stored prompt
                mock_post.assert_called_once()
                _, kwargs = mock_post.call_args
                payload = kwargs.get("json") or {}
                text_prompts = payload.get("text_prompts") or []
                if text_prompts:
                    used_prompt = text_prompts[0].get("text")
                    self.assertEqual(used_prompt, first_panel.image_prompt)
    
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
            with patch('requests.post', return_value=mock_response):
                panel.prompt_approved = True
                panel.save(update_fields=['prompt_approved'])
                result = generate_panel_image(panel)
                
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
            panel.prompt_approved = True
            panel.save(update_fields=['prompt_approved'])
            result = generate_panel_image(panel)
            
            # Should return False when no API key
            self.assertFalse(result)
            
            # No image should be generated
            self.assertIsNone(panel.image.name)

    def test_image_generation_requires_approval(self):
        """Test that images are not generated until prompt is approved."""
        panel = StoryboardPanel.objects.create(
            storyboard=self.storyboard,
            panel_number=1,
            description="Test panel"
        )
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            result = generate_panel_image(panel)
            self.assertFalse(result)
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
            with patch('requests.post', return_value=mock_response) as mock_post:
                panel.prompt_approved = True
                panel.save(update_fields=['prompt_approved'])
                generate_panel_image(panel)
                
                # Verify API was called
                self.assertTrue(mock_post.called)
                
                # Verify the prompt includes artistic direction
                call_args = mock_post.call_args
                request_body = call_args[1]['json']
                prompt = request_body['text_prompts'][0]['text']
                
                self.assertIn('Cinematic storyboard sketch', prompt)
                self.assertIn('black and white pencil drawing', prompt)
                self.assertIn('professional film storyboard style', prompt)
    
    def test_build_image_prompt_basic_and_edge_cases(self):
        """
        build_image_prompt(description):
        - includes the description text in the final prompt
        - returns a non-empty string for empty descriptions
        - is robust for very long descriptions
        """
        from .utils import build_image_prompt
        
        # Basic prompt includes description
        description = "A cat sitting on a red sofa, cinematic lighting"
        prompt = build_image_prompt(description)
        self.assertIsInstance(prompt, str)
        self.assertNotEqual(prompt.strip(), "")
        self.assertIn(description, prompt)

        # Empty description still yields a usable prompt
        empty_prompt = build_image_prompt("")
        self.assertIsInstance(empty_prompt, str)
        self.assertNotEqual(empty_prompt.strip(), "")

        # Very long description should not explode and should preserve leading text
        long_description = "x" * 2000
        long_prompt = build_image_prompt(long_description)
        self.assertIsInstance(long_prompt, str)
        self.assertNotEqual(long_prompt.strip(), "")
        self.assertIn(long_description[:50], long_prompt)


class StoryboardViewTestCase(TestCase):
    """Test storyboard view functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.storyboard = Storyboard.objects.create(
            title="Test Storyboard",
            description="A detective enters a dimly lit office."
        )
        self.panel = StoryboardPanel.objects.create(
            storyboard=self.storyboard,
            panel_number=1,
            description="Panel for testing",
            notes="",
            image_prompt="",
            prompt_approved=False,
        )
    
    def test_generate_panel_image_view_missing_api_key_shows_error(self):
        """
        generate_panel_image_view should refuse to run without STABILITY_API_KEY
        and show a user-facing error message.
        """
        from django.urls import reverse
        from django.contrib.messages import get_messages
        
        with patch.dict(os.environ, {}, clear=True):
            url = reverse("storyboard:generate_panel_image", kwargs={"pk": self.panel.pk})
            response = self.client.post(url, {"prompt": "Custom prompt"}, follow=True)

            self.assertEqual(response.status_code, 200)
            messages = [m.message for m in get_messages(response.wsgi_request)]
            self.assertTrue(
                any("API key" in m or "STABILITY" in m.upper() for m in messages),
                "Expected an error message mentioning the missing Stability API key",
            )

            self.panel.refresh_from_db()
            self.assertTrue(self.panel.prompt_approved)  # Prompt was approved but no image generated
    
    def test_generate_panel_image_view_custom_prompt_success(self):
        """
        generate_panel_image_view:
        - accepts a custom prompt via POST
        - updates panel.image_prompt
        - sets prompt_approved=True on success
        - surfaces a success message
        """
        from django.urls import reverse
        from django.contrib.messages import get_messages
        
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
            with patch('requests.post', return_value=mock_response):
                custom_prompt = "Highly detailed cinematic still of a robot in rain"

                url = reverse("storyboard:generate_panel_image", kwargs={"pk": self.panel.pk})
                response = self.client.post(url, {"prompt": custom_prompt}, follow=True)

                self.assertEqual(response.status_code, 200)
                self.panel.refresh_from_db()
                self.assertEqual(self.panel.image_prompt, custom_prompt)
                self.assertTrue(self.panel.prompt_approved)

                messages = [m.message for m in get_messages(response.wsgi_request)]
                self.assertTrue(
                    any("generated" in m.lower() for m in messages),
                    "Expected a success message about image generation",
                )
    
    def test_generate_panel_image_view_api_failure_shows_error(self):
        """
        On generate_panel_image failure, the view should keep prompt_approved=True
        (since the prompt itself was approved) but show an error message.
        """
        from django.urls import reverse
        from django.contrib.messages import get_messages
        
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            with patch('requests.post', return_value=mock_response):
                custom_prompt = "Prompt that will cause mocked failure"

                url = reverse("storyboard:generate_panel_image", kwargs={"pk": self.panel.pk})
                response = self.client.post(url, {"prompt": custom_prompt}, follow=True)

                self.assertEqual(response.status_code, 200)
                self.panel.refresh_from_db()
                self.assertEqual(self.panel.image_prompt, custom_prompt)
                self.assertTrue(self.panel.prompt_approved)

                messages = [m.message for m in get_messages(response.wsgi_request)]
                self.assertTrue(
                    any("error" in m.lower() or "failed" in m.lower() for m in messages),
                    "Expected an error message about image generation failure",
                )
    
    def test_generate_panel_image_view_empty_prompt_uses_fallback(self):
        """
        When an empty or whitespace-only prompt is submitted, the view should
        fall back to build_image_prompt and not approve the prompt.
        """
        from django.urls import reverse
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            url = reverse("storyboard:generate_panel_image", kwargs={"pk": self.panel.pk})
            response = self.client.post(url, {"prompt": "   "}, follow=True)

            self.assertEqual(response.status_code, 200)
            self.panel.refresh_from_db()
            # Should have a prompt generated from description
            self.assertNotEqual(self.panel.image_prompt, "")
            self.assertIn("Cinematic storyboard sketch", self.panel.image_prompt)
            # Should NOT be approved when prompt is empty/whitespace
            self.assertFalse(self.panel.prompt_approved)
    
    def test_storyboard_detail_view_context_stability_api_configured_false(self):
        """
        StoryboardDetailView.get_context_data should expose stability_api_configured=False
        when STABILITY_API_KEY is not set.
        """
        from django.urls import reverse
        
        with patch.dict(os.environ, {}, clear=True):
            url = reverse("storyboard:detail", kwargs={"pk": self.storyboard.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn("stability_api_configured", response.context)
            self.assertFalse(response.context["stability_api_configured"])
    
    def test_storyboard_detail_view_context_stability_api_configured_true(self):
        """
        StoryboardDetailView.get_context_data should expose stability_api_configured=True
        when STABILITY_API_KEY is set.
        """
        from django.urls import reverse
        
        with patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}):
            url = reverse("storyboard:detail", kwargs={"pk": self.storyboard.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn("stability_api_configured", response.context)
            self.assertTrue(response.context["stability_api_configured"])
