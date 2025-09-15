import asyncio
import json
from typing import Dict, Set

HOST = "26.101.24.101"
PORT = 9999

clients: Set[asyncio.StreamWriter] = set()
names: Dict[asyncio.StreamWriter, str] = {}

def jline(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")

async def broadcast(payload: dict, *, exclude: asyncio.StreamWriter | None = None):
    dead = []
    for w in clients:
        if w is exclude:
            continue
        try:
            w.write(jline(payload))
            await w.drain()
        except Exception:
            dead.append(w)
    for w in dead:
        clients.discard(w)
        names.pop(w, None)
        try:
            w.close()
            await w.wait_closed()
        except Exception:
            pass

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    clients.add(writer)
    name = None

    try:
        # 1) espera JOIN
        line = await reader.readline()
        if not line:
            raise ConnectionError("empty first line")
        try:
            msg = json.loads(line.decode("utf-8").strip())
        except json.JSONDecodeError:
            writer.write(jline({"type": "error", "error": "invalid_json"}))
            await writer.drain()
            return

        if msg.get("type") != "join" or not msg.get("name"):
            writer.write(jline({"type": "error", "error": "first_message_must_be_join_with_name"}))
            await writer.drain()
            return

        name = str(msg["name"])[:32]
        names[writer] = name

        # boas-vindas
        writer.write(jline({"type": "welcome", "you": name}))
        await writer.drain()
        await broadcast({"type": "system", "msg": f"{name} entrou no chat."}, exclude=writer)

        # 2) loop principal
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8").strip())
            except json.JSONDecodeError:
                writer.write(jline({"type": "error", "error": "invalid_json"}))
                await writer.drain()
                continue

            mtype = msg.get("type")
            if mtype == "chat":
                text = (msg.get("msg") or "")[:2000]
                if text:
                    await broadcast({"type": "chat", "from": name, "msg": text})
            elif mtype in ("file_info", "file_data", "file_end"):
                # retransmite arquivos para todos
                payload = dict(msg)
                payload["from"] = name
                await broadcast(payload, exclude=writer)
            elif mtype == "leave":
                break
            else:
                writer.write(jline({"type": "error", "error": "unknown_type"}))
                await writer.drain()

    except Exception:
        pass
    finally:
        clients.discard(writer)
        left_name = names.pop(writer, None)
        if left_name:
            asyncio.create_task(broadcast({"type": "system", "msg": f"{left_name} saiu do chat."}))
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addr = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Servidor escutando em {addr}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
