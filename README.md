# 🕹️ NOR1-5Archi Emulator (N1-5A)

> **"The Silence of Romance in 1-bit Digital!!"**
> (1ビットデジタルに浪漫の静けさ！)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1mj2Lm9Rz1d63R40t_q0mq3KdtIXJ9jBg?usp=sharing)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/sueyoshiryosuke/NOR1-5Archi/blob/main/LICENSE)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)

## 📖 Overview (概要)

**NOR1-5Archi (N1-5A)** は、現代のコンピューターが失った「物理的な手触り」と「思考の静寂」を再構築するプロジェクトです。

NORゲートのみで構成された1ビットの世界で、1Hz（1秒）ごとの論理演算を楽しむためのエミュレータです。

## ✨ Features (特徴)

* **Unique "1-5" Architecture**
    * **Data Width: 1-bit (The Soul)** - データは0か1のみ。究極のシンプルさ。
    * **Instruction Width: 5-bit (The Body)** - 4bitでも8bitでもない、5bit (Op:2bit + Operand:3bit) という制約。
* **The "7-Line" OS (Micro Kernel)**
    * Bank 0には、わずか **7行のマシン語** で記述された極小のOSが搭載されています。
    * 電源投入時の物理的な「不定値（カオス）」を「秩序（Zero）」へと確定させ、ユーザー領域へ制御を渡す、最小にして堅牢なブートローダーです。
* **NOR Logic Only**
    * 加算命令(ADD)すら存在しません。「反転(NOR)」と「条件分岐(JUMP)」だけで全てを計算します。
* **Bank Switching Memory**
    * 3bitのアドレス空間(0-7)を拡張するため、物理的な「バンク（ページ）」を切り替えて動作します。
    * **Bank 0:** System/OS (Read Only / Boot Process)
    * **Bank 1-4:** User Area (Writable)

## 🚀 Quick Start (すぐに試す)

### Option 1: Google Colab (ブラウザのみ)
環境構築不要で、すぐに動作確認ができます。
上の **[Open In Colab]** バッジをクリックしてください。

上の**[Open In Colab]** バッジ、または以下のリンクをクリックしてください。

* [**🕹️ Launch NOR1-5Archi Emulator**](https://colab.research.google.com/drive/1mj2Lm9Rz1d63R40t_q0mq3KdtIXJ9jBg?usp=sharing)

### Option 2: Python (ローカル実行)
ローカル環境（WinPythonなど）で実行する場合は、`Python 3.11以上` と `gradio` ライブラリが必要です。

```bash
# 1. Install Dependency
pip install gradio

# 2. Run Emulator
python n1_5a_emu.py
````

実行するとブラウザが自動的に立ち上がり、エミュレータ画面が表示されます。
（ローカルモード `share=False` で起動します）

## 📂 Files

  * `n1_5a_emu.py`: エミュレータ本体 (Python + Gradio)

-----

## 🏗️ NOR1-5Archi Architecture Specification

| Item | Specification | Note |
| :--- | :--- | :--- |
| **System Name** | **NOR1-5Archi** | Noa-One-Five Architecture |
| **Model** | **N1-5A** | Rev 1.0 |
| **Logic Gate** | **NOR** | Universal Gate |
| **Registers** | **ACC** (1-bit) | Main Accumulator |
| **Memory (ROM)** | **40 Words** | 5 Banks × 8 Lines (5-bit width) |
| **Memory (RAM)** | **1-bit** | Address 7 (Shared with I/O map) |
| **I/O** | 7 Inputs / 2 Outputs | Input: Switch 0-6 / Output: LED 0-1 |

### 1\. Hardware Configuration (ハードウェア構成)

| Component | Specification | Address / Range | Note |
| :--- | :--- | :--- | :--- |
| **ROM** | 40 Words | 5 Banks × 8 Lines | Bank 0 (OS) + Bank 1-4 (User) |
| **Input** | 7 channels | Input 0 - Input 6 | Physical Switches |
| **RAM** | 1 bit | Address 7 | Shared address space |
| **Output** | 2 channels | OUT 0 / OUT 1 | LED Indicators |
| **ACC** | 1 bit | - | Accumulator (Main Register) |
| **PC** | 3 bit | 0 - 7 | Program Counter (within Bank) |

### 2\. Instruction Format (命令フォーマット)

Total: **5 bits**

```text
[ Bit 4 | Bit 3 ]   [ Bit 2 | Bit 1 | Bit 0 ]
    Opcode (2)           Operand (3)
```

### 3\. Instruction Set (命令セット)

| Op | Mnemonic | Operand (3bit) | Description | Python Logic Equivalent |
| :--- | :--- | :--- | :--- | :--- |
| **00** | `LOAD` | `addr` | **読込**: 指定アドレスの値をACCにロードする。 | `ACC = Input[addr] if addr < 7 else RAM` |
| **01** | `NOR` | *(ignored)* | **反転**: ACCの値を反転させる。(NOT) | `ACC = 1 if ACC == 0 else 0` |
| **10** | `STORE` | `addr` | **書込/制御**: 出力、RAM保存、またはバンク切替。 | (See Operand Map below) |
| **11** | `JUMP` | `line` | **分岐**: ACCが **0** の時、指定行へジャンプ。 | `if ACC == 0: PC = line - 1` |

> **Note:** `NOR` 命令は実装上 `NOR(ACC, 0)` と等価であり、実質的に `NOT ACC` として機能します。

### 4\. Operand Map (オペランドマップ)

オペランド（3bit: 0\~7）は、命令コードによって意味が変化します。

#### A. `LOAD` (Op: 00)

| Value | Target | Note |
| :--- | :--- | :--- |
| **0-6** | Input 0 \~ Input 6 | 物理スイッチからの入力 |
| **7** | RAM | 1bitメモリの値を読み出し |

#### B. `STORE` (Op: 10)

この命令は「出力」「RAM保存」「バンク切り替え」の3つの機能を持ちます。

| Value | Target | Description |
| :--- | :--- | :--- |
| **0** | **OUT 0** | 出力ポート0 (Main LED) |
| **1** | **OUT 1** | 出力ポート1 (Sub LED) |
| **2** | **BANK 0** | **[Switch]** Bank 0 (System/OS) へ切替 |
| **3** | **BANK 1** | **[Switch]** Bank 1 (User Area 1) へ切替 |
| **4** | **BANK 2** | **[Switch]** Bank 2 (User Area 2) へ切替 |
| **5** | **BANK 3** | **[Switch]** Bank 3 (User Area 3) へ切替 |
| **6** | **BANK 4** | **[Switch]** Bank 4 (User Area 4) へ切替 |
| **7** | **RAM** | ACCの値をRAMに保存 (Work RAM) |

#### C. `JUMP` (Op: 11)

| Value | Target | Condition |
| :--- | :--- | :--- |
| **0-7** | Line 0 \~ 7 | **Jump if ACC == 0** (それ以外は次の行へ) |

### 5\. Memory Map (Bank Structure)

物理的な「ピンボード」を模したページング方式を採用しています。

  * **Bank 0 (System / OS)**
      * Read Only (Software constraint)
      * システムの初期化、リセット処理、安全なバンク遷移を担当。
  * **Bank 1 - 4 (User Application)**
      * Writable / Pluggable
      * ユーザーが自由にプログラムを配置できる領域。
      * 各バンクの末尾で適切に処理を行わない場合、PCはオーバーフローしてBank 0へ強制リセットされる（仕様）。

-----

*Author: SUEYOSHI Ryosuke & Gemini*
