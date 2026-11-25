#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WS_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

WS_DIR="${WS_DIR:-$DEFAULT_WS_DIR}"
BACKUP_BASE="${BACKUP_BASE:-/usr/local/x400_backup}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_ROOT="$BACKUP_BASE/opencv_local_$TIMESTAMP"

log() {
  echo "[$(date +%H:%M:%S)] $*"
}

fail() {
  echo "失败：$*" >&2
  exit 1
}

find_system_opencv_cmake_dir() {
  local config
  config="$(find /usr/lib -path '*/cmake/opencv4/OpenCVConfig.cmake' -print -quit 2>/dev/null || true)"
  if [[ -n "$config" ]]; then
    dirname "$config"
    return 0
  fi
  return 1
}

echo "X400 OpenCV 4.2 运行环境统一脚本"
echo "WS_DIR=$WS_DIR"
echo
echo "目的："
echo "1. 将 /usr/local 下手动安装的 OpenCV 文件备份移走。"
echo "2. 刷新动态链接器缓存，让 ROS Noetic 优先使用 Ubuntu/ROS 默认 OpenCV 4.2。"
echo "3. 清理并重新编译当前 ROS 工作区。"
echo "4. 检查 realsense2_camera 是否仍链接到 /usr/local/lib/libopencv*。"
echo
echo "注意：本脚本会影响依赖 /usr/local OpenCV 的其它程序。"
echo "      移走的文件会备份到：$BACKUP_ROOT"
echo

[[ "$(uname -s)" == "Linux" ]] || fail "本脚本只能在 Linux 机载电脑上运行。"
[[ -f /opt/ros/noetic/setup.bash ]] || fail "未找到 /opt/ros/noetic/setup.bash，请确认 ROS Noetic 已安装。"
[[ -d "$WS_DIR/src" ]] || fail "未找到工作区 src 目录：$WS_DIR/src"
[[ -f "$WS_DIR/src/CMakeLists.txt" ]] || fail "未找到 $WS_DIR/src/CMakeLists.txt，请确认 WS_DIR 指向 catkin 工作区。"

OPENCV_CMAKE_DIR="${OPENCV_CMAKE_DIR:-}"
if [[ -z "$OPENCV_CMAKE_DIR" ]]; then
  OPENCV_CMAKE_DIR="$(find_system_opencv_cmake_dir)" || fail "未在 /usr/lib 下找到系统 OpenCVConfig.cmake。请先安装 Ubuntu/ROS 默认 OpenCV 4.2。"
fi
[[ -f "$OPENCV_CMAKE_DIR/OpenCVConfig.cmake" ]] || fail "OpenCVConfig.cmake 不存在：$OPENCV_CMAKE_DIR"

echo "系统 OpenCV CMake 路径：$OPENCV_CMAKE_DIR"
if command -v pkg-config >/dev/null 2>&1 && pkg-config --exists opencv4; then
  echo "pkg-config opencv4 版本：$(pkg-config --modversion opencv4)"
fi
echo

shopt -s nullglob
LOCAL_OPENCV_CANDIDATES=(
  /usr/local/lib/libopencv*
  /usr/local/lib/cmake/opencv4
  /usr/local/lib/pkgconfig/opencv4.pc
  /usr/local/share/opencv4
  /usr/local/include/opencv4
)
LOCAL_OPENCV_ITEMS=()
for item in "${LOCAL_OPENCV_CANDIDATES[@]}"; do
  [[ -e "$item" ]] || continue
  LOCAL_OPENCV_ITEMS+=("$item")
done

if (( ${#LOCAL_OPENCV_ITEMS[@]} == 0 )); then
  echo "未发现 /usr/local 下的 OpenCV 文件，跳过备份移除。"
else
  echo "将备份并移走以下 /usr/local OpenCV 文件/目录："
  printf '  %s\n' "${LOCAL_OPENCV_ITEMS[@]}"
fi
echo
read -r -p "确认执行 OpenCV 4.2 统一修复？请输入 YES 继续： " CONFIRM
[[ "$CONFIRM" == "YES" ]] || fail "用户取消。"

if (( ${#LOCAL_OPENCV_ITEMS[@]} > 0 )); then
  log "备份并移走 /usr/local OpenCV 文件"
  sudo mkdir -p "$BACKUP_ROOT"
  for item in "${LOCAL_OPENCV_ITEMS[@]}"; do
    [[ -e "$item" ]] || continue
    dest="$BACKUP_ROOT$item"
    sudo mkdir -p "$(dirname "$dest")"
    sudo mv "$item" "$dest"
  done
fi

log "刷新动态链接器缓存"
sudo ldconfig

echo
echo "当前动态库缓存中的 OpenCV core："
ldconfig -p | grep -E 'libopencv_core\.so' || true
echo

log "清理 catkin build/devel/install 缓存"
rm -rf "$WS_DIR/build" "$WS_DIR/devel" "$WS_DIR/install"
if [[ -d "$WS_DIR/build" || -d "$WS_DIR/devel" || -d "$WS_DIR/install" ]]; then
  fail "build/devel/install 未能清理干净，请检查目录权限后重新运行。"
fi

log "使用系统 OpenCV 重新编译 ROS 工作区"
cd "$WS_DIR"
source /opt/ros/noetic/setup.bash
catkin_make -DOpenCV_DIR="$OPENCV_CMAKE_DIR"
source "$WS_DIR/devel/setup.bash"

LIB_REALSENSE="$WS_DIR/devel/lib/librealsense2_camera.so"
[[ -f "$LIB_REALSENSE" ]] || fail "未找到 $LIB_REALSENSE，realsense2_camera 可能未正确编译。"

echo
echo "realsense2_camera 的 OpenCV 链接结果："
ldd "$LIB_REALSENSE" | grep -E 'opencv|not found' || true
echo

if ldd "$LIB_REALSENSE" | grep -q '/usr/local/lib/libopencv'; then
  fail "仍然链接到了 /usr/local/lib/libopencv*，请检查是否还有其它 /usr/local OpenCV 路径残留。"
fi

if ldd "$LIB_REALSENSE" | grep -q 'not found'; then
  fail "存在动态库 not found，请先修复依赖。"
fi

log "完成：当前 ROS 工作区已统一到系统 OpenCV。"
echo "备份目录：$BACKUP_ROOT"
echo
echo "建议现在运行："
echo "cd $WS_DIR"
echo "检查自启动链路：systemctl status <服务名>；再执行 rostopic echo -n 1 /camera/depth/image_rect_raw/header"

