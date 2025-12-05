use eframe::egui;
use egui_plot::{Line, Plot, PlotPoints, Legend};
use std::thread;
use std::time::Duration;
use enigo::{Enigo, Key, KeyboardControllable};
use rdev::{listen, Event, EventType, Key as RdevKey};
use crossbeam_channel::{unbounded, Sender, Receiver};
use std::sync::atomic::{AtomicBool, Ordering};

mod logic;
use logic::generator::{generate_data, QCParams, DistributionType};
use logic::rules::{apply_rules, RuleConfig};

// --- App State ---

struct QCApp {
    // Inputs
    target_str: String,
    cv_str: String,
    bias_str: String,
    drift_str: String,
    dist_type: DistributionType,

    // Config
    rule_config: RuleConfig,
    show_plot: bool,

    // Data & Results
    qc_data: Vec<f64>,
    westgard_results: std::collections::HashMap<String, bool>,
    stats: Option<(f64, f64, f64)>, // Mean, SD, CV

    // Status
    status_msg: String,

    // Hotkey
    hotkey_listening: bool,
    hotkey_status: String,
    hotkey_sender: Sender<HotKeyEvent>,
    hotkey_receiver: Receiver<HotKeyEvent>,
}

enum HotKeyEvent {
    TriggerOutput,
}

impl Default for QCApp {
    fn default() -> Self {
        let (s, r) = unbounded();
        Self {
            target_str: "100.0".to_owned(),
            cv_str: "2.0".to_owned(),
            bias_str: "0.0".to_owned(),
            drift_str: "0.0".to_owned(),
            dist_type: DistributionType::Normal,

            rule_config: RuleConfig::default(),
            show_plot: false,

            qc_data: Vec::new(),
            westgard_results: std::collections::HashMap::new(),
            stats: None,

            status_msg: "Ready".to_owned(),

            hotkey_listening: false,
            hotkey_status: "Hotkey: Ctrl+Alt+Q (Not listening)".to_owned(),
            hotkey_sender: s,
            hotkey_receiver: r,
        }
    }
}

impl QCApp {
    fn generate(&mut self) {
        let target = self.target_str.parse::<f64>().unwrap_or(100.0);
        let cv_percent = self.cv_str.parse::<f64>().unwrap_or(2.0);

        // Input validation: Clamp CV to avoid panic or bad math (e.g., negative or zero if not handled)
        // Normal::new panics if std_dev < 0. We'll use absolute value and a tiny epsilon for 0.
        let cv = cv_percent.abs() / 100.0;
        let safe_cv = if cv < 1e-6 { 1e-6 } else { cv };

        let bias = self.bias_str.parse::<f64>().unwrap_or(0.0);
        let drift = self.drift_str.parse::<f64>().unwrap_or(0.0);

        let params = QCParams {
            target,
            cv: safe_cv,
            bias,
            drift_rate: drift,
            num_days: 31,
            dist_type: self.dist_type,
        };

        self.qc_data = generate_data(&params);
        // Note: apply_rules uses 'cv' which might be the sanitized one or user one.
        // Logic side should handle it, but we pass sanitized.
        self.westgard_results = apply_rules(&self.qc_data, target, safe_cv, &self.rule_config);

        // Stats
        let mean = self.qc_data.iter().sum::<f64>() / self.qc_data.len() as f64;
        let variance = self.qc_data.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / self.qc_data.len() as f64;
        let std_dev = variance.sqrt();
        let calc_cv = if mean != 0.0 { (std_dev / mean) * 100.0 } else { 0.0 };

        self.stats = Some((mean, std_dev, calc_cv));
        self.status_msg = "Data Generated.".to_owned();
    }

    fn toggle_hotkey_listener(&mut self) {
        if self.hotkey_listening {
            self.hotkey_listening = false;
            self.hotkey_status = "Hotkey: Ctrl+Alt+Q (Paused)".to_owned();
        } else {
            self.hotkey_listening = true;
            self.hotkey_status = "Hotkey: Ctrl+Alt+Q (Listening)".to_owned();

            static LISTENER_STARTED: AtomicBool = AtomicBool::new(false);
            if !LISTENER_STARTED.swap(true, Ordering::SeqCst) {
                 let sender = self.hotkey_sender.clone();
                 thread::spawn(move || {
                     listen_hotkey(sender);
                 });
            }
        }
    }

    fn output_data_to_keyboard(&self) {
        let data = self.qc_data.clone();
        if data.is_empty() { return; }

        thread::spawn(move || {
            let mut enigo = Enigo::new();
            thread::sleep(Duration::from_millis(500));

            for point in data {
                let text = format!("{:.2}\n", point);
                enigo.key_sequence(&text);
                thread::sleep(Duration::from_millis(50));
            }
        });
    }

    fn export_csv(&mut self) {
        if let Some(path) = rfd::FileDialog::new().add_filter("CSV", &["csv"]).save_file() {
             match csv::Writer::from_path(&path) {
                 Ok(mut wtr) => {
                     let mut success = true;
                     if let Err(_) = wtr.write_record(&["Day", "Value"]) { success = false; }
                     if success {
                         for (i, val) in self.qc_data.iter().enumerate() {
                             if let Err(_) = wtr.write_record(&[format!("{}", i+1), format!("{:.2}", val)]) {
                                 success = false;
                                 break;
                             }
                         }
                     }

                     if success && wtr.flush().is_ok() {
                         self.status_msg = format!("Exported to {:?}", path);
                     } else {
                         self.status_msg = "Error writing to CSV file.".to_owned();
                     }
                 },
                 Err(e) => {
                     self.status_msg = format!("Error creating file: {}", e);
                 }
             }
        }
    }
}

fn listen_hotkey(sender: Sender<HotKeyEvent>) {
    let mut ctrl = false;
    let mut alt = false;

    if let Err(error) = listen(move |event| {
        match event.event_type {
            EventType::KeyPress(key) => {
                match key {
                    RdevKey::ControlLeft | RdevKey::ControlRight => ctrl = true,
                    RdevKey::Alt | RdevKey::AltGr => alt = true,
                    RdevKey::KeyQ => {
                        if ctrl && alt {
                            let _ = sender.send(HotKeyEvent::TriggerOutput);
                        }
                    }
                    _ => {}
                }
            },
            EventType::KeyRelease(key) => {
                 match key {
                    RdevKey::ControlLeft | RdevKey::ControlRight => ctrl = false,
                    RdevKey::Alt | RdevKey::AltGr => alt = false,
                    _ => {}
                }
            }
            _ => {}
        }
    }) {
        println!("Error: {:?}", error);
    }
}

impl eframe::App for QCApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        while let Ok(_event) = self.hotkey_receiver.try_recv() {
            if self.hotkey_listening {
                if self.qc_data.is_empty() {
                    self.generate();
                }
                self.output_data_to_keyboard();
                self.status_msg = "Data Output Triggered via Hotkey".to_owned();
            }
        }

        egui::CentralPanel::default().show(ctx, |ui| {
            ui.columns(2, |columns| {
                columns[0].vertical(|ui| {
                    ui.heading("Parameters");
                    ui.add_space(5.0);

                    egui::Grid::new("inputs_grid").show(ui, |ui| {
                        ui.label("Target Value:");
                        ui.text_edit_singleline(&mut self.target_str);
                        ui.end_row();

                        ui.label("CV (%):");
                        ui.text_edit_singleline(&mut self.cv_str);
                        ui.end_row();

                        ui.label("Bias:");
                        ui.text_edit_singleline(&mut self.bias_str);
                        ui.end_row();

                        ui.label("Drift Rate:");
                        ui.text_edit_singleline(&mut self.drift_str);
                        ui.end_row();

                        ui.label("Distribution:");
                        egui::ComboBox::from_id_source("dist_combo")
                            .selected_text(match self.dist_type {
                                DistributionType::Normal => "Normal",
                                DistributionType::LogNormal => "Log-Normal",
                            })
                            .show_ui(ui, |ui| {
                                ui.selectable_value(&mut self.dist_type, DistributionType::Normal, "Normal");
                                ui.selectable_value(&mut self.dist_type, DistributionType::LogNormal, "Log-Normal");
                            });
                        ui.end_row();
                    });

                    ui.add_space(10.0);
                    ui.heading("Westgard Rules");
                    ui.checkbox(&mut self.rule_config.check_1_3s, "1-3s");
                    ui.checkbox(&mut self.rule_config.check_2_2s, "2-2s");
                    ui.checkbox(&mut self.rule_config.check_r_4s, "R-4s");
                    ui.checkbox(&mut self.rule_config.check_3_1s, "3-1s");
                    ui.checkbox(&mut self.rule_config.check_4_1s, "4-1s");
                    ui.checkbox(&mut self.rule_config.check_7t, "7-t");
                    ui.checkbox(&mut self.rule_config.check_10x, "10x");

                    ui.add_space(10.0);
                    ui.checkbox(&mut self.show_plot, "Show Plot");

                    ui.add_space(10.0);
                    if ui.button("Generate QC Data").clicked() {
                        self.generate();
                    }

                    ui.add_space(20.0);
                    ui.separator();
                    ui.heading("Automation");
                    ui.label(&self.hotkey_status);
                    if ui.button(if self.hotkey_listening { "Pause Listener" } else { "Start Listener" }).clicked() {
                        self.toggle_hotkey_listener();
                    }
                    ui.add_space(5.0);
                    if ui.button("Export to CSV").clicked() {
                         self.export_csv();
                    }

                    ui.add_space(10.0);
                    ui.label(&self.status_msg);
                });

                columns[1].vertical(|ui| {
                    ui.heading("Results");
                    if let Some((mean, sd, cv)) = self.stats {
                        ui.group(|ui| {
                            ui.label(format!("Mean: {:.2} | SD: {:.2} | CV: {:.2}%", mean, sd, cv));
                        });
                    }
                    ui.add_space(5.0);
                    if !self.westgard_results.is_empty() {
                         egui::ScrollArea::vertical().max_height(100.0).show(ui, |ui| {
                            let mut violated = false;
                            for (rule, is_violated) in &self.westgard_results {
                                let text = if *is_violated {
                                    violated = true;
                                    egui::RichText::new(format!("{} : VIOLATED", rule)).color(egui::Color32::RED)
                                } else {
                                    egui::RichText::new(format!("{} : Pass", rule)).color(egui::Color32::GREEN)
                                };
                                ui.label(text);
                            }
                            if violated {
                                ui.label(egui::RichText::new("\nWarning: Rules Violated!").strong().color(egui::Color32::RED));
                            } else {
                                ui.label(egui::RichText::new("\nAll Rules Passed.").strong().color(egui::Color32::GREEN));
                            }
                        });
                    }

                    ui.add_space(10.0);
                    if self.show_plot && !self.qc_data.is_empty() {
                        let target = self.target_str.parse::<f64>().unwrap_or(100.0);
                        let cv = self.cv_str.parse::<f64>().unwrap_or(2.0) / 100.0;
                        let sd = target * cv;

                        let points: PlotPoints = self.qc_data.iter().enumerate()
                            .map(|(i, &v)| [i as f64 + 1.0, v])
                            .collect();

                        let line = Line::new(points).name("QC Data");

                        Plot::new("lj_chart")
                            .view_aspect(2.0)
                            .legend(Legend::default())
                            .show(ui, |plot_ui| {
                                plot_ui.line(line);
                                plot_ui.hline(egui_plot::HLine::new(target).color(egui::Color32::GREEN).name("Target"));
                                plot_ui.hline(egui_plot::HLine::new(target + 2.0*sd).color(egui::Color32::YELLOW).name("+2SD"));
                                plot_ui.hline(egui_plot::HLine::new(target - 2.0*sd).color(egui::Color32::YELLOW).name("-2SD"));
                                plot_ui.hline(egui_plot::HLine::new(target + 3.0*sd).color(egui::Color32::RED).name("+3SD"));
                                plot_ui.hline(egui_plot::HLine::new(target - 3.0*sd).color(egui::Color32::RED).name("-3SD"));
                            });
                    } else {
                         ui.label("Data Points:");
                         egui::ScrollArea::vertical().show(ui, |ui| {
                             for (i, val) in self.qc_data.iter().enumerate() {
                                 ui.label(format!("Day {}: {:.2}", i+1, val));
                             }
                         });
                    }
                });
            });
        });
    }
}

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([900.0, 600.0]),
        ..Default::default()
    };
    eframe::run_native(
        "QC Data Generator",
        options,
        Box::new(|_cc| Ok(Box::new(QCApp::default()))),
    )
}
