import asyncio
import json
from typing import Dict, Set

HOST = "127.0.0.1"
PORT = 9999

clients: Set[asyncio.StreamWriter] = set()
names: Dict[asyncio.StreamWriter, str] = {}
by_name: Dict[str, asyncio.StreamWriter] = {}

def jline(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")

async def broadcast(payload: dict, *, exclude: asyncio.StreamWriter | None = None):
    dead = []
    for w in list(clients):
        if w is exclude:
            continue
        try:
            w.write(jline(payload))
            await w.drain()
        except Exception:
            dead.append(w)
    for w in dead:
        await disconnect(w)

async def disconnect(w: asyncio.StreamWriter):
    clients.discard(w)
    name = names.pop(w, None)
    if name and by_name.get(name) is w:
        by_name.pop(name, None)
        # avisa a todos que saiu
        await broadcast({"type": "system", "msg": f"{name} saiu do chat."})
    try:
        w.close()
        await w.wait_closed()
    except Exception:
        pass

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    clients.add(writer)
    addr = writer.get_extra_info("peername")
    name = None

    try:
        # 1) Espera JOIN
        line = await reader.readline()
        if not line:
            return
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

        # valida nome
        name = str(msg["name"]).strip()[:32]
        if not name or "\n" in name:
            writer.write(jline({"type": "error", "error": "invalid_name"}))
            await writer.drain()
            return
        if name in by_name:
            writer.write(jline({"type": "error", "error": "name_in_use"}))
            await writer.drain()
            return

        names[writer] = name
        by_name[name] = writer

        # confirma para o novo cliente
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

            elif mtype == "pm":
                # DM: {"type":"pm","to":"Bob","msg":"texto"}
                to = (msg.get("to") or "").strip()
                text = (msg.get("msg") or "")[:2000]
                if not to or not text:
                    writer.write(jline({"type": "error", "error": "missing_fields"}))
                    await writer.drain()
                    continue
                dest = by_name.get(to)
                if not dest:
                    writer.write(jline({"type": "error", "error": "user_not_found"}))
                    await writer.drain()
                    continue
                # envia somente ao destino
                try:
                    dest.write(jline({"type": "pm", "from": name, "msg": text}))
                    await dest.drain()
                except Exception:
                    # destino caiu; remove e avisa remetente
                    await disconnect(dest)
                    writer.write(jline({"type": "error", "error": "user_not_found"}))
                    await writer.drain()
                    continue
                # opcional: eco para quem enviou (útil pra UI)
                writer.write(jline({"type": "pm", "to": to, "msg": text}))
                await writer.drain()

            elif mtype == "who":
                users = sorted(list(by_name.keys()))
                writer.write(jline({"type": "who", "users": users}))
                await writer.drain()

            elif mtype == "leave":
                break

            # opcional: ignore/erro para tipos desconhecidos, inclusive file_*
            elif mtype in {"file_info", "file_data", "file_end"}:
    # Encaminha arquivo. Se vier "to", envia só para esse usuário (DM); senão, broadcast.
                payload = {"type": mtype}
                for k in ("name", "size", "data"):
                    if k in msg:
                        payload[k] = msg[k]
                        payload["from"] = name  # útil para o receptor logar quem enviou

                to = (msg.get("to") or "").strip()
                if to:
                    dest = by_name.get(to)
                    if not dest:
                        writer.write(jline({"type": "error", "error": "user_not_found"}))
                        await writer.drain()
                    else:
                        try:
                            dest.write(jline(payload))
                            await dest.drain()
                        except Exception:
                            await disconnect(dest)
                            writer.write(jline({"type": "error", "error": "user_not_found"}))
                            await writer.drain()
                else:
        # arquivo público: envia a todos, exceto o remetente
                    await broadcast(payload, exclude=writer)

    except Exception as e:
        # log simples
        # print(f"[erro] {addr}: {e}")
        pass
    finally:
        await disconnect(writer)

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
    print(f"Servidor escutando em {addrs}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
