import bpy
import os

def delete_default_cube():
    """Deletes the default Cube object if it exists."""
    cube = bpy.data.objects.get("Cube")
    if cube:
        bpy.data.objects.remove(cube, do_unlink=True)

def create_procedural_material(name: str, python_code: str):
    """
    Creates or overwrites a material with the given name and executes the python_code
    to generate nodes.
    """
    # Execution environment
    local_vars = {}
    
    delete_default_cube()
    
    try:
        # We wrap the code to ensure it runs
        exec(python_code, globals(), local_vars)

        # Auto-Assign to Preview Object
        preview_name = "PreviewSphere"
        obj = bpy.data.objects.get(preview_name)
        if not obj:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
            obj = bpy.context.active_object
            obj.name = preview_name
            bpy.ops.object.shade_smooth()
        
        # Find the material (assuming the script created it with the given name)
        mat = bpy.data.materials.get(name)
        if mat:
            if not obj.data.materials:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat
        
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
