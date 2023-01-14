def query_yes_no(question):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}


    while True:
        choice = input(question + " [Y/n] ").lower()
        if choice == "":
            return valid["yes"]
        elif choice in valid:
            return valid[choice]
        else:
            print(f"Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

def query_int(question):
    """Ask a question via input() and return the int answer"""
    while True:
        resp = input(question)
        if _is_integer(resp):
            return int(resp)
        else:
            print(f"Please respond with a integer number\n")

def _is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()