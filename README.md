# MirBot

热血传奇（Legend of Mir）法师自动挂机Bot，基于截图分析 + 模拟键鼠操作，适用于 996 引擎私服。

**纯视觉方案** — 不读内存、不注入封包，仅通过屏幕截图识别游戏状态并模拟键鼠输入。

## 功能特性

- HP/MP 血条颜色识别，自动喝药回复
- PaddleOCR 怪物名称识别与分类（普通怪/精英/Boss）
- 有限状态机（FSM）驱动的策略引擎
- 两种练级模式：
  - **火法模式** — 巡逻 → 战斗 → 回复 → 拾取 → 死亡处理 → 补给
  - **宠物法师模式** — 召唤宠物 → 拉怪 → 走位 → 回复 → 拾取 → 死亡处理
- 技能冷却管理，智能释放
- PyQt5 图形界面，支持模式选择、启停控制、状态/日志显示
- 后台截图，不干扰前台操作

## 架构

```
main.py → PyQt5 GUI
  └── MirBot (daemon thread)
        每 tick: 截图 → 识别HP/MP+怪物 → 构建上下文 → FSM决策 → 执行动作
```

| 模块 | 职责 |
|---|---|
| `src/capture/` | Win32 后台截图 + 窗口句柄管理 |
| `src/vision/` | HP/MP 条检测（颜色比例）、怪物名 OCR（PaddleOCR） |
| `src/state/` | `PlayerState` / `GameState` 数据模型 |
| `src/strategy/` | FSM 引擎 + 火法/宠物法师策略实现 |
| `src/action/` | 动作字典 → Win32 键鼠调用；技能冷却追踪 |
| `src/utils/` | YAML 配置加载、日志工具 |

## 安装

```bash
# 克隆仓库
git clone https://github.com/goblinjj/mir.git
cd mir

# 安装依赖
pip install -r requirements.txt
```

> **注意**: `pywin32` 仅在 Windows 上安装，macOS/Linux 下自动跳过。

## 使用

```bash
# 启动 GUI
python main.py
```

1. 打开游戏窗口（支持后台截图）
2. 在 GUI 中选择练级模式（火法 / 宠物法师）
3. 点击"开始"

## 配置

编辑 `config.yaml` 自定义参数：

```yaml
game:
  window_title: "Legend of Mir"   # 游戏窗口标题

player:
  hp_threshold: 0.5              # 触发喝药的 HP 比例
  mp_threshold: 0.3              # 触发喝药的 MP 比例

skills:
  attack_key: "1"                # 攻击技能快捷键
  heal_key: "2"                  # 治疗技能快捷键
```

详细配置项参见 `config.yaml` 文件。

## 测试

```bash
pytest                           # 运行全部 39 个测试
pytest tests/test_fire_mage.py   # 运行单个测试文件
pytest -k test_name              # 按名称运行测试
```

测试为纯单元测试，无外部依赖。Win32 调用在非 Windows 平台自动 stub，PaddleOCR 不可用时回退到 `_StubOCR`。

## 技术栈

- **Python 3.10+**
- **OpenCV** — 图像处理
- **PaddleOCR** — 怪物名称文字识别
- **PyQt5** — GUI
- **PyYAML** — 配置管理
- **pywin32** — Windows 键鼠模拟与截图

## 免责声明

本项目仅供学习与研究用途。使用自动化工具可能违反游戏服务条款，请自行承担风险。

## License

MIT
