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
- **Shared ranking scales** — Define named scales, optionally rank templates, and filter by scale or rank
- **Light, dark, or system theme** — Choose in Settings; System follows your device
- **Return to your container** — Back to templates reopens and scrolls to the template's current container, including Uncategorized. Enabled by default; turn off “Reopen container when returning from feedback” in Settings to keep containers collapsed.

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

## Ranking templates

1. Open **Rankings** and choose **+ New Scale**.
2. Give the scale a unique name and add numbered ranks with descriptions, such
   as `1 — Completed` and `3 — Needs work`. Numbers can have gaps; their meaning
   is yours to define. Scales are shared across all containers.
3. On a template's New/Edit form, choose a scale and rank, or leave it **Unranked**.
4. Use **All rankings** on the home page to select a scale or **Unranked**.
   Selecting a scale enables the rank filter. These work together with name,
   container, and tag filters; **Clear** resets all filters.

Copies keep their rankings. Renaming a scale or editing a rank description
updates every template using it. A scale or rank in use cannot be deleted or
renumbered until its templates are unranked or reassigned. Existing templates
stay unranked automatically; no data migration is required.

## Tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
npm ci
npm test
```

Python tests replace MongoDB collection access with test fixtures and do not
require a running database. Browser validation of rankings used isolated sample
data; production MongoDB persistence still needs deployment verification.

## Project Structure

```
feedback_generator/
├── app.py              # Flask routes and logic
├── database.py         # MongoDB connection helper
├── rankings.py         # Shared scale management and validation
├── requirements.txt    # Python dependencies
├── static/
│   ├── app.js          # Clipboard, placeholder detection, reorder JS
│   ├── rankings.js     # Scale rows and dependent rank controls
│   └── style.css       # Custom styles
└── templates/          # Jinja2 HTML templates
    ├── base.html
    ├── index.html
    ├── template_form.html
    └── generate.html
```

## Browser extension (personal use)

`extension/` holds an unpacked Chrome extension that pastes the most recently
generated feedback into the text box you're using on another site. See
[`extension/README.md`](extension/README.md) to load it.

## License

MIT
