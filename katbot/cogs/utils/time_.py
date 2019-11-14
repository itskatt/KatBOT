import datetime


def ctimestamp(sep: str = "à"):
    return datetime.datetime.now().strftime(f"%d/%m/%Y {sep} %H:%M")


def gettime(sec):
    fmt = []

    # Years
    y = sec / 31557600
    if int(y) > 0:
        sec -= 31557600 * int(y)
        fmt.append(f"{int(y)} années")

    # Days
    d = sec / 86400
    if int(d) > 0:
        sec -= 86400 * int(d)
        fmt.append(f"{int(d)} jours")

    # Hours
    h = sec / 3600
    if int(h) > 0:
        sec -= 3600 * int(h)
        fmt.append(f"{int(h)} heures")

    # Minutes
    m = sec / 60
    if int(m) > 0:
        sec -= 60 * int(m)
        fmt.append(f"{int(m)} minutes")

    fmt.append(f"{int(sec)} secondes")

    return ", ".join(fmt)
