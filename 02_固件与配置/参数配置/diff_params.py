#!/usr/bin/env python3
"""
Pixhawk 6C 参数变更报告自动生成工具
用法: python diff_params.py
功能: 读取 参数配置 目录下所有 .params 文件，逐版本 diff，自动更新参数变更完整报告
"""

import os
import re
import glob
from datetime import date

# ============ 路径配置 ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARAMS_DIR = SCRIPT_DIR  # 脚本就在参数配置目录中
REPORT_DIR = os.path.join(
    os.path.dirname(SCRIPT_DIR),  # 上级目录 02_固件与配置
    "参数变更报告"
)
REPORT_FILE = os.path.join(REPORT_DIR, "Pixhawk 6C_参数变更完整报告_0.0_to_2.9.md")

# ============ 排除参数规则 ============
EXCLUDE_PATTERNS = [
    re.compile(r'^CAL_ACC'),
    re.compile(r'^CAL_MAG'),
    re.compile(r'^CAL_GYRO'),
    re.compile(r'^RC\d+_MIN$'),
    re.compile(r'^RC\d+_TRIM$'),
    re.compile(r'^RC\d+_MAX$'),
    re.compile(r'^RC\d+_REV$'),
    re.compile(r'^RC\d+_REV$'),
    re.compile(r'^SENS_BOARD_X_OFF'),
    re.compile(r'^SENS_BOARD_Y_OFF'),
    re.compile(r'^SENS_BOARD_Z_OFF'),
    re.compile(r'^SENS_BOARD_ROT'),
    re.compile(r'^COM_FLIGHT_UUID'),
    re.compile(r'^FLIGHT_UUID'),
    re.compile(r'^LND_FLIGHT_T_'),
    re.compile(r'^CAL_AIR_'),
    re.compile(r'^CAL_BARO'),
]

# ============ 参数说明字典 ============
# 仅包含曾发生过变更的参数（即生命周期总表中出现的参数）
PARAM_DESC = {
    "COM_DISARM_LAND": "降落后自动上锁延时（秒）",
    "COM_OF_LOSS_T": "Offboard 模式下 setpoint 丢失超时（秒），超时后退出 Offboard",
    "COM_RC_OVERRIDE": "RC 覆盖模式：1=仅自动模式，3=自动+Offboard 模式",
    "COM_RC_STICK_OV": "摇杆接管阈值（%），低于此值不触发接管",
    "CP_DIST": "碰撞预防最小允许前向距离（m），-1=关闭，>0=开启",
    "CP_GO_NO_DATA": "无避障数据时的行为：0=不允许前进，1=允许前进",
    "EKF2_IMU_POS_Z": "IMU 在机架坐标系中的 Z 轴安装偏移（m）",
    "EKF2_MAG_TYPE": "磁罗盘融合类型：0=自动，6=不融合（室内方案）",
    "EKF2_OF_POS_X": "光流传感器在机架坐标系中的 X 轴安装偏移（m）",
    "EKF2_OF_POS_Z": "光流传感器在机架坐标系中的 Z 轴安装偏移（m）",
    "EKF2_RNG_POS_X": "测距传感器在机架坐标系中的 X 轴安装偏移（m）",
    "EKF2_RNG_POS_Z": "测距传感器在机架坐标系中的 Z 轴安装偏移（m）",
    "MAV_2_FORWARD": "MAVLink 实例 2 转发：0=关闭，1=开启",
    "MPC_ACC_HOR": "水平最大加速度（m/s²）",
    "MPC_MAN_TILT_MAX": "手动模式最大倾角（度）",
    "NAV_DLL_ACT": "数传链路丢失后导航动作：0=无动作，1=RTL",
    "RC_MAP_OFFB_SW": "Offboard 模式开关映射的遥控器通道号，0=不映射",
    "SDLOG_MODE": "SD 卡日志记录模式：0=上锁时记录，1=开机即记录",
    "SER_TEL3_BAUD": "TELEM3 串口波特率",
    "SENS_FLOW_MAXHGT": "光流传感器最大工作高度（m）",
    "SENS_FLOW_MAXR": "光流传感器最大角速率（deg/s）",
    "SENS_FLOW_MINHGT": "光流传感器最小工作高度（m）",
    "SENS_FLOW_RATE": "光流传感器更新速率（Hz）",
    "SENS_FLOW_ROT": "光流传感器安装旋转",
    "SENS_FLOW_SCALE": "光流传感器比例因子",
}

# 为每个版本区间预定义的说明（新增/变更/移除的综合描述）
SECTION_DESC = {
    ("0.0", "1.0"): "1.0 是首次飞控基本校准后的基线版本，主要变更日志记录模式。",
    ("1.0", "2.0"): "光流和测距共用 MTF-02 一体传感器，Z 轴位置应一致。2.0 将两者统一为 0.06，同时微调 IMU 偏移，确保 EKF2 融合时三个传感器的位置模型对齐。",
    ("2.0", "2.1"): "2.1 是接管机制小版本，核心目的是在 Offboard 自动飞行时，飞手推动摇杆能立即退出 Offboard 转回人工控制。同时关闭磁罗盘融合（室内方案）。",
    ("2.2", "2.3"): "2.3 引入机载电脑串口通信（TELEM3 提速）和避障功能（CP_DIST 开启），并调整传感器偏移。SENS_FLOW 系列参数被移除。",
    ("2.3", "2.4"): "2.4 微调飞控参数（Offboard 超时缩短），光流偏移从 Z 轴改为 X 轴。SENS_FLOW 系列参数在 2.3 中被移除后，于 2.4 重新添加，值不变。",
    ("2.4", "2.5"): "2.5 调整 SD 卡日志记录模式为开机即记录。",
    ("2.5", "2.6"): "2.6 关闭数传丢失 RTL 动作（NAV_DLL_ACT=0）。",
    ("2.6", "2.7"): "2.7 将日志模式改回上锁时记录。",
    ("2.7", "2.8"): "2.8 是较大的调整版本，涉及飞控手感（水平加速度、最大倾角降低）、传感器偏移对齐（光流与测距 X 轴一致）、以及 MAVLink 通信配置。",
    ("2.8", "2.9"): "2.9 调整避障参数：缩短检测距离并允许无数据时前进，更适合室内近距离飞行场景。",
}


def should_exclude(name):
    for pat in EXCLUDE_PATTERNS:
        if pat.match(name):
            return True
    return False


def parse_params(filepath):
    """Parse a .params file, return dict of name->value."""
    params = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 4:
                name = parts[2].strip()
                value = parts[3].strip()
                params[name] = value
    return params


def read_header_info(filepath):
    """Read firmware version and frame type from file header."""
    fw_version = "unknown"
    frame = "unknown"
    autostart = "unknown"
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('# Version:'):
                fw_version = line.split(':', 1)[1].strip()
            elif line.startswith('# Vehicle:'):
                frame = line.split(':', 1)[1].strip()
            elif 'SYS_AUTOSTART' in line:
                parts = line.split('\t')
                if len(parts) >= 4:
                    autostart = parts[3].strip()
    return fw_version, frame, autostart


def diff_params(old_params, new_params):
    """Diff two param dicts, return (changed, removed, added) lists."""
    changed = []
    removed = []
    added = []

    all_keys = set(list(old_params.keys()) + list(new_params.keys()))

    for key in sorted(all_keys):
        if should_exclude(key):
            continue
        if key in old_params and key in new_params:
            if old_params[key] != new_params[key]:
                changed.append((key, old_params[key], new_params[key]))
        elif key in old_params and key not in new_params:
            removed.append((key, old_params[key], None))
        elif key not in old_params and key in new_params:
            added.append((key, None, new_params[key]))

    return changed, removed, added


def format_value_short(val):
    """Format value to a readable short form."""
    if val is None:
        return "-"
    # Try to trim trailing zeros for floats
    try:
        f = float(val)
        if f == int(f):
            return str(int(f))
        # Show reasonable precision
        return str(round(f, 3)).rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        pass
    return val


def format_value_precise(val):
    """Keep full precision for display."""
    if val is None:
        return "-"
    return val


def get_key_changed_desc(changed, removed, added):
    """Generate a short description of key changes for the summary table."""
    parts = []
    seen = set()
    for key, _, _ in changed:
        name = key
        if name not in seen:
            seen.add(name)
            # Try to shorten name
            parts.append(name)
    for key, _, _ in removed:
        if key not in seen:
            seen.add(key)
            parts.append(f"{key} 移除")
    for key, _, _ in added:
        if key not in seen:
            seen.add(key)
            parts.append(f"{key} 新增")
    # Limit to ~40 chars
    result = "、".join(parts)
    if len(result) > 45:
        # Try to group by prefix
        prefixes = {}
        for p in parts:
            prefix = p.split("_")[0] if "_" in p else p
            if prefix not in prefixes:
                prefixes[prefix] = []
            prefixes[prefix].append(p)
        grouped = []
        for prefix, items in prefixes.items():
            if len(items) > 1:
                grouped.append(f"{prefix}_*")
            else:
                grouped.append(items[0])
        result = "、".join(grouped)
    return result


def generate_report(all_params, versions):
    """Generate the complete markdown report."""
    lines = []
    latest_ver = versions[-1]

    # Read header info from first available file
    fw_version, frame, autostart = "unknown", "unknown", "unknown"
    for ver in versions:
        if ver in all_params:
            filepath = os.path.join(PARAMS_DIR, f"Pixhawk 6C_{ver}.params")
            if os.path.exists(filepath):
                fw_version, frame, autostart = read_header_info(filepath)
                break

    # ===== Title =====
    lines.append(f"# Pixhawk 6C 参数变更完整报告 0.0 → {latest_ver}")
    lines.append("")
    lines.append("> **生成方式**：基于 .params 文件自动化逐版本 diff，过滤校准/统计类参数。")
    lines.append(">")
    lines.append("> **过滤规则**：排除 CAL_ACC\\* / CAL_MAG\\* / CAL_GYRO\\* / RC\\*_MIN/TRIM/MAX/REV / SENS_BOARD_\\*OFF/ROT / COM_FLIGHT_UUID / FLIGHT_UUID\\* / LND_FLIGHT_T_\\* / CAL_AIR_\\* / CAL_BARO\\*")
    lines.append(">")
    lines.append(f"> **固件版本**：{fw_version}")
    lines.append(">")
    lines.append(f"> **机架**：{frame} (SYS_AUTOSTART={autostart})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ===== Version Summary Table =====
    lines.append("## 版本区间汇总")
    lines.append("")
    lines.append("| 区间 | 变更数 | 新增 | 移除 | 关键变更 |")
    lines.append("|------|--------|------|------|----------|")

    all_changed_params = {}  # param -> list of (version, value)
    all_removed = {}  # param -> set of versions where removed

    for i in range(len(versions) - 1):
        old_ver = versions[i]
        new_ver = versions[i + 1]
        if old_ver in all_params and new_ver in all_params:
            changed, removed, added = diff_params(
                all_params[old_ver], all_params[new_ver]
            )
            key_desc = get_key_changed_desc(changed, removed, added)
            lines.append(
                f"| {old_ver} → {new_ver} | {len(changed)} | {len(added)} | {len(removed)} | {key_desc} |"
            )

            # Collect lifecycle data
            for key, old_val, new_val in changed:
                if key not in all_changed_params:
                    all_changed_params[key] = {}
                all_changed_params[key][new_ver] = new_val
            for key, old_val, _ in removed:
                if key not in all_removed:
                    all_removed[key] = set()
                all_removed[key].add(new_ver)
        else:
            lines.append(f"| {old_ver} → {new_ver} | - | - | - | 文件缺失 |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # ===== Per-Version Diff Sections =====
    for i in range(len(versions) - 1):
        old_ver = versions[i]
        new_ver = versions[i + 1]
        lines.append(f"## {old_ver} → {new_ver}")
        lines.append("")

        if old_ver not in all_params or new_ver not in all_params:
            lines.append("**文件缺失，无法对比。**")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        changed, removed, added = diff_params(
            all_params[old_ver], all_params[new_ver]
        )

        if not changed and not removed and not added:
            lines.append("**无参数变更。** 两个版本完全一致。")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        # Changed parameters
        if changed:
            lines.append("### 变更参数")
            lines.append("")
            lines.append(f"| 参数 | {old_ver} | {new_ver} | 说明 |")
            lines.append("|------|-----|-----|------|")
            for key, old_val, new_val in changed:
                desc = PARAM_DESC.get(key, "")
                lines.append(
                    f"| {key} | {format_value_precise(old_val)} | "
                    f"{format_value_precise(new_val)} | {desc} |"
                )
            lines.append("")

        # Removed parameters
        if removed:
            lines.append("### 移除参数")
            lines.append("")
            lines.append(f"| 参数 | {old_ver} 的值 | 说明 |")
            lines.append("|------|----------|------|")
            for key, old_val, _ in removed:
                desc = PARAM_DESC.get(key, "")
                lines.append(f"| {key} | {format_value_precise(old_val)} | {desc} |")
            lines.append("")

        # Added parameters
        if added:
            lines.append("### 新增参数")
            lines.append("")
            lines.append(f"| 参数 | {new_ver} 的值 | 说明 |")
            lines.append("|------|----------|------|")
            for key, _, new_val in added:
                desc = PARAM_DESC.get(key, "")
                lines.append(f"| {key} | {format_value_precise(new_val)} | {desc} |")
            lines.append("")

        # Section description
        desc_key = (old_ver, new_ver)
        if desc_key in SECTION_DESC:
            lines.append(f"> **说明**：{SECTION_DESC[desc_key]}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # ===== Parameter Lifecycle Table =====
    lines.append("## 参数生命周期总表")
    lines.append("")
    lines.append("以下列出在所有版本区间中发生过变更的参数及其完整变化轨迹。")
    lines.append("")

    # Build lifecycle data
    lifecycle_params = {}
    for key in all_changed_params:
        lifecycle_params[key] = {}
        for v in versions:
            lifecycle_params[key][v] = None  # None means we need to compute

    # Also include removed-only params (SENS_FLOW_*)
    for key in all_removed:
        if key not in lifecycle_params:
            lifecycle_params[key] = {}
            for v in versions:
                lifecycle_params[key][v] = None

    # Include params that existed before first change
    all_lifecycle_keys = set()
    for key in lifecycle_params:
        all_lifecycle_keys.add(key)
    for key in all_removed:
        all_lifecycle_keys.add(key)

    # Fill lifecycle data
    for key in sorted(all_lifecycle_keys):
        for v in versions:
            if v in all_params and key in all_params[v]:
                lifecycle_params[key][v] = all_params[v][key]

    # Table header
    header_cols = ["参数"] + versions
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "------|" * len(header_cols))

    # Table rows
    for key in sorted(all_lifecycle_keys):
        row = [key]
        prev_val = None
        prev_exists = False
        for v in versions:
            val = lifecycle_params.get(key, {}).get(v, None)
            if val is not None:
                short_val = format_value_short(val)
                if prev_exists and val != prev_val:
                    row.append(f"**{short_val}**")
                elif not prev_exists:
                    row.append(short_val)
                else:
                    row.append("→")
                prev_val = val
                prev_exists = True
            else:
                # Check if param existed in any earlier version
                existed_earlier = any(
                    lifecycle_params.get(key, {}).get(vv, None) is not None
                    for vv in versions[:versions.index(v)]
                )
                existed_later = any(
                    lifecycle_params.get(key, {}).get(vv, None) is not None
                    for vv in versions[versions.index(v) + 1:]
                )
                if existed_earlier and not existed_later:
                    # Was removed in this or earlier version
                    if any(
                        vv in all_removed.get(key, set())
                        for vv in versions[:versions.index(v) + 1]
                    ):
                        row.append("_rm_")
                    else:
                        row.append("-")
                elif existed_later and not existed_earlier:
                    row.append("-")
                elif existed_earlier and existed_later:
                    # Temporarily removed
                    row.append("_rm_")
                else:
                    row.append("-")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append(
        "> **符号说明**：`→` 表示与前一版本相同；`**值**` 表示该版本发生变更；"
        "`_rm_` 表示该参数被移除；`-` 表示参数尚不存在。"
    )
    lines.append("")

    lines.append("---")
    lines.append("")

    # ===== Summary =====
    lines.append("## 总结")
    lines.append("")
    lines.append(f"从 0.0 到 {latest_ver}，非排除参数的变更可分为以下几个阶段：")
    lines.append("")

    stage_num = 1
    for i in range(len(versions) - 1):
        old_ver = versions[i]
        new_ver = versions[i + 1]
        if old_ver in all_params and new_ver in all_params:
            changed, removed, added = diff_params(
                all_params[old_ver], all_params[new_ver]
            )
            if changed or removed or added:
                key_desc = get_key_changed_desc(changed, removed, added)
                lines.append(f"{stage_num}. **{old_ver}→{new_ver}**：{key_desc}")
                stage_num += 1
            else:
                lines.append(f"{stage_num}. **{old_ver}→{new_ver}**：无变更")
                stage_num += 1
        else:
            lines.append(f"{stage_num}. **{old_ver}→{new_ver}**：文件缺失")
            stage_num += 1

    lines.append("")
    lines.append(f"> **报告生成时间**：{date.today().isoformat()}")
    lines.append(">")
    lines.append("> **自动化工具**：Python diff 脚本 (diff_params.py)")
    lines.append("")

    return "\n".join(lines)


def discover_versions():
    """Auto-discover versions from .params filenames."""
    pattern = os.path.join(PARAMS_DIR, "Pixhawk 6C_*.params")
    files = glob.glob(pattern)
    version_set = set()
    for fpath in files:
        basename = os.path.basename(fpath)
        # Extract version number: Pixhawk 6C_X.Y.params
        m = re.match(r'Pixhawk 6C_([\d.]+)\.params$', basename)
        if m:
            version_set.add(m.group(1))

    # Sort as float tuples
    def version_key(v):
        parts = v.split('.')
        return tuple(int(p) for p in parts)

    return sorted(version_set, key=version_key)


def main():
    versions = discover_versions()
    if not versions:
        print("ERROR: No .params files found!")
        return

    print(f"发现 {len(versions)} 个版本: {', '.join(versions)}")

    # Parse all files
    all_params = {}
    for ver in versions:
        filepath = os.path.join(PARAMS_DIR, f"Pixhawk 6C_{ver}.params")
        if os.path.exists(filepath):
            all_params[ver] = parse_params(filepath)
            print(f"  解析版本 {ver}: {len(all_params[ver])} 个参数")
        else:
            print(f"  WARNING: 版本 {ver} 文件缺失")

    # Generate report
    print(f"\n生成报告...")
    report_content = generate_report(all_params, versions)

    # Ensure report directory exists
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Write report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"报告已写入: {REPORT_FILE}")

    # Print console summary
    print(f"\n{'='*50}")
    print(f"参数变更报告生成完成！")
    print(f"版本范围: 0.0 → {versions[-1]}")
    print(f"版本数量: {len(versions)}")
    print(f"报告路径: {REPORT_FILE}")
    print(f"{'='*50}")

    # Print per-version summary
    print(f"\n变更摘要:")
    for i in range(len(versions) - 1):
        old_ver = versions[i]
        new_ver = versions[i + 1]
        if old_ver in all_params and new_ver in all_params:
            changed, removed, added = diff_params(
                all_params[old_ver], all_params[new_ver]
            )
            status = f"变更{len(changed)}, 新增{len(added)}, 移除{len(removed)}"
            print(f"  {old_ver} → {new_ver}: {status}")
        else:
            print(f"  {old_ver} → {new_ver}: 文件缺失")


if __name__ == "__main__":
    main()
