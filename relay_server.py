"""
Hēlapidi 1v1 host-relay server — matches the REAL client protocol found in index.html.

Model: whoever joins a room FIRST is the host (assigned id 'p1') and runs the
authoritative simulation locally (same engine already used for local 2P). The
second joiner is the guest ('p2'). This server does not simulate anything —
it is a pure router:
  - guest's `input` / `inputBatch`  -> forwarded to host
  - host's `state`                  -> forwarded to guest
  - `ping`                          -> answered directly, not relayed
  - `rtcOffer` / `rtcAnswer` / `rtcIce` -> forwarded to the other player, untouched

Scope: exactly 2 players per room (1v1 only), matching the id convention
CONFIG.players already uses client-side ('p1', 'p2'). A 3rd join attempt is
rejected. 2v2/4v4 need a different id scheme plus client-side camera/HUD work
that hasn't been done yet — deliberately not attempted here.
"""

import asyncio
import json

import websockets

rooms: dict[str, dict] = {}
# rooms[room_id] = {'p1': ws_or_None, 'p2': ws_or_None}

conn_room: dict[object, str] = {}   # websocket -> room_id
conn_id: dict[object, str] = {}     # websocket -> 'p1' | 'p2'


async def send(ws, msg: dict):
    try:
        await ws.send(json.dumps(msg))
    except websockets.exceptions.ConnectionClosed:
        pass


def other_id(pid: str) -> str:
    return 'p2' if pid == 'p1' else 'p1'


async def handle_join(ws, msg: dict):
    room_id = msg.get('roomId') or 'default'
    room = rooms.setdefault(room_id, {'p1': None, 'p2': None})

    if room['p1'] is None:
        pid = 'p1'
    elif room['p2'] is None:
        pid = 'p2'
    else:
        await send(ws, {'type': 'event', 'event': 'roomFull', 'data': {}})
        return

    room[pid] = ws
    conn_room[ws] = room_id
    conn_id[ws] = pid
    await send(ws, {'type': 'playerId', 'id': pid})
    print(f"[join] room={room_id} assigned={pid}")


async def relay_to_peer(ws, msg: dict):
    """Forward a message verbatim to the other player in the same room, if present."""
    room_id = conn_room.get(ws)
    my_id = conn_id.get(ws)
    if room_id is None or my_id is None:
        return
    room = rooms.get(room_id)
    if not room:
        return
    peer = room.get(other_id(my_id))
    if peer is not None:
        await send(peer, msg)


async def handler(ws):
    try:
        async for raw in ws:
            msg = json.loads(raw)
            mtype = msg.get('type')

            if mtype == 'join':
                await handle_join(ws, msg)

            elif mtype in ('input', 'inputBatch'):
                # guest -> host only, by construction (host never sends these upstream)
                await relay_to_peer(ws, msg)

            elif mtype == 'state':
                # host -> guest only, by construction
                await relay_to_peer(ws, msg)

            elif mtype == 'ping':
                await send(ws, {'type': 'pong'})

            elif mtype in ('rtcOffer', 'rtcAnswer', 'rtcIce'):
                await relay_to_peer(ws, msg)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        room_id = conn_room.pop(ws, None)
        pid = conn_id.pop(ws, None)
        if room_id and pid and room_id in rooms:
            rooms[room_id][pid] = None
            peer = rooms[room_id].get(other_id(pid))
            if peer is not None:
                await send(peer, {'type': 'event', 'event': 'peerDisconnected', 'data': {'id': pid}})
            if rooms[room_id]['p1'] is None and rooms[room_id]['p2'] is None:
                del rooms[room_id]
        print(f"[disconnect] room={room_id} id={pid}")


async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("1v1 relay server listening on ws://0.0.0.0:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
