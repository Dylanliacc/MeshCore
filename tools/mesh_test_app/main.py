#!/usr/bin/env python3
"""
MeshCore Test Controller - Cross-platform serial control application
"""

import os
import queue
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
                port=port,
                baudrate=baudrate,
                timeout=0.1,
                write_timeout=1
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
                    data = (data + '\r\n').encode('utf-8')
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
                        self.read_queue.put(data.decode('utf-8', errors='replace'))
                else:
                    time.sleep(0.01)
            except Exception:
                break


class MeshTestApp(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("MeshCore Test Controller")
        self.geometry("900x700")
        self.minsize(700, 500)
        
        # Serial handler
        self.serial = SerialHandler()
        self.log_buffer = []
        
        # Create UI
        self._create_widgets()
        
        # Start update loop
        self.after(50, self._update_serial)
    
    def _create_widgets(self):
        """Create all UI widgets"""
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # === Connection Frame ===
        conn_frame = ctk.CTkFrame(self)
        conn_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        conn_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(conn_frame, text="🔌 串口:", font=("", 14)).grid(
            row=0, column=0, padx=10, pady=10)
        
        self.port_combo = ctk.CTkComboBox(conn_frame, width=200, values=[""])
        self.port_combo.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        
        self.refresh_btn = ctk.CTkButton(conn_frame, text="🔄", width=40,
                                          command=self._refresh_ports)
        self.refresh_btn.grid(row=0, column=2, padx=2, pady=10)
        
        self.connect_btn = ctk.CTkButton(conn_frame, text="连接", width=80,
                                          fg_color="#28a745", hover_color="#218838",
                                          command=self._toggle_connect)
        self.connect_btn.grid(row=0, column=3, padx=10, pady=10)
        
        self.cli_btn = ctk.CTkButton(conn_frame, text="CLI 模式", width=100,
                                      fg_color="#6c757d", hover_color="#5a6268",
                                      command=self._enter_cli_mode)
        self.cli_btn.grid(row=0, column=4, padx=5, pady=10)
        
        self.status_label = ctk.CTkLabel(conn_frame, text="● 未连接", 
                                          text_color="#dc3545", font=("", 12))
        self.status_label.grid(row=0, column=5, padx=15, pady=10)
        
        # === Control Frame ===
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        buttons = [
            ("📊 Test Status", self._cmd_test_status, "#007bff"),
            ("⚙️ Config", self._cmd_config, "#17a2b8"),
            ("📥 Log Dump", self._cmd_log_dump, "#fd7e14"),
            ("🔄 Reboot", self._cmd_reboot, "#dc3545"),
            ("❓ Help", self._cmd_help, "#6c757d"),
        ]
        
        for i, (text, cmd, color) in enumerate(buttons):
            btn = ctk.CTkButton(ctrl_frame, text=text, width=120,
                                fg_color=color, hover_color=self._darken(color),
                                command=cmd)
            btn.grid(row=0, column=i, padx=8, pady=10)
        
        # === Log Display ===
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        
        self.log_text = ctk.CTkTextbox(log_frame, font=("Consolas", 12),
                                        wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # === Command Frame ===
        cmd_frame = ctk.CTkFrame(self)
        cmd_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")
        cmd_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(cmd_frame, text="命令:", font=("", 12)).grid(
            row=0, column=0, padx=10, pady=10)
        
        self.cmd_entry = ctk.CTkEntry(cmd_frame, placeholder_text="输入命令...")
        self.cmd_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.cmd_entry.bind("<Return>", lambda e: self._send_command())
        
        ctk.CTkButton(cmd_frame, text="发送", width=70,
                      command=self._send_command).grid(row=0, column=2, padx=5, pady=10)
        
        ctk.CTkButton(cmd_frame, text="清空", width=70, fg_color="#6c757d",
                      hover_color="#5a6268",
                      command=self._clear_log).grid(row=0, column=3, padx=5, pady=10)
        
        ctk.CTkButton(cmd_frame, text="导出", width=70, fg_color="#28a745",
                      hover_color="#218838",
                      command=self._export_log).grid(row=0, column=4, padx=10, pady=10)
        
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
            self.connect_btn.configure(text="连接", fg_color="#28a745",
                                        hover_color="#218838")
            self.status_label.configure(text="● 未连接", text_color="#dc3545")
            self._log_message("[系统] 已断开连接")
        else:
            port = self.port_combo.get()
            if not port or port == "无可用端口":
                return
            result = self.serial.connect(port)
            if result is True:
                self.connect_btn.configure(text="断开", fg_color="#dc3545",
                                            hover_color="#c82333")
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
    
    def _cmd_log_dump(self):
        """Send log dump command"""
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
        """Export log to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mesh_test_log_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.writelines(self.log_buffer)
            self._log_message(f"[系统] 日志已导出到 {filename}")
        except Exception as e:
            self._log_message(f"[错误] 导出失败: {e}")
    
    def on_closing(self):
        """Handle window close"""
        self.serial.disconnect()
        self.destroy()


def main():
    app = MeshTestApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
