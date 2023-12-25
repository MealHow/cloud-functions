import csv

import config
import helpers


async def _parse_csv(
        csv_data: str, keyword: str, fieldnames: list[str], delimiter: str = ";"
) -> list[dict]:
    split_data = csv_data.splitlines()
    new_split_data = []

    while delimiter not in split_data[0]:
        split_data.pop(0)

    for i in split_data:
        if i.strip() and keyword not in i.lower():
            strip_value = i.strip()
            if strip_value.count(delimiter) == len(fieldnames) - 1:
                new_split_data.append(strip_value)
            elif (
                    strip_value.count(delimiter) + strip_value.count(",")
                    == len(fieldnames) - 1
            ):
                new_split_data.append(strip_value.replace(",", delimiter))

    csv_data = "\n".join(new_split_data)
    reader = csv.DictReader(csv_data.splitlines(), delimiter=delimiter)
    reader.fieldnames = fieldnames
    return list(reader)


async def parse_diet_plan(raw_data: str) -> list[dict]:
    str_to_int_keys = (
        "day",
        "calories",
        "protein",
        "carbs",
        "fats",
        "preparation_time",
    )
    str_keys = (
        "meal_time",
        "meal_name",
    )

    for item in config.REPLACE_WORDS_MAPPING:
        raw_data = raw_data.replace(*item)
        raw_data = raw_data.replace(item[0].lower(), item[1])

    parsed_data = await _parse_csv(
        raw_data, keyword="preparation", fieldnames=config.MEAL_PLAN_FIELDNAMES
    )

    new_data = []
    for i in range(len(parsed_data)):
        try:
            for key in str_keys:
                parsed_data[i][key] = parsed_data[i][key].strip()

            for key in str_to_int_keys:
                parsed_data[i][key] = await helpers.str_to_int(parsed_data[i][key])
        except (ValueError, AttributeError):
            pass
        else:
            new_data.append(parsed_data[i])

    return new_data
