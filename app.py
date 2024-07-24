import traceback
import asyncio
import datetime
from flask import Flask, request, Response, render_template
from botbuilder.core import BotFrameworkAdapterSettings, TurnContext, BotFrameworkAdapter
from botbuilder.schema import Activity, ActivityTypes
from bot import MyBot
from config import DefaultConfig

CONFIG = DefaultConfig()

app = Flask(__name__)

# Create adapter
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Catch-all for errors
async def on_error(context: TurnContext, error: Exception):
    traceback.print_exc()
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity("To continue to run this bot, please fix the bot source code.")
    if context.activity.channel_id == "emulator":
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        await context.send_activity(trace_activity)

ADAPTER.on_turn_error = on_error

# Create the Bot
BOT = MyBot()

# Listen for incoming requests on /api/messages
@app.route("/api/messages", methods=["POST"])
def messages():
    if request.headers["Content-Type"] == "application/json":
        body = request.json
    else:
        return Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        response = loop.run_until_complete(ADAPTER.process_activity(activity, auth_header, BOT.on_turn))
    except Exception as e:
        return Response(status=500)
    finally:
        loop.close()
    
    if response:
        return Response(response.body, status=response.status, content_type="text/plain")
    return Response(status=201)

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=CONFIG.PORT)
    except Exception as error:
        raise error
