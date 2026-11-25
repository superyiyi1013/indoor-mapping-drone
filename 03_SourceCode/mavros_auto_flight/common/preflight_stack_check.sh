#!/usr/bin/env bash

wait_for_topic() {
  local topic="$1"
  local timeout_sec="$2"
  local start
  start="$(date +%s)"
  while true; do
    if rostopic list 2>/dev/null | grep -qx "$topic"; then
      return 0
    fi
    if (( "$(date +%s)" - start >= timeout_sec )); then
      return 1
    fi
    sleep 1
  done
}

wait_for_mavros_connected() {
  local timeout_sec="$1"
  local start
  start="$(date +%s)"
  while true; do
    if rostopic echo -n 1 /mavros/state 2>/dev/null | grep -q "connected: True"; then
      return 0
    fi
    if (( "$(date +%s)" - start >= timeout_sec )); then
      return 1
    fi
    sleep 1
  done
}

wait_for_mavros_subscriber() {
  local topic="$1"
  local timeout_sec="$2"
  local start
  start="$(date +%s)"
  while true; do
    if rostopic info "$topic" 2>/dev/null | grep -A20 "Subscribers:" | grep -q "/mavros"; then
      return 0
    fi
    if (( "$(date +%s)" - start >= timeout_sec )); then
      return 1
    fi
    sleep 1
  done
}

wait_for_topic_publisher() {
  local topic="$1"
  local timeout_sec="$2"
  local start
  start="$(date +%s)"
  while true; do
    if rostopic info "$topic" 2>/dev/null \
      | awk '
          /^Publishers:/ { in_publishers=1; next }
          /^Subscribers:/ { in_publishers=0 }
          in_publishers && /\/.+\(/ { found=1 }
          END { exit found ? 0 : 1 }
        '; then
      return 0
    fi
    if (( "$(date +%s)" - start >= timeout_sec )); then
      return 1
    fi
    sleep 1
  done
}

check_flight_stack_ready() {
  local distance_topic="${DISTANCE_TOPIC:-/x400/obstacle/front_distance}"
  local mavros_distance_topic="${MAVROS_DISTANCE_TOPIC:-/mavros/distance_sensor/laser_1_sub}"
  local mavros_obstacle_topic="${MAVROS_OBSTACLE_TOPIC:-/mavros/obstacle/send}"

  echo "检查飞行前置链路"
  echo "要求：机载电脑开机自启动的 MAVROS + D435i 前向避障链路必须已常驻运行。"
  echo "DISTANCE_TOPIC=$distance_topic"
  echo "MAVROS_DISTANCE_TOPIC=$mavros_distance_topic"
  echo "MAVROS_OBSTACLE_TOPIC=$mavros_obstacle_topic"
  echo

  if ! wait_for_topic /mavros/state 10; then
    echo "失败：未检测到 /mavros/state。" >&2
    echo "请先检查 systemd 自启动服务和机载感知链路：" >&2
    echo "systemctl list-units --type=service | grep -Ei 'x400|sensing|mavros|d435|ros'" >&2
    echo "systemctl status <服务名>" >&2
    return 1
  fi

  if ! wait_for_mavros_connected 10; then
    echo "失败：MAVROS 未连接 Pixhawk。" >&2
    rostopic echo -n 1 /mavros/state >&2 || true
    return 1
  fi
  echo "MAVROS 已连接 Pixhawk。"

  if ! wait_for_topic "$distance_topic" 10; then
    echo "失败：未检测到 D435i 前向距离话题 $distance_topic。" >&2
    return 1
  fi

  if ! wait_for_topic "$mavros_distance_topic" 10; then
    echo "失败：未检测到 MAVROS D435i 前向距离输入话题 $mavros_distance_topic。" >&2
    return 1
  fi

  if ! wait_for_mavros_subscriber "$mavros_distance_topic" 10; then
    echo "失败：$mavros_distance_topic 没有被 /mavros 订阅。" >&2
    echo "请检查开机自启动链路是否加载 x400_bringup/onboard_sensing_stack.launch，并确认 MAVROS distance_sensor 配置生效。" >&2
    rostopic info "$mavros_distance_topic" >&2 || true
    return 1
  fi
  echo "MAVROS 已订阅 D435i 前向距离话题。"

  if ! wait_for_topic "$mavros_obstacle_topic" 10; then
    echo "失败：未检测到 MAVROS obstacle 输入话题 $mavros_obstacle_topic。" >&2
    return 1
  fi

  if ! wait_for_topic_publisher "$mavros_obstacle_topic" 10; then
    echo "失败：$mavros_obstacle_topic 没有 D435i 前向 LaserScan 发布者。" >&2
    rostopic info "$mavros_obstacle_topic" >&2 || true
    return 1
  fi

  if ! wait_for_mavros_subscriber "$mavros_obstacle_topic" 10; then
    echo "失败：$mavros_obstacle_topic 没有被 /mavros 订阅，PX4 Collision Prevention 不会收到 OBSTACLE_DISTANCE。" >&2
    rostopic info "$mavros_obstacle_topic" >&2 || true
    return 1
  fi
  echo "MAVROS 已订阅 D435i 前向 obstacle LaserScan。"

  echo
  echo "D435i 前向距离样例："
  rostopic echo -n 1 "$distance_topic" || return 1
  echo
  echo "前置链路检查通过。"
}
