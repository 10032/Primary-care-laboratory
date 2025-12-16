import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, Menu, Spinbox, LabelFrame, Checkbutton, OptionMenu, StringVar, messagebox
from tkinter.filedialog import asksaveasfilename
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import time
import threading

# 依赖检查
try:
    import keyboard
    import pyautogui
except ImportError:
    messagebox.showerror("缺少依赖", "请先安装自动化库：\npip install keyboard pyautogui")
    exit()

class QCGeneratorGUI:
    # Westgard 常量
    TREND_LENGTH_7T = 7
    RUN_LENGTH_10X = 10

    def __init__(self, root):
        self.root = root
        root.title("高级质控数据生成器 (Lab QC Tool) - Golden Master")
        
        # 线程控制事件
        self.stop_event = threading.Event()
        self.is_running_automation = False

        # ---- 菜单栏 ----
        menubar = Menu(root)
        root.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出数据为 CSV", command=self.export_data_csv)

        # ---- 参数输入框架 ----
        self.input_frame = LabelFrame(root, text="设定参数 (Method Parameters)")
        self.input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

        # 靶值
        ttk.Label(self.input_frame, text="靶值 (Target):").grid(row=0, column=0, sticky=tk.W)
        self.target_entry = ttk.Entry(self.input_frame)
        self.target_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.target_entry.insert(0, "100")

        # 设定 CV
        ttk.Label(self.input_frame, text="设定 CV (%):").grid(row=1, column=0, sticky=tk.W)
        self.cv_entry = ttk.Entry(self.input_frame)
        self.cv_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        self.cv_entry.insert(0, "2.0")

        # Bias
        ttk.Label(self.input_frame, text="初始偏移 (Bias):").grid(row=2, column=0, sticky=tk.W)
        self.bias_entry = ttk.Entry(self.input_frame)
        self.bias_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        self.bias_entry.insert(0, "0")

        # Drift
        ttk.Label(self.input_frame, text="每日漂移 (Drift):").grid(row=3, column=0, sticky=tk.W)
        self.drift_var = tk.DoubleVar(value=0.0)
        self.drift_spinbox = Spinbox(self.input_frame, textvariable=self.drift_var, from_=-2.0, to=2.0, increment=0.1, width=5)
        self.drift_spinbox.grid(row=3, column=1, sticky=tk.W)

        # 分布类型
        ttk.Label(self.input_frame, text="误差分布模型:").grid(row=4, column=0, sticky=tk.W)
        self.distribution_var = StringVar(value="Normal")
        OptionMenu(self.input_frame, self.distribution_var, "Normal", "Log-Normal").grid(row=4, column=1, sticky=(tk.W, tk.E))

        # 绘图开关
        self.plot_var = tk.BooleanVar(value=True) 
        Checkbutton(self.input_frame, text="显示 Levey-Jennings 图", variable=self.plot_var).grid(row=5, column=0, columnspan=2, sticky=tk.W)

        # 生成按钮
        ttk.Button(self.input_frame, text="生成并分析", command=self.generate_and_display_qc).grid(row=6, column=0, columnspan=2, pady=10)

        # ---- Westgard 规则开关 ----
        self.rules_frame = LabelFrame(root, text="Westgard 规则开关")
        self.rules_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        self.rule_vars = {}
        # 完整的规则列表
        rules = ["1-3s", "2-2s", "R-4s", "3-1s", "4-1s", "7-t", "10x"]
        for i, rule in enumerate(rules):
            self.rule_vars[rule] = tk.BooleanVar(value=True)
            Checkbutton(self.rules_frame, text=rule, variable=self.rule_vars[rule]).grid(row=i, column=0, sticky=tk.W)

        # ---- 图表区域 ----
        self.lj_chart_frame = LabelFrame(root, text="Levey-Jennings Chart (Based on Method SD)")
        self.lj_chart_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        self.fig_lj, self.ax_lj = plt.subplots(figsize=(6, 4)) 
        self.canvas_lj = FigureCanvasTkAgg(self.fig_lj, master=self.lj_chart_frame)
        self.canvas_lj.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # ---- 结果区域 ----
        self.result_frame = ttk.Frame(root, padding=10)
        self.result_frame.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # 布局辅助函数
        def create_scroll_area(parent, title, col, width=30):
            ttk.Label(parent, text=title).grid(row=0, column=col, sticky=tk.W)
            area = scrolledtext.ScrolledText(parent, height=10, width=width)
            area.grid(row=1, column=col, sticky="nsew", padx=5)
            return area

        self.qc_data_text = create_scroll_area(self.result_frame, "生成数据:", 0, 25)
        self.rules_result_text = create_scroll_area(self.result_frame, "规则判定:", 1, 35)
        self.stats_text = create_scroll_area(self.result_frame, "统计摘要 (Observed):", 2, 30)

        # ---- 自动化录入 ----
        self.hotkey_frame = LabelFrame(root, text="LIS 自动化录入 (Threaded)")
        self.hotkey_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        ttk.Label(self.hotkey_frame, text="热键:").grid(row=0, column=0)
        self.hotkey_entry = ttk.Entry(self.hotkey_frame, width=15)
        self.hotkey_entry.grid(row=0, column=1)
        self.hotkey_entry.insert(0, "ctrl+alt+q")

        self.start_btn = ttk.Button(self.hotkey_frame, text="启动监听", command=self.start_listening)
        self.start_btn.grid(row=0, column=2, padx=5)
        
        self.stop_btn = ttk.Button(self.hotkey_frame, text="停止监听", command=self.stop_listening, state="disabled")
        self.stop_btn.grid(row=0, column=3, padx=5)

        self.status_label = ttk.Label(self.hotkey_frame, text="就绪 - 按 ESC 可紧急中断录入", foreground="gray")
        self.status_label.grid(row=1, column=0, columnspan=4, sticky=tk.W)

    # ---- 核心逻辑 ----

    def generate_qc_data(self, target, cv, num_days=31, bias=0, drift=0, dist_type="Normal"):
        method_sd = target * cv 
        data = []
        current_mean = target + bias
        
        if dist_type == "Log-Normal" and cv > 0.05:
            messagebox.showwarning("统计预警", "Log-Normal 分布下设定 CV > 5% 极易导致 10x/Trend 规则假阳性，请知悉。")

        for _ in range(num_days):
            if dist_type == "Normal":
                val = np.random.normal(loc=current_mean, scale=method_sd)
            elif dist_type == "Log-Normal":
                sigma_log = np.sqrt(np.log(1 + (method_sd / current_mean)**2))
                mu_log = np.log(current_mean) - 0.5 * sigma_log**2
                val = np.random.lognormal(mean=mu_log, sigma=sigma_log)
            else:
                val = current_mean
            
            data.append(val)
            current_mean += drift 
            
        return np.array(data)

    # ---- Westgard 规则逻辑 (完整补全) ----

    def check_n_s(self, data, target, method_sd, n, s_limit):
        """通用检查: 连续 n 个点超过 s_limit * SD (同侧)"""
        if len(data) < n: return False
        for i in range(len(data) - n + 1):
            segment = data[i : i+n]
            # 检查绝对值是否都超限
            if np.all(np.abs(segment - target) > s_limit * method_sd):
                # 检查是否同侧 (全部大于 Target 或 全部小于 Target)
                if np.all(segment > target) or np.all(segment < target):
                    return True
        return False

    def check_7_t(self, data):
        """使用差分判断单调性"""
        if len(data) < self.TREND_LENGTH_7T: return False
        diffs = np.diff(data)
        for i in range(len(diffs) - self.TREND_LENGTH_7T + 2):
            window = diffs[i : i + self.TREND_LENGTH_7T - 1]
            if np.all(window > 0) or np.all(window < 0):
                return True
        return False

    def apply_westgard_rules(self, data, target, method_sd):
        violations = {}
        
        # 1. 1-3s (单点 > 3SD)
        if self.rule_vars["1-3s"].get():
            violations["1-3s"] = any(abs(x - target) > 3 * method_sd for x in data)
        else:
            violations["1-3s"] = False

        # 2. 2-2s (连续2点 > 2SD 同侧)
        if self.rule_vars["2-2s"].get():
            violations["2-2s"] = self.check_n_s(data, target, method_sd, n=2, s_limit=2)
        else:
            violations["2-2s"] = False
                
        # 3. R-4s (连续两点极差 > 4SD)
        if self.rule_vars["R-4s"].get():
            violations["R-4s"] = False
            for i in range(len(data)-1):
                if abs(data[i] - data[i+1]) > 4 * method_sd:
                     violations["R-4s"] = True; break
        else:
            violations["R-4s"] = False

        # 4. 10x (连续10点在均值一侧)
        if self.rule_vars["10x"].get():
            violations["10x"] = False
            if len(data) >= self.RUN_LENGTH_10X:
                for i in range(len(data) - self.RUN_LENGTH_10X + 1):
                    segment = data[i : i + self.RUN_LENGTH_10X]
                    if np.all(segment > target) or np.all(segment < target):
                        violations["10x"] = True; break
        else:
            violations["10x"] = False

        # 5. 7-t (连续7点趋势)
        if self.rule_vars["7-t"].get():
            violations["7-t"] = self.check_7_t(data)
        else:
            violations["7-t"] = False
            
        # 6. 3-1s (连续3点 > 1SD 同侧) - 补全
        if self.rule_vars["3-1s"].get():
            violations["3-1s"] = self.check_n_s(data, target, method_sd, n=3, s_limit=1)
        else:
            violations["3-1s"] = False
            
        # 7. 4-1s (连续4点 > 1SD 同侧) - 补全
        if self.rule_vars["4-1s"].get():
            violations["4-1s"] = self.check_n_s(data, target, method_sd, n=4, s_limit=1)
        else:
            violations["4-1s"] = False

        return violations

    # ---- 界面交互 ----

    def generate_and_display_qc(self):
        try:
            target = float(self.target_entry.get())
            method_cv = float(self.cv_entry.get()) / 100.0
            bias = float(self.bias_entry.get())
            drift = float(self.drift_var.get())
            dist = self.distribution_var.get()

            # 生成数据
            qc_data = self.generate_qc_data(target, method_cv, bias=bias, drift=drift, dist_type=dist)
            method_sd = target * method_cv 
            
            self.update_ui_components(qc_data, target, method_sd, method_cv)

        except ValueError:
            messagebox.showerror("输入错误", "请检查数值格式")

    def update_ui_components(self, data, target, method_sd, method_cv):
        obs_mean = np.mean(data)
        obs_sd = np.std(data, ddof=1)
        obs_cv = (obs_sd / obs_mean) if obs_mean != 0 else 0

        # 填充数据区
        self.qc_data_text.delete(1.0, tk.END)
        for i, v in enumerate(data):
            self.qc_data_text.insert(tk.END, f"D{i+1}: {v:.2f}\n")

        # 统计摘要
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, "--- 设定参数 (Method) ---\n")
        self.stats_text.insert(tk.END, f"Target: {target}\n")
        self.stats_text.insert(tk.END, f"Set CV: {method_cv*100:.2f}%\n")
        self.stats_text.insert(tk.END, f"Set SD: {method_sd:.3f}\n\n")
        self.stats_text.insert(tk.END, "--- 实测统计 (Observed) ---\n")
        self.stats_text.insert(tk.END, f"Mean: {obs_mean:.2f}\n")
        self.stats_text.insert(tk.END, f"SD  : {obs_sd:.3f}\n")
        self.stats_text.insert(tk.END, f"CV  : {obs_cv*100:.2f}%\n")

        # 规则判断
        results = self.apply_westgard_rules(data, target, method_sd)
        self.rules_result_text.delete(1.0, tk.END)
        for r, v in results.items():
            # 这里也再判断一次，虽然计算时已过滤，但为了展示整洁
            if self.rule_vars.get(r) and self.rule_vars[r].get(): 
                mark = "❌ FAIL" if v else "✅ PASS"
                self.rules_result_text.insert(tk.END, f"{r}: {mark}\n")

        # 绘图
        if self.plot_var.get():
            self.plot_lj(data, target, method_sd)
        else:
            self.ax_lj.clear(); self.canvas_lj.draw()

    def plot_lj(self, data, target, method_sd):
        self.ax_lj.clear()
        # 修正：动态 X 轴范围
        x_axis = range(1, len(data) + 1)
        self.ax_lj.plot(x_axis, data, 'o-', color='navy', markersize=4, label='Observed Data')
        
        # 绘制质控限
        lines = [
            (target, 'green', 2, 'Target'),
            (target + 2*method_sd, 'orange', 1, '+2SD'),
            (target - 2*method_sd, 'orange', 1, '-2SD'),
            (target + 3*method_sd, 'red', 1, '+3SD'),
            (target - 3*method_sd, 'red', 1, '-3SD')
        ]
        
        for y, color, lw, lbl in lines:
            self.ax_lj.axhline(y, color=color, linestyle='--' if color != 'green' else '-', linewidth=lw, label=lbl)

        self.ax_lj.set_title("Levey-Jennings Chart (Limits based on Target SD)")
        self.ax_lj.legend(fontsize='x-small', loc='upper left', bbox_to_anchor=(1, 1))
        self.ax_lj.grid(True, alpha=0.3)
        self.fig_lj.tight_layout()
        self.canvas_lj.draw()

    # ---- 自动化录入 (Threaded) ----

    def start_listening(self):
        hotkey = self.hotkey_entry.get()
        try:
            keyboard.add_hotkey(hotkey, self.on_hotkey_triggered)
            self.status_label.config(text=f"监听中 ({hotkey})... 触发后自动录入", foreground="green")
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def stop_listening(self):
        keyboard.unhook_all_hotkeys()
        self.stop_event.set() 
        self.status_label.config(text="监听已停止", foreground="gray")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def on_hotkey_triggered(self):
        if self.is_running_automation: return
        try:
            tgt = float(self.target_entry.get())
            cv = float(self.cv_entry.get())/100
            bias = float(self.bias_entry.get())
            drift = float(self.drift_var.get())
            dist = self.distribution_var.get()
            
            data = self.generate_qc_data(tgt, cv, bias=bias, drift=drift, dist_type=dist)
            method_sd = tgt * cv
            
            self.root.after(0, lambda: self.update_ui_components(data, tgt, method_sd, cv))
            
            t = threading.Thread(target=self.run_typing_task, args=(data,))
            t.daemon = True 
            t.start()
            
        except Exception as e:
            print(f"Error: {e}")

    def run_typing_task(self, data):
        self.is_running_automation = True
        self.stop_event.clear()
        
        print("开始录入...")
        for val in data:
            if self.stop_event.is_set(): break
            if keyboard.is_pressed('esc'): 
                print("ESC 中断")
                break
                
            pyautogui.write(f"{val:.2f}")
            time.sleep(0.05)
            pyautogui.press('enter')
            
            for _ in range(2): 
                if keyboard.is_pressed('esc'): break
                time.sleep(0.05)
                
        self.is_running_automation = False
        print("录入结束")

    def export_data_csv(self):
        """修复：恢复CSV导出功能，从界面文本中提取数据"""
        try:
            # 简单方式：解析 Text Widget (因为数据已经生成并在那里了)
            raw_text = self.qc_data_text.get("1.0", tk.END)
            lines = raw_text.split('\n')
            data_to_save = []
            for line in lines:
                if ":" in line and "D" in line:
                    try:
                        # 格式: D1: 100.23 -> split(':') -> [1].strip()
                        val = float(line.split(':')[1].strip())
                        data_to_save.append(val)
                    except: continue
            
            if not data_to_save:
                messagebox.showerror("错误", "没有可导出的数据，请先生成。")
                return

            filename = asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if filename:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Day", "Value"])
                    for i, val in enumerate(data_to_save):
                        writer.writerow([i+1, val])
                messagebox.showinfo("成功", "数据已导出")
        except Exception as e:
            messagebox.showerror("导出错误", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = QCGeneratorGUI(root)
    root.mainloop()