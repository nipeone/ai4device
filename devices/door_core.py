import zmq
import time
from .base import SocketControlledDevice
import config
from typing import Literal


class DoorController(SocketControlledDevice):
    """Socket（ZMQ）控制的防护门设备"""
    
    def __init__(self, device_id: str = "01", 
                target_address: str = None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        target_address = target_address or config.DOOR_TARGET_ADDRESS
        # ZMQ Socket通信
        super().__init__("socket_door_" + device_id, device_id, target_address)
        self.target_address = target_address
        self.door_status_cache = {}  # 缓存门状态

    def _get_socket(self, timeout: int= 1000):
        """创建一个新的socket连接"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        # 设置超时 1000ms
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        # 设置LINGER=0：关闭时不等待未发送的消息
        socket.setsockopt(zmq.LINGER, 0)
        return context, socket

    def connect(self):
        """连接ZMQ设备"""
        try:
            # 测试连接：尝试获取门状态
            test_context, test_socket = self._get_socket()
            try:
                test_socket.connect(self.target_address)
                test_socket.send(bytes([0x02, 1, 0, 0, 0]))
                test_socket.recv()
                self.is_connected = True
                self.message = "防护门设备连接成功"
                test_socket.close()
                test_context.term()
                return True
            except:
                test_socket.close()
                test_context.term()
                raise
        except Exception as e:
            self.is_connected = False
            self.message = f"防护门设备连接失败: {str(e)}"
            return False

    def disconnect(self):
        """断开ZMQ设备连接"""
        super().disconnect()  # 调用基类的断开逻辑
        self.message = "防护门设备已断开连接"

    def get_door_status(self, door_index: int):
        """
        获取门的实时状态
        发送: [0x02, SlaveID, 0, 0, 0]
        """
        if not self.is_connected:
            return "设备未连接"

        if not (1 <= door_index <= 6):
            return "无效编号"

        slave_id = (door_index + 1) // 2
        is_channel_1 = (door_index % 2 == 0)
        buffer = bytes([0x02, slave_id, 0, 0, 0])

        context, socket = self._get_socket()
        try:
            socket.connect(self.target_address)
            socket.send(buffer)
            response_bytes = socket.recv()

            if len(response_bytes) == 2:
                target_byte = response_bytes[1] if is_channel_1 else response_bytes[0]
                is_open = (target_byte & 1) == 1
                status = "开启" if is_open else "关闭"
                self.door_status_cache[door_index] = status
                return status
            else:
                return "数据异常"

        except zmq.Again:
            return "通信超时"
        except Exception as e:
            return f"错误:{str(e)}"
        finally:
            socket.close()
            context.term()

    def send_command(self, door_index: int, action: Literal["open", "close"]):
        """
        控制开门/关门
        - door_index: 门编号
        - action: "open" 开门 "close" 关门
        """
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}

        if not (1 <= door_index <= 6):
            return {"status": "error", "message": "门编号必须是 1-6"}

        # === 互斥逻辑检查 ===
        if action == "open":
            # 寻找同组的搭档
            if door_index % 2 != 0:
                partner_index = door_index + 1
            else:
                partner_index = door_index - 1

            # 读取搭档的状态
            partner_status = self.get_door_status(partner_index)

            # 如果搭档是开着的，必须先把它关掉
            if partner_status == "开启":
                print(f"[系统自动] 检测到互斥：门{partner_index}当前开启，正在尝试自动关闭...")

                # 递归调用自己，把搭档关掉
                close_result = self.send_command(partner_index, "close")

                # 如果关门失败，为了安全，终止当前开门操作
                if close_result.get("status") != "success":
                    return {
                        "status": "error",
                        "message": f"互斥保护触发：无法关闭同组门{partner_index}，开门中止。"
                    }

                # 稍微停顿一下，给硬件反应时间
                time.sleep(0.5)

        # === 控制逻辑 ===
        slave_id = (door_index + 1) // 2
        channel = 0 if door_index % 2 == 1 else 1
        value = 1 if action == "open" else 2

        # 控制指令: 0x01 ...
        buffer = bytes([0x01, slave_id, channel, 0, value])

        context, socket = self._get_socket()
        try:
            socket.connect(self.target_address)
            socket.send(buffer)
            frame_string = socket.recv_string()

            if frame_string == "True":
                self.message = f"门{door_index} {action}操作成功"
                self.result = {"status": "success", "door": door_index, "action": action}
                return {"status": "success", "door": door_index, "action": action}
            else:
                self.message = f"门{door_index} {action}操作失败：底层返回False"
                self.result = {"status": "fail", "message": "底层返回False"}
                return {"status": "fail", "message": "底层返回False"}
        except zmq.Again:
            self.message = f"门{door_index} {action}操作超时"
            self.result = {"status": "error", "message": "通信超时"}
            return {"status": "error", "message": "通信超时"}
        except Exception as e:
            self.message = f"门{door_index} {action}操作异常: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            return {"status": "error", "message": str(e)}
        finally:
            socket.close()
            context.term()

    def start(self):
        """启动设备（门设备无需启动操作）"""
        self.message = "门设备就绪"
        self.result = {"status": "success", "message": "门设备就绪"}

    def stop(self):
        """停止设备（门设备无需停止操作）"""
        self.message = "门设备已停止"
        self.result = {"status": "success", "message": "门设备已停止"}

    def get_status(self) -> dict:
        """获取设备状态"""
        status_dict = {}
        for door_id in range(1, 7):
            status_dict[door_id] = self.get_door_status(door_id)
        
        return {
            "name": self.device_name,
            "connected": self.is_connected,
            "doors": status_dict
        }

    def get_result(self) -> dict:
        """获取设备结果"""
        return self.result if self.result else {
            "status": "idle",
            "message": "无操作结果"
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "门设备就绪"


# 创建全局实例（保持向后兼容）
door_controller = DoorController()
