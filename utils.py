def splitKeyboardButtonsToRows(buttons: list) -> list:
    return [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
def shortenToMaxLength(text: str, maxLength: int) -> str:
    if len(text) > maxLength:
        if maxLength <= 3:
            return text[:maxLength]
        return text[:maxLength - 3] + "..."
    else:
        return text
