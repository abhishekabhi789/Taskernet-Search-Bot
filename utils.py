import os
import inspect
import datetime
from markdownify import markdownify

tg_supported_html_tags = ["b", "i", "u", "s", "span", "a", "tg-emoji", "code", "pre"]


# get datetime for logging
def logging_time():
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%Y-%m-%d %H:%M:%S")
    return time_string


# format timestamp to date
def timestamp_to_date(timestamp):
    seconds = int(timestamp) / 1000
    dt = datetime.datetime.fromtimestamp(seconds)
    date = dt.strftime("%d %B %Y")
    return date


# convert html description to markdown/text
def parse_text_for_tg_markdown(html):
    try:
        description = markdownify(html, convert=tg_supported_html_tags)
    except:
        log(f"error parsing html description: {html}")
        description = ""
    finally:
        description += "\n\n"
    return description


def log(message):
    caller_frame = inspect.currentframe().f_back
    caller_module = inspect.getmodule(caller_frame)
    if caller_module:
        calling_file = os.path.basename(caller_module.__file__)
        message = calling_file + " " + message
    print(logging_time() + " " + message)
    # print(message)
