import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mazic.server")

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = BASE_DIR / "assets"
FRAMES_DIR = ASSETS_DIR / "frames"
TUNNEL_FILE = BASE_DIR / "tunnel_url.txt"

# Game Room storage & WebSocket tracking
# rooms: dict[room_id, GameRoom]
rooms: Dict[str, Any] = {}
# room_connections: dict[room_id, dict[player_id, WebSocket]]
room_connections: Dict[str, Dict[str, WebSocket]] = {}

# Background loop task handle
game_loop_task: Optional[asyncio.Task] = None


def get_tunnel_url() -> str:
    """Returns active Cloudflare tunnel URL from env or tunnel_url.txt."""
    if "TUNNEL_URL" in os.environ and os.environ["TUNNEL_URL"].strip():
        return os.environ["TUNNEL_URL"].strip()
    if TUNNEL_FILE.exists():
        try:
            val = TUNNEL_FILE.read_text(encoding="utf-8").strip()
            if val:
                return val
        except Exception as exc:
            logger.warning(f"Failed to read tunnel_url.txt: {exc}")
    return ""


def get_game_room_class():
    """Dynamically loads GameRoom from server.game_engine."""
    from server.game_engine import GameRoom
    return GameRoom


def get_or_create_room(room_id: str = "main"):
    """Gets or instantiates a GameRoom for room_id."""
    if room_id not in rooms:
        RoomCls = get_game_room_class()
        rooms[room_id] = RoomCls(room_id=room_id)
        room_connections[room_id] = {}
        logger.info(f"Initialized new GameRoom: {room_id}")
    return rooms[room_id]


def get_room_dungeon_payload(room: Any) -> dict:
    """Returns the dungeon initialization payload for clients."""
    if hasattr(room, "get_init_payload"):
        return room.get_init_payload()
    return getattr(room, "dungeon", {})


def forward_player_input(room: Any, player_id: str, msg: dict) -> None:
    """Forwards client input to GameRoom (supporting handle_input and handle_player_input)."""
    if hasattr(room, "handle_input"):
        room.handle_input(player_id, msg)
    elif hasattr(room, "handle_player_input"):
        room.handle_player_input(player_id, msg)


async def server_tick_loop():
    """Authoritative server loop running at 30 Hz (33.3 ms per tick)."""
    logger.info("Starting Mazic authoritative 30 Hz game loop...")
    tick_rate = 30.0
    dt = 1.0 / tick_rate

    while True:
        start_time = time.perf_counter()
        # Step all active rooms with connected clients
        for room_id, room in list(rooms.items()):
            active_clients = room_connections.get(room_id, {})
            if not active_clients:
                continue

            try:
                # Step physics, monsters AI, projectiles, spells and events
                snapshot = room.step(dt)
                if snapshot is None and hasattr(room, "get_snapshot"):
                    snapshot = room.get_snapshot()

                message = json.dumps({"type": "state", "state": snapshot})

                dead_sockets = []
                for p_id, ws in list(active_clients.items()):
                    try:
                        await ws.send_text(message)
                    except Exception:
                        dead_sockets.append(p_id)

                for p_id in dead_sockets:
                    logger.info(f"Removing dead socket for player {p_id} in room {room_id}")
                    active_clients.pop(p_id, None)
                    if hasattr(room, "remove_player"):
                        room.remove_player(p_id)

            except Exception as exc:
                logger.error(f"Error in room {room_id} tick: {exc}", exc_info=True)

        elapsed = time.perf_counter() - start_time
        sleep_time = max(0.001, dt - elapsed)
        await asyncio.sleep(sleep_time)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager starting and stopping the 30 Hz server loop."""
    global game_loop_task
    # Pre-create default room
    try:
        get_or_create_room("main")
    except Exception as exc:
        logger.warning(f"Could not pre-init room 'main' at startup (will retry on first connect): {exc}")

    game_loop_task = asyncio.create_task(server_tick_loop())
    yield
    if game_loop_task:
        game_loop_task.cancel()
        try:
            await game_loop_task
        except asyncio.CancelledError:
            pass
        logger.info("Mazic server tick loop stopped.")


app = FastAPI(title="Mazic Authoritative Server", lifespan=lifespan)

# Mount static asset frames
if FRAMES_DIR.exists():
    app.mount("/assets/frames", StaticFiles(directory=str(FRAMES_DIR)), name="frames")
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


# HTTP Routes
@app.get("/")
async def get_index():
    """Serves the main HTML5 game canvas."""
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"error": "web/index.html not found"}, status_code=404)
    return FileResponse(index_file, headers={"Cache-Control": "no-store"})


@app.get("/game.js")
async def get_game_js():
    """Serves game client JavaScript."""
    js_file = WEB_DIR / "game.js"
    if not js_file.exists():
        return JSONResponse({"error": "web/game.js not found"}, status_code=404)
    return FileResponse(js_file, media_type="application/javascript", headers={"Cache-Control": "no-store"})


@app.get("/voice.js")
async def get_voice_js():
    """Serves voice & audio relay client JavaScript."""
    voice_file = WEB_DIR / "voice.js"
    if not voice_file.exists():
        return JSONResponse({"error": "web/voice.js not found"}, status_code=404)
    return FileResponse(voice_file, media_type="application/javascript", headers={"Cache-Control": "no-store"})


@app.get("/web/{file_path:path}")
async def get_web_file(file_path: str):
    """Serves any resource under web/ with Cache-Control: no-store."""
    target = (WEB_DIR / file_path).resolve()
    if not target.is_relative_to(WEB_DIR) or not target.exists():
        return JSONResponse({"error": f"{file_path} not found"}, status_code=404)
    return FileResponse(target, headers={"Cache-Control": "no-store"})


@app.get("/api/info")
async def api_info():
    """Returns tunnel URL, local URL, and list of 0x72 animation frame PNG files."""
    frames = [f.name for f in FRAMES_DIR.glob("*.png")] if FRAMES_DIR.exists() else []
    return {
        "tunnel_url": get_tunnel_url(),
        "local_url": "http://localhost:8090",
        "frames": frames,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "rooms": list(rooms.keys())}


# WebSocket Route
@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str = "main"):
    """Authoritative multiplayer WebSocket endpoint handling inputs, voice, webrtc, and reset."""
    await websocket.accept()
    player_id = f"p_{uuid.uuid4().hex[:6]}"
    player_name = "Wizard"
    player_skin = "wizzard_m"

    room = get_or_create_room(room_id)
    if room_id not in room_connections:
        room_connections[room_id] = {}

    # Wait for initial join message with name & skin
    try:
        raw_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        init_data = json.loads(raw_msg)
        if init_data.get("type") == "join":
            player_name = init_data.get("name") or player_name
            player_skin = init_data.get("skin") or player_skin
    except (asyncio.TimeoutError, json.JSONDecodeError):
        logger.warning(f"No valid join payload received for {player_id}, using defaults.")

    # Add player to game room
    room.add_player(player_id, player_name, player_skin)
    room_connections[room_id][player_id] = websocket
    logger.info(f"Player '{player_name}' ({player_id}) joined room '{room_id}'")

    # Send initial dungeon layout, player_id, and tunnel URL
    init_payload = {
        "type": "init",
        "player_id": player_id,
        "dungeon": get_room_dungeon_payload(room),
        "tunnel_url": get_tunnel_url(),
    }
    await websocket.send_text(json.dumps(init_payload))

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            mtype = msg.get("type")

            if mtype == "input":
                # Forward player inputs (movement, aim_angle, mic_rms, spells) to authoritative engine
                forward_player_input(room, player_id, msg)

            elif mtype == "reset_game":
                # Re-generate a brand-new procedural dungeon and reset all players
                logger.info(f"Resetting game room '{room_id}' on request of {player_id}")
                RoomCls = get_game_room_class()
                new_room = RoomCls(room_id=room_id)
                rooms[room_id] = new_room
                room = new_room

                dungeon_payload = get_room_dungeon_payload(new_room)
                # Re-register all connected players into the new dungeon
                for p_id, p_ws in list(room_connections.get(room_id, {}).items()):
                    p_name = player_name if p_id == player_id else "Ally"
                    p_skin = player_skin if p_id == player_id else "wizzard_f"
                    new_room.add_player(p_id, p_name, p_skin)
                    await p_ws.send_text(
                        json.dumps({
                            "type": "init",
                            "player_id": p_id,
                            "dungeon": dungeon_payload,
                            "tunnel_url": get_tunnel_url(),
                        })
                    )

            elif mtype == "force_transform":
                # Instant test button: toggle Monster Hive Mind / Demon Voice
                if hasattr(room, "force_transform"):
                    room.force_transform(player_id)
                elif hasattr(room, "_transform_player_to_monster") and player_id in getattr(room, "players", {}):
                    p = room.players[player_id]
                    if not p.is_monster:
                        room._transform_player_to_monster(p)
                    else:
                        p.is_monster = False
                        p.skin = "wizzard_m"
                        p.hp = 100.0
                        p.max_hp = 100.0
                elif hasattr(room, "players") and player_id in room.players:
                    p = room.players[player_id]
                    p.is_monster = not getattr(p, "is_monster", False)
                    if p.is_monster:
                        p.hp = 160.0
                        p.max_hp = 160.0
                        p.skin = "big_demon"
                    else:
                        p.hp = 100.0
                        p.max_hp = 100.0

            elif mtype == "spawn_bot_ally":
                # Instant test button: spawn simulated ally/monster
                if hasattr(room, "spawn_bot_ally"):
                    room.spawn_bot_ally()
                elif hasattr(room, "add_player"):
                    bot_id = f"bot_{uuid.uuid4().hex[:4]}"
                    room.add_player(bot_id, "Bot Ally", "elf_m")

            elif mtype == "webrtc_signal":
                # WebRTC peer-to-peer audio signaling relay
                target_id = msg.get("target_id")
                target_ws = room_connections.get(room_id, {}).get(target_id)
                if target_ws:
                    await target_ws.send_text(
                        json.dumps({
                            "type": "webrtc_signal",
                            "from_id": player_id,
                            "target_id": target_id,
                            "signal": msg.get("signal"),
                        })
                    )

            elif mtype == "voice_frame":
                # Real-time WebSocket audio relay fallback (guarantees voice over Cloudflare tunnel)
                pcm_b64 = msg.get("pcm_b64")
                if pcm_b64:
                    voice_payload = json.dumps({
                        "type": "voice_frame",
                        "from_id": player_id,
                        "pcm_b64": pcm_b64,
                    })
                    for other_id, other_ws in list(room_connections.get(room_id, {}).items()):
                        if other_id != player_id:
                            try:
                                await other_ws.send_text(voice_payload)
                            except Exception:
                                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for player {player_id} in room {room_id}")
    except Exception as exc:
        logger.warning(f"WebSocket error for player {player_id}: {exc}")
    finally:
        room_connections.get(room_id, {}).pop(player_id, None)
        if hasattr(room, "remove_player"):
            room.remove_player(player_id)
