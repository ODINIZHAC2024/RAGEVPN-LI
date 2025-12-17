#!/usr/bin/env python3
"""
RAGEVPN - Advanced VPN Client with Multi-Protocol Support
Version: 2.0.0 | PowerMode: ON
"""

import curses
import os
import json
import time
import subprocess
import signal
import sys
import psutil
import threading
import queue
import base64
import hashlib
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import socket
import random
import string

# ========== CONFIGURATION ==========
APP = "⚡ RAGEVPN PRO"
VERSION = "1.0.0"
BASE = os.path.expanduser("~/.ragevpn")
PROFILES = os.path.join(BASE, "profiles")
CONFIG = os.path.join(BASE, "config.json")
LOG_FILE = os.path.join(BASE, "ragevpn.log")
CACHE = os.path.join(BASE, "cache")
TG = "https://t.me/RAGEVPN_N1"
GITHUB = "https://github.com/ODINIZHAC2024/RAGEVPN-LI/"

# Colors
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_YELLOW = 3
COLOR_BLUE = 4
COLOR_MAGENTA = 5
COLOR_CYAN = 6
COLOR_WHITE = 7

# Create directories
os.makedirs(PROFILES, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

# ========== UTILITIES ==========
def log_message(level, message):
    """Enhanced logging system"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    
    if level == "ERROR":
        print(f"[-] {message}")

def sh(cmd, background=False):
    """Execute shell command with options"""
    try:
        if background:
            return subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result
    except Exception as e:
        log_message("ERROR", f"Command failed: {' '.join(cmd)} - {str(e)}")
        return None

def check_singbox():
    """Check if sing-box is installed and get version"""
    try:
        result = sh(["sing-box", "version"])
        if result and result.returncode == 0:
            version = result.stdout.strip()
            return True, version
    except:
        pass
    return False, None

def stop_singbox():
    """Stop all sing-box processes"""
    killed = 0
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if p.info["name"] and "sing-box" in p.info["name"].lower():
                p.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if killed > 0:
        log_message("INFO", f"Stopped {killed} sing-box processes")
    return killed

def generate_random_name():
    """Generate random profile name"""
    adjectives = ["Rage", "Stealth", "Ghost", "Phantom", "Shadow", "Cyber", "Dark", "Black"]
    nouns = ["Tunnel", "Bridge", "Gate", "Portal", "Path", "Link", "Node", "Proxy"]
    return f"{random.choice(adjectives)}_{random.choice(nouns)}_{random.randint(100, 999)}"

def encrypt_profile(data, key):
    """Simple XOR encryption for profiles"""
    if not key:
        return json.dumps(data)
    
    json_str = json.dumps(data)
    key = key * (len(json_str) // len(key) + 1)
    encrypted = ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(json_str, key))
    return base64.b64encode(encrypted.encode()).decode()

def decrypt_profile(encrypted_data, key):
    """Decrypt profile data"""
    if not key:
        return json.loads(encrypted_data)
    
    try:
        decoded = base64.b64decode(encrypted_data).decode()
        key = key * (len(decoded) // len(key) + 1)
        decrypted = ''.join(chr(ord(c) ^ ord(k)) for c, k in zip(decoded, key))
        return json.loads(decrypted)
    except:
        return None

# ========== PROTOCOL PARSERS ==========
def parse_vless(link):
    """Parse VLESS link"""
    try:
        parsed = urlparse(link)
        params = parse_qs(parsed.query)
        
        config = {
            "type": "vless",
            "server": parsed.hostname,
            "port": parsed.port or 443,
            "uuid": parsed.username,
            "security": "tls",
            "sni": params.get("sni", [parsed.hostname])[0],
            "type": params.get("type", ["tcp"])[0],
            "host": params.get("host", [parsed.hostname])[0]
        }
        
        if "path" in params:
            config["path"] = unquote(params["path"][0])
        
        return config
    except Exception as e:
        log_message("ERROR", f"Failed to parse VLESS: {e}")
        return None

def parse_vmess(link):
    """Parse VMess link"""
    try:
        # Remove vmess:// prefix
        if link.startswith("vmess://"):
            encoded = link[8:]
            # Add padding if needed
            missing_padding = len(encoded) % 4
            if missing_padding:
                encoded += '=' * (4 - missing_padding)
            
            decoded = base64.b64decode(encoded).decode()
            config = json.loads(decoded)
            
            return {
                "type": "vmess",
                "server": config.get("add"),
                "port": int(config.get("port", 443)),
                "uuid": config.get("id"),
                "security": config.get("scy", "auto"),
                "alterId": int(config.get("aid", 0))
            }
    except Exception as e:
        log_message("ERROR", f"Failed to parse VMess: {e}")
    return None

def parse_trojan(link):
    """Parse Trojan link"""
    try:
        parsed = urlparse(link)
        
        config = {
            "type": "trojan",
            "server": parsed.hostname,
            "port": parsed.port or 443,
            "password": parsed.username,
            "sni": parsed.hostname
        }
        
        return config
    except Exception as e:
        log_message("ERROR", f"Failed to parse Trojan: {e}")
        return None

def parse_shadowsocks(link):
    """Parse ShadowSocks link"""
    try:
        if link.startswith("ss://"):
            # Handle both plain and encoded formats
            if "#" in link:
                encoded_part = link[5:].split("#")[0]
            else:
                encoded_part = link[5:]
            
            # Decode base64
            missing_padding = len(encoded_part) % 4
            if missing_padding:
                encoded_part += '=' * (4 - missing_padding)
            
            decoded = base64.b64decode(encoded_part).decode()
            
            # Parse method:password@server:port
            if "@" in decoded:
                method_password, server_port = decoded.split("@")
                method, password = method_password.split(":")
                server, port = server_port.split(":")
                
                return {
                    "type": "shadowsocks",
                    "server": server,
                    "port": int(port),
                    "method": method,
                    "password": password
                }
    except Exception as e:
        log_message("ERROR", f"Failed to parse ShadowSocks: {e}")
    return None

# ========== CONFIG BUILDER ==========
def build_singbox_config(profile_data):
    """Build advanced sing-box configuration"""
    
    proto_config = None
    
    # Parse based on protocol
    if profile_data["protocol"] == "vless":
        proto_config = parse_vless(profile_data["link"])
    elif profile_data["protocol"] == "vmess":
        proto_config = parse_vmess(profile_data["link"])
    elif profile_data["protocol"] == "trojan":
        proto_config = parse_trojan(profile_data["link"])
    elif profile_data["protocol"] == "shadowsocks":
        proto_config = parse_shadowsocks(profile_data["link"])
    
    if not proto_config:
        # Fallback to URL method
        cfg = {
            "log": {"level": "warn", "timestamp": True},
            "dns": {
                "servers": [
                    "1.1.1.1",
                    "8.8.8.8",
                    "local"
                ],
                "strategy": "ipv4_only"
            },
            "inbounds": [
                {
                    "type": "tun",
                    "interface_name": "ragevpn0",
                    "inet4_address": "172.19.0.1/30",
                    "mtu": 1500,
                    "auto_route": True,
                    "strict_route": True,
                    "stack": "mixed"
                }
            ],
            "outbounds": [
                {
                    "type": profile_data["protocol"],
                    "tag": "proxy",
                    "url": profile_data["link"]
                },
                {
                    "type": "direct",
                    "tag": "direct"
                },
                {
                    "type": "block",
                    "tag": "block"
                }
            ],
            "route": {
                "auto_detect_interface": True,
                "rules": [
                    {
                        "protocol": "dns",
                        "outbound": "direct"
                    },
                    {
                        "domain_suffix": [".local", ".lan"],
                        "outbound": "direct"
                    },
                    {
                        "geoip": ["private", "cn"],
                        "outbound": "direct"
                    },
                    {
                        "outbound": "proxy",
                        "network": "tcp,udp"
                    }
                ]
            }
        }
    else:
        # Build config from parsed data
        cfg = {
            "log": {"level": "warn", "timestamp": True},
            "dns": {
                "servers": [
                    "1.1.1.1",
                    "8.8.8.8",
                    "local"
                ],
                "strategy": "ipv4_only"
            },
            "inbounds": [
                {
                    "type": "tun",
                    "interface_name": "ragevpn0",
                    "inet4_address": "172.19.0.1/30",
                    "mtu": 1500,
                    "auto_route": True,
                    "strict_route": True,
                    "stack": "mixed"
                }
            ],
            "outbounds": [
                {
                    "type": proto_config["type"],
                    "tag": "proxy",
                    **proto_config
                },
                {
                    "type": "direct",
                    "tag": "direct"
                },
                {
                    "type": "block",
                    "tag": "block"
                }
            ],
            "route": {
                "auto_detect_interface": True,
                "rules": [
                    {
                        "protocol": "dns",
                        "outbound": "direct"
                    },
                    {
                        "domain_suffix": [".local", ".lan"],
                        "outbound": "direct"
                    },
                    {
                        "geoip": ["private", "cn"],
                        "outbound": "direct"
                    },
                    {
                        "outbound": "proxy",
                        "network": "tcp,udp"
                    }
                ]
            }
        }
    
    # Add fake IP DNS if enabled
    cfg["dns"]["fakeip"] = {
        "enabled": True,
        "inet4_range": "198.18.0.0/15"
    }
    
    return cfg

# ========== PROFILE MANAGEMENT ==========
def load_profiles():
    """Load all profiles from disk"""
    profiles = []
    for f in os.listdir(PROFILES):
        if f.endswith(".json"):
            try:
                with open(os.path.join(PROFILES, f), "r") as file:
                    profile = json.load(file)
                    profile["filename"] = f
                    profiles.append(profile)
            except:
                continue
    return sorted(profiles, key=lambda x: x.get("last_used", 0), reverse=True)

def save_profile(profile):
    """Save profile to disk"""
    profile["modified"] = time.time()
    filename = f"{profile['name']}.json"
    filepath = os.path.join(PROFILES, filename)
    
    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    
    log_message("INFO", f"Saved profile: {profile['name']}")
    return True

def delete_profile(profile_name):
    """Delete profile"""
    filepath = os.path.join(PROFILES, f"{profile_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        log_message("INFO", f"Deleted profile: {profile_name}")
        return True
    return False

def test_connection(profile):
    """Test connection speed and latency"""
    try:
        start_time = time.time()
        
        # Quick test using curl
        test_url = "https://1.1.1.1/cdn-cgi/trace"
        result = sh(["curl", "-s", "--max-time", "5", test_url])
        
        if result and result.returncode == 0:
            latency = int((time.time() - start_time) * 1000)
            return True, latency
    except:
        pass
    
    return False, 0

# ========== TRAFFIC MONITOR ==========
class TrafficMonitor:
    """Advanced traffic monitoring"""
    
    def __init__(self):
        self.start_time = time.time()
        self.start_bytes = psutil.net_io_counters()
        self.history = []
        self.max_history = 60  # 1 minute at 1-second intervals
        
    def get_stats(self):
        """Get current traffic statistics"""
        current = psutil.net_io_counters()
        elapsed = time.time() - self.start_time
        
        rx_total = current.bytes_recv - self.start_bytes.bytes_recv
        tx_total = current.bytes_sent - self.start_bytes.bytes_sent
        
        # Calculate speed (bytes per second)
        if len(self.history) > 1:
            last = self.history[-1]
            time_diff = elapsed - last["time"]
            if time_diff > 0:
                rx_speed = (rx_total - last["rx_total"]) / time_diff
                tx_speed = (tx_total - last["tx_total"]) / time_diff
            else:
                rx_speed = tx_speed = 0
        else:
            rx_speed = tx_speed = 0
        
        # Add to history
        self.history.append({
            "time": elapsed,
            "rx_total": rx_total,
            "tx_total": tx_total,
            "rx_speed": rx_speed,
            "tx_speed": tx_speed
        })
        
        # Trim history
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        return {
            "rx_total_kb": rx_total // 1024,
            "tx_total_kb": tx_total // 1024,
            "rx_speed_kbps": int(rx_speed * 8 / 1024),  # Convert to kbps
            "tx_speed_kbps": int(tx_speed * 8 / 1024),
            "elapsed": int(elapsed)
        }
    
    def reset(self):
        """Reset counters"""
        self.start_time = time.time()
        self.start_bytes = psutil.net_io_counters()
        self.history = []

# ========== UI COMPONENTS ==========
def init_colors():
    """Initialize color pairs"""
    curses.start_color()
    curses.use_default_colors()
    
    # Define color pairs
    curses.init_pair(COLOR_RED, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_GREEN, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_YELLOW, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_BLUE, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_MAGENTA, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_CYAN, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_WHITE, curses.COLOR_WHITE, -1)

def draw_box(stdscr, y, x, height, width, title=""):
    """Draw a box with optional title"""
    # Corners
    stdscr.addch(y, x, curses.ACS_ULCORNER)
    stdscr.addch(y, x + width - 1, curses.ACS_URCORNER)
    stdscr.addch(y + height - 1, x, curses.ACS_LLCORNER)
    stdscr.addch(y + height - 1, x + width - 1, curses.ACS_LRCORNER)
    
    # Horizontal lines
    for i in range(1, width - 1):
        stdscr.addch(y, x + i, curses.ACS_HLINE)
        stdscr.addch(y + height - 1, x + i, curses.ACS_HLINE)
    
    # Vertical lines
    for i in range(1, height - 1):
        stdscr.addch(y + i, x, curses.ACS_VLINE)
        stdscr.addch(y + i, x + width - 1, curses.ACS_VLINE)
    
    # Title
    if title:
        title_text = f" {title} "
        title_x = x + (width - len(title_text)) // 2
        if title_x > x:
            stdscr.addstr(y, title_x, title_text, curses.A_BOLD)

def menu(stdscr, title, items, selected=0, show_help=True):
    """Enhanced menu with colors and navigation"""
    height, width = stdscr.getmaxyx()
    
    while True:
        stdscr.clear()
        
        # Draw title
        title_y = 1
        stdscr.addstr(title_y, 2, f"╔{'═' * (len(title) + 2)}╗", curses.color_pair(COLOR_CYAN))
        stdscr.addstr(title_y + 1, 2, f"║ {title} ║", curses.color_pair(COLOR_CYAN) | curses.A_BOLD)
        stdscr.addstr(title_y + 2, 2, f"╚{'═' * (len(title) + 2)}╝", curses.color_pair(COLOR_CYAN))
        
        # Draw items
        start_y = title_y + 4
        max_items = height - start_y - 5
        
        for i, item in enumerate(items):
            if i >= max_items:
                break
            
            y_pos = start_y + i
            if i == selected:
                stdscr.addstr(y_pos, 4, "▶", curses.color_pair(COLOR_GREEN) | curses.A_BOLD)
                stdscr.addstr(y_pos, 6, item, curses.color_pair(COLOR_GREEN) | curses.A_BOLD | curses.A_REVERSE)
            else:
                stdscr.addstr(y_pos, 6, item, curses.color_pair(COLOR_WHITE))
        
        # Help text
        if show_help:
            help_y = height - 3
            help_text = "↑↓: Navigate | Enter: Select | q: Exit"
            stdscr.addstr(help_y, (width - len(help_text)) // 2, help_text, curses.color_pair(COLOR_YELLOW))
        
        stdscr.refresh()
        
        # Handle input
        key = stdscr.getch()
        
        if key == curses.KEY_UP:
            selected = (selected - 1) % len(items)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(items)
        elif key in (10, 13):  # Enter
            return selected
        elif key == ord('q'):
            return -1
        elif key == ord(' '):
            return selected

def input_dialog(stdscr, prompt, default=""):
    """Get user input with dialog"""
    height, width = stdscr.getmaxyx()
    
    # Create input box
    box_height = 5
    box_width = min(60, width - 4)
    box_y = (height - box_height) // 2
    box_x = (width - box_width) // 2
    
    # Draw box
    draw_box(stdscr, box_y, box_x, box_height, box_width, "Input")
    
    # Show prompt
    stdscr.addstr(box_y + 1, box_x + 2, prompt, curses.A_BOLD)
    
    # Input field
    input_y = box_y + 2
    input_x = box_x + 2
    input_width = box_width - 4
    
    # Show default value
    stdscr.addstr(input_y, input_x, default, curses.color_pair(COLOR_CYAN))
    
    # Enable cursor and echo
    curses.echo()
    curses.curs_set(1)
    
    # Get input
    stdscr.move(input_y, input_x + len(default))
    value = stdscr.getstr(input_y, input_x, input_width).decode().strip()
    
    # Restore cursor state
    curses.noecho()
    curses.curs_set(0)
    
    return value if value else default

def show_message(stdscr, message, color=COLOR_WHITE, wait=True):
    """Show message dialog"""
    height, width = stdscr.getmaxyx()
    
    lines = message.split('\n')
    box_height = len(lines) + 4
    box_width = max(len(l) for l in lines) + 4
    
    if box_width > width - 4:
        box_width = width - 4
    
    box_y = (height - box_height) // 2
    box_x = (width - box_width) // 2
    
    draw_box(stdscr, box_y, box_x, box_height, box_width, "Message")
    
    for i, line in enumerate(lines):
        if i < box_height - 3:
            stdscr.addstr(box_y + 2 + i, box_x + 2, line[:box_width-3], curses.color_pair(color))
    
    if wait:
        stdscr.addstr(box_y + box_height - 2, box_x + (box_width - 10) // 2, 
                     "[ OK ]", curses.color_pair(COLOR_GREEN) | curses.A_BOLD)
        stdscr.refresh()
        stdscr.getch()

# ========== MAIN SCREENS ==========
def main_menu(stdscr):
    """Main menu screen"""
    init_colors()
    
    while True:
        # Check sing-box installation
        singbox_installed, version = check_singbox()
        
        items = [
            "🚀 Connect VPN",
            "📁 Manage Profiles",
            "⚙️ Settings",
            "📊 Statistics",
            "🛠️ Tools",
            "ℹ️ About",
            "❌ Exit"
        ]
        
        selected = menu(stdscr, f"{APP} v{VERSION}", items)
        
        if selected == 0:  # Connect VPN
            connect_screen(stdscr)
        elif selected == 1:  # Manage Profiles
            profiles_screen(stdscr)
        elif selected == 2:  # Settings
            settings_screen(stdscr)
        elif selected == 3:  # Statistics
            stats_screen(stdscr)
        elif selected == 4:  # Tools
            tools_screen(stdscr)
        elif selected == 5:  # About
            about_screen(stdscr)
        elif selected == 6 or selected == -1:  # Exit
            break

def connect_screen(stdscr):
    """Connect to VPN screen"""
    profiles = load_profiles()
    
    if not profiles:
        show_message(stdscr, "No profiles found!\nCreate a profile first.", COLOR_RED)
        return
    
    profile_names = [f"{p['name']} ({p['protocol']})" for p in profiles]
    profile_names.append("← Back")
    
    selected = menu(stdscr, "Select Profile", profile_names)
    
    if selected == len(profile_names) - 1 or selected == -1:
        return
    
    selected_profile = profiles[selected]
    
    # Test connection first
    show_message(stdscr, "Testing connection...", COLOR_YELLOW, False)
    test_ok, latency = test_connection(selected_profile)
    
    if not test_ok:
        retry = show_yesno(stdscr, "Connection test failed!\nRetry with force mode?")
        if not retry:
            return
    
    # Build and save config
    config = build_singbox_config(selected_profile)
    with open(CONFIG, "w") as f:
        json.dump(config, f, indent=2)
    
    # Stop existing sing-box
    stop_singbox()
    
    # Start sing-box
    show_message(stdscr, "Starting VPN connection...", COLOR_YELLOW, False)
    
    # Update last used time
    selected_profile["last_used"] = time.time()
    selected_profile["usage_count"] = selected_profile.get("usage_count", 0) + 1
    save_profile(selected_profile)
    
    # Start sing-box in background
    process = sh(["sing-box", "run", "-c", CONFIG], background=True)
    
    if process:
        time.sleep(2)  # Wait for connection
        connection_screen(stdscr, selected_profile, process)
    else:
        show_message(stdscr, "Failed to start VPN!", COLOR_RED)

def connection_screen(stdscr, profile, process):
    """Active connection screen"""
    monitor = TrafficMonitor()
    start_time = time.time()
    
    # Check for public IP
    public_ip = "Checking..."
    
    while True:
        height, width = stdscr.getmaxyx()
        stdscr.clear()
        
        # Header
        header = f"⚡ CONNECTED | {profile['name']}"
        stdscr.addstr(1, (width - len(header)) // 2, header, 
                     curses.color_pair(COLOR_GREEN) | curses.A_BOLD)
        
        # Profile info box
        draw_box(stdscr, 3, 2, 8, width - 4, "Connection Info")
        
        info_y = 4
        stdscr.addstr(info_y, 4, f"Protocol: {profile['protocol'].upper()}", curses.color_pair(COLOR_CYAN))
        stdscr.addstr(info_y + 1, 4, f"IP: {public_ip}", curses.color_pair(COLOR_CYAN))
        
        # Traffic stats
        stats = monitor.get_stats()
        elapsed_min = stats["elapsed"] // 60
        elapsed_sec = stats["elapsed"] % 60
        
        stdscr.addstr(info_y + 3, 4, f"Time: {elapsed_min:02d}:{elapsed_sec:02d}", curses.color_pair(COLOR_YELLOW))
        stdscr.addstr(info_y + 4, 4, f"Download: {stats['rx_total_kb']:,} KB", curses.color_pair(COLOR_BLUE))
        stdscr.addstr(info_y + 5, 4, f"Upload: {stats['tx_total_kb']:,} KB", curses.color_pair(COLOR_MAGENTA))
        
        # Speed graph
        graph_y = 12
        graph_height = 10
        graph_width = width - 10
        
        draw_box(stdscr, graph_y, 5, graph_height, graph_width, "Speed Graph")
        
        # Draw graph
        if len(monitor.history) > 1:
            max_speed = max(max(h["rx_speed"], h["tx_speed"]) for h in monitor.history)
            if max_speed > 0:
                for i, data in enumerate(monitor.history[-graph_width+2:]):
                    x_pos = 6 + i
                    
                    # RX bar
                    rx_height = int((data["rx_speed"] / max_speed) * (graph_height - 3))
                    for j in range(rx_height):
                        stdscr.addch(graph_y + graph_height - 2 - j, x_pos, '█', curses.color_pair(COLOR_BLUE))
                    
                    # TX bar
                    tx_height = int((data["tx_speed"] / max_speed) * (graph_height - 3))
                    for j in range(tx_height):
                        if j < graph_height - 3:
                            stdscr.addch(graph_y + graph_height - 2 - j, x_pos, '█', curses.color_pair(COLOR_MAGENTA))
        
        # Footer with controls
        footer_y = height - 3
        controls = "[D] Details  [S] Speed Test  [R] Reconnect  [Q] Disconnect"
        stdscr.addstr(footer_y, (width - len(controls)) // 2, controls, curses.color_pair(COLOR_YELLOW))
        
        stdscr.refresh()
        
        # Non-blocking input
        stdscr.nodelay(1)
        try:
            key = stdscr.getch()
        except:
            key = -1
        stdscr.nodelay(0)
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('d') or key == ord('D'):
            show_connection_details(stdscr, profile, stats)
        elif key == ord('s') or key == ord('S'):
            run_speed_test(stdscr)
        elif key == ord('r') or key == ord('R'):
            show_message(stdscr, "Reconnecting...", COLOR_YELLOW, False)
            time.sleep(1)
            break
        
        time.sleep(0.5)
    
    # Cleanup
    stop_singbox()
    show_message(stdscr, "Disconnected!", COLOR_GREEN)

def profiles_screen(stdscr):
    """Profile management screen"""
    while True:
        profiles = load_profiles()
        
        items = [
            "➕ Create New Profile",
            "📋 Import Profile (URL)",
            "📁 Import Profile (File)",
            "✏️ Edit Profile",
            "🗑️ Delete Profile",
            "🧪 Test Profile",
            "← Back"
        ]
        
        if profiles:
            items.insert(0, "📊 Profile List")
        
        selected = menu(stdscr, "Profile Management", items)
        
        if selected == -1:
            break
        
        if profiles and selected == 0:  # Profile List
            show_profile_list(stdscr, profiles)
        elif not profiles and selected == 0:  # Create New Profile
            create_profile(stdscr)
        elif (profiles and selected == 1) or (not profiles and selected == 0):
            create_profile(stdscr)
        elif (profiles and selected == 2) or (not profiles and selected == 1):
            import_profile_url(stdscr)
        elif (profiles and selected == 3) or (not profiles and selected == 2):
            import_profile_file(stdscr)
        elif (profiles and selected == 4) or (not profiles and selected == 3):
            edit_profile(stdscr, profiles)
        elif (profiles and selected == 5) or (not profiles and selected == 4):
            delete_profile_screen(stdscr, profiles)
        elif (profiles and selected == 6) or (not profiles and selected == 5):
            test_profile_screen(stdscr, profiles)
        else:
            break

def create_profile(stdscr):
    """Create new profile"""
    stdscr.clear()
    
    # Get profile name
    name = input_dialog(stdscr, "Profile name:", generate_random_name())
    if not name:
        show_message(stdscr, "Profile name cannot be empty!", COLOR_RED)
        return
    
    # Get protocol
    protocols = ["VLESS", "VMess", "Trojan", "Shadowsocks", "Custom URL"]
    proto_idx = menu(stdscr, "Select Protocol", protocols)
    if proto_idx == -1:
        return
    
    protocol = protocols[proto_idx].lower()
    
    # Get connection URL/link
    if protocol == "custom url":
        prompt = "Enter full connection URL:"
    else:
        prompt = f"Paste {protocol.upper()} link:"
    
    link = input_dialog(stdscr, prompt)
    if not link:
        show_message(stdscr, "Link cannot be empty!", COLOR_RED)
        return
    
    # Create profile
    profile = {
        "name": name,
        "protocol": protocol if protocol != "custom url" else "auto",
        "link": link,
        "created": time.ctime(),
        "last_used": 0,
        "usage_count": 0
    }
    
    # Additional settings
    show_message(stdscr, "Add advanced settings? (optional)", COLOR_YELLOW, False)
    advanced = show_yesno(stdscr, "Configure advanced settings?")
    
    if advanced:
        # DNS settings
        dns = input_dialog(stdscr, "DNS servers (comma separated):", "1.1.1.1,8.8.8.8")
        if dns:
            profile["dns"] = [s.strip() for s in dns.split(",")]
        
        # MTU
        mtu = input_dialog(stdscr, "MTU size:", "1500")
        if mtu and mtu.isdigit():
            profile["mtu"] = int(mtu)
    
    # Save profile
    if save_profile(profile):
        show_message(stdscr, f"Profile '{name}' created successfully!", COLOR_GREEN)
    else:
        show_message(stdscr, "Failed to save profile!", COLOR_RED)

def settings_screen(stdscr):
    """Settings screen"""
    items = [
        "🌐 Network Settings",
        "🔒 Security Options",
        "💾 Storage Settings",
        "🎨 UI Customization",
        "🔄 Update Check",
        "← Back"
    ]
    
    selected = menu(stdscr, "Settings", items)
    
    if selected == 0:
        network_settings(stdscr)
    elif selected == 1:
        security_settings(stdscr)
    elif selected == 2:
        storage_settings(stdscr)
    elif selected == 3:
        ui_settings(stdscr)
    elif selected == 4:
        check_updates(stdscr)
    else:
        return

def stats_screen(stdscr):
    """Statistics screen"""
    height, width = stdscr.getmaxyx()
    
    # Load statistics
    stats_file = os.path.join(BASE, "stats.json")
    if os.path.exists(stats_file):
        with open(stats_file, "r") as f:
            stats = json.load(f)
    else:
        stats = {
            "total_rx": 0,
            "total_tx": 0,
            "total_time": 0,
            "connections": 0
        }
    
    stdscr.clear()
    
    # Title
    title = "📊 Statistics"
    stdscr.addstr(1, (width - len(title)) // 2, title, curses.color_pair(COLOR_CYAN) | curses.A_BOLD)
    
    # Stats box
    draw_box(stdscr, 3, 10, 12, width - 20, "Usage Statistics")
    
    info_y = 5
    stdscr.addstr(info_y, 12, f"Total Download: {stats['total_rx'] // (1024*1024):,} MB", curses.color_pair(COLOR_BLUE))
    stdscr.addstr(info_y + 1, 12, f"Total Upload: {stats['total_tx'] // (1024*1024):,} MB", curses.color_pair(COLOR_MAGENTA))
    
    total_gb = (stats['total_rx'] + stats['total_tx']) / (1024**3)
    stdscr.addstr(info_y + 2, 12, f"Total Traffic: {total_gb:.2f} GB", curses.color_pair(COLOR_GREEN))
    
    total_hours = stats['total_time'] // 3600
    total_minutes = (stats['total_time'] % 3600) // 60
    stdscr.addstr(info_y + 3, 12, f"Total Time: {total_hours}h {total_minutes}m", curses.color_pair(COLOR_YELLOW))
    
    stdscr.addstr(info_y + 4, 12, f"Connections: {stats['connections']}", curses.color_pair(COLOR_WHITE))
    
    # Profile usage
    profiles = load_profiles()
    if profiles:
        draw_box(stdscr, 16, 10, len(profiles) + 3, width - 20, "Profile Usage")
        
        for i, profile in enumerate(profiles[:10]):  # Show top 10
            usage = profile.get("usage_count", 0)
            name = profile["name"][:20]
            stdscr.addstr(18 + i, 12, f"{name}: {usage} connections", curses.color_pair(COLOR_WHITE))
    
    stdscr.addstr(height - 2, (width - 20) // 2, "[R] Reset Stats  [Q] Back", curses.color_pair(COLOR_YELLOW))
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('r') or key == ord('R'):
            if show_yesno(stdscr, "Reset all statistics?"):
                with open(stats_file, "w") as f:
                    json.dump({
                        "total_rx": 0,
                        "total_tx": 0,
                        "total_time": 0,
                        "connections": 0
                    }, f)
                show_message(stdscr, "Statistics reset!", COLOR_GREEN)
                break

def tools_screen(stdscr):
    """Tools screen"""
    items = [
        "🔍 Port Scanner",
        "📡 Ping Test",
        "🌐 DNS Lookup",
        "🔧 Config Editor",
        "🧹 Cleanup",
        "← Back"
    ]
    
    selected = menu(stdscr, "Tools", items)
    
    if selected == 0:
        port_scanner(stdscr)
    elif selected == 1:
        ping_test(stdscr)
    elif selected == 2:
        dns_lookup(stdscr)
    elif selected == 3:
        config_editor(stdscr)
    elif selected == 4:
        cleanup_tool(stdscr)
    else:
        return

def about_screen(stdscr):
    """About screen"""
    height, width = stdscr.getmaxyx()
    
    about_text = [
        f"{APP} v{VERSION}",
        "Advanced VPN Client with Multi-Protocol Support",
        "",
        "Features:",
        "• VLESS, VMess, Trojan, Shadowsocks",
        "• Real-time traffic monitoring",
        "• Connection speed testing",
        "• Profile management",
        "• Advanced routing rules",
        "",
        "Telegram: @RAGEVPN_N1",
        "GitHub: github.com/ODINIZHAC2024/RAGEVPN-LI",
        "",
        "⚡ RAGE MODE: ACTIVATED ⚡"
    ]
    
    stdscr.clear()
    
    # Draw fancy border
    for y in range(2, height - 2):
        stdscr.addch(y, 10, '║', curses.color_pair(COLOR_CYAN))
        stdscr.addch(y, width - 11, '║', curses.color_pair(COLOR_CYAN))
    
    for x in range(11, width - 10):
        stdscr.addch(2, x, '═', curses.color_pair(COLOR_CYAN))
        stdscr.addch(height - 3, x, '═', curses.color_pair(COLOR_CYAN))
    
    stdscr.addch(2, 10, '╔', curses.color_pair(COLOR_CYAN))
    stdscr.addch(2, width - 11, '╗', curses.color_pair(COLOR_CYAN))
    stdscr.addch(height - 3, 10, '╚', curses.color_pair(COLOR_CYAN))
    stdscr.addch(height - 3, width - 11, '╝', curses.color_pair(COLOR_CYAN))
    
    # Show about text
    start_y = (height - len(about_text)) // 2
    for i, line in enumerate(about_text):
        if start_y + i < height - 2:
            x_pos = (width - len(line)) // 2
            color = COLOR_GREEN if i == 0 else COLOR_WHITE
            attr = curses.A_BOLD if i == 0 else curses.A_NORMAL
            stdscr.addstr(start_y + i, x_pos, line, curses.color_pair(color) | attr)
    
    stdscr.addstr(height - 2, (width - 20) // 2, "Press any key to continue", curses.color_pair(COLOR_YELLOW))
    stdscr.refresh()
    stdscr.getch()

# ========== HELPER FUNCTIONS ==========
def show_yesno(stdscr, question):
    """Show yes/no dialog"""
    height, width = stdscr.getmaxyx()
    
    lines = question.split('\n')
    box_height = len(lines) + 5
    box_width = max(len(l) for l in lines) + 4
    
    box_y = (height - box_height) // 2
    box_x = (width - box_width) // 2
    
    draw_box(stdscr, box_y, box_x, box_height, box_width, "Confirm")
    
    for i, line in enumerate(lines):
        if i < box_height - 5:
            stdscr.addstr(box_y + 2 + i, box_x + 2, line[:box_width-3])
    
    # Yes/No buttons
    yes_x = box_x + (box_width // 2) - 10
    no_x = box_x + (box_width // 2) + 2
    
    selected = 0  # 0 for Yes, 1 for No
    
    while True:
        if selected == 0:
            stdscr.addstr(box_y + box_height - 3, yes_x, "[ YES ]", 
                         curses.color_pair(COLOR_GREEN) | curses.A_BOLD | curses.A_REVERSE)
            stdscr.addstr(box_y + box_height - 3, no_x, "[ NO ]", 
                         curses.color_pair(COLOR_RED))
        else:
            stdscr.addstr(box_y + box_height - 3, yes_x, "[ YES ]", 
                         curses.color_pair(COLOR_GREEN))
            stdscr.addstr(box_y + box_height - 3, no_x, "[ NO ]", 
                         curses.color_pair(COLOR_RED) | curses.A_BOLD | curses.A_REVERSE)
        
        stdscr.refresh()
        
        key = stdscr.getch()
        
        if key == curses.KEY_LEFT:
            selected = 0
        elif key == curses.KEY_RIGHT:
            selected = 1
        elif key in (10, 13):  # Enter
            return selected == 0
        elif key == ord('y') or key == ord('Y'):
            return True
        elif key == ord('n') or key == ord('N'):
            return False
        elif key == 27:  # ESC
            return False

# ========== TOOL FUNCTIONS ==========
def port_scanner(stdscr):
    """Simple port scanner"""
    target = input_dialog(stdscr, "Enter target IP/hostname:", "127.0.0.1")
    if not target:
        return
    
    ports = input_dialog(stdscr, "Ports to scan (e.g., 80,443,1-1000):", "80,443,22,8080")
    
    show_message(stdscr, "Scanning ports...", COLOR_YELLOW, False)
    
    open_ports = []
    
    # Parse ports
    port_list = []
    for part in ports.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            port_list.extend(range(start, end + 1))
        else:
            port_list.append(int(part))
    
    # Scan ports
    for port in port_list[:100]:  # Limit to 100 ports
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((target, port))
            sock.close()
            
            if result == 0:
                open_ports.append(port)
        except:
            pass
    
    if open_ports:
        ports_str = ', '.join(map(str, open_ports))
        show_message(stdscr, f"Open ports on {target}:\n{ports_str}", COLOR_GREEN)
    else:
        show_message(stdscr, f"No open ports found on {target}", COLOR_RED)

def ping_test(stdscr):
    """Ping test tool"""
    target = input_dialog(stdscr, "Enter target to ping:", "1.1.1.1")
    if not target:
        return
    
    show_message(stdscr, f"Pinging {target}...", COLOR_YELLOW, False)
    
    try:
        result = sh(["ping", "-c", "4", target])
        if result and result.returncode == 0:
            show_message(stdscr, f"Ping successful!\n\n{result.stdout[:500]}", COLOR_GREEN)
        else:
            show_message(stdscr, "Ping failed!", COLOR_RED)
    except:
        show_message(stdscr, "Ping command not available", COLOR_RED)

def run_speed_test(stdscr):
    """Run speed test"""
    show_message(stdscr, "Running speed test...\nThis may take a moment.", COLOR_YELLOW, False)
    
    # Simple speed test using curl
    test_url = "https://speed.cloudflare.com/__down?bytes=10000000"  # 10MB
    
    start_time = time.time()
    try:
        result = sh(["curl", "-s", "-o", "/dev/null", "-w", "%{speed_download}", test_url])
        
        if result and result.stdout:
            speed = float(result.stdout)  # bytes per second
            mbps = (speed * 8) / (1024 * 1024)
            elapsed = time.time() - start_time
            
            show_message(stdscr, f"Speed test complete!\n\n"
                               f"Download: {mbps:.2f} Mbps\n"
                               f"Time: {elapsed:.1f} seconds\n"
                               f"Data: 10 MB", COLOR_GREEN)
    except:
        show_message(stdscr, "Speed test failed!", COLOR_RED)

# ========== MAIN ENTRY ==========
def main():
    """Main entry point"""
    # Check dependencies
    singbox_installed, version = check_singbox()
    
    if not singbox_installed:
        print("[-] sing-box is not installed!")
        print("[*] Please install sing-box to use RAGEVPN")
        print("[*] Download from: https://sing-box.sagernet.org/")
        sys.exit(1)
    
    print(f"[*] Starting {APP} v{VERSION}")
    print(f"[*] sing-box version: {version}")
    print("[*] Initializing...")
    
    # Run curses application
    try:
        curses.wrapper(main_menu)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        stop_singbox()
        print("[*] Goodbye!")

if __name__ == "__main__":
    main()
