import asyncio
from aiohttp import web

routes = web.RouteTableDef()

@routes.get('/')
async def hello(request):
    return web.Response(text="Bot aktif ve çalışıyor!")

async def run_web():
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

def keep_alive():
    loop = asyncio.get_event_loop()
    loop.create_task(run_web())