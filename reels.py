import json
import os
import re
import requests

def translate_color(hex_color, target_language='en'):
    url = f"https://www.thecolorapi.com/id?hex={hex_color.lstrip('#')}"
    response = requests.get(url)
    data = response.json()

    if 'name' in data:
        color_name = data['name']['value']
        return color_name
    else:
        return 'Unknown color'

def is_valid_hex(color):
    pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'

    if re.match(pattern, color):
        trans_color = translate_color(color)
        if trans_color != 'Unknown color':
            print(f"Color '{trans_color}' was applied.")
            return True
        else:
            print(trans_color)
    else:
        return False

def user_custom():
    while True:
        print("Choose the foreground color (hex code) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('fg_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

    while True:
        print("Choose the background color (hex code) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('bg_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

    while True:
        print("Choose the border color (hex code) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('border_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

    while True:
        print("Choose the text color (hex code)\nRecommend white (#FFFFFF) or black (#000000) ")
        choice = input("Enter a hexadecimal color: ")

        if is_valid_hex(choice):
            modify_graphic('text_color', choice)
            break
        else:
            print("Invalid hexadecimal format")

def path_config(config_file):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    folder_name='config_template'

    folder_path = os.path.join(current_dir, folder_name)

    file_name=config_file

    json_file_path = os.path.join(folder_path, file_name)

    return json_file_path

def path_graphic(graphic_file):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    folder_name ='graphic_templates'

    folder_path = os.path.join(current_dir, folder_name)

    file_name = graphic_file

    json_file_path = os.path.join(folder_path, file_name)

    return json_file_path

def modify_graphic(color_config, hex_color):
    
    json_file_path = path_graphic('main_template.json')

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Modify the fg_color value
    data["custom_template"][color_config] = hex_color
    
    # Write the modified data back to the file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)

def modify_config(config_file, type, value, index=0):
    
    json_file_path = path_config(config_file)

    # Read the JSON file
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    if(type == 'graphic_template'):
        data['clip_parameters']['clip_graphic_template'][type] = value
    elif(type == 'action'):
        data['clips'][index]['clip_meta'][0][type] = value
    
    # Write the modified data back to the file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
def count_clips(config_json):
    
    json_path_file = path_config(config_json)

    with open(json_path_file, 'r') as file:
        data = json.load(file)

    if 'clips' in data:
        return len(data['clips'])
    else:
        return 0

def user_options():
    config = None
    while True:
        cmeta = 'action'
        print("Choose a config template (default: example_1clip.json): \n1. example_1clip.json\n2. example_8clip.json")
        choice = input("Enter your choice (1/2): ")

        if choice == '1':
            config = 'example_1clip.json'
            while True:
                print("Choose an action for the clip (default: goal): \n1. Goal\n2. Shot\n3. Yellow card\n4. Red card\n5. Penalty")
                choice = input("Enter your choice (1/2/3/4/5): ")
                if choice == '1':
                    modify_config(config, cmeta, 'goal')
                elif choice == '2':
                    modify_config(config, cmeta, 'shot')
                elif choice == '3':
                    modify_config(config, cmeta, 'yellow card')
                elif choice == '4':
                    modify_config(config, cmeta, 'red card')
                elif choice == '5':
                    modify_config(config, cmeta, 'penalty')
                else:
                    print(f"Error resolving input '{choice}'")
                    continue
                break
            break
        elif choice == '2':
            config = 'example_8clip.json'
            num_clip = 0
            while num_clip < 8:
                while True:
                    print(f"Choose an action for clip #{num_clip+1} (default: goal): \n1. Goal\n2. Shot\n3. Yellow card\n4. Red card\n5. Penalty")
                    choice = input("Enter your choice (1/2/3/4/5): ")
                    if choice == '1':
                        modify_config(config, cmeta, 'goal', num_clip)
                        
                    elif choice == '2':
                        modify_config(config, cmeta, 'shot', num_clip)
                        
                    elif choice == '3':
                        modify_config(config, cmeta, 'yellow card', num_clip)
                        
                    elif choice == '4':
                        modify_config(config, cmeta, 'red card', num_clip)
                        
                    elif choice == '5':
                        modify_config(config, cmeta, 'penalty', num_clip)
                        
                    else:
                        print(f"Error resolving input '{choice}'")
                        continue
                    num_clip += 1
                    break
            break
        else:
            print(f"Error resolving input '{choice}'")

    while True:
        gtemp = 'graphic_template'
        print("Choose a color template (default: yellow): \n1. Red\n2. Orange\n3. Yellow\n4. Custom")
        choice = input("Enter your choice (1/2/3/4): ")

        if choice == '1' or choice == 'red':
            modify_config(config, gtemp, 'red_template')
            break
        elif choice == '2' or choice == 'orange':
            modify_config(config, gtemp, 'orange_template')
            break
        elif choice == '3' or choice == 'yellow':
            modify_config(config, gtemp, 'yellow_template')
            break
        elif choice == '4' or choice == 'custom':
            user_custom()
            modify_config(config, gtemp, 'custom_template')
            break
        else:
            print(f"Error resolving input '{choice}' ")

def main():
    user_options()

if __name__ == '__main__':
    main()

