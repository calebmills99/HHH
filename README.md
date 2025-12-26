# Storyboard Generator

A Django web application that automatically generates storyboards from text descriptions. Simply describe your scene, and the application will break it down into logical panels with suggested camera angles and directional notes.

## Features

- **Text-to-Storyboard Conversion**: Automatically analyzes scene descriptions and generates storyboard panels
- **AI-Powered Image Generation**: Creates cinematic storyboard sketches using Stability AI (optional)
- **Smart Panel Generation**: Intelligently splits scenes into logical panels based on actions and scene changes
- **Directional Notes**: Provides camera angle and shot suggestions for each panel
- **Panel Management**: View, organize, and manage all your storyboards
- **Responsive UI**: Clean, modern interface with gradient styling
- **Admin Interface**: Full Django admin support for managing storyboards

## Installation

1. Clone the repository:
```bash
git clone https://github.com/calebmills99/HHH.git
cd HHH
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (recommended via `.env` file):
```bash
cp .env.example .env
# then edit .env with your own values
```

**Note on Image Generation:**
- If `STABILITY_API_KEY` is not set, the app will still work perfectly but won't generate images
- Images are generated automatically when creating new storyboards
- You can get a free Stability AI API key at [https://platform.stability.ai](https://platform.stability.ai)
- For development without image generation, you can skip setting the API key

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser (optional, for admin access):
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

7. Open your browser and navigate to `http://127.0.0.1:8000/`

## Usage

### Creating a Storyboard

1. Click "Create New" in the navigation menu
2. Enter a title for your storyboard
3. Write a detailed scene description
4. Click "Generate Storyboard"
5. View your generated panels with descriptions and directional notes

### Example Scene Description

```
A detective enters a dimly lit office. He looks around suspiciously. Suddenly, a shadow moves behind the curtain. The detective draws his gun and approaches carefully. He pulls back the curtain to reveal an open window with curtains blowing in the wind. He sighs with relief and holsters his weapon.
```

This will be automatically broken down into multiple panels with appropriate camera directions.

## Project Structure

```
HHH/
├── storyboard/              # Main Django app
│   ├── models.py           # Database models (Storyboard, StoryboardPanel)
│   ├── views.py            # View logic
│   ├── forms.py            # Forms for user input
│   ├── utils.py            # Storyboard generation logic
│   ├── urls.py             # App URL routing
│   ├── admin.py            # Admin interface configuration
│   └── templates/          # HTML templates
│       └── storyboard/
│           ├── base.html
│           ├── home.html
│           ├── storyboard_list.html
│           ├── storyboard_detail.html
│           └── storyboard_create.html
├── storyboard_project/      # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
└── README.md
```

## How It Works

The storyboard generator uses natural language processing techniques to:

1. **Parse the scene description**: Splits text into sentences
2. **Identify scene changes**: Detects transition words like "suddenly", "meanwhile", "later"
3. **Group into panels**: Combines related sentences into logical panels
4. **Generate directional notes**: Analyzes action words to suggest camera angles:
   - Action scenes → Dynamic shots with motion
   - Dialogue → Close-up or medium shots
   - Observation → POV or close-up on eyes/face
   - Entrances → Establishing shot or wide angle

## Models

### Storyboard
- `title`: The title of the storyboard
- `description`: Original text description of the scene
- `created_at`: Timestamp of creation
- `updated_at`: Timestamp of last update

### StoryboardPanel
- `storyboard`: Foreign key to parent Storyboard
- `panel_number`: Sequential panel number
- `description`: Description of this specific panel
- `image`: AI-generated storyboard image (when Stability AI API key is configured)
- `notes`: Directional notes and camera suggestions

## AI Image Generation

The application uses Stability AI's SDXL 1.0 model to automatically generate cinematic storyboard sketches for each panel:

- **Style**: Black and white pencil drawing in professional film storyboard style
- **Format**: Widescreen (1344x768) suitable for film production
- **Automatic**: Images are generated when creating new storyboards (if API key is configured)
- **Graceful Degradation**: Works perfectly without API key, just won't generate images

**Prompt Engineering**: Each panel description is enhanced with artistic direction like "Cinematic storyboard sketch, black and white pencil drawing, professional film storyboard style, clear composition, dramatic lighting"

## Future Enhancements

- Export to PDF format
- Collaborative editing
- Custom panel ordering and editing
- Shot duration estimates
- Character tracking across panels
- Alternative AI image models support

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
