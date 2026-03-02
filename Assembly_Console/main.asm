.586
.model flat, stdcall      ; Плоска модель памяті
option casemap :none      ; великі та малі літери у назвах

includelib msvcrt.lib
includelib legacy_stdio_definitions.lib
includelib ucrt.lib
includelib vcruntime.lib
includelib kernel32.lib      ; Базові функції системи
includelib iphlpapi.lib      ; Функції для роботи з мережею та інтернетом
includelib psapi.lib         ; Функції для отримання розширеної інформації про процеси
includelib user32.lib        ; Функції для для отримання даних про монітор та відеокарту

GRAPH_WIDTH equ 20           ; Ширина графіків у консолі 

; Прототипи функцій
; =================================================================================
printf      proto C :ptr byte, :VARARG
strcat      proto C :ptr byte, :ptr byte
Sleep       proto stdcall :dword
ExitProcess proto stdcall :dword
GetStdHandle proto stdcall :dword
SetConsoleCursorPosition proto stdcall :dword, :dword
GetLocalTime proto stdcall :ptr
GlobalMemoryStatusEx proto stdcall :ptr
SetConsoleOutputCP proto stdcall :dword
GetSystemTimes proto stdcall :ptr, :ptr, :ptr
GetSystemInfo proto stdcall :ptr
GetTickCount  proto stdcall
GetIfTable    proto stdcall :ptr, :ptr, :dword
GetPerformanceInfo proto stdcall :ptr, :dword
GetDiskFreeSpaceExA proto stdcall :ptr, :ptr, :ptr, :ptr
CreateToolhelp32Snapshot proto stdcall :dword, :dword
Process32First proto stdcall :dword, :ptr
Process32Next  proto stdcall :dword, :ptr
CloseHandle    proto stdcall :dword
EnumDisplayDevicesA proto stdcall :ptr, :dword, :ptr, :dword
OpenProcess proto stdcall :dword, :dword, :dword
GetProcessMemoryInfo proto stdcall :dword, :ptr, :dword

; Структури даних - Шаблони куди Windows буде записувати інформацію
; =================================================================================
SysTime struct               ; Зберігає поточний час
    wYear   word ?
    wMonth  word ?
    wDayOfWeek word ?
    wDay    word ?
    wHour   word ?
    wMin    word ?
    wSec    word ?
    wMs     word ?
SysTime ends

MEMORYSTATUSEX struct        ; Інформація про оперативну память
    dwLength        dword ?
    dwMemoryLoad    dword ?  ; Відсоток завантаженості RAM
    ullTotalPhys    qword ?  ; Всього памяті
    ullAvailPhys    qword ?  ; Вільно памяті
    ullTotalPageFile qword ?
    ullAvailPageFile qword ?
    ullTotalVirtual qword ?
    ullAvailVirtual qword ?
    ullAvailExt     qword ?
MEMORYSTATUSEX ends

FILETIME struct ; Допоміжна структура для підрахунку завантаження CPU
    dwLowDateTime  dword ?
    dwHighDateTime dword ?
FILETIME ends

SYSTEM_INFO struct ; Загальна інформація про систему
    wProcessorArchitecture      word ?
    wReserved                   word ?
    dwPageSize                  dword ?
    lpMinimumApplicationAddress dword ?
    lpMaximumApplicationAddress dword ?
    dwActiveProcessorMask       dword ?
    dwNumberOfProcessors        dword ?
    dwProcessorType             dword ?
    dwAllocationGranularity     dword ?
    wProcessorLevel             word ?
    wProcessorRevision          word ?
SYSTEM_INFO ends

PROCESS_MEMORY_COUNTERS struct ; Інформація про використання памяті конкретним процесом
    cb                         dword ?
    PageFaultCount             dword ?
    PeakWorkingSetSize         dword ?
    WorkingSetSize             dword ?   ; байти памяті, які використовує процес
    QuotaPeakPagedPoolUsage    dword ?
    QuotaPagedPoolUsage        dword ?
    QuotaPeakNonPagedPoolUsage dword ?
    QuotaNonPagedPoolUsage     dword ?
    PagefileUsage              dword ?
    PeakPagefileUsage          dword ?
PROCESS_MEMORY_COUNTERS ends

MIB_IFROW struct ; Структура для мережевого адаптера wi-fi, ethernet
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
    dwInOctets      dword ?  ; Скільки байт скачано
    dwInUcastPkts   dword ?
    dwInNUcastPkts  dword ?
    dwInDiscards    dword ?
    dwInErrors      dword ?
    dwInUnknownProtos dword ?
    dwOutOctets     dword ?  ; Скільки байт відправлено
    dwOutUcastPkts  dword ?
    dwOutNUcastPkts dword ?
    dwOutDiscards   dword ?
    dwOutErrors     dword ?
    dwOutQLen       dword ?
    dwDescrLen      dword ?
    bDescr          byte 256 dup(?)
MIB_IFROW ends

PERFORMANCE_INFORMATION struct ; Дані про процеси, потоки та дескриптори системи
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

DISPLAY_DEVICEA struct       ; Структура для збереження даних про відеокарту
    cb           dword ?
    DeviceName   byte 32 dup(0)
    DeviceString byte 128 dup(0) ; тут назва відеоадаптера
    StateFlags   dword ?
    DeviceID     byte 128 dup(0)
    DeviceKey    byte 128 dup(0)
DISPLAY_DEVICEA ends

PROCESSENTRY32 struct          ; інформація про конкретний запущений процес
    dwSize              dword ?
    cntUsage            dword ?
    th32ProcessID       dword ?
    th32DefaultHeapID   dword ?
    th32ModuleID        dword ?
    cntThreads          dword ?
    th32ParentProcessID dword ?
    pcPriClassBase      dword ?
    dwFlags             dword ?
    szExeFile           byte 260 dup(?)
PROCESSENTRY32 ends

.data
    ; шаблон інтерфейсу для функції printf
    fmtData db "=================================================================", 10
            db " SYSTEM: %s", 10
            db " GPU:    %s", 10
            db " TIME: %02d:%02d:%02d        | UPTIME: %02dd %02dh %02dm %02ds", 10
            db "-----------------------------------------------------------------", 10
            db " CPU: %3d%% [%s]   PROCS: %d", 10
            db "                                    THREADS: %d", 10
            db "                                    HANDLES: %d", 10
            db " RAM: %3d%% [%s]   %d GB / %d GB", 10
            db " DISK (C:):                   %d GB / %d GB", 10
            db "-----------------------------------------------------------------", 10
            db " NET: %6d KB/s [%s]   UL: %d KB/s", 10
            db "================================================================= ", 10, 0 
    
    cpuName db 49 dup(0)
    dispDev DISPLAY_DEVICEA <>
    sTime   SysTime <>
    memStat MEMORYSTATUSEX <>
    sysInfo SYSTEM_INFO <>
    perfInfo PERFORMANCE_INFORMATION <>
    hOut    dd ?               ; дескриптор консолі для виводу

    ; шаблони для виводу списку процесів
    fmtProcHeader db "*****************************************************************", 10
                  db "-----------------------------------------------------------------", 10
                  db " PID    | THREADS | RAM      | PROCESS NAME", 10
                  db "-----------------------------------------------------------------", 10, 0
    fmtProc       db " %-6d | %-7d | %-4d MB  | %-25s ", 10, 0

    ; Змінні для роботи з диском
    driveC      db "C:\", 0
    totalBytes  dq 0
    freeBytes   dq 0
    totalDiskGB dd 0
    usedDiskGB  dd 0
    
    ; Змінні для розрахунку CPU
    prevIdle   FILETIME <>
    prevKernel FILETIME <>
    prevUser   FILETIME <>
    currIdle   FILETIME <>
    currKernel FILETIME <>
    currUser   FILETIME <>
    cpuLoad    dd 0
    cpuHistory dd GRAPH_WIDTH dup(0)
    cpuGraph   db 100 dup(0) 
    
    ; Змінні для RAM
    ramHistory dd GRAPH_WIDTH dup(0)
    ramGraph   db 100 dup(0) 
    totalRamGB dd 0
    usedRamGB  dd 0
    
    ; Змінні для розрахунку мережі
    ifTableBuffer db 100000 dup(0)
    ifTableSize   dd 100000
    prevNetRx     dd 0
    prevNetTx     dd 0
    netLoadKB     dd 0
    netTxLoadKB   dd 0
    netHistory    dd GRAPH_WIDTH dup(0)
    netGraph      db 100 dup(0)
    sumRx         dd 0
    sumTx         dd 0
    
    ; Змінні для Uptime
    uptimeDays dd 0
    uptimeHrs  dd 0
    uptimeMin  dd 0
    uptimeSec  dd 0
    
    ; UTF-8 символи для графіків у консолі 
    str0 db " ", 0
    str1 db 0E2h, 096h, 082h, 0
    str2 db 0E2h, 096h, 083h, 0
    str3 db 0E2h, 096h, 084h, 0
    str4 db 0E2h, 096h, 085h, 0
    str5 db 0E2h, 096h, 086h, 0
    str6 db 0E2h, 096h, 087h, 0
    str7 db 0E2h, 096h, 087h, 0
    blocks dd offset str0, offset str1, offset str2, offset str3, offset str4, offset str5, offset str6, offset str7

.code

; Отримання назви процесора
; =================================================================================
GetCpuName proc uses eax ebx ecx edx edi
    lea edi, cpuName
    mov eax, 80000002h      ; CPUID з кодом 80000002h повертає перші 16 символів назви процесора
    cpuid                   ; запитуємо назву процесора, вона повертається у 4 регістрах
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

; назва відеокарти через WinAPI
; =================================================================================
GetGpuName proc
    mov dispDev.cb, sizeof DISPLAY_DEVICEA 
    invoke EnumDisplayDevicesA, 0, 0, addr dispDev, 0
    ret
GetGpuName endp

; швидкость інтернету
; =================================================================================
GetNetworkTraffic proc uses ebx ecx edx esi edi
    mov ifTableSize, 100000
    invoke GetIfTable, addr ifTableBuffer, addr ifTableSize, 0 ; таблиця мережевих адаптерів
    cmp eax, 0                          
    jne error_exit
    
    mov ecx, dword ptr [ifTableBuffer]  
    lea esi, [ifTableBuffer + 4]        
    mov sumRx, 0
    mov sumTx, 0
    test ecx, ecx
    jz done_sum

sum_loop:
    ; перевіряємо чи працює адаптер (потрібен статус = 5) і чи це Ethernet чи Wi-Fi
    mov eax, [esi + MIB_IFROW.dwOperStatus]
    cmp eax, 5
    jne next_adapter
    mov eax, [esi + MIB_IFROW.dwType]
    cmp eax, 6                          
    je add_bytes
    cmp eax, 71                         
    je add_bytes
    jmp next_adapter                    

add_bytes:
    ; сумуємо байти для скачування та віддачі
    mov eax, [esi + MIB_IFROW.dwInOctets]
    add sumRx, eax                        
    mov eax, [esi + MIB_IFROW.dwOutOctets]
    add sumTx, eax                        

next_adapter:
    add esi, sizeof MIB_IFROW
    dec ecx
    jnz sum_loop

done_sum:
    ; вираховуємо скільки байт прийшло за 1 секунду
    mov eax, sumRx                       
    mov ebx, prevNetRx
    mov prevNetRx, eax              
    test ebx, ebx
    jz calc_tx                     
    sub eax, ebx                       
    shr eax, 10                        ; Ділимо на 1024 щоб отримати кілобайти
    mov netLoadKB, eax
    
calc_tx:
    mov eax, sumTx                       
    mov ebx, prevNetTx
    mov prevNetTx, eax              
    test ebx, ebx
    jz end_func                     
    sub eax, ebx                       
    shr eax, 10                        ; віддача в кілобайтах
    mov netTxLoadKB, eax
    jmp end_func

error_exit:
    mov netLoadKB, 0
    mov netTxLoadKB, 0
end_func:
    ret
GetNetworkTraffic endp

; розрахунок CPU Load у відсотках
; =================================================================================
GetCpuPercentage proc uses ebx ecx edx
    ; Отримуємо час простою та роботи процесора
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
    jz return_zero
    mov eax, currIdle.dwLowDateTime
    sub eax, prevIdle.dwLowDateTime
    mov ebx, eax 
    mov eax, ecx
    sub eax, ebx  
    jns calc_percent 
    xor eax, eax
calc_percent:
    imul eax, eax, 100       ; переводимо у відсотки
    xor edx, edx
    div ecx       
    jmp save_prev
return_zero:
    xor eax, eax
save_prev:
    push eax 
    ; зберігаємо поточний стан для розрахунків у наступній секунді
    mov eax, currIdle.dwLowDateTime
    mov prevIdle.dwLowDateTime, eax
    mov eax, currKernel.dwLowDateTime
    mov prevKernel.dwLowDateTime, eax
    mov eax, currUser.dwLowDateTime
    mov prevUser.dwLowDateTime, eax
    pop eax  
    ret
GetCpuPercentage endp

; формування графіку з текстових символів для консолі
; =================================================================================
UpdateGraphBuffer proc uses eax ebx ecx edx edi esi, percentage:dword, maxValue:dword, pHistory:ptr dword, pBuffer:ptr byte
    cld
    mov esi, pHistory
    mov edi, pHistory
    add esi, 4                
    mov ecx, GRAPH_WIDTH - 1
    rep movsd                 ; зсуваємо старі значення графіку вліво
    mov eax, percentage
    cmp eax, maxValue
    jle cap_done
    mov eax, maxValue    
cap_done:
    ; записуємо нове значення графіку в кінець масиву
    mov edi, pHistory
    mov [edi + (GRAPH_WIDTH - 1) * 4], eax
    mov edi, pBuffer
    mov byte ptr [edi], 0     
    xor ebx, ebx              
build_loop:
    cmp ebx, GRAPH_WIDTH
    jge build_done            
    mov esi, pHistory
    mov eax, [esi + ebx * 4]  
    push eax                  
    mov ecx, 8
    mul ecx
    mov ecx, maxValue
    inc ecx                   
    xor edx, edx              
    div ecx
    pop ecx                   
    test eax, eax             
    jnz skip_fix              
    test ecx, ecx             
    jz skip_fix               
    mov eax, 1
skip_fix:
    mov edx, [blocks + eax * 4]
    invoke strcat, pBuffer, edx ; Додаємо UTF-8 символ у рядок графіку
    inc ebx                   
    jmp build_loop            
build_done:
    ret
UpdateGraphBuffer endp

; Вивід списку запущених процесів
; =================================================================================
PrintProcesses proc uses eax ebx ecx edx
    LOCAL hSnap:dword
    LOCAL pe32:PROCESSENTRY32
    LOCAL procCount:dword
    LOCAL hProcess:dword
    LOCAL pmc:PROCESS_MEMORY_COUNTERS
    LOCAL memMB:dword

    mov procCount, 0
    invoke printf, addr fmtProcHeader
    
    invoke CreateToolhelp32Snapshot, 2, 0
    cmp eax, -1
    je exit_proc
    mov hSnap, eax
    mov pe32.dwSize, sizeof PROCESSENTRY32
    invoke Process32First, hSnap, addr pe32
    test eax, eax
    jz close_snap

print_loop:
    cmp procCount, 10        ; показуємо тільки 10 процесів
    jge close_snap

    ; намагаємося отримати доступ до процесу
    invoke OpenProcess, 0400h, 0, pe32.th32ProcessID
    mov hProcess, eax
    test eax, eax
    jz skip_process
    mov pmc.cb, sizeof PROCESS_MEMORY_COUNTERS
    invoke GetProcessMemoryInfo, hProcess, addr pmc, sizeof PROCESS_MEMORY_COUNTERS
    
    ; байти у мегабайти (зсув вправо на 20 біт = ділення на 1048576)
    mov eax, pmc.WorkingSetSize
    shr eax, 20
    mov memMB, eax
    invoke CloseHandle, hProcess

    mov eax, memMB
    test eax, eax
    jz skip_process

    ; 5. Виводимо на екран тільки тільки доступні процеси
    invoke printf, addr fmtProc, pe32.th32ProcessID, pe32.cntThreads, memMB, addr pe32.szExeFile
    inc procCount

skip_process:
    invoke Process32Next, hSnap, addr pe32
    test eax, eax
    jnz print_loop

close_snap:
    invoke CloseHandle, hSnap

exit_proc:
    ret
PrintProcesses endp


; Точка входу, головна процедура 
; =================================================================================
main proc
    ; UTF-8
    invoke SetConsoleOutputCP, 65001
    invoke GetStdHandle, -11
    mov hOut, eax
    
    mov memStat.dwLength, sizeof MEMORYSTATUSEX
    mov perfInfo.cb, sizeof PERFORMANCE_INFORMATION

    invoke GetSystemInfo, addr sysInfo
    invoke GetCpuName
    invoke GetGpuName

    ; цикл оновлення інформації та графіків кожну секунду
mainLoop:
    ; Повертаємо курсор консолі в лівий верхній кут
    invoke SetConsoleCursorPosition, hOut, 0
    invoke GetLocalTime, addr sTime
    invoke GlobalMemoryStatusEx, addr memStat
    invoke GetPerformanceInfo, addr perfInfo, sizeof PERFORMANCE_INFORMATION
    invoke GetCpuPercentage
    mov cpuLoad, eax  
    invoke GetNetworkTraffic
    
    ; Uptime
    invoke GetTickCount       ; Отримуємо час у мілісекундах
    xor edx, edx
    mov ecx, 1000
    div ecx                   ; Переводимо в секунди
    xor edx, edx
    mov ecx, 60
    div ecx                   
    mov uptimeSec, edx
    xor edx, edx
    mov ecx, 60
    div ecx                   
    mov uptimeMin, edx
    xor edx, edx
    mov ecx, 24
    div ecx                   
    mov uptimeHrs, edx
    mov uptimeDays, eax

    ; Розрахунок оперативної памяті та переводимо байти у Гігабайти
    mov eax, dword ptr [memStat.ullTotalPhys]
    mov edx, dword ptr [memStat.ullTotalPhys + 4]
    shrd eax, edx, 30         ; зсув на 30 біт - 1024^3
    mov totalRamGB, eax
    mov eax, dword ptr [memStat.ullAvailPhys]
    mov edx, dword ptr [memStat.ullAvailPhys + 4]
    shrd eax, edx, 30
    mov ecx, totalRamGB
    sub ecx, eax
    mov usedRamGB, ecx

    ; розрахунок місця на системному диску
    invoke GetDiskFreeSpaceExA, addr driveC, 0, addr totalBytes, addr freeBytes
    mov eax, dword ptr [totalBytes]
    mov edx, dword ptr [totalBytes + 4]
    shrd eax, edx, 30
    mov totalDiskGB, eax
    mov eax, dword ptr [freeBytes]
    mov edx, dword ptr [freeBytes + 4]
    shrd eax, edx, 30
    mov ecx, totalDiskGB
    sub ecx, eax
    mov usedDiskGB, ecx

    ; оновлюємоо графіки
    invoke UpdateGraphBuffer, cpuLoad, 20, addr cpuHistory, addr cpuGraph
    invoke UpdateGraphBuffer, memStat.dwMemoryLoad, 100, addr ramHistory, addr ramGraph
    invoke UpdateGraphBuffer, netLoadKB, 800000, addr netHistory, addr netGraph

    ; виводимо головну інформаційну панель на екран
    movzx eax, sTime.wSec
    movzx ebx, sTime.wMin
    movzx ecx, sTime.wHour
    
    invoke printf, addr fmtData, 
        addr cpuName, 
        addr dispDev.DeviceString,
        ecx, ebx, eax, uptimeDays, uptimeHrs, uptimeMin, uptimeSec, 
        cpuLoad, addr cpuGraph, perfInfo.ProcessCount, perfInfo.ThreadCount, perfInfo.HandleCount, 
        memStat.dwMemoryLoad, addr ramGraph, usedRamGB, totalRamGB, 
        usedDiskGB, totalDiskGB, 
        netLoadKB, addr netGraph, netTxLoadKB

    ; виводимо список процесів під панеллю
    invoke PrintProcesses

    invoke Sleep, 1000        ; пауза на 1 секунду
    jmp mainLoop              ; повертаємось на початок циклу

    invoke ExitProcess, 0
main endp
end main