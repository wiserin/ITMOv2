def calculate_average(numbers: list[int]) -> float:
    return sum(numbers) / len(numbers)


def find_user(users: dict, user_id: str):
    return users[user_id]


def add_item(item: str, items: list[str] = []):
    items.append(item)
    return items
