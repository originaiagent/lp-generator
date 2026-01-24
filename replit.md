# LP Generator

## Overview

This is a Landing Page (LP) Generator application built with Streamlit. It provides a multi-page workflow for creating marketing landing pages with AI-assisted content generation, including product management, model image generation, page structure design, and content output. The application integrates with multiple AI providers (Anthropic Claude, OpenAI GPT, Google Gemini) for text generation and image creation.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit multi-page application
- **Entry Point**: `app.py` serves as the main dashboard
- **Page Structure**: Sequential workflow pages in `pages/` directory (01-09), each handling a specific step in the LP creation process
- **Navigation**: Streamlit's native sidebar navigation with Japanese page titles

### Backend Architecture
- **Modular Design**: Core functionality split into specialized modules in `modules/` directory
- **Key Modules**:
  - `data_store.py`: Product data persistence using JSON files
  - `settings_manager.py`: Application configuration management
  - `ai_provider.py`: Unified interface for multiple AI providers
  - `prompt_manager.py`: Template management for AI prompts
  - `image_generator.py`: Multi-provider image generation (DALL-E, Gemini)
  - `model_generator.py`: Human model attribute and image generation
  - `chat_manager.py`: AI chat conversation handling

### Data Storage
- **Pattern**: File-based JSON storage (no database)
- **Product Data**: Individual JSON files per product in `data/products/`
- **Configuration**: `data/settings.json` for app settings, `data/models.json` for available AI models
- **Prompts**: Stored in `prompts/` directory as JSON templates
- **Uploads**: User-uploaded files stored in `data/uploads/{product_id}/`

### AI Integration
- **Multi-Provider Support**: Anthropic, OpenAI, and Google Gemini
- **Configuration**: Provider and model selection stored in settings
- **API Keys**: Read from environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`)
- **Fallback**: Mock responses when API keys are not configured

### Workflow Design
1. **Product Creation** (01_product_list): Manage product entries
2. **Input Collection** (02_input): Upload product images, competitor URLs, reference materials
3. **Model Generation** (03_model): Configure and generate human model images
4. **Structure Design** (04_structure): Define page layout and sections
5. **Page Details** (05_page_detail): Configure content for each section
6. **Output Generation** (06_output): Generate final prompts and instructions
7. **Prompt Management** (07_prompt): Edit AI prompt templates
8. **Settings** (08_settings): Configure AI providers and models
9. **AI Chat** (09_ai_chat): Development assistant chat interface

## External Dependencies

### AI Services
- **Anthropic Claude API**: Primary LLM for text generation
- **OpenAI API**: Alternative LLM and DALL-E image generation
- **Google Gemini API**: Alternative LLM and Imagen image generation

### Python Packages
- **streamlit**: Web application framework
- **requests**: HTTP client for API calls
- **pandas**: Data processing for CSV file parsing

### Environment Variables Required
- `ANTHROPIC_API_KEY`: For Claude models
- `OPENAI_API_KEY`: For GPT models and DALL-E
- `GOOGLE_API_KEY`: For Gemini models

### File Dependencies
- `data/models.json`: Available model configurations
- `data/settings.json`: Application settings
- `prompts/default_prompts.json`: Default prompt templates