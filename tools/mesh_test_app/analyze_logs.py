#!/usr/bin/env python3
"""
MeshCore 丢包率统计脚本
使用方法: python analyze_logs.py mesh_test_*.csv
"""

import csv
import sys
from collections import defaultdict


def analyze_csv(filename):
    """分析单个 CSV 文件"""
    receiver_id = None
    entries = []

    with open(filename, "r") as f:
        for line in f:
            if line.startswith("# Receiver Device ID:"):
                receiver_id = line.split(":")[1].strip()
            elif not line.startswith("#") and line.strip():
                parts = line.strip().split(",")
                if len(parts) >= 7 and parts[0] != "sender_id":
                    entries.append(
                        {
                            "sender": parts[0],
                            "seq": int(parts[1]),
                            "path_len": int(parts[7]) if len(parts) > 7 else 0,
                            "snr": int(parts[5]) if len(parts) > 5 else 0,
                            "rssi": int(parts[6]) if len(parts) > 6 else 0,
                        }
                    )

    return receiver_id, entries


def main():
    if len(sys.argv) < 2:
        print("用法: python analyze_logs.py mesh_test_*.csv")
        print("\n示例:")
        print("  python analyze_logs.py mesh_test_5061_*.csv mesh_test_69F5_*.csv")
        sys.exit(1)

    all_data = {}  # {receiver_id: entries}
    all_senders = set()

    # 读取所有 CSV 文件
    for filename in sys.argv[1:]:
        try:
            receiver_id, entries = analyze_csv(filename)
            if receiver_id:
                all_data[receiver_id] = entries
                for e in entries:
                    all_senders.add(e["sender"])
                print(f"已加载: {filename} (接收者: {receiver_id}, {len(entries)} 条)")
        except Exception as e:
            print(f"警告: 无法读取 {filename}: {e}")

    if not all_data:
        print("\n错误: 没有有效的数据文件")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("MeshCore 网络测试统计报告")
    print("=" * 60)
    print(f"\n检测到 {len(all_data)} 个接收节点: {', '.join(sorted(all_data.keys()))}")
    print(f"检测到 {len(all_senders)} 个发送节点: {', '.join(sorted(all_senders))}")

    # 统计每个发送者的最大序列号
    max_seq = defaultdict(int)
    for entries in all_data.values():
        for e in entries:
            max_seq[e["sender"]] = max(max_seq[e["sender"]], e["seq"])

    print("\n发送统计:")
    for sender, seq in sorted(max_seq.items()):
        print(f"  {sender}: 发送了 {seq + 1} 个包")

    # 计算每对节点的丢包率
    print("\n节点对丢包率:")
    print("-" * 60)
    print(f"{'发送者':<10} {'接收者':<10} {'应收':<8} {'实收':<8} {'丢包率':<10} {'平均SNR':<10}")
    print("-" * 60)

    total_expected = 0
    total_received = 0

    for receiver_id, entries in sorted(all_data.items()):
        sender_data = defaultdict(lambda: {"seqs": set(), "snr_sum": 0, "count": 0})
        for e in entries:
            sender_data[e["sender"]]["seqs"].add(e["seq"])
            sender_data[e["sender"]]["snr_sum"] += e["snr"]
            sender_data[e["sender"]]["count"] += 1

        for sender in sorted(all_senders):
            if sender == receiver_id:
                continue  # 跳过自己发给自己

            expected = max_seq.get(sender, 0) + 1
            received = len(sender_data.get(sender, {}).get("seqs", set()))
            loss_rate = (1 - received / expected) * 100 if expected > 0 else 0
            avg_snr = (
                sender_data[sender]["snr_sum"] / sender_data[sender]["count"] / 4
                if sender_data[sender]["count"] > 0
                else 0
            )

            total_expected += expected
            total_received += received

            print(
                f"{sender:<10} {receiver_id:<10} {expected:<8} {received:<8} {loss_rate:>6.1f}%    {avg_snr:>6.1f} dB"
            )

    print("-" * 60)
    overall_loss = (
        (1 - total_received / total_expected) * 100 if total_expected > 0 else 0
    )
    print(
        f"{'总计':<10} {'':<10} {total_expected:<8} {total_received:<8} {overall_loss:>6.1f}%"
    )
    print("=" * 60)

    # 路径长度分布
    print("\n路径长度分布 (跳数):")
    path_dist = defaultdict(int)
    for entries in all_data.values():
        for e in entries:
            path_dist[e["path_len"]] += 1

    total_packets = sum(path_dist.values())
    for hops in sorted(path_dist.keys()):
        count = path_dist[hops]
        pct = count / total_packets * 100 if total_packets > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {hops} 跳: {count:>5} ({pct:>5.1f}%) {bar}")

    # RSSI 统计
    print("\n信号强度 (RSSI) 分布:")
    rssi_ranges = [(-70, "优秀"), (-85, "良好"), (-100, "一般"), (-120, "差")]
    rssi_dist = defaultdict(int)

    for entries in all_data.values():
        for e in entries:
            for threshold, label in rssi_ranges:
                if e["rssi"] >= threshold:
                    rssi_dist[label] += 1
                    break

    for label in ["优秀", "良好", "一般", "差"]:
        count = rssi_dist.get(label, 0)
        pct = count / total_packets * 100 if total_packets > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {label}: {count:>5} ({pct:>5.1f}%) {bar}")

    # 评估结论
    print("\n" + "=" * 60)
    print("测试结论:")
    if overall_loss < 1:
        print("  ✅ 网络质量: 优秀 (丢包率 < 1%)")
    elif overall_loss < 5:
        print("  ✅ 网络质量: 良好 (丢包率 1-5%)")
    elif overall_loss < 10:
        print("  ⚠️ 网络质量: 一般 (丢包率 5-10%)")
    else:
        print("  ❌ 网络质量: 差 (丢包率 > 10%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
