import argparse
import sys

import uvicorn

from cremalink.local_server_app import create_app, ServerSettings


class LocalServer:
    def __init__(self, settings: ServerSettings) -> None:
        self.settings = settings
        self.app = create_app(settings=self.settings)

    def start(self) -> None:
        uvicorn.run(self.app, host=self.settings.server_ip, port=self.settings.server_port, log_level="info")


def main():
    parser = argparse.ArgumentParser(description="Start the local server.")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to bind the local server to.")
    parser.add_argument("--port", type=int, default=10800, help="Port to run the local server on.")

    if "--help" in parser.parse_known_args()[0]:
        parser.print_help()
        exit(0)

    args = parser.parse_args()
    server = LocalServer(ServerSettings(server_ip=args.ip, server_port=args.port))
    server.start()


if __name__ == "__main__":
    sys.exit(main())
