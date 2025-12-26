import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8000
DIRECTORY = "htmlcov"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


if __name__ == "__main__":
    if not os.path.exists(DIRECTORY):
        print(f"Error: Directory '{DIRECTORY}' not found.")
        print("Run 'uv run pytest --cov=devtul_core --cov-report=html' first.")
        sys.exit(1)

    print(f"Serving coverage report at http://localhost:{PORT}")

    # Open browser automatically
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except:
        pass

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping server.")
            sys.exit(0)
