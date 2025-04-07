import re


def split_markdown(text):
    # Паттерн для поиска форматированных блоков и обычного текста
    pattern = re.compile(
        r'(\*\*|\*|__|_|~~|`|```|\|\|)(.*?)\1'  # Форматированные блоки
        r'|'  # ИЛИ
        r'((?:(?!\*\*|\*|__|_|~~|`|```|\|\|).+)',  # Обычный текст
        re.DOTALL
    )

    parts = []
    for match in pattern.finditer(text):
        if match.group(1):
            # Форматированный блок
            md_tag = match.group(1)
            content = match.group(2)
            parts.append(('md', md_tag, content))
        else:
            # Обычный текст
            plain_text = match.group(3)
            if plain_text:
                parts.append(('plain', plain_text))

    return parts


# Пример использования
text = "Hello **world**! This is __test__ with ~~strikethrough~~ and `code`."
result = split_markdown(text)

for part in result:
    if part[0] == 'md':
        print(f"Markdown [{part[1]}]: {part[2]}")
    else:
        print(f"Plain text: {part[1]}")