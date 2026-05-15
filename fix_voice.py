import winreg
import sys

def copy_onecore_to_sapi5():
    """
    Copies Windows OneCore voices to SAPI5 registry so pyttsx3 can see them.
    Requires Administrator privileges.
    """
    onecore_path = r"SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"
    sapi5_path = r"SOFTWARE\Microsoft\Speech\Voices\Tokens"

    try:
        # Open OneCore tokens
        onecore_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, onecore_path)
        num_voices = winreg.QueryInfoKey(onecore_key)[0]
        
        print(f"Found {num_voices} OneCore voices.")
        
        for i in range(num_voices):
            voice_name = winreg.EnumKey(onecore_key, i)
            
            # Check if it's a Thai voice
            if "thTH" in voice_name or "th-th" in voice_name.lower():
                print(f"Processing Thai voice: {voice_name}")
                
                # Source path
                src_path = f"{onecore_path}\\{voice_name}"
                # Destination path
                dst_path = f"{sapi5_path}\\{voice_name}"
                
                try:
                    # Create the destination key
                    dst_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, dst_path)
                    
                    # Copy all values from source to destination
                    src_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, src_path)
                    num_values = winreg.QueryInfoKey(src_key)[1]
                    for j in range(num_values):
                        val_name, val_data, val_type = winreg.EnumValue(src_key, j)
                        winreg.SetValueEx(dst_key, val_name, 0, val_type, val_data)
                    
                    # Also copy the Attributes subkey
                    src_attr_path = f"{src_path}\\Attributes"
                    dst_attr_path = f"{dst_path}\\Attributes"
                    
                    src_attr_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, src_attr_path)
                    dst_attr_key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, dst_attr_path)
                    
                    num_attr_values = winreg.QueryInfoKey(src_attr_key)[1]
                    for j in range(num_attr_values):
                        val_name, val_data, val_type = winreg.EnumValue(src_attr_key, j)
                        winreg.SetValueEx(dst_attr_key, val_name, 0, val_type, val_data)
                    
                    print(f"✅ Successfully unlocked: {voice_name}")
                except PermissionError:
                    print(f"❌ Permission Denied: Please run this script as Administrator!")
                    return
                except Exception as e:
                    print(f"❌ Error copying {voice_name}: {e}")
            else:
                print(f"Skipping non-Thai voice: {voice_name}")

        print("\nDone! Please try running RobotBrain.py again.")

    except FileNotFoundError:
        print("❌ OneCore voices registry path not found.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    copy_onecore_to_sapi5()
