# At-speed 测试：LOC 与 LOS

低速移位只能验证扫描通路是否连通；要检查逻辑在目标频率下能否完成一次转换，还需要一对有时间关系的 **launch / capture** 事件。

<!-- lab:at-speed -->

## 先读懂两个事件

1. **Launch**：把一个已知状态变成另一个状态，转换沿着组合路径传播。
2. **Capture**：在规定时间后采样路径末端。如果路径仍未稳定，采样到的值可能与预期不同。
3. `Tperiod - Tsetup - Tskew` 是本实验用来估算的简化可用窗口；真实签核还要考虑时钟树、OCV、脉宽、库模型和测试约束。

这里的“通过”只表示输入参数满足这个教学不等式；LOS 还要求 `SE` 在 capture 前留出本实验复用的建立裕量：

```text
路径延迟 + 时钟偏斜 ≤ 时钟周期 − 捕获端建立时间

```text
SE 关闭时间 + SE 建立裕量 ≤ capture 时间
```
```

它不是 STA 报告，也不是 ATPG 或硅片测试结果。

## LOC：launch-on-capture

LOC 先用扫描模式装入状态，再关闭 `SE`，由功能时钟序列完成发起和捕获。教学模型把第一个功能沿记作 `t=0`，第二个功能沿记作 `t=T`；这样可以直接观察两个功能沿之间的路径预算。

LOC 的重点是捕获时序相对清晰，但测试时钟必须在正确的模式下产生，并且 `SE` 的切换不能制造额外的竞争。不同实现对初始化和脉冲数有自己的协议，不能只凭这张图推导工具命令。

## LOS：launch-on-shift

LOS 利用最后一个扫描移位沿发起转换，然后在下一个捕获沿采样。`SE` 必须在捕获前关闭；如果 `SE` 过晚、扫描时钟与功能时钟关系不满足约束，示意中的“最后一个移位沿”并不等于可签核的 launch。

LOS 可能减少额外的功能脉冲，但会把扫描移位、模式切换和 at-speed 采样的边界联系起来。实际流程需要由 OCC、测试协议和 ATPG 共同定义，而不是把 LOC 和 LOS 当作两个可以随意互换的标签。

## 怎样使用实验

- 先保持周期为 `10 ns`，把路径延迟从 `6.5 ns` 增加到超过窗口，观察剩余裕量变为负数。
- 切换 LOC / LOS，观察事件序列的差别；本页的延迟预算相同，只改变教学中的 launch 语义。
- 不要把“通过采样窗口”解读为“该路径在芯片上一定通过”。实验没有建模完整时钟树、温度电压工艺角或测试仪器时序。

## 常见误区

| 误区 | 更准确的说法 |
|---|---|
| 把 shift 频率当作 capture 频率 | shift 是装载/移出，capture 可能需要目标功能频率 |
| 看到波形有两个沿就称为 at-speed | 还必须说明沿的来源、相位、脉宽和约束 |
| LOC 与 LOS 只是名字不同 | 两者对 `SE`、launch 沿和测试协议的要求不同 |
| 一条路径通过就代表覆盖率高 | ATPG 仍需针对故障模型生成并验证大量模式 |

## 边界与工程入口

At-speed 测试还会涉及 transition fault、launch/capture 功耗、不可测路径、时钟域交互和 X 值处理。本实验故意只展示一个单路径预算，适合建立直觉，不代替 DFT DRC、STA、故障仿真或 tester pattern sign-off。

公开资料中，Synopsys 将 TestMAX ATPG 描述为面向测试质量和成本的模式生成方案，并强调 power-aware pattern generation；可阅读 [TestMAX ATPG 官方介绍](https://www.synopsys.com/implementation-and-signoff/test-automation/testmax-atpg.html)。有关扫描插入和时钟域处理的工程背景，可阅读 [Siemens Tessent ScanPro 官方介绍](https://www.siemens.com/en-us/products/ic/tessent/test/scanpro/)。

本页的模型、图形和文字为离线教学内容；网页上的数字由 JavaScript 即时计算，不能冒充厂商工具实现。

## 复核清单

在真实流程中，还应分别确认 launch/capture 波形、`SE` 转换窗口、测试时钟约束、路径报告、故障模型和模式仿真；这些证据缺一项，都不能把教学页的“通过”升级成项目签核结论。

不要把动画里的单一周期外推到多周期路径；多周期约束必须有明确的设计意图和工具约束支持。
