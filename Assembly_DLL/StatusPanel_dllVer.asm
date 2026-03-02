.586
.model flat, stdcall
option casemap :none

includelib kernel32.lib
includelib iphlpapi.lib
includelib psapi.lib
includelib user32.lib

; прототипи функцій, які будуть використовуватися для отримання системної інформації
; =================================================================================
GlobalMemoryStatusEx proto stdcall :ptr
GetSystemTimes proto stdcall :ptr, :ptr, :ptr
GetTickCount  proto stdcall
GetIfTable    proto stdcall :ptr, :ptr, :dword
GetPerformanceInfo proto stdcall :ptr, :dword
GetDiskFreeSpaceExA proto stdcall :ptr, :ptr, :ptr, :ptr
EnumDisplayDevicesA proto stdcall :ptr, :dword, :ptr, :dword

; структури для зберігання даних, які будуть використовуватися в функції UpdateStats і геттерах
; =================================================================================
MEMORYSTATUSEX struct
    dwLength        dword ?
    dwMemoryLoad    dword ?
    ullTotalPhys    qword ?
    ullAvailPhys    qword ?
    ullTotalPageFile qword ?
    ullAvailPageFile qword ?
    ullTotalVirtual qword ?
    ullAvailVirtual qword ?
    ullAvailExt     qword ?
MEMORYSTATUSEX ends

FILETIME struct
    dwLowDateTime  dword ?
    dwHighDateTime dword ?
FILETIME ends

MIB_IFROW struct
    wszName         word 256 dup(?)
    dwIndex         dword ?
    dwType          dword ?
    dwMtu           dword ?
    dwSpeed         dword ?
    dwPhysAddrLen   dword ?
    bPhysAddr       byte 8 dup(?)
    dwAdminStatus   dword ?
    dwOperStatus    dword ?
    dwLastChange    dword ?
    dwInOctets      dword ?
    dwInUcastPkts   dword ?
    dwInNUcastPkts  dword ?
    dwInDiscards    dword ?
    dwInErrors      dword ?
    dwInUnknownProtos dword ?
    dwOutOctets     dword ?
    dwOutUcastPkts  dword ?
    dwOutNUcastPkts dword ?
    dwOutDiscards   dword ?
    dwOutErrors     dword ?
    dwOutQLen       dword ?
    dwDescrLen      dword ?
    bDescr          byte 256 dup(?)
MIB_IFROW ends

PERFORMANCE_INFORMATION struct
    cb                dword ?
    CommitTotal       dword ?
    CommitLimit       dword ?
    CommitPeak        dword ?
    PhysicalTotal     dword ?
    PhysicalAvailable dword ?
    SystemCache       dword ?
    KernelTotal       dword ?
    KernelPaged       dword ?
    KernelNonpaged    dword ?
    PageSize          dword ?
    HandleCount       dword ?
    ProcessCount      dword ?
    ThreadCount       dword ?
PERFORMANCE_INFORMATION ends

DISPLAY_DEVICEA struct
    cb           dword ?
    DeviceName   byte 32 dup(0)
    DeviceString byte 128 dup(0) 
    StateFlags   dword ?
    DeviceID     byte 128 dup(0)
    DeviceKey    byte 128 dup(0)
DISPLAY_DEVICEA ends

.data
    ; кеш для зберігання даних, які будуть обчислюватися в UpdateStats і повертатися в Python через геттери
    memStat MEMORYSTATUSEX <>
    perfInfo PERFORMANCE_INFORMATION <>
    dispDev DISPLAY_DEVICEA <>
    
    driveC      db "C:\", 0
    totalBytes  dq 0
    freeBytes   dq 0

    prevIdle   FILETIME <>
    prevKernel FILETIME <>
    prevUser   FILETIME <>
    currIdle   FILETIME <>
    currKernel FILETIME <>
    currUser   FILETIME <>
    
    ifTableBuffer db 100000 dup(0)
    ifTableSize   dd 100000
    prevNetRx     dd 0
    prevNetTx     dd 0
    sumRx         dd 0
    sumTx         dd 0

    ; змінні для зберігання результатів, які будуть повертатися в Python
    outCpuLoad      dd 0
    outRamLoad      dd 0
    outRamTotalGB   dd 0
    outRamUsedGB    dd 0
    outDiskTotalGB  dd 0
    outDiskUsedGB   dd 0
    outNetRx        dd 0
    outNetTx        dd 0
    outUptime       dd 0

.code

; Точка входу для DLL
DllMain proc hInstDLL:dword, reason:dword, reserved1:dword
    mov eax, 1  ; Повертаємо TRUE
    ret
DllMain endp

; Ініціалізація
InitSystem proc
    mov dispDev.cb, sizeof DISPLAY_DEVICEA 
    invoke EnumDisplayDevicesA, 0, 0, addr dispDev, 0
    ret
InitSystem endp

; Головна функція розрахунків
UpdateStats proc uses eax ebx ecx edx esi edi
    mov memStat.dwLength, sizeof MEMORYSTATUSEX
    mov perfInfo.cb, sizeof PERFORMANCE_INFORMATION

    ; 1. RAM 
    invoke GlobalMemoryStatusEx, addr memStat
    mov eax, memStat.dwMemoryLoad
    mov outRamLoad, eax
    
    mov eax, dword ptr [memStat.ullTotalPhys]
    mov edx, dword ptr [memStat.ullTotalPhys + 4]
    shrd eax, edx, 30         
    mov outRamTotalGB, eax
    
    mov eax, dword ptr [memStat.ullAvailPhys]
    mov edx, dword ptr [memStat.ullAvailPhys + 4]
    shrd eax, edx, 30
    mov ecx, outRamTotalGB
    sub ecx, eax
    mov outRamUsedGB, ecx

    ; 2. Uptime 
    invoke GetTickCount       
    xor edx, edx
    mov ecx, 1000
    div ecx                   
    mov outUptime, eax

    ; 3. Диск C:
    invoke GetDiskFreeSpaceExA, addr driveC, 0, addr totalBytes, addr freeBytes
    mov eax, dword ptr [totalBytes]
    mov edx, dword ptr [totalBytes + 4]
    shrd eax, edx, 30         
    mov outDiskTotalGB, eax

    mov eax, dword ptr [freeBytes]
    mov edx, dword ptr [freeBytes + 4]
    shrd eax, edx, 30
    mov ecx, outDiskTotalGB
    sub ecx, eax
    mov outDiskUsedGB, ecx

    ; 4. Системні показники - Потоки, Дескриптори
    invoke GetPerformanceInfo, addr perfInfo, sizeof PERFORMANCE_INFORMATION

    ; 5. Завантаженість CPU
    invoke GetSystemTimes, addr currIdle, addr currKernel, addr currUser
    mov eax, currKernel.dwLowDateTime
    add eax, currUser.dwLowDateTime
    mov ecx, eax 
    mov eax, prevKernel.dwLowDateTime
    add eax, prevUser.dwLowDateTime
    mov ebx, eax 
    mov eax, ecx
    sub eax, ebx
    mov ecx, eax 
    test ecx, ecx
    jz cpu_zero
    mov eax, currIdle.dwLowDateTime
    sub eax, prevIdle.dwLowDateTime
    mov ebx, eax 
    mov eax, ecx
    sub eax, ebx  
    jns cpu_calc 
    xor eax, eax
cpu_calc:
    imul eax, eax, 100
    xor edx, edx
    div ecx       
    jmp cpu_save
cpu_zero:
    xor eax, eax
cpu_save:
    mov outCpuLoad, eax 
    mov eax, currIdle.dwLowDateTime
    mov prevIdle.dwLowDateTime, eax
    mov eax, currKernel.dwLowDateTime
    mov prevKernel.dwLowDateTime, eax
    mov eax, currUser.dwLowDateTime
    mov prevUser.dwLowDateTime, eax

    ; 6. Мережева активність
    mov ifTableSize, 100000
    invoke GetIfTable, addr ifTableBuffer, addr ifTableSize, 0
    cmp eax, 0                          
    jne net_error
    
    mov ecx, dword ptr [ifTableBuffer]  
    lea esi, [ifTableBuffer + 4]        
    mov sumRx, 0
    mov sumTx, 0
    test ecx, ecx
    jz net_done
net_loop:
    mov eax, [esi + MIB_IFROW.dwOperStatus]
    cmp eax, 5
    jne net_next
    mov eax, [esi + MIB_IFROW.dwType]
    cmp eax, 6                          
    je net_add
    cmp eax, 71                         
    je net_add
    jmp net_next                    
net_add:
    mov eax, [esi + MIB_IFROW.dwInOctets]
    add sumRx, eax                        
    mov eax, [esi + MIB_IFROW.dwOutOctets]
    add sumTx, eax                        
net_next:
    add esi, sizeof MIB_IFROW
    dec ecx
    jnz net_loop
net_done:
    mov eax, sumRx                       
    mov ebx, prevNetRx
    mov prevNetRx, eax              
    test ebx, ebx
    jz net_tx_calc                     
    sub eax, ebx                       
    shr eax, 10                        
    mov outNetRx, eax
net_tx_calc:
    mov eax, sumTx                       
    mov ebx, prevNetTx
    mov prevNetTx, eax              
    test ebx, ebx
    jz net_end                     
    sub eax, ebx                       
    shr eax, 10                        
    mov outNetTx, eax
    jmp net_end
net_error:
    mov outNetRx, 0
    mov outNetTx, 0
net_end:

    ret
UpdateStats endp


; функції геттери для отримання даних з кешу в Python
; =================================================================================

; Копіюємо текст у буфер Python
GetCpuName proc uses ebx ecx edx edi, pBuffer:ptr byte
    mov edi, pBuffer
    mov eax, 80000002h      
    cpuid
    mov [edi], eax
    mov [edi+4], ebx
    mov [edi+8], ecx
    mov [edi+12], edx
    mov eax, 80000003h      
    cpuid
    mov [edi+16], eax
    mov [edi+20], ebx
    mov [edi+24], ecx
    mov [edi+28], edx
    mov eax, 80000004h      
    cpuid
    mov [edi+32], eax
    mov [edi+36], ebx
    mov [edi+40], ecx
    mov [edi+44], edx
    ret
GetCpuName endp

GetGpuName proc uses esi edi ecx, pBuffer:ptr byte
    cld
    lea esi, dispDev.DeviceString
    mov edi, pBuffer
    mov ecx, 128
    rep movsb    ; Копіюємо 128 байт назви GPU у буфер, який передасть Python
    ret
GetGpuName endp

; Повернення числових показників
GetCpuLoad proc
    mov eax, outCpuLoad
    ret
GetCpuLoad endp

GetRamLoad proc
    mov eax, outRamLoad
    ret
GetRamLoad endp

GetRamTotalGB proc
    mov eax, outRamTotalGB
    ret
GetRamTotalGB endp

GetRamUsedGB proc
    mov eax, outRamUsedGB
    ret
GetRamUsedGB endp

GetDiskTotalGB proc
    mov eax, outDiskTotalGB
    ret
GetDiskTotalGB endp

GetDiskUsedGB proc
    mov eax, outDiskUsedGB
    ret
GetDiskUsedGB endp

GetNetRx proc
    mov eax, outNetRx
    ret
GetNetRx endp

GetNetTx proc
    mov eax, outNetTx
    ret
GetNetTx endp

GetUptime proc
    mov eax, outUptime
    ret
GetUptime endp

GetProcesses proc
    mov eax, perfInfo.ProcessCount
    ret
GetProcesses endp

GetThreads proc
    mov eax, perfInfo.ThreadCount
    ret
GetThreads endp

GetHandles proc
    mov eax, perfInfo.HandleCount
    ret
GetHandles endp

end DllMain