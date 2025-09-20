import asyncio
import json
from typing import Dict, Set

HOST = "127.0.0.1"
PORT = 9999

clients: Set[asyncio.StreamWriter] = set()
names: Dict[asyncio.StreamWriter, str] = {}
by_name: Dict[str, asyncio.StreamWriter] = {}
groups: Dict[str, Set[asyncio.StreamWriter]] = {}  # grupos


def jline(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


async def broadcast(msg: dict, exclude: asyncio.StreamWriter = None):
    dead = []
    for w in clients:
        if w is exclude:
            continue
        try:
            w.write(jline(msg))
            await w.drain()
        except Exception:
            dead.append(w)
    for w in dead:
        await disconnect(w)


async def disconnect(writer: asyncio.StreamWriter):
    if writer in clients:
        clients.remove(writer)
    name = names.pop(writer, None)
    if name and name in by_name:
        del by_name[name]
        await broadcast({"type": "system", "msg": f"{name} saiu."})
    for g in groups.values():
        g.discard(writer)
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    clients.add(writer)
    addr = writer.get_extra_info("peername")
    print(f"Nova conexão de {addr}")

    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8").strip())
            except Exception:
                continue

            mtype = msg.get("type")

            if mtype == "join":
                name = msg.get("name")
                if not name or name in by_name:
                    writer.write(jline({"type": "error", "error": "nome_invalido"}))
                    await writer.drain()
                    continue
                names[writer] = name
                by_name[name] = writer
                writer.write(jline({"type": "welcome", "you": name}))
                await writer.drain()
                await broadcast({"type": "system", "msg": f"{name} entrou."}, exclude=writer)

            elif mtype == "leave":
                await disconnect(writer)
                break

            elif mtype == "chat":
                name = names.get(writer, "?")
                text = (msg.get("msg") or "")[:2000]
                await broadcast({"type": "chat", "from": name, "msg": text}, exclude=writer)

            elif mtype == "pm":
                to = (msg.get("to") or "").strip()
                text = (msg.get("msg") or "")[:2000]
                if to not in by_name:
                    writer.write(jline({"type": "error", "error": "destino_offline"}))
                    await writer.drain()
                else:
                    dest = by_name[to]
                    sender = names.get(writer, "?")
                    dest.write(jline({"type": "pm", "from": sender, "msg": text}))
                    await dest.drain()
                    writer.write(jline({"type": "pm", "to": to, "msg": text}))
                    await writer.drain()

            elif mtype == "who":
                writer.write(jline({"type": "who", "users": list(by_name.keys())}))
                await writer.drain()

            elif mtype == "create_group":
                group = msg.get("group", "").strip()
                if not group:
                    writer.write(jline({"type": "error", "error": "grupo_invalido"}))
                    await writer.drain()
                    continue
                if group in groups:
                    writer.write(jline({"type": "error", "error": "grupo_existente"}))
                    await writer.drain()
                    continue
                groups[group] = set()
                writer.write(jline({"type": "system", "msg": f"Grupo {group} criado"}))
                await writer.drain()

            elif mtype == "join_group":
                group = msg.get("group", "").strip()
                if group not in groups:
                    writer.write(jline({"type": "error", "error": "grupo_inexistente"}))
                    await writer.drain()
                    continue
                groups[group].add(writer)
                writer.write(jline({"type": "system", "msg": f"Você entrou no grupo {group}"}))
                await writer.drain()

            elif mtype == "group_msg":
                group = msg.get("group", "").strip()
                text = (msg.get("msg") or "")[:2000]
                if not group or group not in groups:
                    writer.write(jline({"type": "error", "error": "grupo_inexistente"}))
                    await writer.drain()
                    continue
                sender = names.get(writer, "?")
                for dest in list(groups[group]):
                    if dest is writer:
                        continue
                    try:
                        dest.write(jline({"type": "group_msg", "group": group, "from": sender, "msg": text}))
                        await dest.drain()
                    except Exception:
                        await disconnect(dest)

            elif mtype in {"file_info", "file_data", "file_end"}:
                payload = {"type": mtype}
                for k in ("name", "size", "data"):
                    if k in msg:
                        payload[k] = msg[k]
                sender = names.get(writer, "?")
                payload["from"] = sender

                group = msg.get("group")
                to = (msg.get("to") or "").strip()

    # Se for file_info, prepara aviso textual
                notice = None
                if mtype == "file_info":
                    fname = payload.get("name", "?")
                    size = payload.get("size", "?")
                    notice = {"type": "system", "msg": f"[arquivo] {sender} enviou {fname} ({size} bytes)"}

                if group:
                    if group not in groups:
                        writer.write(jline({"type": "error", "error": "grupo_inexistente"}))
                        await writer.drain()
                    else:
                        for dest in list(groups[group]):
                            if dest is writer:
                                continue
                            try:
                                if notice:
                                    dest.write(jline(notice))
                                    await dest.drain()
                                p = dict(payload)
                                p["group"] = group
                                dest.write(jline(p))
                                await dest.drain()
                            except Exception:
                                await disconnect(dest)

                elif to:
                    dest = by_name.get(to)
                    if not dest:
                        writer.write(jline({"type": "error", "error": "destino_offline"}))
                        await writer.drain()
                    else:
                        try:
                            if notice:
                                dest.write(jline(notice))
                                await dest.drain()
                            p = dict(payload)
                            p["pm"] = True
                            dest.write(jline(p))
                            await dest.drain()
                        except Exception:
                            await disconnect(dest)
                            writer.write(jline({"type": "error", "error": "destino_offline"}))
                            await writer.drain()

                else:
                    if notice:
                        await broadcast(notice, exclude=writer)
                        await broadcast(payload, exclude=writer)

    except Exception as e:
        print("Erro cliente:", e)
    finally:
        await disconnect(writer)


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Servidor rodando em {addrs}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

