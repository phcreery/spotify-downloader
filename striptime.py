from datetime import timedelta
# from pytimeparse import parse as timeparse
from time import strptime


def __parse_duration(duration: str) -> float:
    try:
        if len(duration) > 5:
            padded = duration.rjust(8, '0')
            x = strptime(padded, '%H:%M:%S')
        elif len(duration) > 2:
            padded = duration.rjust(5, '0')
            x = strptime(padded, '%M:%S')
        else:
            x = strptime(duration, '%S')

        return timedelta(hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds()
    except (ValueError, TypeError):
        return 0.0


def __parse_duration2(duration: str) -> float:
    try:
        # return float(sum(x * int(t) for x, t in zip([3600, 60, 1], duration.split(":"))))

        seconds = 0

        # {(3600, "h"), (60, "m"), (1, "s")}
        mapped = zip([3600, 60, 1], duration.split(":"))
        for x, t in mapped:
            seconds += x * int(t)
        return float(seconds)
    except (ValueError, TypeError):
        return 0.0


if __name__ == "__main__":
    print(__parse_duration("23:24:24"))  # 84264
    print(__parse_duration2("23:24:24"))  # 84264

    print(__parse_duration("25:24:24"))  # 91464
    print(__parse_duration2("25:24:24"))  # 91464
