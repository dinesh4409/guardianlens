# GuardianLens

## Overview

GuardianLens is an Intelligence & Security Analysis Dashboard designed to monitor, log, and analyze activity in real-time. It combines backend Flask services with a frontend dashboard for seamless tracking.

## Features

* **Live Activity Logging**: Capture and record system activity.
* **Dashboard**: Interactive dashboard for visualizing logged data.
* **Keyword Monitoring**: Track specific keywords from activity logs.
* **User Management**: Login and authentication system.
* **Static and Template Management**: Organized structure for HTML templates and static resources.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/dinesh4409/guardianlens.git
```

2. Navigate into the project directory:

```bash
cd guardianlens
```

3. Set up a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Project Structure

```
DK STABLE V1.9/
├── backend/
│   ├── app.py
│   ├── app_activity.log
│   ├── keywords.txt
│   ├── received_logs.txt
│   ├── static/
│   │   └── style.css
│   └── templates/
│       ├── dashboard.html
│       └── login.html
├── frontend/
│   ├── app-activity.py
│   ├── key-logger.py
│   └── keylog.txt
```

## Usage

1. Run the backend Flask application:

```bash
cd backend
python app.py
```

2. Access the dashboard via your browser at `http://localhost:2000`.
3. Frontend scripts can be run to send requests to the backend for monitoring and logging activity.
cd frontend
python app-activity.py

in another terminal
cd frontend
python key-logger.py


## Contributing

Feel free to fork the project and submit pull requests. Ensure code is properly documented and tested.

## License

This project is open-source and available under the MIT License.
