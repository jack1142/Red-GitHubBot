import asyncio
import logging
import os

import gidgethub
from aiohttp import web
from gidgethub import sansio

from .routers import gh_router

log = logging.getLogger(__name__)

routes = web.RouteTableDef()


@routes.get("/")
async def hello(_request: web.Request) -> web.Response:
    # maybe one day there will be some front-facing UI, you can never know...
    return web.Response(text="Hello, world")


@routes.post("/webhook")
async def webhook(request: web.Request) -> web.Response:
    try:
        body = await request.read()
        secret = os.environ["GH_WEBHOOK_SECRET"]
        try:
            event = sansio.Event.from_http(request.headers, body, secret=secret)
        except gidgethub.ValidationFailure as exc:
            log.info("GH webhook failed secret validation: %s", exc)
            return web.Response(status=401, text=str(exc))
        except gidgethub.BadRequest as exc:
            log.info("GH webhook received a bad request (%d): %s", exc.status_code, exc)
            return web.Response(status=exc.status_code.value, text=str(exc))

        log.info("GH delivery ID: %s", event.delivery_id)

        if event.event == "ping":
            return web.Response(status=200)

        # Give GitHub some time to reach internal consistency.
        await asyncio.sleep(1)
        await gh_router.dispatch(event)

        return web.Response(status=200)
    except Exception as exc:
        log.error("The app did not handle an exception", exc_info=exc)
        return web.Response(status=500)


app = web.Application()
app.add_routes(routes)
