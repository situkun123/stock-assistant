# Stock Assistant

## Project Overview
The Stock Assistant is a tool designed to help users manage and analyze stock market data by using OpenAI ChatGPT. It provides functionalities for fetching stock information, performing analyses, and generating reports.

## Agent Graph
![Financial Agent Graph](financial_agent_graph.png)

## Folder Structure
```
stock-assiant/
├── app.py                # Main application file using chanilit
├── chainlit.md           # Documentation for Chainlit integration
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile            # Dockerfile for building the application
├── README.md             # Project documentation
├── requirements.txt      # Python dependencies
tests/
├── __init__.py
└── unit_test.py
├── backend/              # Backend logic
│   ├── __init__.py
│   ├── agent.py          # Stock agent logic
│   ├── database.py       # Database interactions mainly for logging API usage
│   ├── stock_fetcher.py  # Stock data fetching logic via yahoo finance
│   ├── tools.py          # Langgraph tool functions
│   └── utils.py          # Additional utilities
├── frontend/             # Frontend components (if applicable)
└── terraform/            # Infrastructure as code for web deployment
    ├── main.tf
    ├── outputs.tf
    ├── terraform.tfvars
    └── variables.tf
```


## How to Use using Docker Compose (development and testing)

1. **Clone the repository:**
```bash
   git clone https://github.com/situkun123/stock-assistant.git
   cd stock-assiant
```

2. **Set up environment variables:**
```bash
   cp .env.example .env
```
   Edit `.env` and fill in your credentials:
```bash
   OPENAI_API_KEY=your_openai_api_key
   DUCK_DB_TOKEN=your_motherduck_token
   DOCKER_USERNAME=your_dockerhub_username
   DOCKER_PASSWORD=your_dockerhub_password
   AUTH_USERS=user1:pass1,user2:pass2
   CHAINLIT_AUTH_SECRET=your_chainlit_auth_secret #can be any random string, used to secure the Chainlit dashboard
```

3. **Run with Docker Compose:**

   Using local Dockerfile:
```bash
   docker compose --profile local up --build
```

   Using DockerHub image:
```bash
   docker login
   docker compose --profile hub pull
   docker compose --profile hub up
```

   Stoping DockerHub image:
```bash
   docker compose --profile hub down
```

4. **Access the application:**
   Open your browser and go to:
```
   http://localhost:8000
```

5. **Stop the application:**
```bash
   docker compose --profile local down
   # or
   docker compose --profile hub down
```

## How to Push to Your Private DockerHub Repository

### Using GitHub Actions Workflow (Recommended)
1. **Fork or clone the repository:**
```bash
   git clone https://github.com/situkun123/stock-assiant.git
   cd stock-assiant
```

2. **Set up GitHub Secrets:**
```
   GitHub Repo → Settings → Secrets and variables → Actions → Secrets tab

   DOCKERHUB_USERNAME = your-dockerhub-username
   DOCKERHUB_TOKEN    = your-dockerhub-access-token
```
   Get your DockerHub token:
```
   DockerHub → Account Settings → Security → New Access Token
```

3. **Workflow triggers automatically on push or merge to main:**
```bash
   # Push directly to main
   git add .
   git commit -m "your changes"
   git push origin main
```

4. **In your docker repo**
```
    # you should see the new image tagged as
   your-username/stock-assistant:latest      
```


## Web Deployment with Terraform using Koyeb
1. **Set up Koyeb account and API token:**
```
    Koyeb → Account Settings → API Tokens → Create New Token
```
2. **Add Koyeb token to GitHub Secrets:**
```
   GitHub Repo → Settings → Secrets and variables → Actions → Secrets tab
```
### Using GitHub Actions Workflow 
- Workflow called **Deploy to Koyeb** triggers manually in the action section of GitHub.
