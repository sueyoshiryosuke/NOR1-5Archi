# NOR1-5Archi Emulator for WinPython
"""
============================================================
SYSTEM:  NOR1-5Archi (Noa-One-Five Architecture)
MODEL:   N1-5A
DATE:    2025-12-14
AUTHOR:  SUEYOSHI Ryosuke & Gemini
ENV:     Python 3.11+ / Gradio
------------------------------------------------------------
SPECIFICATIONS:
    - Data Width:        1-bit (The Soul)
    - Instruction Width: 5-bit (The Body)
    - Architecture:      Harvard (Separate ROM/RAM)
    - Logic Gate:        NOR Only
    - Addressing:        Bank Switching (3-bit Operand x 5 Banks)
============================================================
"""
import gradio as gr
import time
import re
import os


# 動作クロック数（●Hz駆動）
NUMBER_OF_CLOCKS = 1

# --- ハードウェア定義 ---
class NOR1_5A_Core:
    def __init__(self):
        self.num_banks = 5
        self.lines_per_bank = 8
        self.banks = [[0] * self.lines_per_bank for _ in range(self.num_banks)]

        # 物理状態
        self.inputs = [0] * 7  # Input 0~6
        self.ram = 0           # Address 7
        self.outputs = [0, 0]  # Output 0(OUT0), 1(OUT1)

        # CPUレジスタ
        self.current_bank = 0
        self.pc = 0
        self.acc = 0

        # ログ管理
        self.display_logs = []  # UI表示用（直近のみ）
        self.full_history = []  # ファイル保存用（全履歴）
        self.system_on = False

    def reset(self):
        self.ram = 0
        self.outputs = [0, 0]
        self.current_bank = 0
        self.pc = 0
        self.acc = 0
        # 電源ONの時はログをクリア
        self.display_logs = ["--- SYSTEM READY (POWER OFF) ---"]
        self.full_history = ["--- SYSTEM READY (POWER OFF) ---"]
        self.system_on = False

    def load_program(self, text):
        # メモリクリア
        self.banks = [[0] * self.lines_per_bank for _ in range(self.num_banks)]

        # 行ごとの解析: #12: 11_011 のような形式
        # Regex: #(Bank)(Line): (Binary)
        pattern = re.compile(r'#(\d)(\d):\s*([01_]+)')

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue

            match = pattern.search(line)
            if match:
                b_idx = int(match.group(1))
                l_idx = int(match.group(2))
                bin_str = match.group(3).replace('_', '')

                if 0 <= b_idx < self.num_banks and 0 <= l_idx < self.lines_per_bank:
                    try:
                        val = int(bin_str, 2)
                        self.banks[b_idx][l_idx] = val
                    except ValueError:
                        # コードのエラー内容を出力する。
                        print(f"ERROR: Invalid binary format in Bank{b_idx} L{l_idx}: '{bin_str}'")
                        #pass # パースエラーは無視

    def set_input(self, index, value):
        if 0 <= index < 7:
            self.inputs[index] = 1 if value else 0

    def fetch(self):
        cmd = self.banks[self.current_bank][self.pc]
        return (cmd >> 3) & 0b11, cmd & 0b111

    def execute_step(self, step_count):
        if not self.system_on:
            return "POWER OFF"

        # 実行前のPCを確実に保存
        exec_pc = self.pc

        opcode, operand = self.fetch()
        log_entry = ""

        # LOAD (00)
        if opcode == 0b00:
            if operand == 7:
                self.acc = self.ram
                src = "RAM"
            else:
                self.acc = self.inputs[operand] if operand < 7 else 0
                src = f"IN_{operand}"
            log_entry = f"LOAD {src} -> ACC:{self.acc}"

        # NOR (01)
        elif opcode == 0b01:
            prev = self.acc
            self.acc = 1 if not(self.acc) else 0 # NOR(ACC, 0) -> NOT ACC
            log_entry = f"NOR  (NOT {prev}) -> ACC:{self.acc}"

        # STORE (10)
        elif opcode == 0b10:
            if operand == 0:   # Output 0
                self.outputs[0] = self.acc
                log_entry = f"STORE OUT0 -> {self.acc}{'💡' if self.acc else '⚫'}"
            elif operand == 1: # Output 1
                self.outputs[1] = self.acc
                log_entry = f"STORE OUT1 -> {self.acc}{'💡' if self.acc else '⚫'}"
            elif operand == 7: # RAM
                self.ram = self.acc
                log_entry = f"STORE RAM <- {self.acc}"
            elif 2 <= operand <= 6: # Bank Switch (2->B0 ... 6->B4)
                target_bank = operand - 2
                self.current_bank = target_bank
                self.pc = -1  # 次のループで+1されて0になる
                log_entry = f"STORE BANK -> Switch to Bank {target_bank}"
            else:
                log_entry = f"STORE (NOP) op:{operand}"

        # JUMP (11)
        elif opcode == 0b11:
            if self.acc == 0:
                target_line = operand
                self.pc = target_line - 1 # 次のループで+1されてtargetになる
                log_entry = f"JUMP to #{self.current_bank}{target_line} (ACC=0)"
            else:
                log_entry = f"JUMP Skip (ACC=1)"

        # PC更新
        self.pc = (self.pc + 1) % 8

        # ログ生成
        full_log = f"[Tick {step_count:05}] B{self.current_bank} L{exec_pc}: {log_entry}"
        # 1. 画面表示用（最新20件だけ保持して軽くする）
        self.display_logs.insert(0, full_log)
        if len(self.display_logs) > 20:
            self.display_logs.pop()

        # 2. 保存用（すべて保持）
        self.full_history.append(full_log)

        return full_log

    def save_log_to_file(self):
        filename = "n1-5a_log.txt"
        with open(filename, "a", encoding="utf-8") as f:
            f.write("\n".join(self.full_history))
            f.write("\n")
        return filename


# グローバルインスタンス
cpu = NOR1_5A_Core()

# --- Gradio UI ロジック ---

def toggle_power(is_on, code_text):
    if is_on:
        cpu.reset()
        cpu.load_program(code_text)
        cpu.system_on = True
        return "System Booting...", gr.update(interactive=False) # コード編集ロック
    else:
        cpu.system_on = False
        return "System Shutdown.", gr.update(interactive=True)

def update_switches(i0, i1, i2, i3, i4, i5, i6):
    # 実行中でもリアルタイムに入力を更新
    vals = [i0, i1, i2, i3, i4, i5, i6]
    for idx, v in enumerate(vals):
        cpu.set_input(idx, v)

def export_logs():
    # ログファイルを作成してパスを返す
    path = cpu.save_log_to_file()
    return path

def simulation_loop(is_on):
    try:
        step = 0
        while True:
            # 電源OFF時、ログを「空文字」で上書きせず、現在のログを返す。
            if not cpu.system_on:
                # 停止時は現状維持
                log_text = "\n".join(cpu.display_logs)
                yield "POWER OFF", log_text
                break

            # 1ステップ実行
            latest_log = cpu.execute_step(step)
            step += 1

            # アイコンで分かりやすく状態表示
            out0_icon = "💡" if cpu.outputs[0] else "⚫"
            out1_icon = "💡" if cpu.outputs[1] else "⚫"

            # 表示用テキスト作成
            # 現在の状態
            status_text = f"""
            ⚡ POWER: ON  | ⏱ Tick: {step}
            -------------------------------
            🏛 Bank: {cpu.current_bank}
            📍 PC   : {cpu.pc}
            🧮 ACC  : {cpu.acc}
            💾 RAM  : {cpu.ram}
            {out0_icon} OUT 0: {cpu.outputs[0]}
            {out1_icon} OUT 1: {cpu.outputs[1]}
            """

            # ログ結合
            log_text = "\n".join(cpu.display_logs)

            yield status_text, log_text

            # 動作クロック調整
            time.sleep(1/NUMBER_OF_CLOCKS)

    except Exception as e:
        print(f"Error in loop: {e}")
        yield f"ERROR: {e}", str(e)

# --- UI構築 ---
# 各バンクの最後は「失敗したらBank0へ戻る」処理(L7)
default_code_bin = """#00: 00_000 ; LOAD IN0 (ブートガード)
#01: 11_011 ; JUMP 3
#02: 01_000 ; NOR
#03: 10_000 ; STORE OUT0 (初期化)
#04: 10_001 ; STORE OUT1 (初期化)
#05: 10_111 ; STORE RAM (初期化)
#06: 10_011 ; STORE BANK1
#07: 00_000 ; NOP

#10: 00_000  ; LOAD IN0 (正解1)
#11: 11_111  ; JUMP_IF_0 7 (失敗ならL7へ)
#12: 00_001  ; LOAD IN1 (正解0)
#13: 11_110  ; JUMP_IF_0 6 (成功ならL6へ)
#14: 01_000  ; NOR (1を0に反転)
#15: 11_000  ; JUMP_IF_0 7 (0になったのでリセットへ)
#16: 10_100  ; Switch to Bank 2 (Op=4)
#17: 10_010  ; Switch to Bank 0 (Reset)

#20: 00_010  ; LOAD IN2 (正解1)
#21: 11_111  ; JUMP_IF_0 7 (失敗ならリセット)
#22: 00_011  ; LOAD IN3 (正解1)
#23: 11_111  ; JUMP_IF_0 7 (失敗ならリセット)
#24: 10_101  ; Switch to Bank 3 (Op=5)
#25: 00_000
#26: 00_000
#27: 10_010  ; Switch to Bank 0 (Reset)

#30: 10_000  ; OUT0 ON
#31: 10_001  ; OUT1 ON
#32: 00_111  ; Wait (RAM(0)を読み込む)
#33: 10_000  ; OUT0 OFF
#34: 00_111  ; Wait
#35: 10_001  ; OUT1 OFF
#36: 00_111  ; Wait
#37: 10_010  ; Switch to Bank 0 (Reset)
"""

with gr.Blocks(theme=gr.themes.Monochrome()) as demo:
    gr.Markdown("# 🕹️ NOR1-5Archi Emulator")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎛 Control Panel")
            power_btn = gr.Checkbox(label="🔌 POWER SWITCH", value=False)

            # --- Input用のボタン ---
            gr.Markdown("---")
            gr.Markdown("### 🎹 Inputs")
            input_switches = []
            for i in range(7):
                input_switches.append(gr.Checkbox(label=f"Input {i}", value=False))

            # --- ログダウンロードボタン ---
            gr.Markdown("---")
            with gr.Row():
                download_btn = gr.Button("💾 Save Log to File")
                file_output = gr.File(label="Download Log")

        # --- 変数などの確認モニター ---
        with gr.Column(scale=2):
            gr.Markdown("### 📺 Monitor")
            status_box = gr.Textbox(label="System State", lines=10, max_lines=8)
            # Log box は最新のみ表示
            log_box = gr.Textbox(label="Execution Log (Display Latest 20)", lines=10, max_lines=10)

    # --- マシン語の書き換え欄 ---
    with gr.Row():
        code_area = gr.Textbox(label="📜 Program Code (Bank 0-4)", value=default_code_bin, lines=20)

    # --- Event Handling ---

    # 電源ON/OFF時の挙動
    power_btn.change(fn=toggle_power, inputs=[power_btn, code_area], outputs=[status_box, code_area])

    # 電源ONの場合、シミュレーションループをトリガー
    power_btn.change(fn=simulation_loop, inputs=[power_btn], outputs=[status_box, log_box])

    # スイッチ入力はリアルタイムでCPUに反映
    for sw in input_switches:
        sw.change(fn=update_switches, inputs=input_switches, outputs=None)

    # ログ保存ボタンのイベント
    download_btn.click(fn=export_logs, inputs=[], outputs=file_output)

# 起動
demo.queue().launch(
    inbrowser=True,  # 起動時に勝手にブラウザを開いてくれる（便利！）
    share=False,     # Gradioの公開サーバーを使わない（ローカル完結）
    server_name="127.0.0.1" # 自分自身（localhost）からしか繋げない設定
)
