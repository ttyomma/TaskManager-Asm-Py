import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk
import collections
import customtkinter as ctk
import os
import sys

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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Load DLL
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

# Initialize system data for GPU
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
        ("WorkingSetSize", ctypes.c_uint32),
        ("QuotaPeakPagedPoolUsage", ctypes.c_uint32),
        ("QuotaPagedPoolUsage", ctypes.c_uint32),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_uint32),
        ("QuotaNonPagedPoolUsage", ctypes.c_uint32),
        ("PagefileUsage", ctypes.c_uint32),
        ("PeakPagefileUsage", ctypes.c_uint32),
    ]

def get_process_list():
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
            
            ram_mb = 0
            hProcess = kernel32.OpenProcess(0x0410, False, pid)
            if hProcess:
                pmc = PROCESS_MEMORY_COUNTERS()
                pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
                if psapi.GetProcessMemoryInfo(hProcess, ctypes.byref(pmc), pmc.cb):
                    ram_mb = pmc.WorkingSetSize // (1024 * 1024) # Convert to Megabytes
                kernel32.CloseHandle(hProcess)

            if ram_mb > 0:
                result.append((pid, threads, ram_mb, name))

            if not kernel32.Process32Next(hSnap, ctypes.byref(pe32)):
                break

    kernel32.CloseHandle(hSnap)
    
    # Sort the list by RAM usage from highest to lowest
    result.sort(key=lambda x: x[2], reverse=True)
    return result

# SystemGraph
class SystemGraph:
    def __init__(self, parent, title, color_line, color_fill, max_val=100, dynamic_scale=False):
        self.frame = ctk.CTkFrame(parent, fg_color="#151A27", corner_radius=15)
        self.frame.pack(fill="x", pady=10, padx=20)

        # Header for the graph
        self.header_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=15, pady=(10, 0))
        self.lbl_title = ctk.CTkLabel(self.header_frame, text=title, font=("Segoe UI", 16, "bold"), text_color="white")
        self.lbl_title.pack(side="left")
        self.lbl_value = ctk.CTkLabel(self.header_frame, text="0%", font=("Segoe UI", 13), text_color="#9CA3AF")
        self.lbl_value.pack(side="right")
        self.w, self.h = 600, 80
        self.canvas = tk.Canvas(self.frame, width=self.w, height=self.h, bg="#151A27", highlightthickness=0)
        self.canvas.pack(pady=(5, 10), padx=15)
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
            self.canvas.create_line(0, y, self.w, y, fill="#1F2937", tags="grid", dash=(2, 2))

    def update(self, new_val, text_label):
        self.lbl_value.configure(text=text_label)
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
        self.canvas.create_polygon(coords, fill=self.color_fill, outline="", tags="graph", stipple="gray50") # Give it some transparency effect if win32 supports stipple
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
    lbl_stat_cpu.configure(text=f"{cpu}%")
    lbl_stat_ram.configure(text=f"{ram_used} GB")
    lbl_stat_disk.configure(text=f"{disk_used} / {disk_tot}")
    lbl_stat_proc.configure(text=str(asm_engine.GetProcesses()))
    graph_cpu.update(cpu, f"{cpu}%")
    graph_ram.update(ram, f"{ram}% ({ram_used} GB / {ram_tot} GB)")
    graph_net.update(net_rx + net_tx, f"DL {net_rx} KB/s  |  UL {net_tx} KB/s")

    # process update, sorted from heaviest to lightest
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

# Function to switch frames
def select_frame(frame_name):
    btn_dash.configure(fg_color="#1D4ED8" if frame_name == "dashboard" else "transparent")
    btn_proc.configure(fg_color="#1D4ED8" if frame_name == "processes" else "transparent")
    
    if frame_name == "dashboard":
        dash_frame.pack(fill="both", expand=True)
    else:
        dash_frame.pack_forget()

    if frame_name == "processes":
        proc_frame.pack(fill="both", expand=True)
    else:
        proc_frame.pack_forget()

def set_dark_titlebar(window):
    try:
        import ctypes as ct
        window.update()
        hwnd = ct.windll.user32.GetParent(window.winfo_id())
        value = ct.c_int(2)
        ct.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ct.byref(value), ct.sizeof(value))
    except:
        pass

# UI
root = ctk.CTk()
root.title("ASM Monitor")
root.geometry("850x750")
root.resizable(False, False)
ctk.set_appearance_mode("Dark")
root.configure(fg_color="#0B0F19")

# Main container
main_container = ctk.CTkFrame(root, fg_color="transparent")
main_container.pack(fill="both", expand=True)

# Sidebar
sidebar_frame = ctk.CTkFrame(main_container, width=220, fg_color="#111827", corner_radius=0)
sidebar_frame.pack(side="left", fill="y")
sidebar_frame.pack_propagate(False)
lbl_logo = ctk.CTkLabel(sidebar_frame, text="ASM Monitor", font=("Segoe UI", 20, "bold"), text_color="white")
lbl_logo.pack(pady=(30, 40))
btn_dash = ctk.CTkButton(sidebar_frame, text="Dashboard", font=("Segoe UI", 14, "bold"), fg_color="#1D4ED8", hover_color="#2563EB", anchor="w", width=180, height=40, command=lambda: select_frame("dashboard"))
btn_dash.pack(pady=5)
btn_proc = ctk.CTkButton(sidebar_frame, text="Processes", font=("Segoe UI", 14, "bold"), fg_color="transparent", text_color="#E5E7EB", hover_color="#1F2937", anchor="w", width=180, height=40, command=lambda: select_frame("processes"))
btn_proc.pack(pady=5)
lbl_uptime = ctk.CTkLabel(sidebar_frame, text="Uptime: ...", font=("Segoe UI", 12), text_color="#9CA3AF")
lbl_uptime.pack(side="bottom", pady=20)

# Content container
content_frame = ctk.CTkFrame(main_container, fg_color="#0B0F19", corner_radius=0)
content_frame.pack(side="right", fill="both", expand=True)

# Dashboard Frame
dash_frame = ctk.CTkFrame(content_frame, fg_color="transparent")

# Header in Dashboard
dash_header = ctk.CTkFrame(dash_frame, fg_color="transparent")
dash_header.pack(fill="x", padx=20, pady=(20, 10))
lbl_header_title = ctk.CTkLabel(dash_header, text="System Overview", font=("Segoe UI", 24, "bold"), text_color="white")
lbl_header_title.pack(anchor="w")
sub_header = ctk.CTkFrame(dash_header, fg_color="transparent")
sub_header.pack(anchor="w", pady=(2, 0))
lbl_cpu = ctk.CTkLabel(sub_header, text=f"CPU: {cpu_name}", font=("Segoe UI", 12), text_color="#9CA3AF")
lbl_cpu.pack(side="left", padx=(0, 15))
lbl_gpu = ctk.CTkLabel(sub_header, text=f"GPU: {gpu_name}", font=("Segoe UI", 12), text_color="#9CA3AF")
lbl_gpu.pack(side="left")

# Stat Cards Row
stats_frame = ctk.CTkFrame(dash_frame, fg_color="transparent")
stats_frame.pack(fill="x", padx=15, pady=5)

def create_stat_card(parent, title, value="0"):
    card = ctk.CTkFrame(parent, fg_color="#151A27", corner_radius=15, width=135, height=80)
    card.pack_propagate(False)
    card.pack(side="left", padx=5, expand=True)
    lbl_t = ctk.CTkLabel(card, text=title, font=("Segoe UI", 12), text_color="#9CA3AF")
    lbl_t.pack(anchor="w", padx=15, pady=(10, 0))
    lbl_v = ctk.CTkLabel(card, text=value, font=("Segoe UI", 20, "bold"), text_color="white")
    lbl_v.pack(anchor="w", padx=15)
    return lbl_v

lbl_stat_cpu = create_stat_card(stats_frame, "CPU Load")
lbl_stat_ram = create_stat_card(stats_frame, "RAM Used")
lbl_stat_disk = create_stat_card(stats_frame, "Disk Space")
lbl_stat_proc = create_stat_card(stats_frame, "Processes")

# Graphs
graph_cpu = SystemGraph(dash_frame, "CPU Performance", color_line="#3B82F6", color_fill="#1e3a8a", max_val=100)
graph_ram = SystemGraph(dash_frame, "Memory Usage", color_line="#8B5CF6", color_fill="#4c1d95", max_val=100)
graph_net = SystemGraph(dash_frame, "Network Traffic", color_line="#10B981", color_fill="#064e3b", dynamic_scale=True)

# Processes Frame
proc_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
proc_header = ctk.CTkFrame(proc_frame, fg_color="transparent")
proc_header.pack(fill="x", padx=20, pady=(20, 10))
ctk.CTkLabel(proc_header, text="Process Explorer", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left")
tree_container = ctk.CTkFrame(proc_frame, fg_color="#151A27", corner_radius=15)
tree_container.pack(fill="both", expand=True, padx=20, pady=10)
tree_frame = ctk.CTkFrame(tree_container, fg_color="transparent")
tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
style = ttk.Style()
style.theme_use("default")
style.configure(
    "Custom.Treeview",
    background="#151A27",
    foreground="#D1D5DB",
    fieldbackground="#151A27",
    borderwidth=0,
    rowheight=35,
    font=("Segoe UI", 11)
)
style.configure(
    "Custom.Treeview.Heading",
    background="#1F2937",
    foreground="white",
    font=("Segoe UI", 12, "bold"),
    borderwidth=0,
    relief="flat"
)
style.map("Custom.Treeview", background=[('selected', '#3B82F6')], foreground=[('selected', 'white')])
style.map("Custom.Treeview.Heading", background=[('active', '#374151')])

scrollbar = ctk.CTkScrollbar(tree_frame)
scrollbar.pack(side="right", fill="y")

columns = ("pid", "threads", "ram", "name")
tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set, style="Custom.Treeview")
scrollbar.configure(command=tree.yview)

tree.heading("pid", text="PID")
tree.column("pid", width=80, anchor="center")
tree.heading("threads", text="Threads")
tree.column("threads", width=80, anchor="center")
tree.heading("ram", text="RAM (MB)")
tree.column("ram", width=100, anchor="center")
tree.heading("name", text="Process Name")
tree.column("name", width=380, anchor="w")
tree.pack(side="left", fill="both", expand=True)

select_frame("dashboard")

# Start
update_dashboard()
root.mainloop()