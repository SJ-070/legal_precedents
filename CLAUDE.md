# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- **Run the application**: `streamlit run main.py`
- **Install dependencies**: `pip install -r requirements.txt`

### Environment Setup
- Set `GOOGLE_API_KEY` environment variable for Google Gemini API access
- Alternatively, create a `.env` file with `GOOGLE_API_KEY=your_api_key`

## Architecture Overview

This is a Korean Customs Law legal precedent chatbot using a multi-agent architecture with Google Gemini models:

### Core Components
- **main.py**: Streamlit web application interface and user interaction logic
- **utils.py**: Core processing logic including data preprocessing, TF-IDF vectorization, agent execution, and API calls

### Multi-Agent System
The system uses 6 AI agents running in parallel:
1. **Agents 1-2**: Analyze customs precedent data (data_kcs.json) split into 2 chunks
2. **Agents 3-6**: Analyze national customs precedent data (data_moleg.json) split into 4 chunks
3. **Head Agent**: Integrates all agent responses using Gemini 2.5 Flash model

### Data Processing Architecture
- **Initial Load**: Data is loaded once and cached using `@st.cache_data`
- **Text Preprocessing**: TF-IDF vectorization with Korean legal stopwords
- **Similarity Search**: Cosine similarity for finding relevant precedents
- **Parallel Processing**: ThreadPoolExecutor for concurrent agent execution

### Key Functions
- `load_data()`: Loads and caches JSON precedent data
- `preprocess_data()`: Handles TF-IDF vectorization and data chunking
- `search_relevant_data()`: Finds relevant precedents using cosine similarity
- `run_parallel_agents()`: Executes 6 agents concurrently
- `run_head_agent()`: Integrates agent responses for final answer

### Session State Management
- `loaded_data`: Cached preprocessed data and vectorizers
- `messages`: Chat conversation history
- `context_enabled`: Whether to use conversation context
- `max_history`: Number of recent messages to maintain as context

### Data Files
- **data_kcs.json**: 423 customs precedent cases from KCS
- **data_moleg.json**: National law information center customs precedents from MOLEG

### Models Used
- **Individual Agents**: Gemini 2.0 Flash (temperature=0.1)
- **Head Agent**: Gemini 2.5 Flash (temperature=0.1)