# NIT_Trichy_winter_internship_2026_SnackFlow
## 🚀 Getting Started

Follow these steps to download, install and run the FactoryFlow application on your local machine.

### 1. Prerequisites

Make sure you have installed:

- Python 3.10 or above
- Git
- VS Code (recommended)

Check your Python installation:

```bash
python --version
```

### 2. Clone the Repository

```bash
git clone https://github.com/siranjeevimr040807/NIT_Trichy_winter_internship_2026_SnackFlow.git
```

Navigate into the project folder:

```bash
cd NIT_Trichy_winter_internship_2026_SnackFlow
```

### 3. Create a Virtual Environment

```bash
python -m venv venv
```

**Windows (PowerShell):**

```powershell
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```cmd
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Initialize the Database

```bash
python seed.py
```

This initializes the SQLite database with sample users and demo data.

### 6. Run the Application

```bash
python app.py
```

### 7. Open the Application

Open your browser and visit:

```text
http://127.0.0.1:5000
```

### 🔐 Demo Login Credentials

| Role | Username | Password |
|---|---|---|
| Salesman A | salesman_a | demo123 |
| Salesman B | salesman_b | demo123 |
| Administrator | admin | demo123 |
| Production | production | demo123 |
| Auditor | auditor | demo123 |
| Owner | owner | demo123 |

### 🛑 Stop the Application

Press `CTRL + C` in the terminal to stop the server.

### ⚠️ Important Notes

- Run `python seed.py` only during the initial setup.
- Running the seed script again resets the existing database and reloads demo data.
- Use `python app.py` whenever you want to restart the application.
- The SQLite database is created automatically inside the project folder.
