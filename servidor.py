import asyncio
import json
from typing import Dict, Set

HOST = "127.0.0.1"
PORT = 9999

# Estado simples em memória (para protótipo):
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
        # 1) Espera JOIN
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

        # Confirmação ao novo cliente e broadcast aos demais
        writer.write(jline({"type": "welcome", "you": name}))
        await writer.drain()
        await broadcast({"type": "system", "msg": f"{name} entrou no chat."}, exclude=writer)

        # 2) Loop de mensagens
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
                if not text:
                    continue
                await broadcast({"type": "chat", "from": name, "msg": text})
            elif mtype == "leave":
                break
            else:
                # Ignora tipos desconhecidos (ou responda com erro)
                writer.write(jline({"type": "error", "error": "unknown_type"}))
                await writer.drain()

    except Exception as e:
        # log simples
        # print(f"Erro com {addr}: {e}")
        pass
    finally:
        # Limpeza
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
