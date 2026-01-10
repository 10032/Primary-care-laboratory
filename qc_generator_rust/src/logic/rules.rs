use std::collections::HashMap;

pub struct WestgardResult {
    pub rule_name: String,
    pub violated: bool,
}

pub struct RuleConfig {
    pub check_1_3s: bool,
    pub check_2_2s: bool,
    pub check_r_4s: bool,
    pub check_3_1s: bool,
    pub check_4_1s: bool,
    pub check_7t: bool,
    pub check_10x: bool,
}

impl Default for RuleConfig {
    fn default() -> Self {
        Self {
            check_1_3s: true,
            check_2_2s: true,
            check_r_4s: true,
            check_3_1s: true,
            check_4_1s: true,
            check_7t: true,
            check_10x: true,
        }
    }
}

pub fn apply_rules(data: &[f64], target: f64, cv: f64, config: &RuleConfig) -> HashMap<String, bool> {
    let std_dev = target * cv;
    let mut results = HashMap::new();

    // Helper to add result if rule is enabled
    let mut check = |name: &str, enabled: bool, func: fn(&[f64], f64, f64) -> bool| {
        if enabled {
            results.insert(name.to_string(), func(data, target, std_dev));
        } else {
            results.insert(name.to_string(), false);
        }
    };

    check("1-3s", config.check_1_3s, check_1_3s);
    check("2-2s", config.check_2_2s, check_2_2s);
    check("R-4s", config.check_r_4s, check_r_4s);
    check("3-1s", config.check_3_1s, check_3_1s);
    check("4-1s", config.check_4_1s, check_4_1s);
    check("7-t", config.check_7t, check_7_t);
    check("10x", config.check_10x, check_10x);

    results
}

fn check_1_3s(data: &[f64], target: f64, std_dev: f64) -> bool {
    let limit = 3.0 * std_dev;
    data.iter().any(|&x| (x - target).abs() > limit)
}

fn check_2_2s(data: &[f64], target: f64, std_dev: f64) -> bool {
    let limit = 2.0 * std_dev;
    for i in 0..data.len().saturating_sub(1) {
        let v1 = data[i];
        let v2 = data[i+1];
        if (v1 - target).abs() > limit && (v2 - target).abs() > limit {
            // Check if same direction
            if (v1 - target).signum() == (v2 - target).signum() {
                return true;
            }
        }
    }
    false
}

fn check_r_4s(data: &[f64], target: f64, std_dev: f64) -> bool {
    let limit = 2.0 * std_dev;
    for i in 0..data.len().saturating_sub(1) {
        let v1 = data[i];
        let v2 = data[i+1];

        let v1_high = v1 > target + limit;
        let v1_low = v1 < target - limit;
        let v2_high = v2 > target + limit;
        let v2_low = v2 < target - limit;

        if (v1_high && v2_low) || (v1_low && v2_high) {
            return true;
        }
    }
    false
}

fn check_3_1s(data: &[f64], target: f64, std_dev: f64) -> bool {
    let limit = 1.0 * std_dev;
    for i in 0..data.len().saturating_sub(2) {
        let chunk = &data[i..i+3];
        if chunk.iter().all(|&x| (x - target).abs() > limit) {
             // Check if all same direction
             let sign = (chunk[0] - target).signum();
             if chunk.iter().all(|&x| (x - target).signum() == sign) {
                 return true;
             }
        }
    }
    false
}

fn check_4_1s(data: &[f64], target: f64, std_dev: f64) -> bool {
    let limit = 1.0 * std_dev;
    for i in 0..data.len().saturating_sub(3) {
        let chunk = &data[i..i+4];
        if chunk.iter().all(|&x| (x - target).abs() > limit) {
             // Check if all same direction
             let sign = (chunk[0] - target).signum();
             if chunk.iter().all(|&x| (x - target).signum() == sign) {
                 return true;
             }
        }
    }
    false
}

fn check_7_t(data: &[f64], _target: f64, _std_dev: f64) -> bool {
    if data.len() < 7 { return false; }
    for i in 0..data.len().saturating_sub(6) { // 7 points
        let chunk = &data[i..i+7];
        // Check strictly increasing
        let increasing = chunk.windows(2).all(|w| w[0] < w[1]);
        // Check strictly decreasing
        let decreasing = chunk.windows(2).all(|w| w[0] > w[1]);

        if increasing || decreasing {
            return true;
        }
    }
    false
}

fn check_10x(data: &[f64], target: f64, _std_dev: f64) -> bool {
    if data.len() < 10 { return false; }
    for i in 0..data.len().saturating_sub(9) { // 10 points
        let chunk = &data[i..i+10];
        let all_above = chunk.iter().all(|&x| x > target);
        let all_below = chunk.iter().all(|&x| x < target);
        if all_above || all_below {
            return true;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_1_3s() {
        let target = 100.0;
        let std_dev = 2.0;
        // 107 is > 3SD (106)
        let data = vec![100.0, 101.0, 107.0, 100.0];
        assert!(check_1_3s(&data, target, std_dev));

        let data_ok = vec![100.0, 105.0, 95.0]; // Within +/- 3SD
        assert!(!check_1_3s(&data_ok, target, std_dev));
    }

    #[test]
    fn test_2_2s() {
        let target = 100.0;
        let std_dev = 2.0; // 2SD = 104
        // Two consecutive points > 104
        let data = vec![100.0, 105.0, 105.0, 100.0];
        assert!(check_2_2s(&data, target, std_dev));

        // One high, one low (not same side) - should pass 2-2s (but might fail R-4s)
        let data_diff_side = vec![100.0, 105.0, 95.0, 100.0];
        assert!(!check_2_2s(&data_diff_side, target, std_dev));
    }
}
