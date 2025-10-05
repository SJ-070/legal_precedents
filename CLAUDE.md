# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- **Run the application**: `streamlit run main.py`
- **Install dependencies**: `pip install -r requirements.txt`

### Environment Setup
- Set `GOOGLE_API_KEY` environment variable for Google Gemini API access
- Alternatively, create a `.env` file with `GOOGLE_API_KEY=your_api_key`

## Project Structure

```
legal_precedents/
├── data/                          # Data management tools
│   ├── __init__.py
│   ├── crawler_kcs.py            # KCS precedent crawler
│   ├── crawler_moleg.py          # MOLEG precedent crawler
│   ├── clean_kcs.py              # KCS data cleaner
│   ├── clean_moleg.py            # MOLEG data cleaner
│   └── update_kcs_data.py        # KCS data update utility
│
├── utils/                         # Chatbot core logic
│   ├── __init__.py               # Module exports
│   ├── config.py                 # Gemini API configuration
│   ├── conversation.py           # Conversation history management
│   ├── data_loader.py            # Data loading and caching
│   ├── text_processor.py         # Text preprocessing
│   ├── vectorizer.py             # TF-IDF vectorization and search
│   └── agent.py                  # AI agent execution
│
├── data_kcs.json                 # KCS precedent data (423 cases)
├── data_moleg.json               # MOLEG precedent data (486 cases)
├── vectorization_cache.pkl.gz    # Vectorization cache
├── main.py                       # Streamlit application
├── requirements.txt
├── CLAUDE.md
└── README.md
```

## Architecture Overview

This is a Korean Customs Law legal precedent chatbot using a multi-agent architecture with Google Gemini models.

### Core Components

#### **main.py**
Streamlit web application interface and user interaction logic

#### **utils/ module**
Core processing logic split into 6 modules:
- `config.py`: Gemini API client initialization
- `conversation.py`: Conversation history management
- `data_loader.py`: Data loading, caching (pickle/gzip)
- `text_processor.py`: Text preprocessing and extraction
- `vectorizer.py`: Character n-gram TF-IDF vectorization and search
- `agent.py`: Parallel agent execution and response integration

#### **data/ module**
Data collection and cleaning tools:
- `crawler_kcs.py`: KCS website crawler (Selenium)
- `crawler_moleg.py`: MOLEG website crawler (Selenium)
- `clean_kcs.py`: KCS data cleaner (duplicate removal, content filtering)
- `clean_moleg.py`: MOLEG data cleaner and field extractor
- `update_kcs_data.py`: KCS data merge and update utility

### Multi-Agent System
The system uses 6 AI agents running in parallel:
1. **Agents 1-2**: Analyze customs precedent data (data_kcs.json) split into 2 chunks
2. **Agents 3-6**: Analyze national customs precedent data (data_moleg.json) split into 4 chunks
3. **Head Agent**: Integrates all agent responses using Gemini 2.5 Flash model

### Data Processing Architecture
- **Initial Load**: Data is loaded once and cached using `@st.cache_data`
- **Vectorization Method**: Character n-gram TF-IDF (analyzer='char', ngram_range=(2,4))
  - Unified vectorization of KCS + MOLEG data (909 total documents)
  - Performance: 2.2x better Precision, 3.1x better Recall vs word-based
  - Cache: Vectorized index saved as gzip-compressed pickle file for fast reloading
- **Similarity Search**: Cosine similarity for finding relevant precedents
- **Parallel Processing**: ThreadPoolExecutor for concurrent agent execution (6 workers)

### Key Functions

#### Data Management (`utils/data_loader.py`)
- `load_data()`: Loads JSON data and manages vectorization cache
- `save_vectorization_cache()`: Saves vectorized index to gzip pickle file
- `load_vectorization_cache()`: Loads cached vectorized index (skip re-vectorization)
- `check_data_files()`: Verifies required data files exist

#### Vectorization (`utils/vectorizer.py`)
- `preprocess_data()`: Character n-gram TF-IDF vectorization of unified data
- `search_relevant_data()`: Finds relevant precedents using cosine similarity

#### Agent Execution (`utils/agent.py`)
- `run_parallel_agents()`: Executes 6 agents concurrently (KCS 2 chunks + MOLEG 4 chunks)
- `run_head_agent()`: Integrates agent responses for final answer
- `get_agent_prompt()`: Generates agent-specific prompts

### Session State Management
- `loaded_data`: Cached preprocessed data and vectorizers
- `messages`: Chat conversation history
- `context_enabled`: Whether to use conversation context
- `max_history`: Number of recent messages to maintain as context

### Models Used
- **Individual Agents**: Gemini 2.5 Flash (temperature=0.1)
- **Head Agent**: Gemini 2.5 Flash (temperature=0.1)

## Data Update Workflow

**IMPORTANT: All data management scripts must be run from the project root directory**

### 1. Update KCS Data

```bash
# Navigate to project root
cd legal_precedents

# Step 1: Crawl new data
python data/crawler_kcs.py
# Output: data_kcs_temp.json (in project root)

# Step 2: Clean and merge
python data/update_kcs_data.py
# Output: data_kcs.json updated (in project root)
```

### 2. Update MOLEG Data

```bash
# Navigate to project root
cd legal_precedents

# Step 1: Crawl new data
python data/crawler_moleg.py
# Output: law_portal_data_YYYYMMDD_HHMMSS.json (in project root)

# Step 2: Clean and structure
python data/clean_moleg.py
# Output: data_moleg.json updated (in project root)
```

### Path Resolution

All data management scripts use **absolute paths** relative to the project root:

```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent

# Always saves to project root
output_file = PROJECT_ROOT / "data_kcs.json"
```

This ensures that:
- ✅ Scripts work regardless of execution location
- ✅ Data files always saved to project root
- ✅ No path confusion or accidental file duplication

## File Locations

### Data Files (Project Root)
- `data_kcs.json` - KCS precedent data
- `data_moleg.json` - MOLEG precedent data
- `vectorization_cache.pkl.gz` - Vectorization cache
- `data_kcs_temp.json` - Temporary crawler output (KCS)
- `law_portal_data_*.json` - Temporary crawler output (MOLEG)
- Backup files: `data_*_backup_*.json`

### Code Files
- `data/` - Data collection and cleaning scripts
- `utils/` - Chatbot core logic modules
- `main.py` - Application entry point
