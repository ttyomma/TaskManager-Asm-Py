import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk
import collections
import customtkinter as ctk
import os
import sys

# Function to get the correct path for the DLL, whether running as a script or as a bundled executable
def get_path(filename):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(__file__), filename)

dll_path = get_path("StatusPanel_dllVer.dll")
asm_engine = ctypes.WinDLL(dll_path)

def resource_path(relative_path):
    import sys, os
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

asm_engine = ctypes.WinDLL(resource_path("StatusPanel_dllVer.dll"))

# Configure dark theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Load backend (ASM DLL)
dll_name = "StatusPanel_dllVer.dll"
try:
    asm_engine = ctypes.WinDLL(f"./{dll_name}")
except Exception as e:
    print(f"DLL Load Error\n{e}")
    exit()

# Configure return types
asm_engine.GetCpuLoad.restype = ctypes.c_uint32
asm_engine.GetRamLoad.restype = ctypes.c_uint32
asm_engine.GetRamTotalGB.restype = ctypes.c_uint32
asm_engine.GetRamUsedGB.restype = ctypes.c_uint32
asm_engine.GetDiskTotalGB.restype = ctypes.c_uint32
asm_engine.GetDiskUsedGB.restype = ctypes.c_uint32
asm_engine.GetNetRx.restype = ctypes.c_uint32
asm_engine.GetNetTx.restype = ctypes.c_uint32
asm_engine.GetUptime.restype = ctypes.c_uint32
asm_engine.GetProcesses.restype = ctypes.c_uint32
asm_engine.GetThreads.restype = ctypes.c_uint32
asm_engine.GetHandles.restype = ctypes.c_uint32

# Initialize system data (for GPU)
asm_engine.InitSystem()

# Get CPU name
cpu_buffer = ctypes.create_string_buffer(50)
asm_engine.GetCpuName(cpu_buffer)
cpu_name = cpu_buffer.value.decode('utf-8', errors='ignore').strip()

# Get GPU name
gpu_buffer = ctypes.create_string_buffer(128)
asm_engine.GetGpuName(gpu_buffer)
gpu_name = gpu_buffer.value.decode('utf-8', errors='ignore').strip()

if not gpu_name:
    gpu_name = "Unknown Graphics Device"

# WinAPI structures for processes and their memory
class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260)
    ]

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_uint32),
        ("WorkingSetSize", ctypes.c_uint32), # Contains the RAM bytes of the process
        ("QuotaPeakPagedPoolUsage", ctypes.c_uint32),
        ("QuotaPagedPoolUsage", ctypes.c_uint32),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_uint32),
        ("QuotaNonPagedPoolUsage", ctypes.c_uint32),
        ("PagefileUsage", ctypes.c_uint32),
        ("PeakPagefileUsage", ctypes.c_uint32),
    ]

def get_process_list():
    """
    Scans processes, gets threads and RAM.
    Hides system processes with Denied access (0 MB).
    """
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    
    hSnap = kernel32.CreateToolhelp32Snapshot(2, 0)
    if hSnap == -1:
        return []

    pe32 = PROCESSENTRY32()
    pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)
    result = []

    if kernel32.Process32First(hSnap, ctypes.byref(pe32)):
        while True:
            pid = pe32.th32ProcessID
            threads = pe32.cntThreads
            name = pe32.szExeFile.decode('cp1251', errors='ignore')
            
            # Request memory usage (Smart filter)
            ram_mb = 0
            # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_VM_READ (0x0010)
            hProcess = kernel32.OpenProcess(0x0410, False, pid)
            if hProcess:
                pmc = PROCESS_MEMORY_COUNTERS()
                pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
                if psapi.GetProcessMemoryInfo(hProcess, ctypes.byref(pmc), pmc.cb):
                    ram_mb = pmc.WorkingSetSize // (1024 * 1024) # Convert to Megabytes
                kernel32.CloseHandle(hProcess)

            # Add to the list ONLY if we have access to it (ram_mb > 0)
            if ram_mb > 0:
                result.append((pid, threads, ram_mb, name))

            if not kernel32.Process32Next(hSnap, ctypes.byref(pe32)):
                break

    kernel32.CloseHandle(hSnap)
    
    # Sort the list by RAM usage (from highest to lowest)
    result.sort(key=lambda x: x[2], reverse=True)
    return result

# Class for drawing live graphs
class SystemGraph:
    def __init__(self, parent, title, color_line, color_fill, max_val=100, dynamic_scale=False):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="x", pady=5, padx=15)

        self.lbl = ctk.CTkLabel(self.frame, text=title, font=("Segoe UI", 13, "bold"))
        self.lbl.pack(anchor="w", padx=5)

        self.w, self.h = 560, 90
        self.canvas = tk.Canvas(self.frame, width=self.w, height=self.h, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(pady=5)

        self.color_line = color_line
        self.color_fill = color_fill
        self.max_val = max_val
        self.dynamic_scale = dynamic_scale
        self.history = collections.deque([0] * 60, maxlen=60)
        self._draw_grid()

    def _draw_grid(self):
        self.canvas.delete("grid")
        for i in range(1, 4):
            y = self.h * (i / 4)
            self.canvas.create_line(0, y, self.w, y, fill="#2a2a2a", tags="grid", dash=(2, 2))

    def update(self, new_val, text_label):
        self.lbl.configure(text=text_label)
        self.history.append(new_val)
        self.canvas.delete("graph")

        current_max = max(self.history) if self.dynamic_scale else self.max_val
        if current_max < 10:
            current_max = 10

        coords = [(0, self.h)]
        line_coords = []
        step_x = self.w / (len(self.history) - 1)

        for i, val in enumerate(self.history):
            x = i * step_x
            y = self.h - (min(val, current_max) / current_max) * self.h
            coords.append((x, y))
            line_coords.append((x, y))

        coords.append((self.w, self.h))
        self.canvas.create_polygon(coords, fill=self.color_fill, outline="", tags="graph")
        self.canvas.create_line(line_coords, fill=self.color_line, width=2, tags="graph")

# Main dashboard update loop
def update_dashboard():
    asm_engine.UpdateStats()

    cpu = asm_engine.GetCpuLoad()
    ram = asm_engine.GetRamLoad()
    ram_used = asm_engine.GetRamUsedGB()
    ram_tot = asm_engine.GetRamTotalGB()
    disk_used = asm_engine.GetDiskUsedGB()
    disk_tot = asm_engine.GetDiskTotalGB()
    net_rx = asm_engine.GetNetRx()
    net_tx = asm_engine.GetNetTx()

    uptime_sec = asm_engine.GetUptime()
    d, h, m, s = (
        uptime_sec // 86400,
        (uptime_sec % 86400) // 3600,
        (uptime_sec % 3600) // 60,
        uptime_sec % 60,
    )

    lbl_uptime.configure(text=f"Uptime: {d}d {h:02d}:{m:02d}:{s:02d}")
    lbl_disk.configure(text=f"Disk C:  {disk_used} GB / {disk_tot} GB")
    lbl_sys_stats.configure(
        text=f"Processes: {asm_engine.GetProcesses()}   |   Threads: {asm_engine.GetThreads()}   |   Handles: {asm_engine.GetHandles()}"
    )

    graph_cpu.update(cpu, f"CPU: {cpu}%")
    graph_ram.update(ram, f"RAM: {ram}% ({ram_used} GB / {ram_tot} GB)")
    graph_net.update(net_rx + net_tx, f"Network:  DL {net_rx} KB/s   |   UL {net_tx} KB/s")

    # Smart process update with RAM consideration (sorted from heaviest to lightest)
    current_pids = set()
    for pid, th_count, ram_mb, name in get_process_list():
        pid_str = str(pid)
        current_pids.add(pid_str)
        if tree.exists(pid_str):
            tree.item(pid_str, values=(pid, th_count, f"{ram_mb} MB", name))
        else:
            tree.insert("", "end", iid=pid_str, values=(pid, th_count, f"{ram_mb} MB", name))

    for row_id in tree.get_children():
        if row_id not in current_pids:
            tree.delete(row_id)

    root.after(1000, update_dashboard)

# Build UI
root = ctk.CTk()
root.title("ASM Monitor")
root.geometry("620x750") # Slightly increased height to fit GPU
root.resizable(False, False)

style = ttk.Style()
style.theme_use("default")
style.configure(
    "Treeview",
    background="#1e1e1e",
    foreground="#dce4ee",
    fieldbackground="#1e1e1e",
    borderwidth=0,
    rowheight=25,
)
style.configure(
    "Treeview.Heading",
    background="#1f538d",
    foreground="white",
    font=("Segoe UI", 10, "bold"),
    borderwidth=0,
)
style.map("Treeview", background=[('selected', '#1f538d')])

tabview = ctk.CTkTabview(root, width=600, height=720)
tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))
tabview.add("Dashboard")
tabview.add("Processes")

# Dashboard Tab
tab_dash = tabview.tab("Dashboard")

header_frame = ctk.CTkFrame(tab_dash, fg_color="transparent")
header_frame.pack(pady=5, fill="x")

# Display CPU and GPU
ctk.CTkLabel(header_frame, text=f"CPU: {cpu_name}", font=("Segoe UI", 16, "bold")).pack()
ctk.CTkLabel(header_frame, text=f"GPU: {gpu_name}", font=("Segoe UI", 14, "bold"), text_color="#4da6ff").pack(pady=(2, 5))

lbl_uptime = ctk.CTkLabel(header_frame, text="...", font=("Segoe UI", 12), text_color="gray")
lbl_uptime.pack()

graph_cpu = SystemGraph(tab_dash, "CPU", color_line="#1f6aa5", color_fill="#14375a", max_val=100)
graph_ram = SystemGraph(tab_dash, "RAM", color_line="#9368d1", color_fill="#4a2e73", max_val=100)
graph_net = SystemGraph(tab_dash, "Network", color_line="#2fa572", color_fill="#154a33", dynamic_scale=True)

bottom_frame = ctk.CTkFrame(tab_dash, fg_color="transparent")
bottom_frame.pack(fill="x", padx=20, pady=10)
lbl_disk = ctk.CTkLabel(bottom_frame, text="Disk C:", font=("Segoe UI", 12, "bold"))
lbl_disk.pack(side="left")
lbl_sys_stats = ctk.CTkLabel(bottom_frame, text="...", font=("Segoe UI", 11), text_color="gray")
lbl_sys_stats.pack(side="right")

# Processes Tab
tab_proc = tabview.tab("Processes")

tree_frame = ctk.CTkFrame(tab_proc, fg_color="transparent")
tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

scrollbar = ctk.CTkScrollbar(tree_frame)
scrollbar.pack(side="right", fill="y", padx=(5, 0))

columns = ("pid", "threads", "ram", "name")
tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
scrollbar.configure(command=tree.yview)

tree.heading("pid", text="PID")
tree.column("pid", width=70, anchor="center")
tree.heading("threads", text="Threads")
tree.column("threads", width=70, anchor="center")
tree.heading("ram", text="RAM (MB)")
tree.column("ram", width=80, anchor="center")
tree.heading("name", text="Process Name")
tree.column("name", width=340, anchor="w")
tree.pack(side="left", fill="both", expand=True)

# Start
update_dashboard()
root.mainloop()