from aiohttp import web
from bot import setup
if __name__ == '__main__':
    web.run_app(setup(), host="0.0.0.0", port=5151)