"""
Transport 抽象接口。

所有 Transport 实现必须提供这组方法。Fly 层只依赖这个接口，
不关心底层是 pymavlink 还是 MAVROS。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VehicleState:
    """飞行器状态快照。"""
    connected: bool = False
    armed: bool = False
    mode: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0   # NED 坐标系，z 向下为负
    yaw: float = 0.0
    front_distance_m: Optional[float] = None


class Transport(ABC):
    """飞行器通信传输层抽象接口。"""

    @abstractmethod
    def connect(self) -> None:
        """建立连接，阻塞直到链路就绪或超时抛出异常。"""

    @abstractmethod
    def close(self) -> None:
        """关闭连接，释放资源。"""

    @abstractmethod
    def get_state(self) -> VehicleState:
        """获取当前飞行器状态快照。"""

    @abstractmethod
    def send_setpoint_local(self, x: float, y: float, z: float,
                            yaw: float = 0.0, use_current_yaw: bool = True) -> None:
        """发送本地坐标系位置 setpoint（NED frame）。"""

    @abstractmethod
    def set_mode(self, mode: str) -> bool:
        """切换飞行模式，返回是否成功。"""

    @abstractmethod
    def arm(self) -> bool:
        """解锁，返回是否成功。"""

    @abstractmethod
    def disarm(self) -> bool:
        """上锁，返回是否成功。"""

    @abstractmethod
    def send_land(self) -> bool:
        """发送 NAV_LAND 指令，返回是否成功。"""

    def has_landed(self) -> bool:
        """返回 PX4 land detector 是否确认已落地；不支持时返回 False。"""
        return False
