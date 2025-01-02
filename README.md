# Primary Care Laboratory - 质控数据生成工具

![GitHub release (latest by date)](https://img.shields.io/github/v/release/10032/Primary-care-laboratory?style=flat-square)
![GitHub](https://img.shields.io/github/license/10032/Primary-care-laboratory?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/10032/Primary-care-laboratory?style=flat-square)

**Primary Care Laboratory** 是一个用于生成符合现实质控规律的数值的工具。它可以帮助实验室在切换第三方质控软件时，生成逼真的质控数据，以便写入到新的系统中。

## 功能特性

- **逼真的质控数据生成**：基于现实质控规律，生成符合统计学分布的质控数值。
- **灵活的配置**：支持自定义质控参数，如均值、标准差、质控规则等。
- **无缝切换第三方软件**：生成的质控数据可直接用于第三方质控软件，确保数据一致性。
- **简单易用**：提供清晰的命令行界面和配置文件，快速上手。

## 安装

### 通过 GitHub Releases 安装

1. 访问 [GitHub Releases](https://github.com/10032/Primary-care-laboratory/releases/tag/v0.0.01) 页面。
2. 下载最新版本的压缩包。
3. 解压缩到您的本地目录。

### 通过源码构建

1. 克隆本仓库：
   ```bash
   git clone https://github.com/10032/Primary-care-laboratory.git
   ```
2. 进入项目目录：
   ```bash
   cd Primary-care-laboratory
   ```
3. 构建项目：
   ```bash
   mvn clean install
   ```

## 使用说明

### 配置文件

在 `config` 目录下，您可以找到 `qc_config.json` 文件，用于配置质控参数。以下是一个示例配置：

```json
{
  "mean": 100,
  "stdDev": 5,
  "controlRules": ["13s", "22s"],
  "numSamples": 30
}
```

### 命令行使用

1. 运行生成工具：
   ```bash
   java -jar primary-care-laboratory.jar -c config/qc_config.json
   ```
2. 生成的质控数据将保存在 `output/qc_data.csv` 文件中。

### 集成到第三方软件

将生成的 `qc_data.csv` 文件导入到您的第三方质控软件中，确保数据的一致性和准确性。

## 贡献

欢迎贡献代码和提出建议！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与项目。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 联系

如有任何问题或建议，请通过 [GitHub Issues](https://github.com/10032/Primary-care-laboratory/issues) 联系我们。

---

**Primary Care Laboratory** - 让质控数据生成更简单、更真实！
