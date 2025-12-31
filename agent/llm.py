import os
import json
import copy
from openai import OpenAI

class LLMClient:
    def __init__(self, provider="gemini", tools=None, history=None):
        self.provider = provider.lower()
        self.tools = tools or []
        self.history = history or [] # [{"role": "user", "content": ...}] for OpenAI
        self.chat_session = None
        self.genai = None # Handle for the module
        
        if self.provider == "gemini":
            import google.generativeai as genai
            self.genai = genai
            api_key = os.getenv("GEMINI_API_KEY")
            self.model_name = os.getenv("GEMINI_MODEL", "gemini")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            
            self.genai.configure(api_key=api_key)
            self.model = self.genai.GenerativeModel(self.model_name, tools=self.tools)
            self.chat_session = self.model.start_chat(enable_automatic_function_calling=False)
            
        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            self.model_name = os.getenv("OPENAI_MODEL", "gpt")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found")
            
            self.client = OpenAI(api_key=api_key)
            # OpenAI doesn't have a stateful "chat session" object like Gemini, 
            # so we manage self.history manually.
            
            # Convert Gemini-style tools to OpenAI format
            self.openai_tools = []
            for t in self.tools:
                # We need to sanitize the function definition
                openai_func = self._sanitize_schema(t)
                self.openai_tools.append({
                    "type": "function",
                    "function": openai_func
                })
                
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _sanitize_schema(self, schema):
        """Helper to convert Gemini schema (uppercase types) to OpenAI (lowercase)"""
        new_schema = copy.deepcopy(schema)
        
        def recurse(d):
            if isinstance(d, dict):
                if "type" in d and isinstance(d["type"], str):
                    d["type"] = d["type"].lower()
                for v in d.values():
                    recurse(v)
            elif isinstance(d, list):
                for i in d:
                    recurse(i)
        
        recurse(new_schema)
        return new_schema

    def send_message(self, message):
        """
        Sends a message and returns (text_response, function_call_info).
        function_call_info is None if no call, or {"name": str, "args": dict}.
        """
        if self.provider == "gemini":
            response = self.chat_session.send_message(message)
            
            # Check for function call
            fc = None
            text_response = ""
            
            try:
                # Iterate parts to find function call
                for part in response.parts:
                    if part.function_call:
                        fc = {"name": part.function_call.name, "args": dict(part.function_call.args)}
                
                # If there's a function call, response.text might fail
                if not fc:
                    text_response = response.text
                else:
                    # Optional: Check if there's also text parts, but for now safe default
                    # response.text fails if multiple parts have different types or just function call
                    # We try to extract text parts if any
                    texts = [p.text for p in response.parts if p.text]
                    text_response = "\n".join(texts)
                    
            except Exception:
                # Fallback if accessing attributes fails
                pass
            
            return text_response, fc

        elif self.provider == "openai":
            # Add user message to history
            self.history.append({"role": "user", "content": message})
            
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                tools=self.openai_tools if self.openai_tools else None,
                tool_choice="auto" if self.openai_tools else None
            )
            
            msg = completion.choices[0].message
            # Add assistant message to history (important for context)
            self.history.append(msg)

            text_response = msg.content or ""
            fc = None
            
            if msg.tool_calls:
                # OpenAI can return multiple calls, but to keep it simple and consistent with our loop,
                # we'll pick the first one or handle sequentially.
                # For this simple agent, let's just take the first one.
                t = msg.tool_calls[0]
                fc = {
                    "name": t.function.name,
                    "args": json.loads(t.function.arguments),
                    "id": t.id # OpenAI needs this for response
                }
                
            return text_response, fc

    def send_tool_result(self, tool_name, result, tool_call_id=None):
        """
        Sends the result of a tool execution back to the LLM.
        """
        if self.provider == "gemini":
            # Gemini expects a FunctionResponse
            response = self.chat_session.send_message(
                self.genai.protos.Content(
                    parts=[self.genai.protos.Part(
                        function_response=self.genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": result}
                        )
                    )]
                )
            )
            
            # Check for function call
            fc = None
            text_parts = []
            
            try:
                # Iterate parts to extract content safely
                for part in response.parts:
                    if part.function_call:
                        fc = {"name": part.function_call.name, "args": dict(part.function_call.args)}
                    else:
                        # Try to extract text from non-function parts
                        try:
                            if part.text:
                                text_parts.append(part.text)
                        except:
                            pass
                
                text_response = "\n".join(text_parts)
                    
            except Exception:
                # Fallback
                try: 
                    text_response = response.text
                except:
                    pass
            
            return text_response

        elif self.provider == "openai":
            # Add tool result to history
            self.history.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": str(result)
            })
            
            # Get follow-up response
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                tools=self.openai_tools if self.openai_tools else None
            )
            
            msg = completion.choices[0].message
            self.history.append(msg)
            
            return msg.content
