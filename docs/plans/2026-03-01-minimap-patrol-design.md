# 小地图视觉导航巡逻系统设计

## 问题

当前巡逻只有8方向轮换+坐标卡住检测，没有地形感知。角色走到角落/墙边后持续撞墙，轮换所有方向都走不通。

## 方案：小地图视觉导航

利用右上角固定小地图的视觉信息：
- **白色点** = 角色当前位置
- **纯黑区域** = 地图边界（不可移动）
- **灰棕色区域** = 可走路径

用户在GUI上点击小地图设置巡逻路径点，机器人每帧检测白点位置并向下一个路径点方向移动。

## 模块设计

### 1. 小地图分析模块 (`src/vision/minimap.py`)

**白点检测**：
- 从截屏中截取小地图区域（config配置）
- 亮度阈值（>240, RGB均高）找白色亮点
- 取连通区域质心 → 角色在小地图上的像素坐标 `(mx, my)`

**边界检测**：
- 纯黑像素（RGB均 < 15）= 不可走
- 生成二值 walkability mask
- 用于验证巡逻点合法性

**接口**：
```python
class MinimapAnalyzer:
    def detect_player_position(self, frame) -> Optional[Tuple[int, int]]
    def is_walkable(self, frame, x, y) -> bool
    def get_walkability_mask(self, frame) -> np.ndarray
```

### 2. GUI巡逻路径编辑器

在GUI中新增巡逻路径设置面板：
- 显示小地图截图（点击刷新按钮更新）
- 鼠标点击添加巡逻点，显示编号和连线
- 支持：添加、删除（右键）、清空
- 黑色区域点击时提示不可走
- 路径点保存到 config.yaml

### 3. 导航逻辑（改造 `PatrolState`）

**每帧逻辑**：
1. 检测白点位置 → 当前角色 `(cx, cy)`
2. 取当前目标巡逻点 `(tx, ty)`
3. `atan2(ty-cy, tx-cx)` → 8方向
4. 向该方向右键移动
5. `distance < arrival_radius` → 切到下一个点
6. 最后一个点 → 回到第一个点循环

**传送卷轴恢复**：
- 检测白点位置突变（距离 > 跳变阈值）
- 找距离最近的巡逻点作为新目标
- 从最近点继续巡逻

**卡住处理**：
- 保留现有stuck检测
- stuck时尝试随机偏移方向（目标方向±45°）
- 连续stuck多次则跳过当前点

### 4. 配置

```yaml
minimap:
  region: [1230, 30, 160, 180]  # 小地图截取区域 [x, y, w, h]
  white_threshold: 240           # 白点亮度阈值
  black_threshold: 15            # 黑色边界阈值
  arrival_radius: 5              # 到达判定半径(小地图像素)

patrol:
  waypoints: []                  # GUI设置的巡逻点 [[x,y], ...]
```

## 数据流

```
截屏 → 截取小地图区域 → 白点检测 → 角色位置(mx, my)
                                          ↓
GUI巡逻点列表 → 当前目标点(tx, ty) ← 到达判定/传送跳变
                      ↓
              计算方向角 → 8方向 → 右键移动
```
