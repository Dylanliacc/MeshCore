#!/usr/bin/env python3
"""
MeshCore Test Controller - Cross-platform serial control application
"""

import os
import queue
import random
import re
import threading
import time
from datetime import datetime

import customtkinter as ctk
import serial
import serial.tools.list_ports

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SerialHandler:
    """Handle serial port communication"""

    def __init__(self):
        self.serial_port = None
        self.read_queue = queue.Queue()
        self.running = False
        self.read_thread = None

    @staticmethod
    def list_ports():
        """List available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect(self, port, baudrate=115200):
        """Connect to serial port"""
        try:
            self.serial_port = serial.Serial(
                port=port, baudrate=baudrate, timeout=0.1, write_timeout=1
            )
            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            return True
        except Exception as e:
            return str(e)

    def disconnect(self):
        """Disconnect from serial port"""
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=1)
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

    def is_connected(self):
        """Check if connected"""
        return self.serial_port is not None and self.serial_port.is_open

    def write(self, data):
        """Write data to serial port"""
        if self.is_connected():
            try:
                if isinstance(data, str):
                    data = (data + "\r\n").encode("utf-8")
                self.serial_port.write(data)
                return True
            except Exception as e:
                return str(e)
        return False

    def _read_loop(self):
        """Background thread to read serial data"""
        while self.running and self.serial_port:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self.read_queue.put(data.decode("utf-8", errors="replace"))
                else:
                    time.sleep(0.01)
            except Exception:
                break


class MeshTestApp(ctk.CTk):
    """Main application window with Christmas theme"""

    # Christmas color palette
    XMAS_RED = "#c41e3a"
    XMAS_GREEN = "#228b22"
    XMAS_GOLD = "#ffd700"
    XMAS_SNOW = "#fffafa"
    XMAS_DARK = "#0d1117"

    def __init__(self):
        super().__init__()

        # Window setup
        self.title("🎄 MeshCore Test Controller - Merry Christmas! 🎅")
        self.geometry("1100x700")
        self.minsize(900, 500)

        # Serial handler
        self.serial = SerialHandler()
        self.log_buffer = []
        self.line_buffer = ""
        self.test_logs = []  # Parsed test log entries

        # Snowflake animation
        self.snowflakes = []
        self.snow_canvas = None

        # Create UI
        self._create_widgets()

        # Start update loops
        self.after(50, self._update_serial)
        self.after(100, self._animate_snow)

    def _create_widgets(self):
        """Create all UI widgets"""

        # Configure grid - 2 columns now
        self.grid_columnconfigure(0, weight=0, minsize=260)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(2, weight=1)

        # === Connection Frame (spans both columns) ===
        conn_frame = ctk.CTkFrame(self)
        conn_frame.grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew"
        )
        conn_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(conn_frame, text="🔌 串口:", font=("", 14)).grid(
            row=0, column=0, padx=10, pady=10
        )

        self.port_combo = ctk.CTkComboBox(conn_frame, width=200, values=[""])
        self.port_combo.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        self.refresh_btn = ctk.CTkButton(
            conn_frame, text="🔄", width=40, command=self._refresh_ports
        )
        self.refresh_btn.grid(row=0, column=2, padx=2, pady=10)

        self.connect_btn = ctk.CTkButton(
            conn_frame,
            text="连接",
            width=80,
            fg_color="#28a745",
            hover_color="#218838",
            command=self._toggle_connect,
        )
        self.connect_btn.grid(row=0, column=3, padx=10, pady=10)

        self.cli_btn = ctk.CTkButton(
            conn_frame,
            text="CLI 模式",
            width=100,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self._enter_cli_mode,
        )
        self.cli_btn.grid(row=0, column=4, padx=5, pady=10)

        self.status_label = ctk.CTkLabel(
            conn_frame, text="● 未连接", text_color="#dc3545", font=("", 12)
        )
        self.status_label.grid(row=0, column=5, padx=15, pady=10)

        # === Control Frame (spans both columns) ===
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        buttons = [
            ("📊 Status", self._cmd_test_status, "#007bff"),
            ("📈 Info", self._cmd_test_info, "#20c997"),
            ("⚙️ Config", self._cmd_config, "#17a2b8"),
            ("📥 Dump", self._cmd_log_dump, "#fd7e14"),
            ("🗑️ Clear", self._cmd_test_clear, "#6610f2"),
            ("🔄 Reboot", self._cmd_reboot, "#dc3545"),
            ("❓ Help", self._cmd_help, "#6c757d"),
        ]

        for i, (text, cmd, color) in enumerate(buttons):
            btn = ctk.CTkButton(
                ctrl_frame,
                text=text,
                width=120,
                fg_color=color,
                hover_color=self._darken(color),
                command=cmd,
            )
            btn.grid(row=0, column=i, padx=8, pady=10)

        # === Sidebar (Left) ===
        sidebar = ctk.CTkFrame(self, fg_color="#0d1117")
        sidebar.grid(row=2, column=0, padx=(10, 5), pady=5, sticky="nsew")
        sidebar.grid_rowconfigure(2, weight=1)

        # Device Info Section
        info_frame = ctk.CTkFrame(
            sidebar, fg_color="#1a2a1a", border_width=2, border_color=self.XMAS_GREEN
        )
        info_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            info_frame,
            text="🎁 设备信息",
            font=("", 13, "bold"),
            text_color=self.XMAS_GREEN,
        ).pack(pady=(8, 5))

        self.info_labels = {}
        for label, key in [("设备 ID:", "id"), ("已发送:", "seq"), ("已接收:", "log")]:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label, font=("", 11), width=70, anchor="w").pack(
                side="left"
            )
            self.info_labels[key] = ctk.CTkLabel(
                row, text="--", font=("Consolas", 12, "bold"), text_color="#00ff88"
            )
            self.info_labels[key].pack(side="right", padx=5)

        # Add some padding at bottom
        ctk.CTkFrame(info_frame, height=8, fg_color="transparent").pack()

        # Buffer Info Section
        buffer_frame = ctk.CTkFrame(
            sidebar, fg_color="#1a1a2a", border_width=2, border_color=self.XMAS_GOLD
        )
        buffer_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            buffer_frame,
            text="💾 缓冲区状态",
            font=("", 13, "bold"),
            text_color=self.XMAS_GOLD,
        ).pack(pady=(8, 5))

        self.buffer_labels = {}
        for label, key in [
            ("已用/总量:", "entries"),
            ("剩余条目:", "remaining"),
            ("使用率:", "percent"),
            ("循环模式:", "circular"),
        ]:
            row = ctk.CTkFrame(buffer_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label, font=("", 11), width=70, anchor="w").pack(
                side="left"
            )
            self.buffer_labels[key] = ctk.CTkLabel(
                row, text="--", font=("Consolas", 11), text_color="#88ccff"
            )
            self.buffer_labels[key].pack(side="right", padx=5)

        ctk.CTkFrame(buffer_frame, height=8, fg_color="transparent").pack()

        # Radio Config Section
        config_frame = ctk.CTkFrame(
            sidebar, fg_color="#2a1a1a", border_width=2, border_color=self.XMAS_RED
        )
        config_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(
            config_frame,
            text="🎀 无线配置",
            font=("", 13, "bold"),
            text_color=self.XMAS_RED,
        ).pack(pady=(8, 5))

        self.config_labels = {}
        for label, key in [
            ("频率:", "freq"),
            ("SF:", "sf"),
            ("BW:", "bw"),
            ("CR:", "cr"),
            ("功率:", "tx_power"),
            ("转发:", "fwd"),
        ]:
            row = ctk.CTkFrame(config_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label, font=("", 11), width=50, anchor="w").pack(
                side="left"
            )
            self.config_labels[key] = ctk.CTkLabel(
                row, text="--", font=("Consolas", 11), text_color="#ffd166"
            )
            self.config_labels[key].pack(side="right", padx=5)

        ctk.CTkFrame(config_frame, height=8, fg_color="transparent").pack()

        # === Log Display (Right) ===
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=1, padx=(5, 10), pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        # Log header
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        ctk.CTkLabel(log_header, text="🖥️ 串口输出", font=("", 13, "bold")).pack(
            side="left"
        )

        self.log_text = ctk.CTkTextbox(
            log_frame, font=("Consolas", 11), wrap="word", state="disabled"
        )
        self.log_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # === Command Frame (spans both columns) ===
        cmd_frame = ctk.CTkFrame(self)
        cmd_frame.grid(
            row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew"
        )
        cmd_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cmd_frame, text="命令:", font=("", 12)).grid(
            row=0, column=0, padx=10, pady=10
        )

        self.cmd_entry = ctk.CTkEntry(cmd_frame, placeholder_text="输入命令...")
        self.cmd_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.cmd_entry.bind("<Return>", lambda e: self._send_command())

        ctk.CTkButton(
            cmd_frame, text="发送", width=70, command=self._send_command
        ).grid(row=0, column=2, padx=5, pady=10)

        ctk.CTkButton(
            cmd_frame,
            text="清空",
            width=70,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self._clear_log,
        ).grid(row=0, column=3, padx=5, pady=10)

        ctk.CTkButton(
            cmd_frame,
            text="导出",
            width=70,
            fg_color="#28a745",
            hover_color="#218838",
            command=self._export_log,
        ).grid(row=0, column=4, padx=10, pady=10)

        # Initial port refresh
        self._refresh_ports()

    @staticmethod
    def _darken(hex_color):
        """Darken a hex color"""
        r = max(0, int(hex_color[1:3], 16) - 30)
        g = max(0, int(hex_color[3:5], 16) - 30)
        b = max(0, int(hex_color[5:7], 16) - 30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _refresh_ports(self):
        """Refresh available ports"""
        ports = SerialHandler.list_ports()
        self.port_combo.configure(values=ports if ports else ["无可用端口"])
        if ports:
            self.port_combo.set(ports[0])

    def _toggle_connect(self):
        """Connect or disconnect"""
        if self.serial.is_connected():
            self.serial.disconnect()
            self.connect_btn.configure(
                text="连接", fg_color="#28a745", hover_color="#218838"
            )
            self.status_label.configure(text="● 未连接", text_color="#dc3545")
            self._log_message("[系统] 已断开连接")
        else:
            port = self.port_combo.get()
            if not port or port == "无可用端口":
                return
            result = self.serial.connect(port)
            if result is True:
                self.connect_btn.configure(
                    text="断开", fg_color="#dc3545", hover_color="#c82333"
                )
                self.status_label.configure(text="● 已连接", text_color="#28a745")
                self._log_message(f"[系统] 已连接到 {port}")
            else:
                self._log_message(f"[错误] 连接失败: {result}")

    def _enter_cli_mode(self):
        """Enter CLI rescue mode"""
        if self.serial.is_connected():
            self.serial.write("~~~")
            self._log_message("[系统] 发送 ~~~ 进入 CLI 模式")

    def _send_command(self):
        """Send custom command"""
        cmd = self.cmd_entry.get().strip()
        if cmd and self.serial.is_connected():
            self.serial.write(cmd)
            self._log_message(f">>> {cmd}")
            self.cmd_entry.delete(0, "end")

    def _cmd_test_status(self):
        """Send test status command"""
        self._send_cli_cmd("test status")

    def _cmd_config(self):
        """Send config command"""
        self._send_cli_cmd("config")

    def _cmd_test_info(self):
        """Send test info command"""
        self._send_cli_cmd("test info")

    def _cmd_test_clear(self):
        """Send test clear command"""
        self._send_cli_cmd("test clear")

    def _cmd_log_dump(self):
        """Send log dump command"""
        self.test_logs.clear()  # Clear previous logs before new dump
        self._send_cli_cmd("test dump")

    def _cmd_reboot(self):
        """Send reboot command"""
        self._send_cli_cmd("reboot")

    def _cmd_help(self):
        """Send help command"""
        self._send_cli_cmd("help")

    def _send_cli_cmd(self, cmd):
        """Send CLI command"""
        if self.serial.is_connected():
            self.serial.write(cmd)
            self._log_message(f">>> {cmd}")
        else:
            self._log_message("[警告] 请先连接串口")

    def _parse_line(self, line):
        """Parse incoming line for structured data"""
        line = line.strip()
        if not line:
            return

        # Parse TESTSTATUS: TESTSTATUS 69F5 seq=63 log=63
        match = re.match(r"TESTSTATUS\s+([A-F0-9]+)\s+seq=(\d+)\s+log=(\d+)", line)
        if match:
            self.info_labels["id"].configure(text=match.group(1))
            self.info_labels["seq"].configure(text=match.group(2))
            self.info_labels["log"].configure(text=match.group(3))
            return

        # Parse test info output: Entries: 342 / 1000 (34.2% used)
        match = re.match(r"Entries:\s*(\d+)\s*/\s*(\d+)\s*\(([\d.]+)%", line)
        if match:
            self.buffer_labels["entries"].configure(
                text=f"{match.group(1)} / {match.group(2)}"
            )
            self.buffer_labels["percent"].configure(text=f"{match.group(3)}%")
            return

        # Parse remaining entries: Remaining: 658 entries
        match = re.match(r"Remaining:\s*(\d+)\s*entries", line)
        if match:
            self.buffer_labels["remaining"].configure(text=match.group(1))
            return

        # Parse circular mode: Circular Mode: YES/NO
        match = re.match(r"Circular Mode:\s*(\w+)", line)
        if match:
            mode = match.group(1)
            if mode == "YES":
                self.buffer_labels["circular"].configure(
                    text="是 ⚠️", text_color="#ffaa00"
                )
            else:
                self.buffer_labels["circular"].configure(
                    text="否", text_color="#88ccff"
                )
            return

        # Parse TESTLOG header - clear logs when new dump starts
        if line.startswith("TESTLOG ") and not line.startswith("TESTLOG_END"):
            self.test_logs.clear()
            return

        # Parse Radio Config lines
        if "freq:" in line:
            m = re.search(r"freq:\s*([\d.]+)", line)
            if m:
                self.config_labels["freq"].configure(text=f"{m.group(1)} MHz")
        elif "sf:" in line:
            m = re.search(r"sf:\s*(\d+)", line)
            if m:
                self.config_labels["sf"].configure(text=m.group(1))
        elif "bw:" in line:
            m = re.search(r"bw:\s*([\d.]+)", line)
            if m:
                self.config_labels["bw"].configure(text=f"{m.group(1)} kHz")
        elif "cr:" in line:
            m = re.search(r"cr:\s*(\d+)", line)
            if m:
                self.config_labels["cr"].configure(text=m.group(1))
        elif "tx_power:" in line:
            m = re.search(r"tx_power:\s*(\d+)", line)
            if m:
                self.config_labels["tx_power"].configure(text=f"{m.group(1)} dBm")
        elif "fwd:" in line:
            m = re.search(r"fwd:\s*(\d+)", line)
            if m:
                self.config_labels["fwd"].configure(
                    text="启用" if m.group(1) == "1" else "禁用"
                )

        # Parse test log entries: <device_id>,<seq>,<tx_time>,<rx_time>,<snr>,<rssi>,<path_len>
        match = re.match(
            r"^([A-F0-9]{4}),(\d+),(\d+),(\d+),(-?\d+),(-?\d+),(\d+)$", line
        )
        if match:
            entry = {
                "device_id": match.group(1),
                "seq": match.group(2),
                "tx_time": match.group(3),
                "rx_time": match.group(4),
                "snr": match.group(5),
                "rssi": match.group(6),
                "path_len": match.group(7),
            }
            self.test_logs.append(entry)

    def _log_message(self, msg):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}\n"
        self.log_buffer.append(full_msg)

        self.log_text.configure(state="normal")
        self.log_text.insert("end", full_msg)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _update_serial(self):
        """Update serial data from queue"""
        try:
            while True:
                data = self.serial.read_queue.get_nowait()
                self.log_buffer.append(data)

                # Parse lines for structured data
                self.line_buffer += data
                while "\n" in self.line_buffer:
                    line, self.line_buffer = self.line_buffer.split("\n", 1)
                    self._parse_line(line)

                # Update raw log
                self.log_text.configure(state="normal")
                self.log_text.insert("end", data)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass

        self.after(50, self._update_serial)

    def _clear_log(self):
        """Clear log display"""
        self.log_buffer.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _export_log(self):
        """Export test logs to CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Get receiver device ID from UI
        receiver_id = self.info_labels["id"].cget("text")
        if receiver_id == "--":
            receiver_id = "UNKNOWN"

        # Export parsed test logs as CSV
        if self.test_logs:
            csv_filename = f"mesh_test_{receiver_id}_{timestamp}.csv"
            try:
                with open(csv_filename, "w", encoding="utf-8") as f:
                    # Write metadata header
                    f.write(f"# MeshCore Network Test Log\n")
                    f.write(f"# Receiver Device ID: {receiver_id}\n")
                    f.write(
                        f"# Export Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write(f"# Total Entries: {len(self.test_logs)}\n")
                    f.write(f"#\n")
                    # Write CSV header
                    f.write(
                        "sender_id,seq,tx_time,rx_time,delay_sec,snr,rssi,path_len\n"
                    )
                    # Write data
                    for entry in self.test_logs:
                        tx = int(entry["tx_time"])
                        rx = int(entry["rx_time"])
                        delay = rx - tx if tx > 0 and rx > 0 else 0
                        f.write(
                            f"{entry['device_id']},{entry['seq']},{entry['tx_time']},{entry['rx_time']},{delay},{entry['snr']},{entry['rssi']},{entry['path_len']}\n"
                        )
                self._log_message(
                    f"[系统] 测试日志已导出到 {csv_filename} ({len(self.test_logs)} 条)"
                )
            except Exception as e:
                self._log_message(f"[错误] CSV导出失败: {e}")
        else:
            self._log_message("[警告] 没有测试日志可导出，请先执行 Log Dump")

        # Also export raw log
        txt_filename = f"mesh_raw_{receiver_id}_{timestamp}.txt"
        try:
            with open(txt_filename, "w", encoding="utf-8") as f:
                f.writelines(self.log_buffer)
            self._log_message(f"[系统] 原始日志已导出到 {txt_filename}")
        except Exception as e:
            self._log_message(f"[错误] 原始日志导出失败: {e}")

    def on_closing(self):
        """Handle window close"""
        self.serial.disconnect()
        self.destroy()

    def _animate_snow(self):
        """Animate falling snowflakes in the title bar area"""
        # Simple snowflake animation using title update
        snow_chars = ["❄", "❅", "❆", "✻", "✼"]
        current_title = self.title()

        # Cycle through festive titles
        titles = [
            "🎄 MeshCore Test Controller - Merry Christmas! 🎅",
            "❄️ MeshCore Test Controller - Merry Christmas! 🎁",
            "🎁 MeshCore Test Controller - Merry Christmas! 🎄",
            "⭐ MeshCore Test Controller - Merry Christmas! ❄️",
        ]

        # Find current and switch to next
        try:
            idx = titles.index(current_title)
            next_idx = (idx + 1) % len(titles)
        except ValueError:
            next_idx = 0

        self.title(titles[next_idx])
        self.after(1000, self._animate_snow)  # Update every second


def main():
    app = MeshTestApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
