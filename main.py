import numpy as np
import pyautogui
import keyboard
import tkinter as tk
from tkinter import messagebox
from scipy.stats import truncnorm


def generate_data(target_value, acceptable_range, intra_precision, num_values, max_attempts=100):
    """
    根据给定参数生成符合截断正态分布的随机数据。
    """
    mu = target_value
    sigma = target_value * (intra_precision / 100)
    lower = target_value * (1 - acceptable_range / 100)
    upper = target_value * (1 + acceptable_range / 100)
    
    for _ in range(max_attempts):
        a = (lower - mu) / sigma
        b = (upper - mu) / sigma
        data = truncnorm.rvs(a, b, loc=mu, scale=sigma, size=1000 * num_values)
        data = data[(data >= lower) & (data <= upper)]
        if len(data) >= num_values:
            sample = data[:num_values]
            if np.std(sample, ddof=1) <= sigma:
                return sample
    raise ValueError("无法生成满足条件的数据，请检查参数设置。")


def validate_inputs(target_value, acceptable_range, intra_precision, num_values):
    """
    验证用户输入是否合法。
    """
    if target_value <= 0:
        raise ValueError("靶值必须为正数！")
    if acceptable_range <= 0 or intra_precision <= 0:
        raise ValueError("可接受范围和室内不精密度必须为正数！")
    if intra_precision >= acceptable_range:
        raise ValueError("室内不精密度必须小于可接受范围！")
    if num_values <= 0:
        raise ValueError("数据点数量必须为正整数！")


def generate_and_output():
    """
    生成数据并输出到当前焦点处。
    """
    try:
        target_value = float(target_entry.get())
        acceptable_range = float(acceptable_range_entry.get())
        intra_precision = float(intra_precision_entry.get())
        num_values = int(num_values_entry.get())
        validate_inputs(target_value, acceptable_range, intra_precision, num_values)
        data = generate_data(target_value, acceptable_range, intra_precision, num_values)
        for value in data:
            pyautogui.write(f"{value:.2f}\n")
    except ValueError as e:
        messagebox.showerror("错误", str(e))


def start_listening():
    """
    启动热键监听。
    """
    start_hotkey = hotkey_entry.get().strip()
    if not start_hotkey:
        messagebox.showerror("错误", "请设置一个有效的快捷键！")
        return
    
    try:
        keyboard.add_hotkey(start_hotkey, generate_and_output)
        start_button["state"] = "disabled"
        stop_button["state"] = "normal"
        status_label.config(text=f"监听快捷键: {start_hotkey}")
    except ValueError:
        messagebox.showerror("错误", "无效的快捷键组合！")


def stop_listening():
    """
    停止热键监听。
    """
    start_hotkey = hotkey_entry.get().strip()
    if start_hotkey:
        keyboard.remove_hotkey(start_hotkey)
    start_button["state"] = "normal"
    stop_button["state"] = "disabled"
    status_label.config(text="未监听快捷键")


# GUI 初始化
root = tk.Tk()
root.title("质控数据生成软件")

# GUI 控件
tk.Label(root, text="靶值:").grid(row=0, column=0)
target_entry = tk.Entry(root)
target_entry.grid(row=0, column=1)

tk.Label(root, text="可接受范围（±%）:").grid(row=1, column=0)
acceptable_range_entry = tk.Entry(root)
acceptable_range_entry.grid(row=1, column=1)

tk.Label(root, text="室内不精密度（<%）:").grid(row=2, column=0)
intra_precision_entry = tk.Entry(root)
intra_precision_entry.grid(row=2, column=1)

tk.Label(root, text="数据点数量:").grid(row=3, column=0)
num_values_entry = tk.Entry(root)
num_values_entry.grid(row=3, column=1)

tk.Label(root, text="设置快捷键:").grid(row=4, column=0)
hotkey_entry = tk.Entry(root)
hotkey_entry.grid(row=4, column=1)

start_button = tk.Button(root, text="开始监听", command=start_listening)
start_button.grid(row=5, column=0)

stop_button = tk.Button(root, text="停止监听", command=stop_listening, state="disabled")
stop_button.grid(row=5, column=1)

status_label = tk.Label(root, text="未监听快捷键")
status_label.grid(row=6, column=0, columnspan=2)

# 启动 GUI
root.mainloop()
