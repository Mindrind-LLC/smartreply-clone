# Smart Reply Clone

A FastAPI application that automatically processes Facebook page comments, analyzes user intent using LLM, and sends personalized DM responses.

## Features

- **Webhook Processing**: Receives Facebook page webhook events
- **Intent Analysis**: Uses LangChain with OpenAI/Gemini to analyze comment intent
- **Auto DM**: Sends personalized private replies to interested users
- **Database Storage**: Stores all comment data, intent analysis, and DM responses in SQLite
- **REST API**: Provides endpoints to view comments and analytics

## Setup

### 1. Install Dependencies

```bash
# Install dependencies using uv
uv sync
```

### 2. Environment Variables

Create a `.env` file with the following variables:

```env
# Meta API Configuration
META_API_TOKEN=your_meta_api_token_here
PAGE_ACCESS_TOKEN=your_page_access_token_here

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo

# Database Configuration
DATABASE_URL=sqlite:///./comments.db

# Comment Moderation (optional)
META_GRAPH_API_VERSION=v24.0
HARMFUL_COMMENT_KEYWORDS=cheater,cheaters,scam,scams,scammer,scammers,fraud,fake

# Feature Flags
TESTING=false
```

- `META_GRAPH_API_VERSION` lets you pin the Graph API version used for deletion calls.
- `HARMFUL_COMMENT_KEYWORDS` is a comma-separated list of phrases that help label why a negative comment was removed (removals now only happen for LLM-tagged `negative` intents).
- `TESTING=true` will prefix every Messenger response with `Testing` and persist chat history; when `false`, Messenger events are ignored entirely (no AI call, DB write, or outbound reply).

### 3. Run the Application

```bash
# Run with uvicorn
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Webhook Endpoints
- `GET /webhook` - Webhook verification
- `POST /webhook` - Webhook event processing

### Utility Endpoints
- `GET /health` - Health check
- `GET /comments` - Get all comments
- `GET /comments/interested` - Get comments with "interested_in_services" intent

## Workflow

1. **Comment Received**: Facebook sends webhook with comment data
2. **Data Storage**: Comment is stored in SQLite database
3. **Intent Analysis**: LLM analyzes comment to detect "interested_in_services" intent
4. **DM Generation**: Personalized DM message is generated based on comment
5. **Auto Reply**: Private reply is sent via Meta GraphQL API
6. **Status Update**: Database is updated with DM status

## Database Schema

The `comments` table stores:
- Comment metadata (ID, post ID, user info)
- Comment message and timestamp
- Raw webhook JSON data
- Intent analysis results
- Generated DM message
- DM sending status and timestamp

The `deleted_comments` table stores:
- Original comment metadata when a comment is removed (IDs, user info, text)
- The intent detected for that comment
- When it was originally created and when it was removed
- The removal reason (auto moderation vs webhook removal)

## Configuration

### LLM Providers
- **OpenAI**: Set `LLM_PROVIDER=openai` and provide `OPENAI_API_KEY`
- **Google**: Set `LLM_PROVIDER=google` and provide `GOOGLE_API_KEY`

### Few-shot Examples
DM examples can be modified in `config.py` under `DM_EXAMPLES`.

## Error Handling

The application includes comprehensive error handling:
- LLM failures fall back to default responses
- Meta API failures are logged and retried
- Database errors are handled gracefully
- All operations are logged for debugging
