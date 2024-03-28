import re


def precision_from_string(string):
    # this function was taken from ccxt
    parts = re.sub(r'0+$', '', string).split('.')
    return len(parts[1]) if len(parts) > 1 else 0
