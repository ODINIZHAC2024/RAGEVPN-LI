# ⚡RAGEVPN-LI⚡
<p align="center">
  <img src="https://img.shields.io/badge/RAGEVPN--LI-RAGEVPN-red?style=for-the-badge">
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/ODINIZHAC2024/RAGEVPN-LI?style=flat-square">
  <img src="https://img.shields.io/github/forks/ODINIZHAC2024/RAGEVPN-LI?style=flat-square">
  <img src="https://img.shields.io/github/license/ODINIZHAC2024/RAGEVPN-LI?style=flat-square">
  <img src="https://img.shields.io/badge/Linux-Supported-success?style=flat-square">
  <img src="https://img.shields.io/badge/Windows-Planned-inactive?style=flat-square">
  <img src="https://img.shields.io/badge/Powered%20by-sing--box-black?style=flat-square">
</p>

---
<pre>
██████╗  █████╗  ██████╗ ███████╗██╗   ██╗██████╗ ███╗   ██╗
██╔══██╗██╔══██╗██╔════╝ ██╔════╝██║   ██║██╔══██╗████╗  ██║
██████╔╝███████║██║  ███╗█████╗  ██║   ██║██████╔╝██╔██╗ ██║
██╔══██╗██╔══██║██║   ██║██╔══╝  ██║   ██║██╔══██╗██║╚██╗██║
██║  ██║██║  ██║╚██████╔╝███████╗╚██████╔╝██║  ██║██║ ╚████║
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝</pre>

**RAGEVPN-LI** is a terminal-based VPN client for Linux built on top of **sing-box**.  
The project is designed as a universal, minimalistic, and extensible VPN frontend with support for modern proxy protocols.

> 🖥️ A Windows GUI version (`.exe`) will be released later.

---

## ✨ Features

- 📟 Terminal user interface (TUI, curses)
- 🌐 Supported protocols:
  - **VLESS**
  - **Shadowsocks (SS)**
  - **Trojan**
  - **VMess**
  - **SOCKS5**
- 🔗 Connection via standard links (`vless://`, `ss://`, `trojan://`, etc.)
- 👤 Profile manager
- 🔄 Auto reconnect
- 📊 RX / TX traffic monitoring
- 🧠 Automatic protocol detection
- 🧩 Clean architecture (frontend + sing-box)
- 🚫 No hardcoded servers
- ⚡ Minimal dependencies

---

## 🧠 Architecture

RAGEVPN-LI **does not implement VPN protocols itself**.  
It works as:

> **A TUI controller and configuration manager for sing-box**

This makes the project secure, maintainable, and easy to extend.

---

## 📦 Dependencies

### System
```bash
sudo apt install python3 python3-pip
```
### Python
```bash
pip install psutil
```
### VPN Core
Install sing-box and make sure it is available in $PATH:
```
sing-box version
```
---

### 🚀 Installation
```
git clone https://github.com/ODINIZHAC2024/RAGEVPN-LI
cd RAGEVPN-LI
chmod +x RAGEVPN.py
./RAGEVPN.py
```
---

### 🖱️ Usage

1. Launch the client


2. Add a profile by pasting a connection link:
```
vless://...
ss://...
trojan://...
```
3. Select a profile
4. VPN starts automatically via sing-box
5. Monitor connection status and traffic in the terminal

---

### Exit:
<pre>
Ctrl + C
</pre>

---

### 📣 Community

📢 **Official Telegram channel**:
👉 *https://t.me/RAGEVPN_N1*
