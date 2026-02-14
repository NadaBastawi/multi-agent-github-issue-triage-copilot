# 🔥 AgentForge

**Forge intelligent AI agents with CrewAI - Transform ideas into powerful multi-agent systems**

AgentForge is the **first multi-agent framework** to use **reinforcement learning** for automatic agent creation and optimization. Unlike traditional frameworks that require manual agent design, AgentForge intelligently creates, adapts, and optimizes agents based on performance feedback.

## 🎯 What Makes AgentForge Special?

- 🔧 **Intelligent Tool Management**: Automatic mapping of custom tool names to CrewAI implementations
- 🤖 **Adaptive Agents**: Automatically creates specialized agents when needed
- 📊 **AI-Powered Analytics**: Intelligent performance tracking and optimization
- 🎨 **Creative CLI**: Beautiful, intuitive command-line interface
- 🔌 **Multi-Provider**: Support for all major LLM providers including local models
- 📚 **Template Library**: Pre-built patterns for common use cases
- 🛠️ **Robust Tool Registry**: Comprehensive tool management with fallback mechanisms

## 📦 Installation

```bash
# Install from PyPI (when available)
pip install agentforge

# Or install from source
git clone https://github.com/h9-tec/agentforge
cd agentforge
python -m venv venv

# Activate virtualenv (macOS/Linux)
source venv/bin/activate

# Activate virtualenv (Windows PowerShell)
# .\venv\Scripts\Activate.ps1

# Activate virtualenv (Windows CMD)
# venv\Scripts\activate.bat

pip install -e .
```

## ⚡ Quick Start

### 1. Configure Your LLM Provider
```bash
# Configure OpenAI (most common)
agentforge providers --configure openai --api-key "your-key" --model "gpt-4"

# Or configure local models
agentforge providers --configure ollama --model "llama3.1"
```

### 2. Create Your First Crew
```bash
# Basic crew creation
agentforge forge "Create a blog writer who writes engaging content" --name blog_writer

# Using templates for faster setup
agentforge forge "Analyze sales data" --template data_analysis --name sales_analyst
```

### 3. Execute Your Crew
```bash
# Run the crew
agentforge ignite blog_writer --input "Write a blog post about AI trends"

# With additional context
agentforge ignite sales_analyst --input "Focus on Q4 performance"
```

### 4. Monitor Performance
```bash
# View analytics
agentforge analytics --summary

# Check specific crew performance
agentforge analytics --crew blog_writer --days 7
```

## 🔧 Tool Management System

AgentForge features an intelligent tool management system that automatically handles tool mapping and instantiation:

### **Automatic Tool Mapping**
The system automatically maps custom tool names to actual CrewAI tool implementations:

```yaml
# In your agent configuration
tools:
  - api_calls          # Maps to SerperDevTool
  - file_operations    # Maps to FileReadTool
  - code_execution     # Maps to CodeInterpreterTool
  - document_search    # Maps to PDFSearchTool
  - github_search      # Maps to GithubSearchTool
  - web_scraping       # Maps to ScrapeWebsiteTool
  - database_search    # Maps to PGSearchTool
  - browser_automation # Maps to BrowserbaseLoadTool
  - vision            # Maps to VisionTool
```

### **Supported Tools**
- **Web Search**: `api_calls`, `web_search` → SerperDevTool
- **File Operations**: `file_operations` → FileReadTool
- **Code Execution**: `code_execution` → CodeInterpreterTool
- **Document Search**: `document_search` → PDFSearchTool, DOCXSearchTool, etc.
- **GitHub Integration**: `github_search` → GithubSearchTool
- **Web Scraping**: `web_scraping` → ScrapeWebsiteTool
- **Database**: `database_search` → PGSearchTool
- **Browser Automation**: `browser_automation` → BrowserbaseLoadTool
- **Vision**: `vision` → VisionTool

### **Fallback Mechanisms**
- Automatic fallback to SerperDevTool for unknown tools
- Graceful handling of missing dependencies
- Comprehensive error logging and reporting

### **Usage Example**
```python
# In your crew configuration (agents.yaml)
tools:
  - api_calls          # Automatically maps to SerperDevTool
  - file_operations    # Automatically maps to FileReadTool
  - code_execution     # Automatically maps to CodeInterpreterTool

# The system automatically handles:
# 1. Tool name mapping
# 2. Tool instantiation
# 3. Error handling
# 4. Fallback mechanisms
```

## 🏗️ Project Structure

```
agentforge/
├── agentforge/           # Core framework
│   ├── agents/          # Agent implementations
│   ├── core/            # Core functionality
│   ├── tools/           # Tool registry and management
│   ├── analytics/       # Performance analytics
│   ├── logging/         # Logging system
│   └── templates/       # Crew templates
├── crews/               # Production crews
│   ├── simple_writer/   # Simple blog writing crew
│   └── tech_blog_writer_final/  # Advanced tech blog writing crew
└── docs/                # Documentation
```

## 🎭 Production Crews

AgentForge comes with pre-built production crews ready to use:

### **Simple Writer Crew**
A streamlined crew for basic content creation:
- **Agents**: Social Media Content Language Model Specialist, Text Generator Specialist
- **Tools**: FileReadTool, CodeInterpreterTool
- **Use Case**: Quick content generation and social media posts

### **Tech Blog Writer Final Crew**
A comprehensive crew for technical content creation:
- **Agents**: Research Specialist, Content Creator, Editor Specialist, Database Specialist
- **Tools**: api_calls, file_operations, document_search, github_search, database_search
- **Use Case**: Technical blog posts, research articles, and comprehensive content

## 🚀 Enhanced Features

### 🧠 **Adaptive Agent Creation with Reinforcement Learning**
The system can automatically create new agents based on performance feedback using sophisticated RL algorithms:

```bash
# Analyze crew performance and get recommendations
agentforge adaptive analyze --crew my_crew

# Let the system decide to create specialized agents
agentforge adaptive create --crew my_crew --context "complex data analysis"

# Train the RL system to make better decisions
agentforge rl train --crew my_crew --episodes 50

# Get insights into the learning system
agentforge rl insights
```

**Key Benefits:**
- 🤖 **Self-Evolving**: Automatically creates agents when performance drops
- 🎯 **Context-Aware**: Considers task complexity and requirements
- 📈 **Learning**: Improves decisions through reinforcement learning
- ⚡ **Specialized**: Creates domain-specific agents (research, creative, technical, etc.)

### 🔌 **Multi-Provider LLM Support**
Support for all major LLM providers including local models:

```bash
# OpenAI
agentforge providers --configure openai --api-key "your-key" --model "gpt-4"

# Anthropic Claude
agentforge providers --configure anthropic --api-key "your-key" --model "claude-3-sonnet"

# Google Gemini
agentforge providers --configure google --api-key "your-key" --model "gemini-pro"

# Local Models
agentforge providers --configure ollama --model "llama3.1" --ollama-host "http://localhost:11434"
agentforge providers --configure llamacpp --model "llama-3.1-8b" --model-path "/path/to/model.gguf"

# Custom Providers
agentforge providers --configure custom --api-key "your-key" --base-url "https://api.example.com/v1" --model "gpt-4o-mini"
```

### 📚 **Crew Templates & Pattern Library**
Pre-built templates for common use cases:

```bash
# List available templates
agentforge templates --list

# Search for specific templates
agentforge templates --search "data analysis"

# Use a template when creating a crew
agentforge forge "Analyze sales data" --template data_analysis

# Get template recommendations
agentforge templates --recommend "content creation"
```

**Available Templates:**
- 📊 **Data Analysis**: Statistical analysis, data processing, visualization
- ✍️ **Content Creation**: Blog writing, social media, marketing content
- 🔍 **Research**: Market research, competitive analysis, academic research
- 💻 **Development**: Code generation, debugging, system design
- 📈 **Business**: Strategy planning, financial analysis, reporting

### 📊 **Performance Analytics & Cost Optimization**
Comprehensive tracking and optimization:

```bash
# View performance summary
agentforge analytics --summary

# Analyze specific crew performance
agentforge analytics --crew my_crew --days 30

# Get cost analysis
agentforge analytics --costs --crew my_crew

# Get optimization recommendations
agentforge analytics --optimize --crew my_crew

# Export analytics data
agentforge analytics --export analytics_report.json
```

**Analytics Features:**
- 📈 **Performance Tracking**: Success rates, execution times, quality scores
- 💰 **Cost Analysis**: LLM usage costs, efficiency metrics
- 🎯 **Optimization**: AI-powered recommendations for improvement
- 📊 **Visualization**: Charts and graphs for better insights

### 🛠️ **Enhanced Error Handling & Logging**
Robust error management and debugging:

```bash
# View log summary
agentforge logs --summary

# Check for errors
agentforge logs --errors

# Enable debug tracing
agentforge logs --debug

# Set log level
agentforge logs --set-level DEBUG

# Export logs
agentforge logs --export debug_logs.txt
```

**Logging Features:**
- 🔍 **Structured Logging**: Context-aware logging with metadata
- 🚨 **Error Classification**: Categorized error handling and recovery
- 📊 **Performance Tracing**: Function-level performance monitoring
- 🔄 **Recovery Strategies**: Automatic error recovery mechanisms

### 🎨 **Creative CLI Design**
Beautiful, intuitive command-line interface:

```bash
# Fancy ASCII art banner
agentforge

# Creative command names
agentforge forge "Create a blog writer"    # Instead of "create"
agentforge ignite my_crew                  # Instead of "run"

# Rich output with colors and formatting
agentforge providers --list
agentforge analytics --summary
```

**CLI Features:**
- 🎨 **Rich Formatting**: Colors, emojis, and beautiful output
- ⚡ **Intuitive Commands**: Creative naming (forge, ignite, etc.)
- 📱 **Interactive Prompts**: Guided setup and configuration
- 🔍 **Help System**: Comprehensive help and examples

## 📋 Complete Command Reference

### 🔥 **Core Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `agentforge forge` | Create a new agent crew | `agentforge forge "Create a blog writer" --name blog_crew` |
| `agentforge ignite` | Execute an existing crew | `agentforge ignite blog_crew --input "Write about AI"` |
| `agentforge providers` | Manage LLM providers | `agentforge providers --configure openai --api-key "key"` |
| `agentforge version` | Show version information | `agentforge version` |

### 🧠 **Adaptive & RL Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `agentforge adaptive analyze` | Analyze crew performance | `agentforge adaptive analyze --crew my_crew` |
| `agentforge adaptive create` | Create adaptive agents | `agentforge adaptive create --crew my_crew --context "complex task"` |
| `agentforge adaptive insights` | View adaptive system insights | `agentforge adaptive insights` |
| `agentforge adaptive learn` | Update learning parameters | `agentforge adaptive learn` |
| `agentforge rl step` | Execute RL step | `agentforge rl step --crew my_crew --context "task"` |
| `agentforge rl train` | Train RL system | `agentforge rl train --crew my_crew --episodes 50` |
| `agentforge rl insights` | View RL system insights | `agentforge rl insights` |
| `agentforge rl reset` | Reset RL model | `agentforge rl reset` |

### 📚 **Template Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `agentforge templates --list` | List available templates | `agentforge templates --list` |
| `agentforge templates --search` | Search templates | `agentforge templates --search "data analysis"` |
| `agentforge templates --show` | Show template details | `agentforge templates --show data_analysis` |
| `agentforge templates --recommend` | Get recommendations | `agentforge templates --recommend "content creation"` |
| `agentforge templates --filter` | Filter by category | `agentforge templates --filter business` |

### 📊 **Analytics Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `agentforge analytics --summary` | View performance summary | `agentforge analytics --summary` |
| `agentforge analytics --crew` | Analyze specific crew | `agentforge analytics --crew my_crew --days 30` |
| `agentforge analytics --costs` | View cost analysis | `agentforge analytics --costs --crew my_crew` |
| `agentforge analytics --optimize` | Get optimizations | `agentforge analytics --optimize --crew my_crew` |
| `agentforge analytics --export` | Export analytics | `agentforge analytics --export report.json` |

### 🛠️ **Logging Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `agentforge logs --summary` | View log summary | `agentforge logs --summary` |
| `agentforge logs --errors` | View error logs | `agentforge logs --errors` |
| `agentforge logs --debug` | View debug traces | `agentforge logs --debug` |
| `agentforge logs --set-level` | Set log level | `agentforge logs --set-level DEBUG` |
| `agentforge logs --export` | Export logs | `agentforge logs --export logs.txt` |
| `agentforge logs --clear` | Clear log history | `agentforge logs --clear` |

## 🆚 Feature Comparison

| Feature | AgentForge | Basic CrewAI | Other Frameworks |
|---------|------------|--------------|------------------|
| **Multi-Agent Creation** | ✅ AI-Powered | ✅ Manual | ❌ Limited |
| **Tool Management** | ✅ Intelligent Mapping | ⚠️ Manual | ❌ Basic |
| **Adaptive Agents** | ✅ RL-Based | ❌ Static | ❌ Not Available |
| **Template Library** | ✅ 10+ Templates | ❌ None | ⚠️ Basic |
| **Performance Analytics** | ✅ Advanced | ❌ None | ⚠️ Basic |
| **Cost Optimization** | ✅ AI-Powered | ❌ None | ❌ Not Available |
| **Error Handling** | ✅ Comprehensive | ⚠️ Basic | ⚠️ Basic |
| **Local LLM Support** | ✅ Ollama + LlamaCpp | ⚠️ Limited | ⚠️ Limited |
| **CLI Experience** | ✅ Rich & Creative | ⚠️ Basic | ⚠️ Basic |
| **Learning System** | ✅ Reinforcement Learning | ❌ None | ❌ Not Available |
| **Specialization** | ✅ Domain-Specific | ❌ Generic | ⚠️ Limited |
| **Production Crews** | ✅ Ready-to-Use | ❌ None | ❌ Not Available |

## 🆕 Recent Updates

### **Tool Management System Overhaul**
- ✅ **Intelligent Tool Mapping**: Automatic mapping of custom tool names to CrewAI implementations
- ✅ **Comprehensive Tool Registry**: Support for 15+ different tool types
- ✅ **Fallback Mechanisms**: Graceful handling of missing tools and dependencies
- ✅ **Error Recovery**: Robust error handling with detailed logging

### **Codebase Cleanup**
- ✅ **Test Agent Removal**: Cleaned up all test and development agents
- ✅ **Production-Ready**: Only production crews remain (simple_writer, tech_blog_writer_final)
- ✅ **Updated .gitignore**: Comprehensive patterns for excluding test files and cache directories
- ✅ **Optimized Structure**: Streamlined project structure for better maintainability

### **Enhanced Documentation**
- ✅ **Updated README**: Comprehensive documentation with current features
- ✅ **Tool Reference**: Complete tool mapping and usage examples
- ✅ **Project Structure**: Clear overview of the codebase organization

## 🎯 **Why Choose AgentForge?**

### 🚀 **Advanced AI Capabilities**
- **Self-Evolving**: Agents automatically improve and specialize
- **Context-Aware**: Understands task complexity and requirements
- **Learning System**: Gets smarter with every interaction
- **Intelligent Optimization**: AI-powered performance improvements

### 🛠️ **Developer Experience**
- **Rich CLI**: Beautiful, intuitive command-line interface
- **Comprehensive Logging**: Detailed debugging and monitoring
- **Template System**: Pre-built patterns for common use cases
- **Multi-Provider**: Support for all major LLM providers

### 📊 **Enterprise Features**
- **Performance Analytics**: Detailed metrics and insights
- **Cost Management**: Budget-aware execution and optimization
- **Error Recovery**: Robust error handling and recovery
- **Scalability**: Handles complex, multi-step workflows

### 🔬 **Research & Innovation**
- **Reinforcement Learning**: Cutting-edge RL algorithms
- **Adaptive Systems**: Self-modifying agent architectures
- **Specialization Patterns**: Domain-specific agent creation
- **Performance Optimization**: Continuous improvement algorithms

## 🌟 **Key Innovations**

### 🧠 **Reinforcement Learning for Agent Creation**
AgentForge is the first framework to use RL algorithms for automatic agent creation:
- **Q-Learning**: Learns optimal decisions through experience
- **State Management**: Tracks 6 different environmental states
- **Action Selection**: 7 different actions for agent management
- **Continuous Learning**: Improves with every interaction

### 🤖 **Adaptive Agent Specialization**
Agents automatically specialize based on performance and requirements:
- **Domain-Specific**: Research, creative, technical, analytical, communication
- **Performance-Driven**: Creates agents when performance drops
- **Context-Aware**: Considers task complexity and requirements
- **Self-Evolving**: Agents improve and adapt over time

### 📊 **AI-Powered Analytics & Optimization**
Comprehensive performance tracking with intelligent optimization:
- **Real-Time Metrics**: Success rates, execution times, quality scores
- **Cost Analysis**: LLM usage costs and efficiency metrics
- **Predictive Optimization**: AI-powered recommendations
- **Performance Trends**: Historical analysis and forecasting

### 🎨 **Creative Developer Experience**
Beautiful, intuitive interface designed for productivity:
- **Rich CLI**: Colors, emojis, and beautiful formatting
- **Creative Commands**: forge, ignite, adaptive, rl
- **Interactive Prompts**: Guided setup and configuration
- **Comprehensive Help**: Detailed examples and documentation

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests if applicable
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/AgentForge/agentforge
cd agentforge

# Install development dependencies
pip install -e .
```

## 📄 License

AgentForge is released under the MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [CrewAI](https://github.com/joaomdmoura/crewAI) - Core multi-agent framework
- [LangChain](https://github.com/langchain-ai/langchain) - LLM integration tools  
- [Sentence Transformers](https://github.com/UKPLab/sentence-transformers) - Text embeddings
- [FAISS](https://github.com/facebookresearch/faiss) - Vector similarity search



---

**Built with ❤️ for the AI community**

*AgentForge represents the future of multi-agent systems - intelligent, adaptive, and self-evolving.*

## FastAPI Issue Triage Crew

New production-ready crew: `crews/fastapi_issue_triage`

- Target repository: `tiangolo/fastapi`
- Purpose: human-in-the-loop issue triage + repro checklist + maintainer reply draft
- Outputs: `triage.json`, `repro_checklist.md`, `draft_maintainer_reply.md`

Quick run:

```bash
cd crews/fastapi_issue_triage
uv venv
uv sync
uv run fastapi_issue_triage "https://github.com/tiangolo/fastapi/issues/12176"
```

Detailed setup and ordered commands for any developer:

- `crews/fastapi_issue_triage/README.md`
- Environment template: `crews/fastapi_issue_triage/.env.example`
