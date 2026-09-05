# DFT 概念地图

DFT（Design for Test，可测试性设计）是在芯片中加入便于测试的结构，让内部状态更容易设置、让测试响应更容易读出。它帮助发现制造缺陷，不替代功能验证，也不意味着加入某个结构就能检出全部故障。

## 从两个问题开始

- **可控性**：只靠芯片外部引脚，如何让深处某个寄存器或逻辑节点变成想要的值？
- **可观测性**：内部逻辑产生了错误，如何让这个差异传播到可读出的地方？

[故障与 ATPG](dft-fault-atpg.html)先解释什么条件下能看见故障；[Scan 动画](dft-scan.html)展示“移入状态 → 捕获逻辑响应 → 移出检查”；[EDT 动画](dft-edt.html)继续解释扫描链很多、测试引脚有限时的数据传输。

## 六条学习路线

每个主题有独立页面，可以按顺序阅读，也可以沿工程问题跳转。先认识 DFF、组合逻辑、时钟沿和 0/1/X 的含义，再观察测试模式怎样改变数据或控制通路。

| 路线 | 阅读入口 | 学完要能解释的问题 |
|---|---|---|
| 测试原理 | [故障模型与 ATPG](dft-fault-atpg.html)、[覆盖率](dft-coverage.html)、[Test Point](dft-testpoints.html) | 测什么，怎样观察，测不到是因为什么？ |
| 扫描与时钟 | [Scan 基础](dft-scan.html)、[Scan 工程结构](dft-scan-engineering.html)、[At-speed](dft-at-speed.html)、[OCC 与复位](dft-clock-reset.html) | 数据如何装入、在哪个时钟捕获、链和控制怎样组织？ |
| 压缩与功耗 | [EDT 基础](dft-edt.html)、[编码约束与 X](dft-compression.html)、[测试功耗](dft-test-power.html) | 有限通道、未知值和测试资源怎样影响方案？ |
| 访问与分层 | [JTAG / Boundary Scan](dft-jtag.html)、[IJTAG](dft-ijtag.html)、[Wrapper](dft-wrapper.html) | 如何从芯片外访问引脚、片内仪器与独立核？ |
| 内建自测试 | [MBIST / BIRA / BISR](dft-memory-bist.html)、[LBIST](dft-logic-bist.html) | 谁生成激励、谁比较结果、发现故障后是否能够修复？ |
| 工程落地 | [完整流程与调试](dft-flow.html) | 每阶段交付什么，失败时需要什么证据？ |

## 不要混为一谈

- **DFT 与功能验证**：DFT 为制造测试及其他测试场景提供结构，不替代功能正确性验证。
- **Scan 与 ATPG**：Scan 提供访问能力；ATPG 在故障模型和约束下寻找模式。接好链不等于已经产生高质量模式。
- **EDT 与普通文件压缩**：刺激编码受硬件约束，响应压缩可能混叠，不能把任意响应可逆还原。
- **JTAG、Boundary Scan 与 IJTAG**：TAP 是访问入口；边界扫描关注 I/O 边界；IJTAG 组织片内仪器访问。内部逻辑的 Scan 数据不必全部经过 JTAG。
- **Wrapper 与 Boundary Cell**：核边界和芯片引脚边界的测试目标不同，不能只因都有“边界”就视作同一结构。
- **MBIST、BIRA 与 BISR**：执行测试、分析冗余分配、应用修复是不同职责。测试失败并不保证有足够冗余完成修复。
- **覆盖率与产品质量**：统计基于指定故障集合、分类和口径；一组示例响应相同不能证明芯片没有缺陷。

## 怎么看这里的动画

先单步观察一个时钟沿，再播放完整过程。观察数据、模式信号和比较结果，而不只是沿着箭头看方向。动画中的电路规模、位数、组合逻辑和故障均为说明概念而选取；不是实际 PAD 库、电路生成结果或 Sailor 插入验证。

本知识区以 17 个页面覆盖上述路线，其中 16 个主题提供本地交互实验。实验控制、状态和比较结果由 JavaScript 计算；纯计算验证不等于 HDL 仿真或工艺签核。

每次练习先做三件事：预测改变条件后的结果，单步验证自己的判断，再解释没有观察到差异的原因。关闭 JavaScript 后仍可阅读正文和静态示意，但交互控件不可操作。

## 遇到实际问题，从哪里开始

| 现象 | 推荐入口 |
|---|---|
| Scan 移出数据错位、链长度不符 | [Scan 工程结构](dft-scan-engineering.html) → [工程调试](dft-flow.html) |
| 移位正常，高速捕获失败 | [At-speed](dft-at-speed.html) → [OCC 与复位](dft-clock-reset.html) |
| 压缩结果出现大量 X | [EDT 约束与 X 处理](dft-compression.html) |
| 覆盖率不达标或模式特别多 | [覆盖率口径](dft-coverage.html) → [Test Point](dft-testpoints.html) |
| 找不到片内仪器或核测试入口 | [IJTAG](dft-ijtag.html) → [Wrapper](dft-wrapper.html) |
| 存储器测试失败，需要判断能否修复 | [MBIST / BIRA / BISR](dft-memory-bist.html) |

这些路线用于理解和组织调查，不凭症状直接断言真实项目的根因。实际接口、时序、故障分类和工具选项仍应以目标工程资料为依据。

## 公开参考

主流 DFT 工具提供扫描链、测试压缩、边界扫描及分层测试访问等不同能力，可参阅 [Synopsys TestMAX DFT 官方介绍](https://www.synopsys.com/implementation-and-signoff/test-automation/testmax-dft.html)。EDT 的产品背景参阅 [Siemens Tessent TestKompress 官方介绍](https://www.siemens.com/en-gb/products/ic/tessent/test/testkompress/)。页面正文、图形和动画均随仓库离线提供，参考链接只有主动打开时才联网。
