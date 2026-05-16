# Feedback Generator

A web app for creating reusable feedback templates with replaceable placeholders. Designed for teachers and anyone who writes repetitive personalized feedback.

## Features

- **Template management** — Create, edit, delete, and reorder feedback templates
- **Flexible placeholders** — Use `{placeholder}` tokens in template text, configured as:
  - **Freeform** — free text input
  - **Dropdown** — predefined options (e.g., "Good", "Great", "Needs improvement")
- **Live placeholder detection** — Placeholders are detected as you type the template body
- **Drag-and-drop reordering** — Rearrange templates on the home page
- **One-click copy** — Copy generated feedback to clipboard instantly

## Example

Template:
```
Hello, {name}. {assessment} work on your discussion. If you have any questions, feel free to reach me at {address}.
```

Generated output:
```
Hello, Jon. Good work on your discussion. If you have any questions, feel free to reach me at reuben@teacher.tech.
```

## Tech Stack

- **Backend:** Python 3 / Flask
- **Database:** MongoDB (via pymongo)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Drag & Drop:** SortableJS

## Prerequisites

- Python 3.10+
- MongoDB running on `localhost:27017` (e.g., via Docker)

## Setup

1. **Start MongoDB** (if not already running):
   ```bash
   docker run -d --name mongo -p 27017:27017 -v mongo_data:/data/db mongo:7
   ```

2. **Clone the repo:**
   ```bash
   git clone https://github.com/rhwilson1971/feedback_generator.git
   cd feedback_generator
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```

5. **Open** [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Usage

1. Click **+ New Template** to create a template
2. Write your feedback text using `{placeholder_name}` for replaceable fields
3. Configure each placeholder as freeform or dropdown (with options)
4. From the home page, click **Generate** on a template
5. Fill in the placeholder values and submit
6. Click **Copy to Clipboard** to copy the result

## Project Structure

```
feedback_generator/
├── app.py              # Flask routes and logic
├── database.py         # MongoDB connection helper
├── requirements.txt    # Python dependencies
├── static/
│   ├── app.js          # Clipboard, placeholder detection, reorder JS
│   └── style.css       # Custom styles
└── templates/          # Jinja2 HTML templates
    ├── base.html
    ├── index.html
    ├── template_form.html
    └── generate.html
```

## License

MIT
