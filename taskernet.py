from telebot import types
from uuid import uuid4
import urllib
from utils import *
import aiohttp

TASKERNET_URL = "https://taskernet.com/"
TASKERNET_API = TASKERNET_URL + "_ah/api/datashare/v1/"


# get shares for the query from taskernet
async def fetch_shares(query):
    encoded_query = urllib.parse.quote(query)
    url = f"{TASKERNET_API}shares/public?a=0&tags=&q={encoded_query}&minDate=AllTime"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    shares_data = await response.json()
                    if "shares" in shares_data:
                        log(
                            f"Found {len(shares_data['shares'])} shares for \"{query}\""
                        )
                        return shares_data
                else:
                    log(f"Not 200. {await response.text()}")
        except aiohttp.ClientError as e:
            log(f"Error fetching shares: {e}")

    return None


async def fetch_info_from_url(shareurl):
    id = shareurl.split(f"{TASKERNET_URL}shares/?user=")[1]
    formatted_id = id.replace("&id=", "/")
    url = f"{TASKERNET_API}shares/{formatted_id}?a=0&countView=false"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
        except aiohttp.ClientError as e:
            log(f"Error fetching data from shareurl: {e}")

    return None


def get_buttons(query, url):
    buttons = types.InlineKeyboardMarkup(row_width=2)
    btn_retry = types.InlineKeyboardButton(
        "Search again", switch_inline_query_current_chat=query
    )
    btn_open = types.InlineKeyboardButton("Open in Browser", url=url)
    buttons.row(btn_retry, btn_open)
    return buttons


def get_views_and_downloads(data):
    if "stats" in data:
        data = data["stats"]
    if "views" in data and "downloads" in data:
        return data["views"], data["downloads"]
    else:
        return None, None


def parse_description(data):
    description_html = data["description"]
    description = parse_text_for_tg_markdown(description_html)
    description += "\n"
    return description


# prepare input message(visible in chat) to share
def prepare_input_message(data):
    if "date" in data:
        date = "Date: {}\n".format(timestamp_to_date(data["date"]))
    else:
        date = ""
    views, downloads = get_views_and_downloads(data)
    message_text = f"\n#{data['type']}\n\n*{data['name']}*\n\nViews: {views} | Downloads: {downloads}\n{date}\n"
    if "tags" in data:
        message_text += " ".join([f"#{tag}" for tag in data["tags"]])
    if "description" in data:
        message_text += parse_description(data)
    return message_text, {"message_text": str(message_text), "parse_mode": "Markdown"}


async def get_info_from_inline_url(url):
    results = []
    data = await fetch_info_from_url(url)
    if data:
        data = data["info"]
        text_message, input_message = prepare_input_message(data)
        views, downloads = get_views_and_downloads(data)
        description = f" Views: {views} | Downloads: {downloads} \n"
        results.append(
            types.InlineQueryResultArticle(
                id=str(uuid4()),
                title=data["id"],
                input_message_content=types.InputTextMessageContent(**input_message),
                url=url,
                description=description,
                reply_markup=get_buttons(data["name"], url),
            )
        )
        return results
    return None


# these dictonaries are needed later to edit message
results_dict = {}
urls_dict = {}
buttons_dict = {}


def prepare_inline_results(query, data):
    results = []
    shares = data["shares"]
    for share in shares:
        id = str(uuid4())
        title = share["id"]
        text_message, input_message = prepare_input_message(share)
        url = share["url"]
        views, downloads = get_views_and_downloads(share)
        description = f" Views: {views} | Downloads: {downloads} \n" + " ".join(
            [f"#{tag}" for tag in share["tags"]]
        )
        buttons = get_buttons(query, url)
        buttons_dict[id] = buttons
        results_dict[id] = text_message
        urls_dict[id] = url
        results.append(
            types.InlineQueryResultArticle(
                id=id,
                title=title,
                input_message_content=types.InputTextMessageContent(**input_message),
                # url=url,
                description=description,
                reply_markup=buttons,
            )
        )
    return results


async def get_inline_data(query):
    if query.startswith(TASKERNET_URL):
        results = await get_info_from_inline_url(query)
    else:
        data = await fetch_shares(query)
        if data is None:
            results = []
        else:
            results = prepare_inline_results(query, data)
    return results


def get_message_url_and_button_for(id):
    """
    Returns message, url and button for the given inline message id.
    """
    message = results_dict.get(id)
    url = urls_dict.get(id)
    button = buttons_dict.get(id)
    return message, url, button


# get description from the share url
async def get_description(shareurl):
    data = await fetch_info_from_url(shareurl)
    if data:
        data = data["info"]
        description = parse_description(data)
        return description
    return None
