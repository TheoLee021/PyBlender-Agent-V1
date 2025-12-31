# Blender Agent

A simple, pure-Python AI agent that generates 3D Procedural Materials in Blender. 
It uses the Model Context Protocol (MCP) to communicate with a headless Blender instance, allowing you to create materials using natural language.

## Prerequisites
- Python 3.10+ (Managed by `uv`)
- Blender 4.5 (Must be installed and accessible)
- API Keys: Google Gemini (AI Studio) or OpenAI.

## Installation

1. Clone & Install Dependencies
   We use `uv` for fast dependency management.
   ```bash
   uv sync
   ```

2. Configure Environment
   Rename `.env.example` to `.env` and validate your API keys and Blender path.
   ```bash
   cp .env.example .env
   ```
   
   `.env` Configuration:
   ```ini
   # LLM Provider Configuration
   LLM_PROVIDER=gemini       # 'gemini' or 'openai'
   
   # Google Gemini
   GEMINI_API_KEY=your_key_here
   GEMINI_MODEL=gemini-3-flash-preview
   
   # OpenAI
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-5-mini
   
   # Blender Path (Critical!)
   # macOS Example:
   BLENDER_PATH=/Applications/Blender.app/Contents/MacOS/Blender
   # Windows Example:
   # BLENDER_PATH="C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
   ```

## Usage

Run the agent:
```bash
uv run agent/main.py
```

1. The agent will launch Blender in the background (headless).
2. It will connect via MCP.
3. Type your request in the terminal.

Example Interaction:
```text
You: Create a brushed aluminum material with some scratches.
Agent: (Generating code...)
Tool Output: Material 'Brushed_Aluminum' created. Saved code to 'output/Brushed_Aluminum.py' and blend to 'output/Brushed_Aluminum.blend'
Agent: I have created the brushed aluminum material for you! It's saved in the output folder.
```

## Project Structure

- `agent/`: The "Client" side.
  - `main.py`: Entry point. Manages the MCP connection and REPL loop.
  - `llm.py`: unified generic wrapper for Gemini/OpenAI.
- `blender_server/`: The "Server" side (runs inside Blender).
  - `server.py`: MCP Server implementation (JSON-RPC loop).
  - `utils.py`: Actual Blender API (`bpy`) calls to create nodes and save files.
- `output/`: Generated artifacts (.blend, .py).

## How it Works
1. User inputs a prompt (e.g., "Make gold").
2. LLM (Gemini/GPT) decides to call the `create_procedural_material` tool.
3. Agent sends a JSON-RPC request to the Blender Process.
4. Blender Server executes the Python code using `exec()` inside Blender's memory.
5. Blender Server saves the result to `output/` and returns success.
6. Agent reports back to the User.
