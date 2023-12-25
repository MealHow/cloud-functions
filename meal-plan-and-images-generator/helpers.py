import re


def to_snake_case(s):
    s = s.lower()
    s = re.sub(r'\W+', '_', s)
    s = s.strip('_')

    return s
