# Primary Care Laboratory - 质控数据生成工具

![GitHub release (latest by date)](https://img.shields.io/github/v/release/10032/Primary-care-laboratory?style=flat-square)
![GitHub](https://img.shields.io/github/license/10032/Primary-care-laboratory?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/10032/Primary-care-laboratory?style=flat-square)

**Primary Care Laboratory** 是一个用于生成符合现实质控规律的数值的工具。它可以帮助实验室在切换第三方质控软件时，生成逼真的质控数据，并写入质控软件中。

## 功能特性

- **逼真的质控数据生成**：基于现实质控规律，生成符合统计学分布的质控数值。
- **灵活的配置**：支持自定义质控参数，如靶值、可接受范围、室内不精密度、并且不违反质控的Westgard规则。
- **无缝切换第三方软件**：生成的质控数据可直接写入第三方质控软件，确保数据随机性。
- **简单易用**：提供清晰的GUI界面，快速上手。

## 安装

### 通过 GitHub Releases 安装

1. 访问 [GitHub Releases](https://github.com/10032/Primary-care-laboratory/releases/tag/v0.0.01) 页面。
2. 下载最新版本的EXE文件。
3. 直接运行。

## 贡献

欢迎贡献代码和提出建议！

## 界面
![主界面](https://github.com/user-attachments/assets/008d64d5-1939-442c-8c2b-4bf79e44cf90)
![例子](https://github.com/user-attachments/assets/eb22c4a4-b019-4f4e-b56f-45a9ef88c46b)
![数值](https://github.com/user-attachments/assets/8d6d49e6-4d3b-4d86-b810-5fdbdb8b51ac)

## 使用方法
1. 打开软件，并设置对应参数。
2. 点击开始监听，会监听对应快捷键。
3. 按下快捷键，会生成对应的随机数，并调用键盘输入值，默认每一个值后面加入回车键。
4. 自己审核数值，看是否违反检验科质控规则。一般情况下不会触发±1sd，如有问题，请提交错误报告。

## 联系

如有任何问题或建议，请通过 [GitHub Issues]联系我。

## 本程序用python语言
本程序完全由ai编写，详细注释看源代码。

---

**Primary Care Laboratory** - 让质控数据生成更简单、更真实！
