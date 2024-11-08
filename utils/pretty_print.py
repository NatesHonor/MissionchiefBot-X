import art

def display_message(message):
    ascii_art = art.text2art(message)
    print(ascii_art)

def display_error(message):
    print(f"\033[91m{message}\033[0m")

def display_info(message):
    print(f"{message}")
