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
    file_buffers = {}  # {filename: bytes acumulados}

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
        elif t == "file_info":
            fname = msg["name"]
            print(f"[arquivo] Recebendo {fname} ({msg['size']} bytes)...")
            file_buffers[fname] = b""
        elif t == "file_data":
            data = base64.b64decode(msg["data"])
            # adiciona ao primeiro arquivo pendente
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
            # DM recebida (ou eco do servidor com "to")
            if "from" in msg:
                print(f"[PM] {msg['from']}: {msg.get('msg','')}")
            elif "to" in msg:
                print(f"[PM para {msg['to']}] {msg.get('msg','')}")
        elif t == "who":
            users = msg.get("users", [])
            print("[online]", ", ".join(users))
        elif t == "error":
            print(f"[erro] {msg.get('error')}")
        else:
            # mensagens desconhecidas
            pass

async def send_file(writer, filepath: str):
    if not os.path.exists(filepath):
        print("[erro] arquivo não encontrado")
        return

    filename = os.path.basename(filepath)
    size = os.path.getsize(filepath)

    # avisa que começará envio
    writer.write(jline({"type": "file_info", "name": filename, "size": size}))
    await writer.drain()

    # lê em pedaços e envia em base64
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            b64 = base64.b64encode(chunk).decode("utf-8")
            writer.write(jline({"type": "file_data", "data": b64}))
            await writer.drain()

    # fim do arquivo
    writer.write(jline({"type": "file_end", "name": filename}))
    await writer.drain()
    print(f"[+] Arquivo {filename} enviado")

async def writer_task(writer: asyncio.StreamWriter, name: str):
    # primeiro JOIN
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
            to = parts[1].strip()
            msg_txt = parts[2].strip()
            if not to or not msg_txt:
                print("[erro] uso: /pm <nome> <mensagem>")
                continue
            writer.write(jline({"type": "pm", "to": to, "msg": msg_txt}))
            await writer.drain()
            continue


        if text.lower() == "/quem":
            writer.write(jline({"type": "who"}))
            await writer.drain()
            continue

        # comando para enviar arquivo
        if text.startswith("/enviar "):
            filepath = text.split(" ", 1)[1]
            await send_file(writer, filepath)
            continue

        if text:
            writer.write(jline({"type": "chat", "msg": text}))
            await writer.drain()

    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass

async def main():
    while True:
        name = input("Digite seu nome: ").strip()
        if name:
            name = name
            break
        print("Nome não pode ser vazio. Tente novamente.")

    reader, writer = await asyncio.open_connection(HOST, PORT)
    await asyncio.gather(
        reader_task(reader),
        writer_task(writer, name),
    )

if __name__ == "__main__":
    asyncio.run(main())
