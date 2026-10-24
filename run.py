import os
import socket
from app import create_app

app = create_app()

def get_lan_ip():
    """Retrieve local network IP for mobile testing demonstration."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    lan_ip = get_lan_ip()

    print("\n" + "=" * 65)
    print("  CIVICFIX — SMART INFRASTRUCTURE ISSUE TRACKING PLATFORM")
    print("  Innovators Conclave 2026 (Challenge IC26-04-02)")
    print("=" * 65)
    print(f"  Laptop / Local URL:  http://localhost:{port}")
    print(f"  Mobile Phone Access: http://{lan_ip}:{port}")
    print("=" * 65)
    print("  Demo Accounts:")
    print("  • Citizen:    citizen@civicfix.org    / Password@123")
    print("  • Staff:      staff@civicfix.org      / Password@123")
    print("  • Sanitation: sanitation@civicfix.org / Password@123")
    print("  • Admin:      admin@civicfix.org      / Admin@123")
    print("=" * 65 + "\n")

    app.run(host=host, port=port, debug=True)
