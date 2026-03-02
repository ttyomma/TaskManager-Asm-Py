# Task Manager (ASM Core + Python GUI)

[![Language: Assembly](https://img.shields.io/badge/Language-Assembly-blue.svg)](https://en.wikipedia.org/wiki/Assembly_language)
[![Language: Python](https://img.shields.io/badge/Language-Python-yellow.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

A dual-version system monitoring tool designed to demonstrate low-level system interaction and cross-language integration. Developed as a coursework project, it features a core written in **x86 Assembly** and a interface built with **Python**.

> 🇺🇦 **[Українська версія нижче](#диспетчер-завдань-ядро-asm--python-gui)**

## 🔹 About the Project
This project explores the principles of operating system task management and hardware interaction. It provides real-time data about system processes, RAM usage, and disk space.

**Key Features:**
* **Console Version:** Pure x86 Assembly (MASM) application with a minimal memory footprint.
* **GUI Version:** Modern interface using `customtkinter`.
* **Hybrid Logic:** The Python UI offloads heavy system calls and memory management to a custom-built **Assembly DLL**.

## 🔹 Technical Architecture
The project demonstrates interoperability between different abstraction levels:
1. **Backend (ASM):** Written in x86 Assembly using Windows API (`Kernel32.lib`).
2. **Bridge (DLL):** The Assembly code is compiled as a Dynamic Link Library (DLL) for external consumption.
3. **Frontend (Python):** Uses `ctypes` to interface with the 32-bit Assembly DLL and map data to a responsive UI.

## 🚀 Releases & Downloads
**Don't have an Assembly compiler?** You can download the pre-compiled executable versions directly:

👉 **[Download Latest Release (v1.0.0)](https://github.com/ttyomma/TaskManager-Asm-Py/releases/tag/v1.0.0)**
*(Includes both the Standalone Console EXE and the GUI Application).*

## 🛠️ Installation & Build from Source
**Prerequisites:**
* Python 3.14 (32-bit is required for DLL compatibility)
* Visual Studio (with MASM build customizations enabled)

**Steps:**
1. Clone the repository: `git clone https://github.com/ttyomma/TaskManager-Asm-Py.git`
2. Install Python dependencies: `pip install -r requirements.txt`
3. Open `.sln` in Visual Studio and build the Assembly projects in **Release/x86** mode.

---

# Диспетчер завдань (Ядро ASM + Python GUI)

Курсовий проект: двоверсійний інструмент для моніторингу системи, створений для демонстрації низькорівневої взаємодії з ОС та міжмовної інтеграції. Має ядро на **x86 Асемблері** та інтерфейс на **Python**.

## 🔹 Про проект
Проект досліджує принципи управління завданнями операційної системи. Він надає дані в реальному часі про системні процеси, використання оперативної пам'яті та дискового простору.

**Основні можливості:**
* **Консольна версія:** Додаток на чистому x86 Асемблері (MASM) з мінімальним споживанням ресурсів.
* **GUI версія:** Інтерфейс з використанням `customtkinter`.
* **Гібридна логіка:** Python-інтерфейс делегує важкі системні виклики та роботу з пам'яттю спеціально написаній **DLL-бібліотеці на Асемблері**.

## 🔹 Архітектура
Проект демонструє взаємодію між різними рівнями абстракції:
1. **Бекенд (ASM):** Написаний на x86 Асемблері з використанням Windows API.
2. **Міст (DLL):** Асемблерний код скомпільований як динамічна бібліотека (DLL).
3. **Фронтенд (Python):** Використовує модуль `ctypes` для зв'язку з 32-бітною DLL та виведення даних у UI.

## 🚀 Релізи та Завантаження
👉 **[Завантажити останній реліз (v1.0.0)](https://github.com/ttyomma/TaskManager-Asm-Py/releases/tag/v1.0.0)**
*(Архів включає як консольний EXE, так і GUI-додаток).*

## 🛠️ Встановлення та збірка з вихідного коду
**Вимоги:**
* Python 3.13+ (Обов'язково 32-бітна версія для сумісності з DLL)
* Visual Studio (з увімкненою підтримкою MASM)

**Кроки:**
1. Клонувати репозиторій: `git clone https://github.com/ttyomma/TaskManager-Asm-Py.git`
2. Встановити залежності: `pip install -r requirements.txt`
3. Відкрити `.sln` у Visual Studio та зібрати проекти в режимі **Release/x86**.
