import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, Menu, Spinbox, LabelFrame, Checkbutton, OptionMenu, StringVar, DoubleVar, messagebox
from tkinter.filedialog import asksaveasfilename
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
import keyboard  # 导入 keyboard 库
import pyautogui # 导入 pyautogui 库
from tkinter import font # 导入 font 模块，为了 Tooltip (提示信息)

class QCGeneratorGUI:
    SD_3 = 3     # 3σ 常量定义
    SD_2 = 2     # 2σ 常量定义
    SD_1 = 1     # 1σ 常量定义
    TREND_LENGTH_7T = 7  # 7-t 规则的连续数据点数量
    RUN_LENGTH_10X = 10 # 10x 规则的连续数据点数量

    def __init__(self, root):
        self.root = root
        root.title("高级质控数据生成器")

        # ---- 菜单栏 ----
        menubar = Menu(root)
        root.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导出数据为 CSV", command=self.export_data_csv)

        # ---- 参数输入框架 ----
        self.input_frame = LabelFrame(root, text="参数设置")
        self.input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10) # column=0

        # 靶值 (Target Value)
        self.target_label = ttk.Label(self.input_frame, text="靶值 (Target Value):")
        self.target_label.grid(row=0, column=0, sticky=tk.W)
        self.target_entry = ttk.Entry(self.input_frame)
        self.target_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.target_entry.insert(0, "100")

        # 变异系数 (CV, %)
        self.cv_label = ttk.Label(self.input_frame, text="变异系数 (CV, %):")
        self.cv_label.grid(row=1, column=0, sticky=tk.W)
        self.cv_var = tk.DoubleVar(value=2.0) # 默认值 2.0%  (保留 cv_var)
        self.cv_entry = ttk.Entry(self.input_frame) # 使用 Entry 替换 Slider
        self.cv_entry.grid(row=1, column=1, sticky=(tk.W, tk.E)) # 布局与之前滑块相同
        self.cv_entry.insert(0, "2.0") # 设置默认值为 "2.0"

        # 初始偏移量 (Bias)
        self.bias_label = ttk.Label(self.input_frame, text="初始偏移量 (Bias):")
        self.bias_label.grid(row=2, column=0, sticky=tk.W)
        self.bias_entry = ttk.Entry(self.input_frame)
        self.bias_entry.grid(row=2, column=1, sticky=(tk.W, tk.E))
        self.bias_entry.insert(0, "0")

        # 每日漂移率 (Drift Rate)
        self.drift_label = ttk.Label(self.input_frame, text="每日漂移率 (Drift Rate):")
        self.drift_label.grid(row=3, column=0, sticky=tk.W)
        self.drift_var = tk.DoubleVar(value=0.0) # 默认值 0
        self.drift_spinbox = Spinbox(self.input_frame, textvariable=self.drift_var, from_=-1.0, to=1.0, increment=0.1, width=5)
        self.drift_spinbox.grid(row=3, column=1, sticky=(tk.W))

        # 误差分布类型
        self.distribution_label = ttk.Label(self.input_frame, text="误差分布类型:")
        self.distribution_label.grid(row=4, column=0, sticky=tk.W)
        self.distribution_var = StringVar(value="Normal") # 默认 正态分布
        self.distribution_optionmenu = OptionMenu(self.input_frame, self.distribution_var, "Normal", "Log-Normal")
        self.distribution_optionmenu.grid(row=4, column=1, sticky=(tk.W, tk.E))

        # 是否显示图表 开关
        self.plot_var = tk.BooleanVar(value=False) # 默认不显示图表
        self.plot_check = Checkbutton(self.input_frame, text="显示质控图", variable=self.plot_var)
        self.plot_check.grid(row=5, column=0, columnspan=2, sticky=tk.W) # 放在生成数据按钮的上方

        # 生成数据按钮
        self.generate_button = ttk.Button(self.input_frame, text="生成质控数据", command=self.generate_and_display_qc)
        self.generate_button.grid(row=6, column=0, columnspan=2, pady=10) # row 下移一位


        # ---- Westgard 规则选择框架 ----
        self.rules_frame = LabelFrame(root, text="Westgard 规则选择")
        self.rules_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10) # column=1  与 input_frame 并排

        self.rule_vars = {}
        rules = ["1-3s", "2-2s", "R-4s", "3-1s", "4-1s", "7-t", "10x"]
        for i, rule in enumerate(rules):
            self.rule_vars[rule] = tk.BooleanVar(value=True) # 默认全部启用
            check_button = Checkbutton(self.rules_frame, text=rule + " 规则", variable=self.rule_vars[rule])
            check_button.grid(row=i, column=0, sticky=tk.W)


        # ---- Levey-Jennings 图表框架 ---- 
        self.lj_chart_frame = LabelFrame(root, text="Levey-Jennings 质控图")
        self.lj_chart_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10) # column=2  移动到右侧, row 改为 0, 与 参数和规则框架 同行
        self.fig_lj, self.ax_lj = plt.subplots(figsize=(8, 5)) # 创建 Figure 和 Axes 对象
        self.canvas_lj = FigureCanvasTkAgg(self.fig_lj, master=self.lj_chart_frame) # 创建 FigureCanvasTkAgg 对象
        self.canvas_lj_widget = self.canvas_lj.get_tk_widget()
        self.canvas_lj_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))


        # ---- 结果显示框架 ----  
        self.result_frame = ttk.Frame(root, padding=10)
        self.result_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10) # row=1, columnspan=3, columnspan 改为 3 以跨越所有列

        # 质控数据显示框
        self.qc_data_label = ttk.Label(self.result_frame, text="31天质控数据:")
        self.qc_data_label.grid(row=0, column=0, sticky=tk.W)
        self.qc_data_text = scrolledText = scrolledtext.ScrolledText(self.result_frame, height=10, width=40)
        self.qc_data_text.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Westgard 规则检查结果显示框
        self.rules_result_label = ttk.Label(self.result_frame, text="Westgard 规则检查结果:")
        self.rules_result_label.grid(row=0, column=1, sticky=tk.W, padx=10)
        self.rules_result_text = scrolledtext.ScrolledText(self.result_frame, height=10, width=40)
        self.rules_result_text.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=10)

        # 基本统计信息显示框
        self.stats_label = ttk.Label(self.result_frame, text="基本统计信息:")
        self.stats_label.grid(row=0, column=2, sticky=tk.W, pady=(10,0))
        self.stats_text = scrolledtext.ScrolledText(self.result_frame, height=10, width=40)
        self.stats_text.grid(row=1, column=2, sticky=(tk.W, tk.E), pady=(0,10))


        # ---- 热键设置框架 ----  
        self.hotkey_frame = LabelFrame(root, text="热键设置")
        self.hotkey_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10) # row=2, columnspan=3, columnspan 改为 3 以跨越所有列

        # 热键输入框
        self.hotkey_label = ttk.Label(self.hotkey_frame, text="设置快捷键:")
        self.hotkey_label.grid(row=0, column=0, sticky=tk.W)
        self.hotkey_entry = ttk.Entry(self.hotkey_frame)
        self.hotkey_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.hotkey_entry.insert(0, "ctrl+alt+q") # 默认快捷键

        # 启动监听按钮
        self.start_button = ttk.Button(self.hotkey_frame, text="启动监听", command=self.start_listening)
        self.start_button.grid(row=0, column=2, padx=5)

        # 停止监听按钮
        self.stop_button = ttk.Button(self.hotkey_frame, text="停止监听", command=self.stop_listening, state="disabled")
        self.stop_button.grid(row=0, column=3, padx=5)

        # 状态标签
        self.status_label = ttk.Label(self.hotkey_frame, text="未监听快捷键 (已停止)")
        self.status_label.grid(row=1, column=0, columnspan=4, sticky=tk.W)

        # Tooltip 函数
        self.create_tooltip(self.bias_entry, "初始偏移量 (Bias):  质控数据整体的初始偏移程度。\n正值表示整体偏高，负值表示整体偏低。") # 为 初始偏移量 输入框 添加 Tooltip
        self.create_tooltip(self.drift_spinbox, "每日漂移率 (Drift Rate):  质控数据每日均值线性漂移的速率。\n正值表示均值每日递增，负值表示每日递减。") # 为 每日漂移率 数值微调框 添加 Tooltip


    # Tooltip 函数 
    def create_tooltip(self, widget, text):
        """为 Tkinter 组件创建工具提示."""
        tooltip = ToolTip(widget)  # 使用下面的 ToolTip 类
        def on_enter(event):
            tooltip.showtip(text)
        def on_leave(event):
            tooltip.hidetip()
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)


    def generate_qc_data(self, target_value, cv=0.02, num_days=31, bias=0, drift_rate=0, distribution_type="Normal"):
        """
        生成更真实的质控数据，包含误差分布选择和线性漂移.
        """
        std_dev = target_value * cv

        qc_data = []
        current_mean = target_value + bias  #  起始均值加入 初始偏移量 bias
        for _ in range(num_days):
            # 选择误差分布
            if distribution_type == "Normal":
                data_point = np.random.normal(loc=current_mean, scale=std_dev)
            elif distribution_type == "Log-Normal":
                #  为了生成对数正态分布，先生成正态分布，然后取指数。
                #  均值和标准差的转换需要考虑对数正态分布的性质，这里简化处理。
                log_mean = np.log(current_mean) - 0.5 * np.log(1 + (std_dev/current_mean)**2) # 简化近似
                log_std_dev = np.sqrt(np.log(1 + (std_dev/current_mean)**2)) # 简化近似
                data_point = np.random.lognormal(mean=log_mean, sigma=log_std_dev)
            else: # 默认正态分布
                data_point = np.random.normal(loc=current_mean, scale=std_dev)

            qc_data.append(data_point)
            current_mean += drift_rate  # 每日均值递增 漂移率 drift_rate

        return np.array(qc_data)


    def check_1_3s(self, data, target, std_dev):
        """检查 1-3s 规则."""
        for point in data:
            if abs(point - target) > self.SD_3 * std_dev:
                return True
        return False

    def check_2_2s(self, data, target, std_dev):
        """检查 2-2s 规则."""
        for i in range(len(data) - 1):
            if (abs(data[i] - target) > self.SD_2 * std_dev and
                    abs(data[i+1] - target) > self.SD_2 * std_dev and
                    ((data[i] - target) * (data[i+1] - target) > 0)): #  同一方向
                return True
        return False

    def check_r_4s(self, data, target, std_dev):
        """检查 R-4s 规则."""
        for i in range(len(data) - 1):
            if ((data[i] > target + self.SD_2 * std_dev and data[i+1] < target - self.SD_2 * std_dev) or
                    (data[i] < target - self.SD_2 * std_dev and data[i+1] > target + self.SD_2 * std_dev)):
                return True
        return False

    def check_3_1s(self, data, target, std_dev):
        """检查 3-1s 规则."""
        for i in range(len(data) - 2):
            if (abs(data[i] - target) > self.SD_1 * std_dev and
                    abs(data[i+1] - target) > self.SD_1 * std_dev and
                    abs(data[i+2] - target) > self.SD_1 * std_dev and
                    ((data[i] - target) * (data[i+1] - target) > 0 and # 同方向
                     (data[i] - target) * (data[i+2] - target) > 0)):
                return True
        return False

    def check_4_1s(self, data, target, std_dev):
        """检查 4-1s 规则."""
        for i in range(len(data) - 3):
            if (abs(data[i] - target) > self.SD_1 * std_dev and
                    abs(data[i+1] - target) > self.SD_1 * std_dev and
                    abs(data[i+2] - target) > self.SD_1 * std_dev and
                    abs(data[i+3] - target) > self.SD_1 * std_dev and
                    ((data[i] - target) * (data[i+1] - target) > 0 and # 同方向
                     (data[i] - target) * (data[i+2] - target) > 0 and
                     (data[i] - target) * (data[i+3] - target) > 0)):
                return True
        return False


    def check_7_t(self, data, target, std_dev):
        """检查 7-t 规则 (连续7点趋势)."""
        if len(data) < self.TREND_LENGTH_7T: # 数据点不足7个，无法判断
            return False

        for i in range(len(data) - self.TREND_LENGTH_7T + 1):
            segment = data[i:i+self.TREND_LENGTH_7T]
            is_trend_up = all(segment[j] < segment[j+1] for j in range(self.TREND_LENGTH_7T - 1))
            is_trend_down = all(segment[j] > segment[j+1] for j in range(self.TREND_LENGTH_7T - 1))
            if is_trend_up or is_trend_down:
                return True
        return False


    def check_10x(self, data, target, std_dev):
        """检查 10x 规则 (连续10点偏向一侧)."""
        if len(data) < self.RUN_LENGTH_10X: #  数据点不足10个，无法判断
            return False

        for i in range(len(data) - self.RUN_LENGTH_10X + 1):
            segment = data[i:i+self.RUN_LENGTH_10X]
            all_above = all(point > target for point in segment)
            all_below = all(point < target for point in segment)
            if all_above or all_below: #  全部高于靶值 或 全部低于靶值
                return True
        return False


    def apply_westgard_rules(self, data, target_value, cv=0.02):
        """应用 Westgard 规则."""
        std_dev = target_value * cv
        rules_violated = {}

        rule_funcs = {
            "1-3s": self.check_1_3s,
            "2-2s": self.check_2_2s,
            "R-4s": self.check_r_4s,
            "3-1s": self.check_3_1s,
            "4-1s": self.check_4_1s,
            "7-t": self.check_7_t,
            "10x": self.check_10x,
        }

        for rule_name, check_func in rule_funcs.items():
            if self.rule_vars[rule_name].get(): #  检查规则是否被启用
                violated = check_func(data, target_value, std_dev)
                rules_violated[rule_name] = violated
            else:
                rules_violated[rule_name] = False #  如果规则未启用，则视为未违反

        return rules_violated


    def generate_and_display_qc(self):
        """从 GUI 获取参数，生成质控数据，进行规则检查，并显示结果和图表."""
        try:
            target = float(self.target_entry.get())
            cv_str = self.cv_entry.get() # 先获取 CV 值的字符串形式
            try:
                cv = float(cv_str) / 100.0 # 尝试转换为 float
                if cv <= 0 or cv > 0.1: # CV 变异系数的合理范围 0.1% - 10% (验证范围)
                    messagebox.showerror("参数错误", "变异系数 (CV) 请设置在 0.1% - 10% 范围内。")
                    return
            except ValueError:
                messagebox.showerror("参数错误", "变异系数 (CV) 请输入有效的数字。") #  输入非数字错误提示
                return
            bias = float(self.bias_entry.get())  #  从 bias_entry 获取 初始偏移量
            drift_rate = float(self.drift_var.get()) # 从 drift_var 获取 每日漂移率
            distribution_type = self.distribution_var.get()

            if cv <= 0 or cv > 0.1: # CV 变异系数的合理范围 0.1% - 10%
                messagebox.showerror("参数错误", "变异系数 (CV) 请设置在 0.1% - 10% 范围内。")
                return
            if abs(drift_rate) > 1.0: # 每日漂移率合理范围 -1.0 - 1.0
                messagebox.showerror("参数错误", "每日漂移率 (Drift Rate) 请设置在 -1.0 到 1.0 范围内。")
                return

            # 显示 "正在生成数据..." 提示
            self.qc_data_text.delete(1.0, tk.END)
            self.qc_data_text.insert(tk.END, "正在生成质控数据，请稍候...\n")
            self.rules_result_text.delete(1.0, tk.END)
            self.rules_result_text.insert(tk.END, "正在进行 Westgard 规则检查...\n")
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(tk.END, "正在计算统计信息...\n")
            self.root.update() # 立即更新 GUI，显示提示信息

            qc_data_31_days = self.generate_qc_data(target, cv, bias=bias, drift_rate=drift_rate, distribution_type=distribution_type) # bias 和 drift_rate 参数正确传递
            rules_result = self.apply_westgard_rules(qc_data_31_days, target, cv=cv)

            # 显示质控数据
            self.qc_data_text.delete(1.0, tk.END)
            self.qc_data_text.insert(tk.END, "31天质控数据:\n")
            for i, data_point in enumerate(qc_data_31_days):
                self.qc_data_text.insert(tk.END, f"第{i+1}天: {data_point:.2f}\n")

            # 显示 Westgard 规则检查结果
            self.rules_result_text.delete(1.0, tk.END)
            self.rules_result_text.insert(tk.END, "Westgard 规则检查结果:\n")
            rule_violated_flag = False  # 用于标记是否有规则被违反
            for rule, violated in rules_result.items():
                rule_status = '是 (违反)' if violated else '否'
                self.rules_result_text.insert(tk.END, f"{rule} 规则是否违反: {rule_status}\n")
                if violated:
                    rule_violated_flag = True

            if rule_violated_flag:
                self.rules_result_text.insert(tk.END, "\n注意：Westgard 规则被违反，请审核质控结果。\n")
            else:
                self.rules_result_text.insert(tk.END, "\n恭喜：所有启用的 Westgard 规则均未被违反。\n")

            # 计算基本统计信息并显示
            mean_val = np.mean(qc_data_31_days)
            std_dev_val = np.std(qc_data_31_days)
            cv_val_percent = (std_dev_val / mean_val) * 100 if mean_val != 0 else 0 # 避免除以零
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(tk.END, f"均值 (Mean): {mean_val:.2f}\n")
            self.stats_text.insert(tk.END, f"标准差 (SD): {std_dev_val:.2f}\n")
            self.stats_text.insert(tk.END, f"变异系数 (CV): {cv_val_percent:.2f}%\n")

            # 生成 Levey-Jennings 图表
            if self.plot_var.get(): # 检查绘图开关是否开启
                self.plot_levey_jennings(qc_data_31_days, target, std_dev_val)
            else: # 如果不绘图，则清空之前的图表显示区域 (可选)
                self.ax_lj.clear()
                self.canvas_lj.draw() # 更新画布以清空图表


        except ValueError:
            self.rules_result_text.delete(1.0, tk.END)
            self.rules_result_text.insert(tk.END, "输入值无效，请检查靶值、变异系数、偏移量和漂移率是否为数字。\n")


    def plot_levey_jennings(self, qc_data, target, std_dev):
        """生成 Levey-Jennings 质控图."""
        self.ax_lj.clear() # 清空之前的图表

        days = range(1, len(qc_data) + 1)
        self.ax_lj.plot(days, qc_data, marker='o', linestyle='-', color='blue', label='QC Data')

        # 绘制靶值线和控制限
        self.ax_lj.axhline(target, color='green', linestyle='-', label='Target')
        self.ax_lj.axhline(target + 2 * std_dev, color='orange', linestyle='--', label='+2SD & -2SD')
        self.ax_lj.axhline(target - 2 * std_dev, color='orange', linestyle='--')
        self.ax_lj.axhline(target + 3 * std_dev, color='red', linestyle='--', label='+3SD & -3SD')
        self.ax_lj.axhline(target - 3 * std_dev, color='red', linestyle='--')

        self.ax_lj.set_xlabel("Day")
        self.ax_lj.set_ylabel("QC Value")
        self.ax_lj.set_title("Levey-Jennings 质控图")
        self.ax_lj.legend(loc='upper left')
        self.ax_lj.grid(True)

        self.canvas_lj.draw() # 重新绘制图表


    def export_data_csv(self):
        """导出质控数据到 CSV 文件."""
        try:
            qc_data_text = self.qc_data_text.get("1.0", tk.END).strip() # 获取文本框数据
            if not qc_data_text.startswith("31天质控数据:"):
                tk.messagebox.showerror("导出错误", "请先生成质控数据再导出。")
                return

            data_lines = qc_data_text.split('\n')[1:] # 跳过标题行，获取数据行
            data_values = []
            for line in data_lines:
                try:
                    value = float(line.split(':')[1].strip()) # 从 "第X天: YYY" 格式的字符串中提取数值
                    data_values.append(value)
                except (IndexError, ValueError):
                    continue  # 忽略无法解析的行

            if not data_values:
                tk.messagebox.showerror("导出错误", "未能解析到有效的质控数据。")
                return

            filename = asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
            if filename:
                with open(filename, 'w', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(["Day", "QC_Value"])  # 写入标题行
                    for i, value in enumerate(data_values):
                        csv_writer.writerow([i+1, value]) # 写入数据行
                    tk.messagebox.showinfo("导出成功", f"质控数据已导出到: {filename}")

        except Exception as e:
             tk.messagebox.showerror("导出错误", f"导出CSV文件时发生错误: {e}")


    def start_listening(self):
        """启动热键监听。"""
        start_hotkey = self.hotkey_entry.get().strip()
        if not start_hotkey:
            messagebox.showerror("错误", "请设置一个有效的快捷键！")
            return

        try:
            keyboard.add_hotkey(start_hotkey, self.generate_and_output)
            self.start_button["state"] = "disabled"
            self.stop_button["state"] = "normal"
            self.status_label.config(text=f"监听快捷键: {start_hotkey} (已启动)")  #  状态栏显示 "已启动"
        except ValueError:  #  更具体地捕获 ValueError，可能是无效快捷键组合
            messagebox.showerror("错误", "无效的快捷键组合！请检查快捷键设置。")  #  更详细的错误信息
        except Exception as e:  # 捕获其他可能的热键启动错误
            messagebox.showerror("错误", f"启动热键监听失败: {e}")  #  更通用的错误信息


    def stop_listening(self):
        """停止热键监听。"""
        start_hotkey = self.hotkey_entry.get().strip()
        if start_hotkey:
            keyboard.remove_hotkey(start_hotkey)
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.status_label.config(text="未监听快捷键 (已停止)") # 状态栏显示 "已停止"


    def generate_and_output(self):
        """生成质控数据并输出到当前焦点处，使用 pyautogui.write()."""
        try:
            self.status_label.config(text="正在生成数据并输出... (热键触发)") #  状态栏显示 "正在生成..."
            target = float(self.target_entry.get())
            cv_str = self.cv_entry.get() # 先获取 CV 值的字符串形式
            try:
                cv = float(cv_str) / 100.0 # 尝试转换为 float
                if cv <= 0 or cv > 0.1: # CV 变异系数的合理范围 0.1% - 10% (验证范围)
                    messagebox.showerror("参数错误", "变异系数 (CV) 请设置在 0.1% - 10% 范围内。")
                    return
            except ValueError:
                messagebox.showerror("参数错误", "变异系数 (CV) 请输入有效的数字。") #  输入非数字错误提示
                return
            bias = float(self.bias_entry.get())
            drift_rate = float(self.drift_var.get())
            distribution_type = self.distribution_var.get()

            qc_data_31_days = self.generate_qc_data(target, cv, bias=bias, drift_rate=drift_rate, distribution_type=distribution_type)

            # 调用 update_gui_display 函数来更新 GUI 显示
            self.update_gui_display(qc_data_31_days, target, cv)

            # 强制 GUI 立即更新
            self.root.update()

            # 格式化数据并使用 pyautogui.write() 输出
            for data_point in qc_data_31_days:
                pyautogui.write(f"{data_point:.2f}\n")

            # 在状态栏显示提示信息 (可选)
            self.status_label.config(text="数据已生成并输出到焦点处 (热键触发)") #  状态栏显示 "已完成"

        except ValueError:
            tk.messagebox.showerror("错误", "输入值无效，请检查参数设置。")
        except Exception as e:  # 捕获更广泛的异常，例如 pyautogui 相关错误
            tk.messagebox.showerror("错误", f"生成数据或输出时发生错误: {e}") # 更通用的错误信息
        finally:  #  无论成功还是失败，最终都将状态改回监听状态或未监听状态
            if self.stop_button["state"] == "normal":  # 如果停止按钮可用，说明监听是启动的
                start_hotkey = self.hotkey_entry.get().strip()
                self.status_label.config(text=f"监听快捷键: {start_hotkey} (已启动)")  # 恢复监听状态
            else:
                self.status_label.config(text="未监听快捷键 (已停止)") # 恢复未监听状态


    def update_gui_display(self, qc_data_31_days, target, cv): # 新增函数，用于封装 GUI 更新代码
        """
        更新 GUI 显示 (文本框和图表).  从 generate_and_output 中调用
        """
        rules_result = self.apply_westgard_rules(qc_data_31_days, target, cv=cv)

        # 显示质控数据
        self.qc_data_text.delete(1.0, tk.END)
        self.qc_data_text.insert(tk.END, "31天质控数据:\n")
        for i, data_point in enumerate(qc_data_31_days):
            self.qc_data_text.insert(tk.END, f"第{i+1}天: {data_point:.2f}\n")

        # 显示 Westgard 规则检查结果
        self.rules_result_text.delete(1.0, tk.END)
        self.rules_result_text.insert(tk.END, "Westgard 规则检查结果:\n")
        rule_violated_flag = False  # 用于标记是否有规则被违反
        for rule, violated in rules_result.items():
            rule_status = '是 (违反)' if violated else '否'
            self.rules_result_text.insert(tk.END, f"{rule} 规则是否违反: {rule_status}\n")
            if violated:
                rule_violated_flag = True

        if rule_violated_flag:
            self.rules_result_text.insert(tk.END, "\n注意：Westgard 规则被违反，请审核质控结果。\n")
        else:
            self.rules_result_text.insert(tk.END, "\n恭喜：所有启用的 Westgard 规则均未被违反。\n")


        # 计算基本统计信息并显示
        mean_val = np.mean(qc_data_31_days)
        std_dev_val = np.std(qc_data_31_days)
        cv_val_percent = (std_dev_val / mean_val) * 100 if mean_val != 0 else 0 # 避免除以零
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, f"均值 (Mean): {mean_val:.2f}\n")
        self.stats_text.insert(tk.END, f"标准差 (SD): {std_dev_val:.2f}\n")
        self.stats_text.insert(tk.END, f"变异系数 (CV): {cv_val_percent:.2f}%\n")

        # 生成 Levey-Jennings 图表
        if self.plot_var.get(): # 检查绘图开关是否开启
            self.plot_levey_jennings(qc_data_31_days, target, std_dev_val)
        else: # 如果不绘图，则清空之前的图表显示区域 (可选)
            self.ax_lj.clear()
            self.canvas_lj.draw() # 更新画布以清空图表


class ToolTip:  # ToolTip 类定义在 QCGeneratorGUI 类之外
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() +25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                           background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                           font=("tahoma", "8", "normal")) # 可以自定义字体和背景
        label.pack(ipadx=1)
        # label.bind("<ButtonPress-1>", self.hidetip) # 点击tooltip窗口可以隐藏
        # label.bind("<Leave>", self.hidetip) #  鼠标离开tooltip窗口也可以隐藏, 可选
        self.id = self.widget.after_idle(self.show)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

    def show(self):
        pass  #  可以根据需要添加额外的显示逻辑, 目前为空


if __name__ == "__main__":
    root = tk.Tk()
    gui = QCGeneratorGUI(root)
    root.mainloop()
