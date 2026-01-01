import os
import sys
import json
import subprocess
import time

from dotenv import load_dotenv

try:
    from agent.llm import LLMClient
except ImportError:
    from llm import LLMClient

# Load environment variables
load_dotenv(override=True)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
BLENDER_PATH = os.getenv("BLENDER_PATH", "blender")

class BlenderMCPClient:
    def __init__(self, blender_path):
        self.blender_path = blender_path
        self.process = None
        self.request_id = 0

    def start(self):
        server_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blender_server", "server.py")
        cmd = [
            self.blender_path,
            "--background",
            "--python", server_script
        ]
        print(f"Starting Blender server: {' '.join(cmd)}")
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr, # Forward stderr
            text=True,
            bufsize=1 # Line buffered
        )
        
        # Initialize MCP Handshake
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05", # MCP version
            "capabilities": {},
            "clientInfo": {"name": "BlenderAgent", "version": "0.1.0"}
        })
        self._waiting_response() # Wait for initialize response
        
        self._send_notification("notifications/initialized", {})
        print("Blender MCP Connected.")

    def _send_request(self, method, params=None):
        self.request_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        json_line = json.dumps(req)
        self.process.stdin.write(json_line + "\n")
        self.process.stdin.flush()
        return self.request_id

    def _send_notification(self, method, params=None):
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        json_line = json.dumps(req)
        self.process.stdin.write(json_line + "\n")
        self.process.stdin.flush()

    def _waiting_response(self):
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Server closed connection")
            try:
                msg = json.loads(line)
                if "id" in msg and msg["id"] == self.request_id:
                    return msg
            except json.JSONDecodeError:
                continue

    def call_tool(self, name, arguments):
        self._send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        resp = self._waiting_response()
        
        if "error" in resp:
            return f"Error: {resp['error']['message']}"
        
        # Parse result
        content = resp.get("result", {}).get("content", [])
        text_res = [c["text"] for c in content if c["type"] == "text"]
        return "\n".join(text_res)

    def close(self):
        if self.process:
            self.process.terminate()

# Define tools
tools_def = [
    {
        "name": "create_procedural_material",
        "description": "Generate a 3D procedural material implementation in Blender nodes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING",
                    "description": "Name of the material"
                },
                "python_code": {
                    "type": "STRING",
                    "description": "Create a blender material from user input using Blender 4.5's Python API with BlenderMCP. Do not use image node or embed image. IMPORTANT: 1. 'ShaderNodeTexMusgrave' is removed in 4.5; use 'ShaderNodeTexNoise' instead. 2. For Principled BSDF, use 'Specular IOR Level' instead of 'Specular'."
                }
            },
            "required": ["name", "python_code"]
        }
    },
    {
        "name": "list_materials",
        "description": "List existing materials.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "save_blend_file",
        "description": "Save the current Blender file to disk.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filepath": {
                    "type": "STRING",
                    "description": "Path to save the .blend file (e.g., 'output.blend')"
                }
            },
            "required": ["filepath"]
        }
    }
]

import threading
import itertools

class Spinner:
    def __init__(self, message="Thinking..."):
        self.message = message
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._spin)

    def start(self):
        self.stop_event.clear()
        if not self.thread.is_alive():
            self.thread = threading.Thread(target=self._spin)
            self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join()

    def _spin(self):
        ws = itertools.cycle(["|", "/", "-", "\\"])
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r{self.message} {next(ws)}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(self.message) + 2) + "\r")
        sys.stdout.flush()

def main():
    client = BlenderMCPClient(BLENDER_PATH)
    try:
        client.start()
        
        print(f"Initializing LLM Provider: {LLM_PROVIDER}")
        llm = LLMClient(provider=LLM_PROVIDER, tools=tools_def)
        
        print(f"\nAgent is ready! (LLM Model: {llm.model_name})")
        print("Example: 'Create a shiny red metallic material'")
        print("Type 'quit' to exit")
        
        while True:
            user_input = input("\nYou('quit' to exit): ")
            if user_input.lower() in ["quit", "exit"]:
                break
                
            spinner = Spinner("Agent is thinking...")
            spinner.start()
            try:
                response_text, func_call = llm.send_message(user_input)
            finally:
                spinner.stop()
            
            # Print initial thought if any
            if response_text:
                print(f"Agent: {response_text}")

            # Limit loop count to prevent infinite loops
            loop_count = 0
            MAX_LOOPS = 10
            
            while func_call and loop_count < MAX_LOOPS:
                loop_count += 1
                fname = func_call["name"]
                fargs = func_call["args"]
                call_id = func_call.get("id")
                
                print(f"Agent calling tool: {fname}(...)({loop_count}/{MAX_LOOPS})")
                
                # Execute tool via MCP
                spinner_tool = Spinner(f"Running tool {fname}...")
                spinner_tool.start()
                try:
                    result = client.call_tool(fname, fargs)
                finally:
                    spinner_tool.stop()
                    
                print(f"Tool Output: {result}")
                
                # Feed result back to LLM
                spinner_res = Spinner("Analyzing result...")
                spinner_res.start()
                try:
                    # Reformatted to receive tuple (text, func_call)
                    response_text, func_call = llm.send_tool_result(fname, result, tool_call_id=call_id)
                finally:
                    spinner_res.stop()
                
                if response_text:
                    print(f"Agent: {response_text}")
            
            if loop_count >= MAX_LOOPS:
                print("Warning: Maximum tool loop limit reached.")
            
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
