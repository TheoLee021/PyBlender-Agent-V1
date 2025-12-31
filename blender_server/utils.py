import bpy
import os

def create_procedural_material(name: str, python_code: str):
    """
    Creates or overwrites a material with the given name and executes the python_code
    to generate nodes.
    """
    # Execution environment
    local_vars = {}
    
    try:
        # We wrap the code to ensure it runs
        exec(python_code, globals(), local_vars)
        
        # Prepare output directory
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        safe_name = "".join([c if c.isalnum() else "_" for c in name])
        
        # Save Python code
        py_filename = os.path.join(output_dir, f"{safe_name}.py")
        with open(py_filename, "w") as f:
            f.write(python_code)
            
        # Auto-save Blend file
        blend_filename = os.path.join(output_dir, f"{safe_name}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_filename)
        
        return True, f"Material '{name}' created. Saved code to '{py_filename}' and blend to '{blend_filename}'"
    except Exception as e:
        return False, f"Error creating material: {str(e)}"

def list_materials():
    return [m.name for m in bpy.data.materials]

def save_blend_file(filepath: str):
    try:
        bpy.ops.wm.save_as_mainfile(filepath=filepath)
        return True, f"Saved to {filepath}"
    except Exception as e:
        return False, f"Failed to save: {str(e)}"
