use rand::prelude::*;
use rand_distr::{Normal, LogNormal, Distribution};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum DistributionType {
    Normal,
    LogNormal,
}

pub struct QCParams {
    pub target: f64,
    pub cv: f64, // e.g., 0.02 for 2%
    pub bias: f64,
    pub drift_rate: f64,
    pub num_days: usize,
    pub dist_type: DistributionType,
}

pub fn generate_data(params: &QCParams) -> Vec<f64> {
    let mut rng = rand::thread_rng();
    let mut data = Vec::with_capacity(params.num_days);

    // Initial mean starts with bias
    let mut current_mean = params.target + params.bias;
    let std_dev = params.target * params.cv;

    for _ in 0..params.num_days {
        let value = match params.dist_type {
            DistributionType::Normal => {
                let normal = Normal::new(current_mean, std_dev).unwrap();
                normal.sample(&mut rng)
            },
            DistributionType::LogNormal => {
                // For LogNormal, parameters are mu and sigma of the underlying normal distribution.
                // We need to convert our desired mean and std_dev to mu and sigma.
                // Formula:
                // sigma^2 = ln(1 + (var / mean^2))
                // mu = ln(mean) - 0.5 * sigma^2

                // Note: The Python code used a simplified approximation:
                // log_mean = np.log(current_mean) - 0.5 * np.log(1 + (std_dev/current_mean)**2)
                // log_std_dev = np.sqrt(np.log(1 + (std_dev/current_mean)**2))

                let var = std_dev * std_dev;
                let mean_sq = current_mean * current_mean;

                let sigma_sq = (1.0 + (var / mean_sq)).ln();
                let sigma = sigma_sq.sqrt();
                let mu = current_mean.ln() - 0.5 * sigma_sq;

                // Handle potential errors if sigma is invalid (though unlikely with positive mean/std_dev)
                match LogNormal::new(mu, sigma) {
                    Ok(dist) => dist.sample(&mut rng),
                    Err(_) => current_mean, // Fallback
                }
            }
        };

        data.push(value);
        current_mean += params.drift_rate;
    }

    data
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_normal() {
        let params = QCParams {
            target: 100.0,
            cv: 0.02,
            bias: 0.0,
            drift_rate: 0.0,
            num_days: 1000,
            dist_type: DistributionType::Normal,
        };

        let data = generate_data(&params);
        let mean: f64 = data.iter().sum::<f64>() / data.len() as f64;
        let variance: f64 = data.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / data.len() as f64;
        let std_dev = variance.sqrt();

        // Check if mean is close to 100
        assert!((mean - 100.0).abs() < 1.0, "Mean should be close to 100, got {}", mean);
        // Check if CV is close to 2% (SD approx 2.0)
        assert!((std_dev - 2.0).abs() < 0.2, "StdDev should be close to 2.0, got {}", std_dev);
    }

    #[test]
    fn test_drift() {
        let params = QCParams {
            target: 100.0,
            cv: 0.0, // No random variation to test pure drift
            bias: 0.0,
            drift_rate: 1.0,
            num_days: 5,
            dist_type: DistributionType::Normal,
        };
        // With CV=0, Normal::new might panic or return mean.
        // Rust's rand_distr Normal::new requires std_dev > 0.
        // Let's use a tiny CV.
        let params = QCParams {
            target: 100.0,
            cv: 0.000001,
            bias: 0.0,
            drift_rate: 1.0,
            num_days: 5,
            dist_type: DistributionType::Normal,
        };

        let data = generate_data(&params);
        // Expected: approx 100, 101, 102, 103, 104
        assert!((data[0] - 100.0).abs() < 0.01);
        assert!((data[4] - 104.0).abs() < 0.01);
    }
}
