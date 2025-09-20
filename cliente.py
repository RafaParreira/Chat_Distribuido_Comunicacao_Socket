import asyncio
import json
import sys
import base64
import os

HOST = "127.0.0.1"
PORT = 9999


def jline(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")


async def reader_task(reader: asyncio.StreamReader):
    file_buffers = {}

    while True:
        line = await reader.readline()
        if not line:
            print("<< desconectado do servidor >>")
            break
        try:
            msg = json.loads(line.decode("utf-8").strip())
        except json.JSONDecodeError:
            continue

        t = msg.get("type")
        if t == "welcome":
            print(f"<< conectado como {msg.get('you')} >>")
        elif t == "system":
            print(f"[*] {msg.get('msg')}")
        elif t == "chat":
            print(f"{msg.get('from')}: {msg.get('msg')}")
        elif t == "group_msg":
            print(f"[{msg['group']}] {msg['from']}: {msg['msg']}")
        elif t == "file_info":
            fname = msg["name"]
            group = msg.get("group")
            if group:
                print(f"[arquivo grupo:{group}] Recebendo {fname} ({msg['size']} bytes)...")
            else:
                print(f"[arquivo] Recebendo {fname} ({msg['size']} bytes)...")
            file_buffers[fname] = b""
        elif t == "file_data":
            data = base64.b64decode(msg["data"])
            for fname in file_buffers:
                file_buffers[fname] += data
                break
        elif t == "file_end":
            fname = msg["name"]
            if fname in file_buffers:
                with open("recv_" + fname, "wb") as f:
                    f.write(file_buffers[fname])
                print(f"[+] Arquivo salvo como recv_{fname}")
                del file_buffers[fname]
        elif t == "pm":
            if "from" in msg:
                print(f"[PM] {msg['from']}: {msg.get('msg','')}")
            elif "to" in msg:
                print(f"[PM para {msg['to']}] {msg.get('msg','')}")
        elif t == "who":
            users = msg.get("users", [])
            print("[online]", ", ".join(users))
        elif t == "error":
            print(f"[erro] {msg.get('error')}")


async def send_file(writer, filepath):
    if not os.path.exists(filepath):
        print("[erro] arquivo não encontrado")
        return
    size = os.path.getsize(filepath)
    name = os.path.basename(filepath)
    writer.write(jline({"type": "file_info", "name": name, "size": size}))
    await writer.drain()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            b64 = base64.b64encode(chunk).decode("utf-8")
            writer.write(jline({"type": "file_data", "data": b64}))
            await writer.drain()
    writer.write(jline({"type": "file_end", "name": name}))
    await writer.drain()
    print("[+] Arquivo enviado")


async def send_file_pm(writer, to, filepath):
    if not os.path.exists(filepath):
        print("[erro] arquivo não encontrado")
        return
    size = os.path.getsize(filepath)
    name = os.path.basename(filepath)
    writer.write(jline({"type": "file_info", "to": to, "name": name, "size": size}))
    await writer.drain()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            b64 = base64.b64encode(chunk).decode("utf-8")
            writer.write(jline({"type": "file_data", "to": to, "data": b64}))
            await writer.drain()
    writer.write(jline({"type": "file_end", "to": to, "name": name}))
    await writer.drain()
    print(f"[+] Arquivo enviado para {to}")


async def send_file_group(writer, group, filepath):
    if not os.path.exists(filepath):
        print("[erro] arquivo não encontrado")
        return
    size = os.path.getsize(filepath)
    name = os.path.basename(filepath)
    writer.write(jline({"type": "file_info", "group": group, "name": name, "size": size}))
    await writer.drain()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            b64 = base64.b64encode(chunk).decode("utf-8")
            writer.write(jline({"type": "file_data", "group": group, "data": b64}))
            await writer.drain()
    writer.write(jline({"type": "file_end", "group": group, "name": name}))
    await writer.drain()
    print(f"[+] Arquivo enviado para grupo {group}")


async def writer_task(writer: asyncio.StreamWriter, name: str):
    writer.write(jline({"type": "join", "name": name}))
    await writer.drain()

    loop = asyncio.get_running_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
        except Exception:
            break
        if not line:
            break
        text = line.strip()

        if text.lower() in ("/sair", "/quit", "/exit"):
            writer.write(jline({"type": "leave"}))
            await writer.drain()
            break

        if text.startswith("/pm "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                print("[erro] uso: /pm <nome> <mensagem>")
                continue
            to, msg_txt = parts[1], parts[2]
            writer.write(jline({"type": "pm", "to": to, "msg": msg_txt}))
            await writer.drain()
            continue

        if text.startswith("/criargrupo "):
            group = text.split(" ", 1)[1].strip()
            writer.write(jline({"type": "create_group", "group": group}))
            await writer.drain()
            continue

        if text.startswith("/entrargrupo "):
            group = text.split(" ", 1)[1].strip()
            writer.write(jline({"type": "join_group", "group": group}))
            await writer.drain()
            continue

        if text.startswith("/g "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                print("[erro] uso: /g <grupo> <mensagem>")
                continue
            group, msg_txt = parts[1], parts[2]
            writer.write(jline({"type": "group_msg", "group": group, "msg": msg_txt}))
            await writer.drain()
            continue

        if text.startswith("/gfile "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                print("[erro] uso: /gfile <grupo> <caminho>")
                continue
            group, filepath = parts[1], parts[2]
            await send_file_group(writer, group, filepath)
            continue

        if text.lower() == "/quem":
            writer.write(jline({"type": "who"}))
            await writer.drain()
            continue

        if text.startswith("/pmfile "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                print("[erro] uso: /pmfile <nome> <caminho>")
                continue
            to, filepath = parts[1], parts[2]
            await send_file_pm(writer, to, filepath)
            continue

        if text.startswith("/enviar "):
            filepath = text.split(" ", 1)[1]
            await send_file(writer, filepath)
            continue

        if text:
            writer.write(jline({"type": "chat", "msg": text}))
            await writer.drain()


async def main():
    if len(sys.argv) < 2:
        print(f"uso: python {sys.argv[0]} <seu_nome>")
        return
    name = sys.argv[1]
    reader, writer = await asyncio.open_connection(HOST, PORT)
    await asyncio.gather(reader_task(reader), writer_task(writer, name))


if __name__ == "__main__":
    asyncio.run(main())
