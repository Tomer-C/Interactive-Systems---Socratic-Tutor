# 🦉 Socratic Tutor – AI-Powered Python Debugging Tutor

An **intelligent Socratic-style Python tutoring system** that helps learners debug code through guided questioning, adaptive difficulty, skill tracking, and AI-based reasoning.

Built with **Streamlit**, **Gemini API**, **semantic retrieval**, and **learning analytics**, the system provides a personalized, interactive learning experience focused on *understanding*, not just fixing.

---

# ✨ Key Features

- 🧠 **Socratic AI Tutor** – Guides students using targeted questions instead of giving answers.
- 🔍 **Semantic Bug Retrieval** – Finds similar buggy code using CodeBERT embeddings.
- 📊 **Skill Tracking & Analytics** – Tracks progress across multiple cognitive dimensions.
- 🎯 **Adaptive Difficulty System** – Locks/unlocks problems based on mastery.
- 🧪 **Calibration System** – Automatically builds an initial skill profile.
- 📈 **Learning Progress Visualization** – Skill radar chart + progress line charts.
- 👤 **User System** – Registration, login, persistent learning profiles.
- 🔁 **Multi-Key Gemini API Rotation** – Automatic failover between API keys.

---

# 🏗️ Architecture Overview

The system is structured as a **multi-layer AI tutoring pipeline**:

```
User → Streamlit UI → AI Tutor → Semantic Retriever → Skill Engine → Analytics → Database
```

---

# 📁 Project Structure

```
.
├── app.py              # Streamlit entry point
├── ui_logic.py         # UI logic + AI tutoring pipeline
├── retriever.py        # Semantic retrieval engine
├── ast_analyzer.py     # AST-based structural analysis
├── taxonomy.py         # Error taxonomy hierarchy
├── analytics.py        # Learning analytics + charts
├── database.py         # SQLite persistence layer
├── config.py           # Global configuration
├── requirements.txt    # Python dependencies
└── data/
    ├── error_database.json
    ├── embeddings.npy
    └── snippet_ids.json
```

---

# 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Tomer-C/Interactive-Systems---Socratic-Tutor.git](https://github.com/Tomer-C/Interactive-Systems---Socratic-Tutor.git)
   cd Interactive-Systems---Socratic-Tutor
   ```
2. **Set up the virtual environment:**
   ```bash
   python -m venv venv
   # Activate on Mac/Linux:
   source venv/bin/activate
   # Activate on Windows:
   venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
---

# 🔐 Gemini API Key Setup (VERY IMPORTANT)

You must define **a list of API keys** inside `config.py`.

Even if you only have **one API key**, it must still be placed inside a list.

```python
GEMINI_KEYS = [
    "enter your API key here",
    "enter another API key here",
    ...
]
```

The system automatically rotates keys on failure, preventing rate-limit crashes and increasing reliability.

---

# ▶️ Running the Application

```bash
streamlit run app.py
```

Then open:

```
http://localhost:8501
```

---

# 🧠 Learning Flow

```
Login → Calibration → Dashboard → Analyze → Warm‑up → Fix → AI Evaluation → Skill Update
```

---

# 📊 Skills Tracked

- Syntax
- Logic
- Loops
- Recursion
- Data Structures

---

# 🗄️ Database

SQLite database automatically initializes on first run.

Tables:
- users
- user_skills
- attempts

---

# 💡 Author Notes

Designed as a **research-grade intelligent tutoring system**, combining:

- Semantic retrieval
- Cognitive modeling
- LLM-based Socratic tutoring
- Learning analytics

Built for **deep understanding, not shortcuts**.
