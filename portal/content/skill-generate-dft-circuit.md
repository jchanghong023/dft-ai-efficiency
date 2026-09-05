# generate-dft-circuit

## 用途

在用户指定工程生成 DFT 插入前的最小电路，默认遵循 tiny_base 规范；效率仓库本身不交付电路工程。

## 适用与不适用

适用于构造层级清晰的小型 RTL 输入、为后续 Sailor 流程准备基础电路与可重复验证。不适用于自动完成全套 DFT 插入、没有资料时猜测工艺库或 Sailor 命令，也不会擅自扩展成大规模 SoC。

## 如何调用

Agent 可自动选择：**是**。必须手动调用：**否**。也可显式调用：

```text
/skill:generate-dft-circuit 在 /path/to/project 生成 tiny_base 基础 RTL；按该工程的 PAD 库资料连接真实 PAD，提供文件清单和仿真入口
```

## 输入

目标工程及输出目录、用户的接口或层级要求、真实 PAD 单元与端口资料、仿真模型、HDL 工具和工具版本。用户明确规格优先于默认值。

## 默认电路

层级为 `TOP → CORE_A → CORE_B`，包含少量普通 DFF 与组合逻辑。默认接口：输入 `TCK`、`TMS`、`TDI`、`TRST_N`、`scan_clk`、`dft_lgc_rst_n`、`scan_in`、`dft_se`、`dft_edt_update`、`dft_se_occ`，输出 `TDO`、`scan_out`。

JTAG 信号只预留；`scan_clk` 是功能时钟，`scan_in/scan_out` 是功能数据通路。初始不加入 Scan Chain、EDT、Wrapper、IJTAG、TAP 或 Boundary Cell。接口名不代表已经实现相应协议。

## 输出

按需求生成 RTL、文件清单、测试平台和 Python 3.11+ 验证入口；报告已执行的层级/语法/仿真验证和未验证项。实际 PAD 单元及端口必须来自目标库。

## 缺少 PAD 库时

列出缺少的单元、端口、电源/使能和模型信息。与工艺无关的核心 RTL 可以完成，但逻辑版须标明“未接真实 PAD”；不得虚构工艺单元或用假模型声称完成 PAD 集成。

## 后续扩展

只有用户明确要求时增加 Scan、EDT、JTAG/Boundary Scan、IJTAG、OCC，必要时再增加 Memory/MBIST。每阶段读取真实工具资料并保留输入与结果；资料或环境缺失时不能宣称插入成功。

参阅[团队开发流程](team.html)。

## Skill 原始文件

以下内容在构建时直接读取公共源文件，保留配置头与完整正文。

<!-- team-source:omp/skills/generate-dft-circuit/SKILL.md -->

### 引用的默认电路规范

<!-- team-source:omp/skills/generate-dft-circuit/references/tiny-base.md -->
