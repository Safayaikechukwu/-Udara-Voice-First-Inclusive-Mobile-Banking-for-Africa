import asyncio
import base64
import json
import os
import websockets
from dotenv import load_dotenv

from banking_functions import FUNCTION_MAP

load_dotenv()

def sts_connect():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise Exception("DEEPGRAM_API_KEY environment variable not set")
    
    sts_ws = websockets.connect(
        "wss://agent.deepgram.com/v1/agent/converse",
        subprotocols=["token", api_key]
    )

    return sts_ws


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

#Barge-in handler, if deepgram detects that the user has interrupted the agent, it will send a clear event to twilio
async def handle_barge_in(decoded, twilio_ws, streamsid):
    if decoded["type"] == "UsertStartedSpeaking":
        clear_message = {
            "event": "clear",
            "streamSid": streamsid
        }
        await twilio_ws.send(json.dumps(clear_message))

def execute_function_call(func_name, arguments):
    if func_name in FUNCTION_MAP:
        result = FUNCTION_MAP[func_name](**arguments)
        print(f"Function '{func_name}' executed with result: {result}")
        return result
    else:
        result = {"error": f"Function '{func_name}' not found."}
        print(result)
        return result
    
def create_function_call_response(func_id, func_name, result):
    return {
        "type": "FunctionCallResponse",
        "id": func_id,
        "name": func_name,
        "content": json.dumps(result)
    }

async def handle_function_call_request(decoded, sts_ws):
    try:
        for function_call in decoded["functions"]:
            func_name = function_call["name"]
            func_id = function_call["id"]
            arguments = json.loads(function_call["arguments"])

            print(f"Function Call Request: {func_name} with ID: {func_id} and arguments: {arguments}")
            
            result = execute_function_call(func_name, arguments)

            function_result = create_function_call_response(func_id, func_name, result)
            await sts_ws.send(json.dumps(function_result))
            print(f"Sent function result: {function_result}")

    except Exception as e:
        print(f"An error occurred: {e}")
        error_result = create_function_call_response(
            func_id if 'func_id' in locals() else "unknown",
            func_name if 'func_name' in locals() else "unknown",
            result: {"error": f"Function failed with: {str(e)}"}
        )
        await sts_ws.send(json.dumps(error_result))

async def handle_text_message(decoded, twilio_ws, sts_ws, streamsid):
    await handle_barge_in(decoded, twilio_ws, streamsid)

    if decoded["type"] == "FunctionCallRequest":
        await handle_function_call_request(decoded, sts_ws)
    #TODO: Handle function calling

#Sending the audio data from twilio to deepgram
async def sts_sender(sts_ws, audio_queue):
    print("sts sender started")
    while True:
        chunk = await audio_queue.get()
        await sts_ws.send(chunk)

#The receiver from deepgram, to know what to do with the data. If response is text, 
# send it to twilio. If barge-in, stop the audio from twilio. If bytes(audio), send it to twilio
async def sts_receiver(sts_ws, twilio_ws, streamsid_queue):
    print("sts receiver started")
    streamsid = await streamsid_queue.get()

    async for message in sts_ws:
        #If the message is a text message
        if type(message) == str:
            print(message)
            decoded = json.loads(message)
            await handle_text_message(decoded, twilio_ws, sts_ws, streamsid)
            continue
        
        #If the message is raw audio data
        #converting the raw audio to base64 then decoded using ascii and sending it to twilio
        raw_mulaw = message
        media_message = {
            "event": "media",
            "streamSid": streamsid,
            "media": {"payload": base64.b64encode(raw_mulaw).decode("ascii")}
        }

        await twilio_ws.send(json.dumps(media_message))

#Taking the audio from twilio, dividing it into chunks and putting it in a queue
async def twilio_receiver(twilio_ws, audio_queue, streamsid_queue):
    BUFFER_SIZE = 20 * 160  # Adjust buffer size as needed
    inbuffer = bytearray(b"")

    async for message in twilio_ws:
        try:
            data = json.loads(message)
            event = data["event"]

            if event == "start":
                print("get streamsid")
                start = data["start"]
                streamsid = start["streamSid"]
                streamsid_queue.put_nowait(streamsid)
            elif event == "connected":
                continue
            elif event == "media":
                media = data["media"]
                payload = media["payload"]
                chunk = base64.b64decode(payload)
                if media["track"] == "inbound":
                    inbuffer.extend(chunk)
            elif event == "stop":
                break

            while len(inbuffer) >= BUFFER_SIZE:
                chunk = inbuffer[:BUFFER_SIZE]
                audio_queue.put_nowait(chunk)
                inbuffer = inbuffer[BUFFER_SIZE:]
            
        except:
            break

async def twilio_handler(twilio_ws):
    audio_queue = asyncio.Queue()
    streamsid_queue = asyncio.Queue()

    async with sts_connect() as sts_ws:
        config_message = load_config()
        await sts_ws.send(json.dumps(config_message))

        await asyncio.wait(
            [
                asyncio.ensure_future(sts_sender(sts_ws, audio_queue)),
                asyncio.ensure_future(sts_receiver(sts_ws, twilio_ws, streamsid_queue)),
                asyncio.ensure_future(twilio_receiver(twilio_ws, audio_queue, streamsid_queue))
            ]
        )

        await twilio_ws.close()

async def main():
    await websockets.serve(twilio_handler, "localhost", 5000)
    print("Server started")
    await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())