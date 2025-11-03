# Flask POS System

A simple, extendable Point of Sale (POS) application built with Flask (Python) and standard web technologies (HTML/CSS/JavaScript). This repository contains the server-side Flask app, templates (HTML), static assets (CSS/JS), and simple database-backed sales and inventory management logic.

Repository language composition: Python (55.6%), HTML (24.6%), CSS (11.2%), JavaScript (8.6%).

## Features

- Product and inventory management
- Create and manage sales / transactions
- Receipt generation and printing
- Simple reporting (daily sales, inventory levels)
- User authentication (if implemented)
- Web UI served by Flask templates (Jinja2)

## Tech stack

- Backend: Python, Flask
- Templates: Jinja2 (HTML)
- Frontend: CSS, JavaScript
- Database: SQLite (default), optionally PostgreSQL/MySQL

## Prerequisites

- Python 3.8+
- pip (or pipenv/poetry)

## Quickstart (development)

1. Clone the repository

```bash
git clone https://github.com/tijnara/flask-pos-system.git
cd flask-pos-system
```

2. Create and activate a virtual environment

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
``` 

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Copy environment example and set secrets

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL, SECRET_KEY, etc.
```

5. Initialize the database (example with Flask-Migrate)

```bash
flask db upgrade
# or, if using raw SQL/SQLite, run the provided init script if any:
# python scripts/init_db.py
```

6. Run the development server

```bash
export FLASK_APP=run.py  # or the appropriate entrypoint
export FLASK_ENV=development
flask run
# On Windows (PowerShell):
# $env:FLASK_APP = "run.py"; $env:FLASK_ENV = "development"; flask run
```

Open http://localhost:5000 in your browser.

## Production

For production serve the app with a WSGI server (Gunicorn) behind a reverse proxy.

```bash
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

Adjust worker count and bind address as needed.

## Configuration

- Use `.env` or environment variables to store SECRET_KEY and database connection strings.
- Optional variables:
  - DATABASE_URL
  - SECRET_KEY
  - FLASK_ENV

## Database and Migrations

If the project uses Flask-Migrate / Alembic, use the provided migration commands (e.g., `flask db migrate`, `flask db upgrade`). If the repo uses raw SQL scripts, follow the scripts in `scripts/`.

## Tests

If tests are present run:

```bash
pytest
```

or the configured test runner.

## Folder layout (typical)

```
flask-pos-system/
├── app/                  # Flask application package
├── migrations/           # DB migrations (if present)
├── templates/            # Jinja2 HTML templates
├── static/               # CSS, JS, images
├── requirements.txt
├── run.py                # application entrypoint
└── README.md
```

Adjust based on the actual repository layout.

## Contributing

Contributions are welcome. Suggested workflow:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes with clear messages
4. Push and open a Pull Request

Please include tests and update documentation for new features.

## TODO / Improvements

- Add role-based access control and admin dashboard
- Integrate barcode scanner and hardware support
- Add CSV/PDF export for reports and receipts
- Add automated tests and CI

## License

Add a LICENSE file in the repository root. A common choice is the MIT License.

MIT License

Copyright (c) 2025 tijnara

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[...] 

## Contact

For questions or help, open an issue or mention @tijnara on GitHub.
