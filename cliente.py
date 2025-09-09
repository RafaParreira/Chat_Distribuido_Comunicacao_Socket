import asyncio
import json
import sys

HOST = "127.0.0.1"
PORT = 9999

def jline(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")

async def reader_task(reader: asyncio.StreamReader):
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
        elif t == "error":
            print(f"[erro] {msg.get('error')}")
        else:
            # mensagens desconhecidas
            pass

async def writer_task(writer: asyncio.StreamWriter, name: str):
    # primeiro JOIN
    writer.write(jline({"type": "join", "name": name}))
    await writer.drain()

    loop = asyncio.get_running_loop()
    # lê stdin sem bloquear o loop
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
        if text:
            writer.write(jline({"type": "chat", "msg": text}))
            await writer.drain()

    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass

async def main():
    if len(sys.argv) < 2:
        print("Uso: python client.py <seu_nome>")
        return
    name = sys.argv[1]

    reader, writer = await asyncio.open_connection(HOST, PORT)
    await asyncio.gather(
        reader_task(reader),
        writer_task(writer, name),
    )

if __name__ == "__main__":
    asyncio.run(main())
