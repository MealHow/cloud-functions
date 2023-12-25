import re


def to_snake_case(s):
    s = s.lower()
    s = re.sub(r'\W+', '_', s)
    s = s.strip('_')

    return s


async def str_to_int(raw_data: str) -> int:
    data = raw_data.strip().split(".")[0]
    return int("".join([i for i in data if i.isdigit()]))
