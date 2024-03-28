valid_hex = '0123456789ABCDEF'.__contains__
RESET = '\033[0m'


def rgb_to_hex(rgb):
    return '%02x%02x%02x' % rgb


def clean_hex(data):
    return ''.join(filter(valid_hex, data.upper()))


def fore_from_hex(text, hex_code) -> str:
    """
    Return a colorized string ready to be print
    References:
     - https://www.codespeedy.com/convert-rgb-to-hex-color-code-in-python/
    :param text:
    :param hex_code:
    :return:
    """
    hex_int = int(clean_hex(hex_code), 16)
    return "\x1B[38;2;{};{};{}m{}\x1B[0m".format(hex_int >> 16, hex_int >> 8 & 0xFF, hex_int & 0xFF, text)


def get_color_escape(r, g, b, background=False):
    # https://stackoverflow.com/questions/45782766/color-python-output-given-rrggbb-hex-value
    return '\033[{};2;{};{};{}m'.format(48 if background else 38, r, g, b)
