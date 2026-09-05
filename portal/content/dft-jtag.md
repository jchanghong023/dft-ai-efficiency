# JTAG 与 Boundary Scan：从 TAP 到引脚测试

JTAG 常被用作 IEEE 1149.1 的简称。它定义了一组测试访问端口（TAP）和状态机，使测试机可以选择指令、扫描数据寄存器，并在芯片边界观察或驱动数字值。本页先讲协议骨架，再用一个可逐拍操作的教学模型把状态机“走一遍”。

> **范围声明**：页面中的寄存器宽度、引脚值和通过结果都是可重复的教学数据。真实芯片的指令编码、Boundary Cell 数量、BSDL 描述和电气约束必须以芯片厂商资料为准。

## 四根信号与一个复位入口

| 信号 | 作用 |
| --- | --- |
| TCK | 测试时钟；TMS/TDI 通常在上升沿采样，TDO 在规定边沿移出 |
| TMS | 每个 TCK 选择 TAP 状态机的 0/1 分支 |
| TDI | 当前数据寄存器或指令寄存器的串行输入 |
| TDO | 当前扫描寄存器的串行输出；不移位时可能保持高阻 |

TMS 连续保持为 1 至少五个 TCK，协议上可把 TAP 带回 `Test-Logic-Reset`。上电复位、系统复位脚与这个协议复位的具体关系，仍取决于芯片实现。教学模型中点击“复位”直接设为该状态，方便从同一位置开始。

## TAP 的 16 个状态

状态转换只由当前状态和 TMS 决定；TCK 本身不决定走哪条路。`Capture` 把并行值装入寄存器，`Shift` 串行移动，`Update` 把移入的值提交给选中的指令或数据通路。DR 路径与 IR 路径各有一组 Capture/Shift/Update 状态。

```text
Test-Logic-Reset --0--> Run-Test/Idle --1--> Select-DR-Scan
Select-DR-Scan --0--> Capture-DR --0--> Shift-DR --1--> Exit1-DR
Select-DR-Scan --1--> Select-IR-Scan
Select-IR-Scan --0--> Capture-IR --0--> Shift-IR --1--> Exit1-IR
Exit1-{DR,IR} --0--> Pause-{DR,IR} --1--> Exit2-{DR,IR}
Exit1-{DR,IR} --1--> Update-{DR,IR} --0--> Run-Test/Idle
Exit2-{DR,IR} --0--> Shift-{DR,IR}; Exit2-{DR,IR} --1--> Update-{DR,IR}
```

上面的缩写是为了阅读方便；交互实验中的 16 个节点列出各自的 TMS=0/1 分支。你可以分别给出 TMS 与 TDI：TMS 选择下一状态，TDI 只在移位时进入寄存器；TDO 读数是本拍采出的旧位，不是本拍结束后的引脚电平。

每次按钮执行一个完整 TCK 拍：上升沿按沿前状态捕获/移位并迁移状态；如果进入 Update，则在**同一拍随后的下降沿**提交 IR 或 EXTEST 输出。进入 Capture 的那一拍不会提前移位；TMS=1 离开 Shift 的那一拍仍移位一次。这个数字模型不模拟 TDO 电气延迟、高阻驱动或 setup/hold。

逐拍表记录状态、移位位、已选指令的前后值和下降沿提交。选择记录后，TAP 高亮、读数和讲解一起回到该拍；下一次操作从最新状态继续，不改写历史。选择状态节点只查看说明，不直接跳转 TAP。

<!-- lab:jtag -->

## 指令、DR 与三种常见操作

指令寄存器（IR）决定接下来 DR 扫描访问什么。每个器件至少需要一种旁路路径；具体指令编码和长度由实现规定，不能只凭名字推导。

交互为了让两位寄存器可复现，采用明确的教学编码（按本模型的移位顺序）：`EXTEST=00`、`SAMPLE=01`、`BYPASS=11`。这些不是通用硅片编码；“生成 IR 序列并更新”从 TAP 复位执行九拍，并保留当前引脚刺激和故障条件。第 8 拍进入 Update-IR 并在下降沿提交，第 9 拍回到 Idle；每拍的 TMS/TDI 均可回看。未定义编码在本模型中保留当前指令，不代表真实器件必须这样处理。

实验按 TDO 端到 TDI 端列出移位寄存器位序，不把左端当作传统二进制数的最高位。BYPASS 选择一位 DR；EXTEST/SAMPLE 选择两位示例边界寄存器 `[接收值, 驱动值]`。`Capture-DR` 捕获当前引脚示例值，EXTEST 的 `Update-DR` 提交输出驱动；图中的引脚比较是独立的数字连线小实验，开路固定读 0、短路固定读 1 都是明确简化，不模拟真实电气行为。

| 指令 | 教学含义 | 常见用途 |
| --- | --- | --- |
| `BYPASS` | 选中一位旁路寄存器 | 把当前器件快速串入更长的 JTAG 链 |
| `EXTEST` | 让边界单元驱动/采样芯片外部连接 | 板级互连测试、隔离内部逻辑 |
| `SAMPLE` / `PRELOAD` | 观察引脚或预装边界寄存器 | 不改变功能运行的情况下取样、为后续 EXTEST 准备值 |

真实 EXTEST 不只是“写 1 再读 1”：还要考虑输出使能、复位、模拟/电源引脚、时序和板级电气模型。交互中的引脚比较按钮是独立数字实验，不自动执行完整 DR 扫描；未加载 EXTEST 时不生成期望/实际测试结果。提供正常、开路固定读 0、短路固定读 1 三种简化连线；驱动 0 遇到开路固定 0，或驱动 1 遇到短路固定 1 时会显示“未检出”。更改刺激、故障或提交指令/驱动后，旧比较结果失效，必须重新执行。

### 一个最小访问序列

先用 TMS=1 进入 `Select-IR-Scan`，再经过 `Capture-IR` 和 `Shift-IR` 写入指令，最后在 `Update-IR` 提交。随后回到 `Select-DR-Scan`，进入对应的 DR 路径。真实操作还要依据 IR 捕获特征位、指令长度和最低有效位顺序填充数据。

交互没有把这些步骤压缩成一个“完成”按钮，而是保留每个 TMS 决策。这样可以看到 `Pause` 和 `Exit2` 不是装饰状态：长链扫描或调试器暂停时，数据可以暂时停住，再通过 TMS 回到 Shift。

## 与 Boundary Scan 的边界

Boundary Scan Cell 放在核与 PAD 的边界附近，通常由捕获、移位、更新和输出控制组成；它是芯片 I/O 测试结构。JTAG TAP 是访问控制入口，Boundary Scan 是可能被选中的数据寄存器/单元集合。二者有关联，但不能把 TAP 状态机称作一排 Boundary Cell，也不能把核级 Wrapper 当作 PAD 边界。

当两颗器件串接时，一颗器件可选择 `EXTEST` 驱动，另一颗选择 `SAMPLE` 观察，TDI/TDO 把多个器件的寄存器串起来。工程中还要根据 BSDL 的端口、指令和边界寄存器定义生成合法向量。

## 自测问题

1. 为什么 `Shift-DR` 中 TMS=1 后不会直接回到 `Run-Test/Idle`？因为必须经过 `Exit1-DR`，再由下一个 TMS 选择 `Update-DR` 或 `Pause-DR`。
2. 为什么只加载 EXTEST 还不能宣称完成板级测试？还需明确边界单元映射、驱动方向、连接拓扑和可观测响应。
3. 为什么 BYPASS 只有一位并不意味着整条链只有一位？每个器件各自有一位旁路寄存器，串接后长度仍随器件数增加。

## 资料与继续阅读

- [IEEE 1149.1 标准页面](https://standards.ieee.org/ieee/1149.1/)：TAP、状态机和测试逻辑的规范入口。
- [Microchip DS31400 数据手册，第 9.2–9.3 节](https://ww1.microchip.com/downloads/en/DeviceDoc/DS31400datasheet2019-04.pdf)：状态迁移与进入 Update 后下降沿提交的厂商实现说明。这里只核对边沿关系，不采用该器件的三位 IR 编码。
- [Siemens Tessent BoundaryScan](https://www.siemens.com/en-us/products/ic/tessent/test/boundaryscan/)：商业工具对边界扫描流程的说明；不代表本门户实现该工具。
- [Synopsys TestMAX DFT](https://www.synopsys.com/implementation-and-signoff/test-automation/testmax-dft.html)：DFT 设计、检查与测试自动化的产品资料。

阅读资料时请区分标准规定的协议行为、供应商对流程的建议，以及本页为了教学而选定的寄存器数值。
