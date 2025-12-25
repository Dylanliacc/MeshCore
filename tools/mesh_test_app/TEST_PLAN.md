# MeshCore 网络测试方案

## 1. 测试目标

验证 Mesh 网络在泛洪模式下的：

- **网络覆盖范围**：各节点之间的可达性
- **丢包率**：统计发送/接收包数量
- **多跳性能**：验证中继转发功能
- **信号质量**：SNR 和 RSSI 分布

---

## 2. 测试环境准备

### 2.1 硬件要求

| 数量 | 设备         | 说明             |
| ---- | ------------ | ---------------- |
| 3-10 | T1000-E 节点 | 烧录最新测试固件 |
| 1    | 电脑         | 运行串口测试工具 |

### 2.2 固件配置

确保所有节点使用相同的参数：

- 频率：869.525 MHz（或 915 MHz）
- SF: 11
- BW: 250 kHz
- CR: 5
- 转发: 启用 (fwd: 1)

### 2.3 节点部署

```
拓扑示例（5 节点）：

     [A] ---- [B] ---- [C]
              |
             [D] ---- [E]

建议距离：
- 邻居节点：100-500m（可视范围）
- 非邻居节点：通过中继可达
```

---

## 3. 测试流程

### 3.1 单节点数据采集

对每个节点重复以下步骤：

```
1. 连接节点串口
2. 进入 CLI 模式（发送 ~~~）
3. 执行 test status 确认节点 ID
4. 等待测试时间（如 30 分钟）
5. 执行 test dump 导出日志
6. 点击"导出"保存 CSV
```

### 3.2 测试时长建议

| 节点数 | 广播间隔 | 建议测试时长 | 预期数据量             |
| ------ | -------- | ------------ | ---------------------- |
| 3      | 10s      | 10 分钟      | 60 × 2 = 120 条/节点   |
| 5      | 10s      | 20 分钟      | 120 × 4 = 480 条/节点  |
| 10     | 10s      | 30 分钟      | 180 × 9 = 1620 条/节点 |

### 3.3 CSV 文件命名

导出的 CSV 文件格式：

```
mesh_test_<接收节点ID>_<时间戳>.csv
```

示例：

- `mesh_test_5061_20251225_103000.csv` - 节点 5061 的接收记录
- `mesh_test_69F5_20251225_103500.csv` - 节点 69F5 的接收记录

---

## 4. 数据格式

### 4.1 CSV 结构

```csv
# MeshCore Network Test Log
# Receiver Device ID: 5061
# Export Time: 2025-12-25 10:30:00
# Total Entries: 342
#
sender_id,seq,tx_time,rx_time,delay_sec,snr,rssi,path_len
69F5,0,1735093800,1735093801,1,47,-85,0
69F5,1,1735093810,1735093811,1,52,-82,0
A1B2,0,1735093805,1735093807,2,35,-90,1
...
```

### 4.2 字段说明

| 字段      | 说明                     |
| --------- | ------------------------ |
| sender_id | 发送节点 ID (2字节 hex)  |
| seq       | 发送序列号               |
| tx_time   | 发送时间戳 (UNIX 秒)     |
| rx_time   | 接收时间戳 (UNIX 秒)     |
| delay_sec | 延迟 (rx_time - tx_time) |
| snr       | 信噪比 × 4               |
| rssi      | 信号强度 (dBm)           |
| path_len  | 经过的跳数 (0=直接收到)  |

---

## 5. 丢包率统计方案

### 5.1 统计公式

```
丢包率 = 1 - (实际收到包数 / 理论应收包数) × 100%
```

对于 N 个节点，每节点发送 S 个包：

- **理论应收包数** = S × (N - 1)（每个节点应收到其他所有节点的包）
- **实际收到包数** = CSV 中的总行数

### 5.2 Python 统计脚本

创建 `analyze_logs.py`：

```python
#!/usr/bin/env python3
"""
MeshCore 丢包率统计脚本
使用方法: python analyze_logs.py mesh_test_*.csv
"""

import sys
import csv
from collections import defaultdict

def analyze_csv(filename):
    """分析单个 CSV 文件"""
    receiver_id = None
    entries = []

    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('# Receiver Device ID:'):
                receiver_id = line.split(':')[1].strip()
            elif not line.startswith('#') and line.strip():
                parts = line.strip().split(',')
                if len(parts) >= 7 and parts[0] != 'sender_id':
                    entries.append({
                        'sender': parts[0],
                        'seq': int(parts[1]),
                        'path_len': int(parts[7]) if len(parts) > 7 else 0
                    })

    return receiver_id, entries

def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_logs.py mesh_test_*.csv")
        sys.exit(1)

    all_data = {}  # {receiver_id: entries}
    all_senders = set()

    # 读取所有 CSV 文件
    for filename in sys.argv[1:]:
        receiver_id, entries = analyze_csv(filename)
        if receiver_id:
            all_data[receiver_id] = entries
            for e in entries:
                all_senders.add(e['sender'])

    print("=" * 60)
    print("MeshCore 网络测试统计报告")
    print("=" * 60)
    print(f"\n检测到 {len(all_data)} 个接收节点: {', '.join(all_data.keys())}")
    print(f"检测到 {len(all_senders)} 个发送节点: {', '.join(all_senders)}")

    # 统计每个发送者的最大序列号
    max_seq = defaultdict(int)
    for entries in all_data.values():
        for e in entries:
            max_seq[e['sender']] = max(max_seq[e['sender']], e['seq'])

    print("\n发送统计:")
    for sender, seq in sorted(max_seq.items()):
        print(f"  {sender}: 发送了 {seq + 1} 个包")

    # 计算每对节点的丢包率
    print("\n节点对丢包率:")
    print("-" * 50)
    print(f"{'发送者':<10} {'接收者':<10} {'应收':<8} {'实收':<8} {'丢包率':<10}")
    print("-" * 50)

    total_expected = 0
    total_received = 0

    for receiver_id, entries in sorted(all_data.items()):
        sender_counts = defaultdict(set)
        for e in entries:
            sender_counts[e['sender']].add(e['seq'])

        for sender in sorted(all_senders):
            if sender == receiver_id:
                continue  # 跳过自己发给自己

            expected = max_seq.get(sender, 0) + 1
            received = len(sender_counts.get(sender, set()))
            loss_rate = (1 - received / expected) * 100 if expected > 0 else 0

            total_expected += expected
            total_received += received

            print(f"{sender:<10} {receiver_id:<10} {expected:<8} {received:<8} {loss_rate:>6.1f}%")

    print("-" * 50)
    overall_loss = (1 - total_received / total_expected) * 100 if total_expected > 0 else 0
    print(f"{'总计':<10} {'':<10} {total_expected:<8} {total_received:<8} {overall_loss:>6.1f}%")
    print("=" * 60)

    # 路径长度分布
    print("\n路径长度分布:")
    path_dist = defaultdict(int)
    for entries in all_data.values():
        for e in entries:
            path_dist[e['path_len']] += 1

    for hops in sorted(path_dist.keys()):
        count = path_dist[hops]
        pct = count / sum(path_dist.values()) * 100
        bar = '█' * int(pct / 2)
        print(f"  {hops} 跳: {count:>5} ({pct:>5.1f}%) {bar}")

if __name__ == '__main__':
    main()
```

### 5.3 使用示例

```bash
# 收集所有节点的 CSV 文件到同一目录
# 然后运行统计脚本

python analyze_logs.py mesh_test_*.csv
```

### 5.4 输出示例

```
============================================================
MeshCore 网络测试统计报告
============================================================

检测到 3 个接收节点: 5061, 69F5, A1B2
检测到 3 个发送节点: 5061, 69F5, A1B2

发送统计:
  5061: 发送了 120 个包
  69F5: 发送了 118 个包
  A1B2: 发送了 115 个包

节点对丢包率:
--------------------------------------------------
发送者     接收者     应收     实收     丢包率
--------------------------------------------------
5061       69F5       120      118       1.7%
5061       A1B2       120      115       4.2%
69F5       5061       118      116       1.7%
69F5       A1B2       118      110       6.8%
A1B2       5061       115      108       6.1%
A1B2       69F5       115      105       8.7%
--------------------------------------------------
总计                  706      672       4.8%
============================================================

路径长度分布:
  0 跳:   450 ( 67.0%) █████████████████████████████████
  1 跳:   180 ( 26.8%) █████████████
  2 跳:    42 (  6.3%) ███
```

---

## 6. 结果分析

### 6.1 丢包率评估标准

| 丢包率 | 评级 | 说明                   |
| ------ | ---- | ---------------------- |
| < 1%   | 优秀 | 网络非常稳定           |
| 1-5%   | 良好 | 正常工作范围           |
| 5-10%  | 一般 | 可能存在干扰或距离问题 |
| > 10%  | 差   | 需要检查节点位置或配置 |

### 6.2 常见问题排查

| 现象                   | 可能原因         | 解决方案               |
| ---------------------- | ---------------- | ---------------------- |
| 某节点完全收不到包     | 距离太远或障碍物 | 增加中继节点           |
| path_len 始终为 0      | 节点间直接可达   | 正常                   |
| 丢包率高且 path_len 大 | 多跳衰减         | 减少跳数或增加节点密度 |
| SNR 很低               | 信号弱           | 调整天线或位置         |

---

## 7. 快速测试清单

- [ ] 烧录最新固件到所有节点
- [ ] 确认所有节点无线参数一致
- [ ] 部署节点并记录位置
- [ ] 连接第一个节点，进入 CLI 模式
- [ ] 执行 `test status` 记录设备 ID
- [ ] 等待测试时间
- [ ] 执行 `test dump` + 导出 CSV
- [ ] 重复其他节点
- [ ] 运行统计脚本分析
