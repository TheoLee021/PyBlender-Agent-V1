import sys
import json
import traceback

# Add current directory to path so we can import utils
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import utils
except ImportError:
    # Fallback if running from root
    import blender_server.utils as utils

def log(msg):
    # Log to stderr to avoid corrupting stdout JSON
    sys.stderr.write(f"[BlenderServer] {msg}\n")
    sys.stderr.flush()

def handle_request(request):
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    log(f"Received request: {method}")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05", # MCP version
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "BlenderMCP",
                    "version": "0.1.0"
                }
            }
        }
    
    elif method == "notifications/initialized":
        # Sent after initialization
        return None 

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "create_procedural_material",
                        "description": "Create a procedural material in Blender using Python code. The code has access to 'bpy', 'material' (the material object), 'nodes', and 'links'.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Name of the material"},
                                "python_code": {"type": "string", "description": "Python code using bpy to create nodes. e.g. 'node_tex = nodes.new(\"ShaderNodeTexNoise\")'"}
                            },
                            "required": ["name", "python_code"]
                        }
                    },
                    {
                        "name": "list_materials",
                        "description": "List all existing materials in the Blender file.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                        }
                    },
                    {
                        "name": "save_blend_file",
                        "description": "Save the current Blender file to disk.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "filepath": {"type": "string", "description": "Path to save the .blend file (e.g., 'output.blend')"}
                            },
                            "required": ["filepath"]
                        }
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        result_content = []
        is_error = False

        if tool_name == "create_procedural_material":
            name = args.get("name")
            code = args.get("python_code")
            success, msg = utils.create_procedural_material(name, code)
            result_content.append({"type": "text", "text": msg})
            is_error = not success
            
        elif tool_name == "list_materials":
            mats = utils.list_materials()
            result_content.append({"type": "text", "text": json.dumps(mats)})

        elif tool_name == "save_blend_file":
            filepath = args.get("filepath")
            success, msg = utils.save_blend_file(filepath)
            result_content.append({"type": "text", "text": msg})
            is_error = not success
            
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": result_content,
                "isError": is_error
            }
        }

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }
        
    return None

def main():
    log("Starting Blender MCP Server...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
                
            request = json.loads(line)
            response = handle_request(request)
            
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
        except json.JSONDecodeError:
            log("Invalid JSON received")
        except Exception as e:
            log(f"Error: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
