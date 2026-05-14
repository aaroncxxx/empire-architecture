#!/usr/bin/env python3
"""
量子计算思维模拟器 v2.1
Quantum Computing Thinking Simulator

基于帝国架构的多智能体协作模式，直观演示量子计算核心概念。

灵感来源：九章四号光量子计算原型机

用法:
  python3 quantum_cli.py              # 交互模式
  python3 quantum_cli.py demo         # 运行完整演示
  python3 quantum_cli.py superposition # 叠加态演示
  python3 quantum_cli.py entangle     # 纠缠演示
  python3 quantum_cli.py timeslice    # 时空复用演示
  python3 quantum_cli.py debate       # 量子辩论演示
"""
import sys
import os
import asyncio
import math

# 确保能找到包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from skills.quantum_sim.qubit import Qubit, QubitState, QuantumRegister
from skills.quantum_sim.gates import QuantumGate, CircuitVisualizer
from skills.quantum_sim.entanglement import EntanglementChamber
from skills.quantum_sim.timeslice import TimeSpaceMultiplexer
from skills.quantum_sim.quantum_agent import QuantumAgent, QuantumSwarm
from skills.quantum_sim.qcomm import QCommCodec, compare_encoding, MsgType
from skills.quantum_sim.multi_entangle import GHZState, WState, multi_qubit_entanglement_demo


class QuantumSimulatorCLI:
    """量子计算思维模拟器 CLI"""

    def __init__(self):
        self.swarm = QuantumSwarm()
        self.multiplexer = TimeSpaceMultiplexer()

    def print_banner(self):
        # 响应式：根据终端宽度调整
        width = self._term_width()
        pad = max(2, (width - 56) // 2)
        def line(ch="─"): return ch * (width - 2)
        def center(text): return text.center(width - 2)
        print("╔" + line("═") + "╗")
        print("║" + center("量子计算思维模拟器 v2.1") + "║")
        print("║" + center("Quantum Computing Thinking Simulator") + "║")
        print("║" + line("─") + "║")
        print("║" + center("灵感: 九章四号光量子计算原型机") + "║")
        print("║" + center("框架: 帝国架构 Empire Architecture") + "║")
        print("║" + center("概念: 叠加态 | 纠缠 | 并行计算 | 时空复用") + "║")
        print("╚" + line("═") + "╝")

    def _term_width(self) -> int:
        """获取终端宽度（响应式）"""
        try:
            import shutil
            return shutil.get_terminal_size((80, 24)).columns
        except Exception:
            return 80

    def print_help(self):
        width = self._term_width()
        def line(ch="─"): return ch * (width - 2)
        print(f"""
命令:
  demo              运行完整量子概念演示
  superposition     叠加态实验
  lhs               拉丁超立方 vs 蒙特卡罗对比
  entangle          纠缠实验
  ghz               GHZ/W 多比特纠缠
  qcomm             二进制编码效率对比
  timeslice         时空复用演示（九章四号风格）
  debate            量子辩论实验
  walk              量子行走实验
  bell               Bell 不等式测试
  webgl             WebGL 概率幅可视化
  network           查看 Agent 纠缠网络
  help              显示帮助
  exit / quit       退出
        """)

    # ─── 叠加态演示 ───

    def demo_superposition(self):
        """叠加态演示"""
        print(f"\n{'═' * 60}")
        print("🔮 叠加态实验 (Superposition)")
        print(f"{'─' * 60}")
        print("原理：量子比特可以同时处于 |0⟩ 和 |1⟩ 的叠加态")
        print("经典比特只能是 0 或 1，量子比特可以同时是两者！\n")

        # 1. 创建各种叠加态
        print("1️⃣  创建量子态:")
        states = [
            ("|0⟩ 基态", Qubit.zero("q0")),
            ("|1⟩ 激发态", Qubit.one("q1")),
            ("|+⟩ 叠加态", Qubit.plus("q2")),
            ("|-⟩ 叠加态", Qubit.minus("q3")),
            ("随机量子态", Qubit.random("q4")),
        ]
        for name, state in states:
            print(f"  {name:12s} → {state.description()}")

        # 2. Hadamard 门创建叠加
        print(f"\n2️⃣  Hadamard 门（创建叠加态）:")
        print("  矩阵: H = 1/√2 [[1, 1], [1, -1]]")
        print("  H|0⟩ = |+⟩ = (|0⟩+|1⟩)/√2")
        print("  H|1⟩ = |-⟩ = (|0⟩-|1⟩)/√2\n")

        q = Qubit.zero("q")
        print(f"  初始: {q.description()}")
        q = QuantumGate.hadamard(q)
        print(f"  H 之后: {q.description()}")

        # 3. 测量统计
        print(f"\n3️⃣  测量统计（测量 1000 次 |+⟩）:")
        counts = {0: 0, 1: 0}
        for _ in range(1000):
            q = Qubit.plus("q")
            r = Qubit.measure(q)
            counts[r] += 1

        print(f"  |0⟩: {counts[0]} 次 ({counts[0]/10:.1f}%)")
        print(f"  |1⟩: {counts[1]} 次 ({counts[1]/10:.1f}%)")
        print(f"  理论概率: 50% / 50%")
        print(f"  结论: 叠加态测量概率与振幅的平方成正比！")

        # 4. 量子寄存器
        print(f"\n4️⃣  量子寄存器（4 qubits）:")
        reg = QuantumRegister(4, "q")
        reg.hadamard(0)
        reg.hadamard(1)
        reg.pauli_x(2)
        print(reg.description())

    # ─── 拉丁超立方 vs 蒙特卡罗对比 ───

    def demo_lhs(self):
        """拉丁超立方抽样 vs 蒙特卡罗对比"""
        print(f"\n{'═' * 60}")
        print("📊 拉丁超立方 vs 蒙特卡罗对比 (LHS vs MC)")
        print(f"{'─' * 60}")
        print("LHS: 每层恰好采样一次，收敛速度 O(1/n)")
        print("MC:  随机采样，收敛速度 O(1/√n)\n")

        # 用非对称态来更好展示 LHS 优势
        q = QubitState(alpha=complex(0.8, 0), beta=complex(0.6, 0), label="cmp")
        true_p0 = q.probability_0()
        print(f"量子态: α=0.8, β=0.6  理论 P(0) = {true_p0:.4f}\n")

        sample_sizes = [10, 50, 100, 500, 1000]
        print(f"{'样本数':>8} │ {'LHS误差':>10} │ {'MC误差':>10} │ {'LHS优势':>10}")
        print(f"{'─' * 8}─┼─{'─' * 10}─┼─{'─' * 10}─┼─{'─' * 10}")

        for n in sample_sizes:
            lhs = Qubit.lhs_estimate_probability(q, n)
            mc = Qubit.monte_carlo_measure(q, n)
            err_lhs = lhs["error_p0"]
            err_mc = mc["error_p0"]
            advantage = f"{err_mc / err_lhs:.1f}x" if err_lhs > 1e-10 else "完美"
            print(f"{n:>8} │ {err_lhs:>10.4f} │ {err_mc:>10.4f} │ {advantage:>10}")

        print(f"\n结论: LHS 在相同样本量下误差更小，收敛更快。")
        print(f"      对大量子比特系统的概率估计尤其有效。")

    # ─── WebGL 概率幅可视化 ───

    def demo_webgl(self):
        """WebGL 概率幅可视化（生成 HTML）"""
        print(f"\n{'═' * 60}")
        print("🎨 WebGL 概率幅可视化")
        print(f"{'─' * 60}")

        # 生成 3-qubit 状态的概率分布数据
        import json
        n_qubits = 3
        states = []
        for i in range(2**n_qubits):
            # 用 Hadamard 创建均匀叠加
            q = Qubit.zero(f"q{i}")
            for _ in range(n_qubits):
                q = QuantumGate.hadamard(q)
            states.append({
                "label": f"|{i:0{n_qubits}b}⟩",
                "prob": 1.0 / (2**n_qubits),
                "amp_re": q.alpha.real,
                "amp_im": q.alpha.imag,
            })

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>量子概率幅 WebGL</title>
<style>
body {{ margin:0; background:#0a0a1a; color:#fff; font-family:monospace; }}
#info {{ padding:10px; font-size:14px; }}
canvas {{ display:block; }}
</style></head><body>
<div id="info">量子概率幅 3D 可视化 (WebGL) — {len(states)} 个基态</div>
<canvas id="c"></canvas>
<script>
const DATA = {json.dumps(states)};
const c = document.getElementById('c');
const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
if (!gl) {{ document.body.innerHTML = '<h2>WebGL 不支持</h2>'; }}
else {{
  function resize() {{ c.width=innerWidth; c.height=innerHeight; gl.viewport(0,0,c.width,c.height); }}
  resize(); addEventListener('resize', resize);
  // 简易着色器
  const vs = `attribute vec2 p; attribute float prob; attribute vec3 color;
    varying float vProb; varying vec3 vColor;
    void main() {{ vProb=prob; vColor=color; gl_Position=vec4(p,0,1); gl_PointSize=10.0+prob*40.0; }}`;
  const fs = `varying float vProb; varying vec3 vColor;
    void main() {{ gl_FragColor=vec4(vColor, 0.3+vProb*0.7); }}`;
  function mkShader(t,s) {{ const sh=gl.createShader(t); gl.shaderSource(sh,s); gl.compileShader(sh); return sh; }}
  const prog=gl.createProgram();
  gl.attachShader(prog,mkShader(gl.VERTEX_SHADER,vs));
  gl.attachShader(prog,mkShader(gl.FRAGMENT_SHADER,fs));
  gl.linkProgram(prog); gl.useProgram(prog);
  const n=DATA.length, pos=new Float32Array(n*2), col=new Float32Array(n*3), prb=new Float32Array(n);
  DATA.forEach((d,i) => {{ const a=i/n*Math.PI*2; pos[i*2]=Math.cos(a)*d.prob*3; pos[i*2+1]=Math.sin(a)*d.prob*3;
    col[i*3]=0.2+d.prob*2; col[i*3+1]=0.6; col[i*3+2]=1.0; prb[i]=d.prob; }});
  function bind(attr,data,size) {{ const b=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,b);
    gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW); const loc=gl.getAttribLocation(prog,attr);
    gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc,size,gl.FLOAT,false,0,0); }}
  bind('p',pos,2); bind('color',col,3); bind('prob',prb,1);
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  function draw() {{ gl.clearColor(0.04,0.04,0.1,1); gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.POINTS,0,n); requestAnimationFrame(draw); }}
  draw();
}}</script></body></html>"""

        out_path = os.path.join(os.path.dirname(__file__), "quantum_viz.html")
        with open(out_path, "w") as f:
            f.write(html)
        print(f"  ✅ 已生成: {out_path}")
        print(f"  用浏览器打开即可查看 WebGL 3D 概率幅图")
        print(f"  {len(states)} 个基态，概率越大圆点越大越亮")

    # ─── GHZ/W 多比特纠缠 ───

    def demo_ghz(self):
        """GHZ/W 多比特纠缠演示"""
        print(multi_qubit_entanglement_demo())

    # ─── 二进制编码对比 ───

    def demo_qcomm(self):
        """二进制编码 vs JSON 效率对比"""
        print(f"\n{'═' * 60}")
        print("📡 二进制编码 vs JSON (QComm Protocol)")
        print(f"{'─' * 60}")
        print("JSON: 可读性强，适合 demo\n二进制: 体积小、解析快，适合大规模\n")

        test_states = [
            ("|0⟩", Qubit.zero("t")),
            ("|+⟩", Qubit.plus("t")),
            ("随机态", Qubit.random("t")),
        ]

        print(f"{'状态':>10} │ {'JSON':>8} │ {'Binary':>8} │ {'压缩比':>8} │ {'速度提升':>10}")
        print(f"{'─' * 10}─┼─{'─' * 8}─┼─{'─' * 8}─┼─{'─' * 8}─┼─{'─' * 10}")

        for name, q in test_states:
            result = compare_encoding(q)
            print(f"{name:>10} │ {result['json_bytes']:>6} B │ {result['binary_bytes']:>6} B │ {result['compression_ratio']:>8} │ {result['speedup']:>10}")

        # 编码/解码验证
        print(f"\n编解码验证:")
        q = Qubit.plus("v")
        encoded = QCommCodec.encode_qubit(q)
        decoded = QCommCodec.decode_qubit(encoded)
        print(f"  原始:  α={q.alpha:.4f}, β={q.beta:.4f}")
        print(f"  编码:  {encoded.hex()}")
        print(f"  解码:  α={decoded.alpha:.4f}, β={decoded.beta:.4f}")
        print(f"  精度损失: {abs(q.alpha - decoded.alpha) + abs(q.beta - decoded.beta):.2e}")

        # 门操作编码
        print(f"\n门操作编码:")
        from skills.quantum_sim.qcomm import GateOp
        for gate_name, op in [("H", GateOp.HADAMARD), ("X", GateOp.PAULI_X), ("CNOT", GateOp.CNOT)]:
            encoded = QCommCodec.encode_gate_op(op, 0, 1 if gate_name == "CNOT" else -1)
            decoded = QCommCodec.decode_gate_op(encoded)
            print(f"  {gate_name:5s}: {len(encoded)} 字节 → {decoded}")

    # ─── 纠缠演示 ───

    def demo_entanglement(self):
        """纠缠演示"""
        print(f"\n{'═' * 60}")
        print("🔗 量子纠缠实验 (Entanglement)")
        print(f"{'─' * 60}")
        print("原理：两个粒子形成关联，测量一个会瞬间确定另一个")
        print("爱因斯坦称之为 '鬼魅般的超距作用'\n")

        # 1. 创建 Bell 态
        print("1️⃣  创建 Bell 纠缠对:")
        for bell in ["Φ+", "Φ-", "Ψ+", "Ψ-"]:
            pair = EntanglementChamber.create_bell_pair(bell)
            print(f"  {pair.description()}")

        # 2. 纠缠测量
        print(f"\n2️⃣  纠缠测量（验证关联性）:")
        print("  对 1000 对 Φ+ 纠缠粒子进行测量...\n")

        result = EntanglementChamber.classical_correlation_test(1000, "Φ+")
        print(f"  Bell 态: {result['bell_state']}")
        print(f"  测量对数: {result['total_pairs']}")
        print(f"  关联次数: {result['correlations']}")
        print(f"  关联率: {result['correlation_rate']}")
        print(f"  是纠缠态: {'✅ 是' if result['is_entangled'] else '❌ 否'}")

        # 3. 各 Bell 态对比
        print(f"\n3️⃣  各 Bell 态对比:")
        for bell in ["Φ+", "Φ-", "Ψ+", "Ψ-"]:
            r = EntanglementChamber.classical_correlation_test(500, bell)
            print(f"  {bell}: 关联率={r['correlation_rate']}", end="")
            if bell in ("Ψ+", "Ψ-"):
                print(f" (反向关联)")
            else:
                print(f" (同向关联)")

    # ─── 时空复用演示 ───

    def demo_timeslice(self):
        """时空复用演示 — 九章四号风格"""
        print(f"\n{'═' * 60}")
        print("⏰ 时空复用实验 (Time-Space Multiplexing)")
        print(f"{'─' * 60}")
        print("灵感: 九章四号光量子计算原型机")
        print("核心: 同一个 Agent 在不同时间片承担不同角色\n")

        # 1. 基本时间线
        print("1️⃣  Agent 时间线:")
        mux = TimeSpaceMultiplexer()

        tl = mux.create_timeline("agent_alpha")
        tl.add_slice("翻译官", "翻译技术文档", 50)
        tl.add_slice("编码员", "编写测试用例", 80)
        tl.add_slice("分析师", "分析性能数据", 60)
        print(tl.description())

        # 2. 叠加态角色
        print(f"\n2️⃣  叠加态角色（同时多个身份）:")
        mux2 = TimeSpaceMultiplexer()
        agent = QuantumAgent("agent_beta", "Beta", ["编码", "翻译", "分析"])
        mux2.create_timeline("agent_beta")

        s1 = mux2.assign_superposed_roles(
            "agent_beta",
            ["翻译官", "编码员"],
            "处理多语言代码注释",
            100,
        )
        s2 = mux2.assign_superposed_roles(
            "agent_beta",
            ["分析师", "测试员", "文档员"],
            "全面质量保证",
            100,
        )

        print(mux2.visualize_schedule())

        # 3. 测量坍缩
        print(f"\n3️⃣  测量坍缩（确定角色）:")
        role1 = mux2.measure_role("agent_beta", s1.slice_id)
        role2 = mux2.measure_role("agent_beta", s2.slice_id)
        print(f"  时间片1 测量结果: {role1}")
        print(f"  时间片2 测量结果: {role2}")
        print(f"  叠加态坍缩为确定角色 — 这就是量子测量！")

        # 4. 九章四号类比
        print(f"\n4️⃣  九章四号类比:")
        print("  ┌─────────────────────────────────────────────┐")
        print("  │  九章四号光学网络    ←→    帝国架构时空复用   │")
        print("  ├─────────────────────────────────────────────┤")
        print("  │  光纤通道            ←→    Agent             │")
        print("  │  时间片              ←→    角色分配          │")
        print("  │  光子叠加态          ←→    叠加态角色        │")
        print("  │  探测器测量          ←→    坍缩确定          │")
        print("  │  多模光纤            ←→    并行 Agent        │")
        print("  └─────────────────────────────────────────────┘")

    # ─── 量子辩论 ───

    def demo_debate(self):
        """量子辩论演示"""
        print(f"\n{'═' * 60}")
        print("💬 量子辩论实验 (Quantum Debate)")
        print(f"{'─' * 60}")
        print("两个纠缠 Agent 就同一问题展开辩论")
        print("每轮交换观点，通过纠缠效应逐渐收敛\n")

        # 创建两个 Agent
        agent_a = QuantumAgent("strategist", "谋略参谋", ["战略", "规划"])
        agent_b = QuantumAgent("tech_advisor", "技术参谋", ["技术", "架构"])

        # 纠缠
        pair = agent_a.entangle_with(agent_b)
        print(f"🔗 纠缠建立: {pair.description()}\n")

        # 辩论
        print("议题: '帝国架构应该优先发展量子计算能力吗？'")
        print("立场: 同意 / 反对 / 中立\n")

        debate = agent_a.quantum_debate(
            agent_b,
            "帝国架构应该优先发展量子计算能力吗？",
            rounds=3,
        )

        for log in debate["log"]:
            print(f"  第{log['round']}轮:")
            print(f"    {log['谋略参谋']}")
            print(f"    {log['技术参谋']}")
            print(f"    {'✅ 立场一致' if log['alignment'] else '❌ 立场不同'}")

        print(f"\n最终结果:")
        print(f"  谋略参谋: {debate['final_a']}")
        print(f"  技术参谋: {debate['final_b']}")

    # ─── 量子行走 ───

    def demo_walk(self):
        """量子行走演示"""
        print(f"\n{'═' * 60}")
        print("🚶 量子行走实验 (Quantum Walk)")
        print(f"{'─' * 60}")
        print("经典随机行走：每一步随机左或右")
        print("量子行走：同时探索多条路径\n")

        agent = QuantumAgent("walker", "行者", ["探索"])

        print("10 步量子行走路径:")
        path = agent.quantum_walk(10)
        print(f"  路径: {path}")
        print(f"  最终位置: {path[-1]}")

        # 多次行走统计
        print(f"\n1000 次行走统计:")
        final_positions = []
        for _ in range(1000):
            p = agent.quantum_walk(10)
            final_positions.append(p[-1])

        from collections import Counter
        dist = Counter(final_positions)
        for pos in sorted(dist.keys()):
            count = dist[pos]
            bar = "█" * (count // 20)
            print(f"  位置 {pos:+3d}: {bar} {count}")

    # ─── Bell 不等式 ───

    def demo_bell(self):
        """Bell 不等式测试"""
        print(f"\n{'═' * 60}")
        print("📏 Bell 不等式测试 (Bell's Inequality)")
        print(f"{'─' * 60}")
        print("验证量子力学的非局域性")
        print("经典局域隐变量理论: S ≤ 2")
        print("量子力学预测: S = 2√2 ≈ 2.83\n")

        result = EntanglementChamber.bell_inequality_test(1000)
        print(f"  S 值: {result['S_value']}")
        print(f"  经典上限: {result['classical_limit']}")
        print(f"  量子上限: {result['quantum_limit']}")
        print(f"  违反不等式: {'✅ 是' if result['violates_inequality'] else '❌ 否'}")
        print(f"  解释: {result['interpretation']}")

    # ─── Agent 网络 ───

    def show_network(self):
        """显示 Agent 纠缠网络"""
        # 创建示例网络
        agents = [
            QuantumAgent("chancellor", "丞相", ["协调", "决策"]),
            QuantumAgent("strategist", "谋略参谋", ["战略"]),
            QuantumAgent("tech", "技术参谋", ["技术"]),
            QuantumAgent("writer", "文曹", ["写作"]),
            QuantumAgent("coder", "码曹", ["编码"]),
        ]

        swarm = QuantumSwarm()
        for a in agents:
            swarm.add_agent(a)

        swarm.entangle_agents("chancellor", "strategist")
        swarm.entangle_agents("chancellor", "tech")
        swarm.entangle_agents("strategist", "tech")

        print(swarm.visualize_network())

    # ─── 完整演示 ───

    def run_full_demo(self):
        """运行完整演示"""
        self.print_banner()
        print("🚀 开始完整量子概念演示...\n")

        self.demo_superposition()
        input("\n按 Enter 继续下一个实验...")

        self.demo_entanglement()
        input("\n按 Enter 继续下一个实验...")

        self.demo_timeslice()
        input("\n按 Enter 继续下一个实验...")

        self.demo_debate()
        input("\n按 Enter 继续下一个实验...")

        self.demo_walk()
        input("\n按 Enter 继续下一个实验...")

        self.demo_bell()

        print(f"\n{'═' * 60}")
        print("✅ 全部演示完成！")
        print("核心概念总结:")
        print("  🔮 叠加态: 量子比特可以同时处于多个状态")
        print("  🔗 纠缠: 两个粒子形成超距关联")
        print("  ⏰ 时空复用: 同一 Agent 在不同时刻扮演不同角色")
        print("  📏 测量坍缩: 观测导致叠加态坍缩到确定状态")
        print("  🚶 量子行走: 同时探索多条路径")
        print(f"{'═' * 60}")

    # ─── 交互模式 ───

    def interactive(self):
        """交互模式"""
        self.print_banner()
        self.print_help()

        while True:
            try:
                cmd = input("\n🔮 量子> ").strip()
                if not cmd:
                    continue

                if cmd in ("exit", "quit", "q"):
                    print("退出量子模拟器。")
                    break
                elif cmd == "help":
                    self.print_help()
                elif cmd == "demo":
                    self.run_full_demo()
                elif cmd == "superposition":
                    self.demo_superposition()
                elif cmd == "lhs":
                    self.demo_lhs()
                elif cmd == "entangle":
                    self.demo_entanglement()
                elif cmd == "ghz":
                    self.demo_ghz()
                elif cmd == "qcomm":
                    self.demo_qcomm()
                elif cmd == "timeslice":
                    self.demo_timeslice()
                elif cmd == "debate":
                    self.demo_debate()
                elif cmd == "walk":
                    self.demo_walk()
                elif cmd == "bell":
                    self.demo_bell()
                elif cmd == "webgl":
                    self.demo_webgl()
                elif cmd == "network":
                    self.show_network()
                else:
                    print(f"未知命令: {cmd}，输入 help 查看帮助")

            except KeyboardInterrupt:
                print("\n退出量子模拟器。")
                break
            except EOFError:
                break


async def main():
    cli = QuantumSimulatorCLI()

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "demo":
            cli.run_full_demo()
        elif arg == "superposition":
            cli.demo_superposition()
        elif arg == "lhs":
            cli.demo_lhs()
        elif arg == "entangle":
            cli.demo_entanglement()
        elif arg == "ghz":
            cli.demo_ghz()
        elif arg == "qcomm":
            cli.demo_qcomm()
        elif arg == "timeslice":
            cli.demo_timeslice()
        elif arg == "debate":
            cli.demo_debate()
        elif arg == "walk":
            cli.demo_walk()
        elif arg == "bell":
            cli.demo_bell()
        elif arg == "webgl":
            cli.demo_webgl()
        elif arg == "network":
            cli.show_network()
        else:
            print(f"未知参数: {arg}")
            print("用法: python3 quantum_cli.py [demo|superposition|entangle|timeslice|debate|walk|bell|network]")
    else:
        cli.interactive()


if __name__ == "__main__":
    asyncio.run(main())
