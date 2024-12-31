use eframe::egui; // Import the eframe and egui crates
use egui_plot::{Line, Plot, PlotPoints}; // Import the necessary plotting components from egui_plot
use rand::Rng; // Import the random number generator from the rand crate
use std::fs; // Import file system operations from the standard library

fn main() {
    let options = eframe::NativeOptions::default(); // Set default options for the eframe application
    let _ = eframe::run_native(
        "Rust 数据生成程序（带 Westgard 规则验证）", // Set the window title
        options, // Pass the options to the eframe application
        Box::new(|cc| {
            // Initialize the application
            // 加载自定义字体
            let mut fonts = egui::FontDefinitions::default(); // Get the default font definitions
            if let Ok(font_data) = fs::read("assets/fonts/NotoSansSC-Regular.ttf") {
                // Try to read the custom font file
                fonts.font_data.insert(
                    "noto_sans_sc".to_string(),
                    egui::FontData::from_owned(font_data).into(), // Convert the font data to Arc<FontData>
                );
                if let Some(family) = fonts.families.get_mut(&egui::FontFamily::Proportional) {
                    // Insert the custom font as the first font in the proportional family
                    family.insert(0, "noto_sans_sc".to_string());
                }
            } else {
                eprintln!("未找到字体文件，将使用默认字体。"); // Print an error message if the font file is not found
            }
            cc.egui_ctx.set_fonts(fonts); // Set the custom fonts in the egui context

            Ok(Box::new(MyApp::default())) // Return an instance of MyApp
        }),
    );
}

#[derive(Default)]
struct MyApp {
    target_value: String, // Field for target value input
    acceptable_range: String, // Field for acceptable range input
    imprecision: String, // Field for imprecision input
    num_data: String, // Field for the number of data points input
    results: Vec<f64>, // Vector to store generated results
    error_message: String, // Field for error messages
    is_dark_mode: bool, // Field to toggle dark mode
}

impl eframe::App for MyApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // 设置主题
        if self.is_dark_mode {
            ctx.set_visuals(egui::Visuals::dark()); // Apply dark theme
        } else {
            ctx.set_visuals(egui::Visuals::light()); // Apply light theme
        }

        // 主界面
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("Rust 数据生成程序（带 Westgard 规则验证）"); // Display heading

            // 主题切换开关
            ui.horizontal(|ui| {
                ui.label("主题模式:"); // Label for theme switch
                ui.checkbox(&mut self.is_dark_mode, "深色模式")
                    .on_hover_text("切换深色/浅色模式"); // Checkbox to toggle dark mode
            });

            // 输入字段
            ui.label("目标值:"); // Label for target value input
            ui.text_edit_singleline(&mut self.target_value); // Input field for target value
            ui.label("可接受范围 (%):"); // Label for acceptable range input
            ui.text_edit_singleline(&mut self.acceptable_range); // Input field for acceptable range
            ui.label("不精密度 (%):"); // Label for imprecision input
            ui.text_edit_singleline(&mut self.imprecision); // Input field for imprecision
            ui.label("生成数据的数量:"); // Label for number of data points input
            ui.text_edit_singleline(&mut self.num_data); // Input field for number of data points

            // 错误消息
            if !self.error_message.is_empty() {
                ui.colored_label(egui::Color32::RED, &self.error_message); // Display error message in red
            }

            // 生成按钮
            if ui.button("生成数据").clicked() {
                self.results.clear(); // Clear previous results
                self.error_message.clear(); // Clear previous error messages

                // 解析输入
                let target_value = match self.target_value.parse::<f64>() {
                    Ok(value) if value > 0.0 => value, // Parse and validate target value
                    _ => {
                        self.error_message = "目标值无效，请输入一个正数。".to_string(); // Set error message if invalid
                        return;
                    }
                };

                let acceptable_range = match self.acceptable_range.parse::<f64>() {
                    Ok(value) if value > 0.0 => value, // Parse and validate acceptable range
                    _ => {
                        self.error_message = "可接受范围无效，请输入一个正数。".to_string(); // Set error message if invalid
                        return;
                    }
                };

                let imprecision = match self.imprecision.parse::<f64>() {
                    Ok(value) if value > 0.0 => value, // Parse and validate imprecision
                    _ => {
                        self.error_message = "不精密度无效，请输入一个正数。".to_string(); // Set error message if invalid
                        return;
                    }
                };

                let num_data = match self.num_data.parse::<usize>() {
                    Ok(value) if value > 0 => value, // Parse and validate number of data points
                    _ => {
                        self.error_message = "数据数量无效，请输入一个正整数。".to_string(); // Set error message if invalid
                        return;
                    }
                };

                // 计算标准差和范围
                let std_dev = (target_value * acceptable_range) / 200.0; // Calculate standard deviation
                let min_value = target_value - 2.0 * std_dev; // Calculate minimum acceptable value
                let max_value = target_value + 2.0 * std_dev; // Calculate maximum acceptable value

                // 生成数据
                let mut rng = rand::thread_rng(); // Initialize random number generator
                while self.results.len() < num_data {
                    let deviation = rng.gen_range(-imprecision / 100.0..imprecision / 100.0); // Generate random deviation
                    let value = target_value * (1.0 + deviation); // Calculate data point

                    if value < min_value || value > max_value {
                        continue; // Skip data points outside acceptable range
                    }

                    if !westgard_check(&self.results, value, target_value, std_dev) {
                        continue; // Skip data points violating Westgard rules
                    }

                    self.results.push(value); // Add valid data point to results
                }
            }
        });

        // 右侧面板：显示生成的数据
        egui::SidePanel::right("data_panel")
            .default_width(200.0)
            .show(ctx, |ui| {
                ui.heading("生成的数据"); // Display heading for data panel
                for value in &self.results {
                    ui.label(format!("{:.2}", value)); // Display each data point
                }
            });

        // 底部面板：实时绘图
        egui::TopBottomPanel::bottom("plot_panel")
            .default_height(300.0)
            .show(ctx, |ui| {
                ui.heading("实时数据图"); // Display heading for plot panel

                // 解析目标值
                let target_value = self.target_value.parse::<f64>().unwrap_or(0.0); // Parse target value

                // 计算标准差
                let std_dev = (target_value * self.acceptable_range.parse::<f64>().unwrap_or(0.0)) / 200.0; // Calculate standard deviation

                // 固定 Y 轴范围为 ±3 SD
                let min_y = target_value - 3.0 * std_dev; // Calculate minimum Y-axis value
                let max_y = target_value + 3.0 * std_dev; // Calculate maximum Y-axis value

                // 固定图形大小
                let plot = Plot::new("data_plot")
                    .height(300.0) // Set plot height
                    .width(ui.available_width()) // Set plot width to panel width
                    .include_x(0.0) // X-axis starts at 0
                    .include_x(self.results.len() as f64) // X-axis ends at number of data points
                    .include_y(min_y) // Set Y-axis minimum
                    .include_y(max_y); // Set Y-axis maximum

                plot.show(ui, |plot_ui| {
                    // 绘制数据点
                    let points: PlotPoints = self
                        .results
                        .iter()
                        .enumerate()
                        .map(|(i, &v)| [i as f64, v]) // Map data points to plot points
                        .collect();
                    plot_ui.line(Line::new(points).name("数据")); // Plot data points

                    // 靶值
                    plot_ui.hline(
                        egui_plot::HLine::new(target_value)
                            .name("靶值")
                            .color(egui::Color32::BLUE), // Plot target value line in blue
                    );

                    // 标准差范围
                    plot_ui.hline(
                        egui_plot::HLine::new(target_value + std_dev)
                            .name("+1 SD")
                            .color(egui::Color32::GREEN), // Plot +1 SD line in green
                    );
                    plot_ui.hline(
                        egui_plot::HLine::new(target_value - std_dev)
                            .name("-1 SD")
                            .color(egui::Color32::GREEN), // Plot -1 SD line in green
                    );
                    plot_ui.hline(
                        egui_plot::HLine::new(target_value + 2.0 * std_dev)
                            .name("+2 SD")
                            .color(egui::Color32::YELLOW), // Plot +2 SD line in yellow
                    );
                    plot_ui.hline(
                        egui_plot::HLine::new(target_value - 2.0 * std_dev)
                            .name("-2 SD")
                            .color(egui::Color32::YELLOW), // Plot -2 SD line in yellow
                    );
                    plot_ui.hline(
                        egui_plot::HLine::new(target_value + 3.0 * std_dev)
                            .name("+3 SD")
                            .color(egui::Color32::RED), // Plot +3 SD line in red
                    );
                    plot_ui.hline(
                        egui_plot::HLine::new(target_value - 3.0 * std_dev)
                            .name("-3 SD")
                            .color(egui::Color32::RED), // Plot -3 SD line in red
                    );
                });
            });
    }
}

/// 检查 Westgard 规则
fn westgard_check(data: &Vec<f64>, value: f64, mean: f64, std_dev: f64) -> bool {
    let n = data.len(); // Get the number of data points

    // 1-2s: 单个值超过均值 ±2 SD
    if (value - mean).abs() > 2.0 * std_dev {
        return false; // Fail if value is outside ±2 SD
    }

    // 1-3s: 单个值超过均值 ±3 SD
    if (value - mean).abs() > 3.0 * std_dev {
        return false; // Fail if value is outside ±3 SD
    }

    // 2-2s: 连续两个值超过均值 ±2 SD
    if n >= 1 && (data[n - 1] - mean).abs() > 2.0 * std_dev && (value - mean).abs() > 2.0 * std_dev {
        return false; // Fail if two consecutive values are outside ±2 SD
    }

    // R-4s: 任意两个连续值的差异超过 4 SD
    if n >= 1 && (value - data[n - 1]).abs() > 4.0 * std_dev {
        return false; // Fail if the difference between two consecutive values is >4 SD
    }

    // 4-1s: 连续四个值超过均值 ±1 SD 的同一方向
    if n >= 4 {
        let last_direction = (data[n - 1] - mean).signum(); // Get the direction of the last value
        if (data[n - 2] - mean).signum() == last_direction
            && (data[n - 3] - mean).signum() == last_direction
            && (data[n - 4] - mean).signum() == last_direction
            && (value - mean).signum() == last_direction
            && (data[n - 1] - mean).abs() > mean * 0.01
            && (data[n - 2] - mean).abs() > mean * 0.01
            && (data[n - 3] - mean).abs() > mean * 0.01
            && (data[n - 4] - mean).abs() > mean * 0.01
            && (value - mean).abs() > mean * 0.01
        {
            return false; // Fail if four consecutive values are on the same side of the mean and exceed ±1 SD
        }
    }

    // 10-x: 连续十个值在均值的一侧
    if n >= 10 {
        let current_side = (value - mean).signum(); // Get the side of the current value
        if data.iter().rev().take(9).all(|&v| (v - mean).signum() == current_side) {
            return false; // Fail if ten consecutive values are on the same side of the mean
        }
    }

    true // Pass if none of the rules are violated
  }
