# tiny_base 默认原始电路规范

## 结构

`TOP → CORE_A → CORE_B`。CORE_A 包含输入寄存器、少量组合逻辑及输出寄存器；CORE_B 使用普通 DFF → 组合逻辑 → DFF。单路数据接口起步，不加入存储器或额外时钟域。

## 顶层接口

| 信号 | 方向 | 初始含义 |
|---|---|---|
| TCK、TMS、TDI、TRST_N | Input | JTAG 预留输入，不实现 TAP |
| TDO | Output | JTAG 输出预留；选用明确说明的确定值，不冒充 JTAG 响应 |
| scan_clk | Input | 原始功能时钟，供 CORE_A / CORE_B 使用 |
| dft_lgc_rst_n | Input | 原始低有效功能复位；按目标项目规范选择同步/异步并记录 |
| scan_in | Input | 原始功能数据输入，后续可复用为 Scan/EDT 输入 |
| dft_se | Input | 原始功能控制输入，尚非 Scan Enable |
| dft_edt_update | Input | 原始功能控制输入，尚非 EDT Update |
| dft_se_occ | Input | OCC 控制预留，不加入 OCC |
| scan_out | Output | 原始功能输出，尚非扫描链输出 |

TOP 输入经真实 Input PAD 进入内核，输出经真实 Output PAD 引出；具体单元、PAD/core 端口名、电源、使能和模型必须来自指定库。未提供库时核心逻辑可以生成，但 PAD 接入仍未完成。保留信号可确定连接或说明暂不使用，避免未驱动输出和未经说明的锁存器。

## 验证

检查顶层接口、三级层级、普通寄存器、复位行为、功能输入到输出的预期延迟，以及设计未包含未要求的 DFT 结构。测试平台使用明确参考行为，不仅断言仿真退出码；文件清单包含生成模块及真实所需库模型，不提交库本体到公共仓库。

## 仅在用户要求时扩展

基础 Scan → EDT → JTAG / Boundary Scan → IJTAG → OCC / 时钟结构 → 必要时 Memory / MBIST。每次仅增加当前目标结构，保留输入、配置、已确认工具运行入口及真实结果。

JTAG 通过 TAP 指令选择当前数据寄存器，不把 BSCAN、IJTAG 和 BYPASS 固定全串联。内部 ATPG 数据默认走 Scan/EDT 通路；需要更多 channel 时依据真实配置增加接口和对应 PAD。
