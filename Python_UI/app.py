# Loading DLL and Basic Settings
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox
import collections
import customtkinter as ctk
import os
import sys

def get_path(name):
    base = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base, name)

try:
    asm = ctypes.WinDLL(get_path("kursASM_UIPython/StatusPanel_dllVer.dll"))
except Exception as err:
    print("Error loading DLL:", err)
    sys.exit()

funcs = [
    "GetCpuLoad", "GetRamLoad", "GetRamTotalGB", "GetRamUsedGB",
    "GetDiskTotalGB", "GetDiskUsedGB", "GetNetRx", "GetNetTx",
    "GetUptime", "GetProcesses", "GetThreads", "GetHandles", "KillProcess"
]
for f in funcs:
    getattr(asm, f).restype = ctypes.c_uint32

asm.KillProcess.argtypes = [ctypes.c_uint32]
try:
    asm.InitSystem()
except:
    pass

def get_hw_str(func, size=128):
    buf = ctypes.create_string_buffer(size)
    getattr(asm, func)(buf)
    return buf.value.decode('utf-8', errors='ignore').strip()

cpu_name = get_hw_str("GetCpuName", 50) or "Unknown CPU"
gpu_name = get_hw_str("GetGpuName", 128) or "Unknown GPU"

# Data Structures for API 
class PE32(ctypes.Structure):
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

class PMC(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t)
    ]

def get_procs():
    k32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    pe = PE32()
    pe.dwSize = ctypes.sizeof(PE32)
    
    procs = []
    if k32.Process32First(snap, ctypes.byref(pe)):
        while True:
            pid = pe.th32ProcessID
            name = pe.szExeFile.decode('cp1251', errors='ignore')
            mem = 0
            
            handle = k32.OpenProcess(0x0410, False, pid)
            if handle:
                count = PMC()
                count.cb = ctypes.sizeof(PMC)
                if psapi.GetProcessMemoryInfo(handle, ctypes.byref(count), count.cb):
                    mem = count.WorkingSetSize // (1024 * 1024)
                k32.CloseHandle(handle)
                
            if mem > 0:
                procs.append((pid, pe.cntThreads, mem, name))
                
            if not k32.Process32Next(snap, ctypes.byref(pe)):
                break
                
    k32.CloseHandle(snap)
    procs.sort(key=lambda x: x[2], reverse=True) 
    return procs


#Graphic
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class Graph:
    def __init__(self, parent, title, col1, col2, max_v=100, dyn=False):
        self.c1 = col1
        self.c2 = col2
        self.mv = max_v
        self.dyn = dyn
        self.hist = collections.deque([0] * 60, maxlen=60)
        self.box = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1E293B")
        self.box.pack(fill="x", pady=5, padx=15)
        hdr = ctk.CTkFrame(self.box, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=8)
        dot = ctk.CTkLabel(hdr, text="●", font=("Segoe UI", 12), text_color=col1)
        dot.pack(side="left", padx=(0, 5))
        self.lbl1 = ctk.CTkLabel(hdr, text=title, font=("Segoe UI", 13, "bold"), text_color="#F1F5F9")
        self.lbl1.pack(side="left")
        self.lbl2 = ctk.CTkLabel(hdr, text="—", font=("Segoe UI", 12), text_color="#94A3B8")
        self.lbl2.pack(side="right")
        self.w, self.h = 620, 75
        self.canv = tk.Canvas(self.box, width=self.w, height=self.h, bg="#111827", highlightthickness=0)
        self.canv.pack(pady=(0, 10), padx=14)
        
        for i in range(1, 4):
            y = self.h * i // 4
            self.canv.create_line(0, y, self.w, y, fill="#1E293B", dash=(3, 6))

    def update(self, val, txt):
        self.lbl2.configure(text=txt)
        self.hist.append(val)
        self.canv.delete("line")
        
        pts = list(self.hist)
        mx = max(pts) if self.dyn else self.mv
        if mx < 10: mx = 10
            
        step = self.w / (len(pts) - 1)
        cords = []
        for i, v in enumerate(pts):
            x = i * step
            y = self.h - (min(v, mx) / mx) * self.h
            cords.append((x, y))
            
        poly = [(0, self.h)] + cords + [(self.w, self.h)]
        self.canv.create_polygon(poly, fill=self.c2, outline="", tags="line", stipple="gray25")
        self.canv.create_line(cords, fill=self.c1, width=2, smooth=True, tags="line")


def make_card(parent, text, icon=""):
    card = ctk.CTkFrame(parent, fg_color="#182236", corner_radius=15, border_width=1, border_color="#334155", width=160, height=105)
    card.pack_propagate(False)
    card.pack(side="left", padx=8, expand=True, fill="x")
    txt = f"{icon}  {text}" if icon else text
    ctk.CTkLabel(card, text=txt, font=("Segoe UI", 12), text_color="#94A3B8").pack(anchor="w", padx=15, pady=(12, 0))
    val = ctk.CTkLabel(card, text="—", font=("Segoe UI", 24, "bold"), text_color="#FFFFFF")
    val.pack(anchor="w", padx=15)
    bar = ctk.CTkProgressBar(card, height=4, fg_color="#0F172A", progress_color="#3B82F6")
    bar.set(0)
    bar.pack(fill="x", padx=15, pady=(8, 0))
    
    return val, bar

#Main window and navigation
app = ctk.CTk()
app.title("ASM Monitor")
app.geometry("900x760")
app.resizable(False, False)
app.configure(fg_color="#080C14")

try:
    app.update()
    hwnd = ctypes.windll.user32.GetParent(app.winfo_id())
    opt = ctypes.c_int(2)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(opt), ctypes.sizeof(opt))
except:
    pass

main = ctk.CTkFrame(app, fg_color="transparent")
main.pack(fill="both", expand=True)
sidebar = ctk.CTkFrame(main, width=210, fg_color="#090E1A", corner_radius=0)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)
logo = ctk.CTkFrame(sidebar, fg_color="transparent")
logo.pack(pady=30, padx=20, fill="x")
ctk.CTkLabel(logo, text="ASM", font=("Segoe UI", 26, "bold"), text_color="#3B82F6").pack(side="left")
ctk.CTkLabel(logo, text=" Monitor", font=("Segoe UI", 18), text_color="#F1F5F9").pack(side="left", pady=(4, 0))
ctk.CTkFrame(sidebar, height=1, fg_color="#334155").pack(fill="x", padx=16, pady=(0, 20))
content = ctk.CTkFrame(main, fg_color="#080C14", corner_radius=0)
content.pack(side="right", fill="both", expand=True)
dash = ctk.CTkFrame(content, fg_color="transparent")
proc_tab = ctk.CTkFrame(content, fg_color="transparent")

def switch_tab(name):
    if name == "dash":
        btn_dash.configure(fg_color="#1D4ED8", text_color="#FFFFFF")
        btn_proc.configure(fg_color="transparent", text_color="#94A3B8")
        dash.pack(fill="both", expand=True)
        proc_tab.pack_forget()
    else:
        btn_proc.configure(fg_color="#1D4ED8", text_color="#FFFFFF")
        btn_dash.configure(fg_color="transparent", text_color="#94A3B8")
        proc_tab.pack(fill="both", expand=True)
        dash.pack_forget()

fnt = ("Segoe UI", 13, "bold")
btn_dash = ctk.CTkButton(sidebar, text="  Dashboard", font=fnt, anchor="w", width=180, height=42, corner_radius=8, command=lambda: switch_tab("dash"))
btn_dash.pack(pady=5, padx=15)
btn_proc = ctk.CTkButton(sidebar, text="  Processes", font=fnt, anchor="w", width=180, height=42, corner_radius=8, command=lambda: switch_tab("proc"))
btn_proc.pack(pady=5, padx=15)
lbl_time = ctk.CTkLabel(sidebar, text="↑ Uptime: 0d 00:00:00", font=("Segoe UI", 12), text_color="#64748B")
lbl_time.pack(side="bottom", pady=25)

hdr1 = ctk.CTkFrame(dash, fg_color="transparent")
hdr1.pack(fill="x", padx=20, pady=20)
ctk.CTkLabel(hdr1, text="System Overview", font=("Segoe UI", 24, "bold"), text_color="#FFFFFF").pack(anchor="w")
ctk.CTkLabel(hdr1, text=f"⬡ {cpu_name}   |   ◈ {gpu_name}", font=("Segoe UI", 12), text_color="#94A3B8").pack(anchor="w", pady=5)

cards = ctk.CTkFrame(dash, fg_color="transparent")
cards.pack(fill="x", padx=12, pady=5)

lbl_cpu, bar_cpu = make_card(cards, "CPU Load", "▲")
lbl_ram, bar_ram = make_card(cards, "RAM Used", "▣")
lbl_disk, bar_disk = make_card(cards, "Disk Space", "◉")
lbl_proc, bar_proc = make_card(cards, "Processes", "◈")

gr_cpu = Graph(dash, "CPU History", "#3B82F6", "#1E3A8A")
gr_ram = Graph(dash, "Memory History", "#8B5CF6", "#4C1D95")
gr_net = Graph(dash, "Network Traffic", "#10B981", "#064E3B", dyn=True)

hdr2 = ctk.CTkFrame(proc_tab, fg_color="transparent")
hdr2.pack(fill="x", padx=20, pady=20)
ctk.CTkLabel(hdr2, text="Process Explorer", font=("Segoe UI", 24, "bold"), text_color="#FFFFFF").pack(side="left")

def kill_proc():
    sel = table.selection()
    if not sel:
        messagebox.showinfo("Error", "Please select a process to kill.")
        return
        
    data = table.item(sel[0], "values")
    pid = int(data[0])
    name = data[3]
    
    if messagebox.askyesno("Confirm", f"Are you sure you want to kill '{name}' (PID: {pid})?"):
        if asm.KillProcess(pid):
            messagebox.showinfo("Success", f"Process killed successfully.")
        else:
            messagebox.showerror("Failed", f"Access denied.")

btn_kill = ctk.CTkButton(hdr2, text="⊘ Kill Process", font=("Segoe UI", 12, "bold"), fg_color="#7F1D1D", hover_color="#991B1B", width=130, height=36, corner_radius=8, command=kill_proc)
btn_kill.pack(side="right")
table_bg = ctk.CTkFrame(proc_tab, fg_color="#182236", corner_radius=12)
table_bg.pack(fill="both", expand=True, padx=20, pady=(0, 20))

s = ttk.Style()
s.theme_use("default")
s.configure("Procs.Treeview", background="#182236", foreground="#E2E8F0", fieldbackground="#182236", borderwidth=0, rowheight=35, font=("Segoe UI", 11))
s.configure("Procs.Treeview.Heading", background="#0F172A", foreground="#94A3B8", font=("Segoe UI", 11, "bold"), borderwidth=0, relief="flat")
s.map("Procs.Treeview", background=[("selected", "#2563EB")])
scroll = ctk.CTkScrollbar(table_bg)
scroll.pack(side="right", fill="y", pady=10)
table = ttk.Treeview(table_bg, columns=("p", "t", "r", "n"), show="headings", yscrollcommand=scroll.set, style="Procs.Treeview")
scroll.configure(command=table.yview)
table.heading("p", text="PID")
table.heading("t", text="Threads")
table.heading("r", text="RAM Usage")
table.heading("n", text="Process Name")
table.column("p", width=80, anchor="center")
table.column("t", width=80, anchor="center")
table.column("r", width=100, anchor="center")
table.column("n", width=380, anchor="w")
table.pack(side="left", fill="both", expand=True, padx=10, pady=10)

# Logic for updating the UI with real-time data from the DLL and Windows API
def update_ui():
    asm.UpdateStats()
    cpu = asm.GetCpuLoad()
    ram = asm.GetRamLoad()
    ram_u = asm.GetRamUsedGB()
    ram_t = asm.GetRamTotalGB()
    disk_u = asm.GetDiskUsedGB()
    disk_t = asm.GetDiskTotalGB()
    net_rx = asm.GetNetRx()
    net_tx = asm.GetNetTx()
    up = asm.GetUptime()
    procs_cnt = asm.GetProcesses()

    d = up // 86400
    h = (up % 86400) // 3600
    m = (up % 3600) // 60
    secs = up % 60
    lbl_time.configure(text=f"↑ Uptime: {d}d {h:02d}:{m:02d}:{secs:02d}")
    lbl_cpu.configure(text=f"{cpu}%")
    bar_cpu.set(cpu / 100)
    lbl_ram.configure(text=f"{ram_u} GB")
    bar_ram.set(ram_u / ram_t if ram_t else 0)
    lbl_disk.configure(text=f"{disk_u}/{disk_t} GB")
    bar_disk.set(disk_u / disk_t if disk_t else 0)
    lbl_proc.configure(text=str(procs_cnt))
    bar_proc.set(procs_cnt / 500) 
    
    if procs_cnt > 300: 
        bar_proc.configure(progress_color="#EF4444")
    else: 
        bar_proc.configure(progress_color="#3B82F6")

    gr_cpu.update(cpu, f"{cpu}%")
    gr_ram.update(ram, f"{ram}%   ({ram_u} / {ram_t} GB)")
    gr_net.update(net_rx + net_tx, f"▼ {net_rx} KB/s   ▲ {net_tx} KB/s")

    now = set()
    for pid, th, mem, name in get_procs():
        k = str(pid)
        now.add(k)
        v = (pid, th, f"{mem} MB", name)
        
        if table.exists(k):
            table.item(k, values=v)
        else:
            table.insert("", "end", iid=k, values=v)

    for row in table.get_children():
        if row not in now:
            table.delete(row)
            
    for i, row in enumerate(table.get_children()):
        table.item(row, tags=("odd" if i % 2 == 0 else "even",))
    table.tag_configure("odd", background="#1E293B")
    table.tag_configure("even", background="#0F172A")

    app.after(1000, update_ui)

# launching
switch_tab("dash")
update_ui()
app.mainloop()