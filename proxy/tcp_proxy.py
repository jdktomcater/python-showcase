import asyncio
import argparse

BUFFER_SIZE = 65536

async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, direction: str, verbose: bool):
    try:
        while True:
            data = await reader.read(BUFFER_SIZE)
            if not data:
                break
            if verbose:
                # Redis 协议是 RESP，直接按二进制打印更安全
                preview = data[:200]
                print(f"[{direction}] {len(data)} bytes: {preview!r}")
            writer.write(data)
            await writer.drain()
    except Exception as e:
        if verbose:
            print(f"[{direction}] error: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle_client(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter,
                        target_host: str, target_port: int, verbose: bool):
    peer = client_writer.get_extra_info("peername")
    if verbose:
        print(f"[+] client connected: {peer}")

    try:
        server_reader, server_writer = await asyncio.open_connection(target_host, target_port)

        # 双向转发
        c2s = asyncio.create_task(pipe(client_reader, server_writer, "C->S", verbose))
        s2c = asyncio.create_task(pipe(server_reader, client_writer, "S->C", verbose))

        done, pending = await asyncio.wait(
            [c2s, s2c],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    except Exception as e:
        if verbose:
            print(f"[!] connect/forward error: {e}")
    finally:
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except Exception:
            pass
        if verbose:
            print(f"[-] client disconnected: {peer}")


async def main():
    parser = argparse.ArgumentParser(description="Simple TCP proxy (Redis-like).")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=6380)
    parser.add_argument("--target-host", default="127.0.0.1")
    parser.add_argument("--target-port", type=int, default=6379)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, args.target_host, args.target_port, args.verbose),
        args.listen_host,
        args.listen_port
    )

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Proxy listening on {addrs} -> {args.target_host}:{args.target_port}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())