#!/usr/bin/env python3
"""
MeshCore Network Test Log Analyzer

用法:
  1. 从每台T1000-E获取测试日志: 串口连接，输入 "test dump"
  2. 将输出保存到文件 (如 device_001.log, device_002.log, ...)
  3. 运行此脚本: python3 analyze_test_log.py device_*.log
"""

import csv
import os
import sys
from collections import defaultdict


def parse_log_file(filepath):
    """解析单个设备的日志文件"""
    device_id = None
    seq_num = 0
    log_count = 0
    entries = []
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('TESTLOG '):
                # Header: TESTLOG <device_id> <seq_num> <log_count>
                parts = line.split()
                if len(parts) >= 4:
                    device_id = parts[1]
                    seq_num = int(parts[2])
                    log_count = int(parts[3])
            elif line.startswith('TESTLOG_END'):
                break
            elif ',' in line and len(line) > 20:
                # Entry: <device_id>,<seq>,<timestamp>,<snr>,<rssi>,<path_len>
                parts = line.split(',')
                if len(parts) >= 6:
                    entries.append({
                        'sender_id': parts[0],
                        'seq': int(parts[1]),
                        'timestamp': int(parts[2]),
                        'snr': int(parts[3]) / 4.0,  # SNR * 4 stored
                        'rssi': int(parts[4]),
                        'path_len': int(parts[5])
                    })
    
    return {
        'device_id': device_id,
        'seq_num': seq_num,  # 本设备发送的包数量
        'log_count': log_count,
        'entries': entries,
        'source_file': filepath
    }

def analyze_network(logs):
    """分析网络统计"""
    print("\n" + "="*60)
    print("MeshCore 网络测试分析报告")
    print("="*60)
    
    # 收集所有设备ID
    all_devices = set()
    for log in logs:
        if log['device_id']:
            all_devices.add(log['device_id'])
        for entry in log['entries']:
            all_devices.add(entry['sender_id'])
    
    print(f"\n检测到设备数量: {len(all_devices)}")
    print(f"日志文件数量: {len(logs)}")
    
    # 发送统计
    print("\n--- 发送统计 ---")
    total_sent = {}
    for log in logs:
        if log['device_id']:
            total_sent[log['device_id']] = log['seq_num']
            print(f"  {log['device_id']}: 发送 {log['seq_num']} 包")
    
    # 接收矩阵
    print("\n--- 接收矩阵 (发送者 -> 接收者: 收到包数) ---")
    recv_matrix = defaultdict(lambda: defaultdict(int))
    
    for log in logs:
        receiver = log['device_id']
        if not receiver:
            continue
        for entry in log['entries']:
            sender = entry['sender_id']
            recv_matrix[sender][receiver] += 1
    
    # 计算丢包率
    print("\n--- 丢包率分析 ---")
    total_expected = 0
    total_received = 0
    
    for sender in sorted(all_devices):
        sent = total_sent.get(sender, 0)
        if sent == 0:
            continue
        
        for receiver in sorted(all_devices):
            if sender == receiver:
                continue
            expected = sent
            received = recv_matrix[sender].get(receiver, 0)
            total_expected += expected
            total_received += received
            
            loss_rate = (1 - received/expected) * 100 if expected > 0 else 0
            if loss_rate > 0:
                print(f"  {sender[:8]} -> {receiver[:8]}: "
                      f"{received}/{expected} ({loss_rate:.1f}% 丢失)")
    
    overall_loss = (1 - total_received/total_expected) * 100 if total_expected > 0 else 0
    print(f"\n总体丢包率: {overall_loss:.2f}%")
    print(f"  总期望接收: {total_expected}")
    print(f"  实际接收: {total_received}")
    
    # SNR/RSSI 统计
    print("\n--- 信号质量统计 ---")
    all_snr = []
    all_rssi = []
    all_path_len = []
    
    for log in logs:
        for entry in log['entries']:
            all_snr.append(entry['snr'])
            all_rssi.append(entry['rssi'])
            all_path_len.append(entry['path_len'])
    
    if all_snr:
        print(f"  SNR 范围: {min(all_snr):.1f} ~ {max(all_snr):.1f} dB, "
              f"平均: {sum(all_snr)/len(all_snr):.1f} dB")
    if all_rssi:
        print(f"  RSSI 范围: {min(all_rssi)} ~ {max(all_rssi)} dBm, "
              f"平均: {sum(all_rssi)/len(all_rssi):.0f} dBm")
    if all_path_len:
        print(f"  跳数范围: {min(all_path_len)} ~ {max(all_path_len)}, "
              f"平均: {sum(all_path_len)/len(all_path_len):.1f}")
    
    return all_devices, recv_matrix, total_sent

def export_csv(logs, all_devices, recv_matrix, total_sent, output_file='test_results.csv'):
    """导出CSV结果"""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # 写入设备列表
        writer.writerow(['# 设备列表'])
        writer.writerow(['Device ID', 'Sent Packets', 'Source File'])
        for log in logs:
            if log['device_id']:
                writer.writerow([log['device_id'], log['seq_num'], log['source_file']])
        
        writer.writerow([])
        
        # 写入接收矩阵
        writer.writerow(['# 接收矩阵'])
        headers = ['Sender'] + list(sorted(all_devices))
        writer.writerow(headers)
        
        for sender in sorted(all_devices):
            row = [sender]
            for receiver in sorted(all_devices):
                if sender == receiver:
                    row.append('-')
                else:
                    row.append(recv_matrix[sender].get(receiver, 0))
            writer.writerow(row)
        
        writer.writerow([])
        
        # 写入原始日志
        writer.writerow(['# 原始日志条目'])
        writer.writerow(['Receiver', 'Sender', 'Seq', 'Timestamp', 'SNR', 'RSSI', 'PathLen'])
        for log in logs:
            for entry in log['entries']:
                writer.writerow([
                    log['device_id'],
                    entry['sender_id'],
                    entry['seq'],
                    entry['timestamp'],
                    entry['snr'],
                    entry['rssi'],
                    entry['path_len']
                ])
    
    print(f"\n结果已导出到: {output_file}")

def main():
    if len(sys.argv) < 2:
        print("用法: python3 analyze_test_log.py <log_file1> [log_file2] ...")
        print("\n示例:")
        print("  python3 analyze_test_log.py device_*.log")
        print("  python3 analyze_test_log.py node1.txt node2.txt node3.txt")
        sys.exit(1)
    
    logs = []
    for filepath in sys.argv[1:]:
        if os.path.exists(filepath):
            print(f"解析文件: {filepath}")
            log = parse_log_file(filepath)
            logs.append(log)
        else:
            print(f"警告: 文件不存在 {filepath}")
    
    if not logs:
        print("错误: 没有有效的日志文件")
        sys.exit(1)
    
    all_devices, recv_matrix, total_sent = analyze_network(logs)
    export_csv(logs, all_devices, recv_matrix, total_sent)

if __name__ == '__main__':
    main()
