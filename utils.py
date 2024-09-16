import folder_paths

def update_dynamic_inputs(input_type, num_inputs, prefix="input", options=None):
    if options is None:
        options = ['None']
    
    current_selected = ["None"] + [f"{prefix.capitalize()} {i+1}" for i in range(num_inputs)]
    inputs = {
        "required": {
            "selected": (current_selected,),
        }
    }
    for i in range(1, num_inputs + 1):
        inputs["required"][f"{prefix}_{i}"] = (options,)
    return inputs

def get_lora_list():
    return ['None'] + folder_paths.get_filename_list("loras")

# Add more utility functions here as needed for future nodes