import asyncio
import functools
import json

from aiohttp import web, ClientSession
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from loguru import logger

def timer(interval):
    def decorator(f):
        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    await f(*args, **kwargs)
                except asyncio.CancelledError as e:
                    raise e
                except Exception:
                    logger.exception("Exception in {}", f.__name__)
                await asyncio.sleep(interval)
        return wrapper
    return decorator


class HTTPView(web.View):
    async def get(self):
        print("httpview get")
        pass

    async def post(self):
        return web.json_response(await self.handle(
            await self.request.text(),
            self.request.headers,
        ))


class WSView(web.View):
    async def get(self):
        self.ws = web.WebSocketResponse()
        await self.ws.prepare(self.request)

        async for message in self.ws:
            await self.ws.send_json(await self.handle(message.data, {}))

    async def handle(self, data, headers):
        raise NotImplementedError


class JSONRPCView(web.View):
    SCHEMA = {
        "additionalProperties": False,
        "properties": {
            "jsonrpc": {
                "enum": ["2.0"],
            },
            "id": {
                "type": "integer",
                "minimum": 1,
            },
            "method": {
                "type": "string",
            },
            "params": {
                "type": "object",
            },
        },
        "required": ["jsonrpc", "id", "method"],
    }

    def login_required(coroutine):
        async def wrapper(self, **params):
            db_client = self.request.app["database"]
            if "token" not in params:
                return None, "Have no token"
            session = db_client.get_session(token=params["token"])
            if session is None:
                return None, "Incorrect token"
            del params["token"]
            self.session = session
            return await coroutine(self, **params)

        return wrapper

    # jsonschema validator for json-rpc 2.0
    async def handle(self, data, headers):
        response_required = True
        response = {"jsonrpc": "2.0", "error": None, "result": None, "id": None}
        try:
            data = json.loads(data)
            validate(data, schema=self.SCHEMA)
            if hasattr(self, data["method"]):
                method = getattr(self, data["method"])
                response["result"], response["error"] = await method(**data.get("params", {}))
            else:
                response["error"] = f"Have no method '{data['method']}'"
            response["id"] = data["id"]
        except json.decoder.JSONDecodeError:
            response["error"] = "Incorrect format"
        except ValidationError as e:
            response["error"] = e.args[0]
            response["id"] = data.get("id")
        except Exception as e:
            print(e)
            response["error"] = "Server error"
        finally:
            if "error" in data:
                if data["error"]:
                    response_required = False
            if "result" in data:
                if data["result"]:
                    response_required = False
            return response, response_required
