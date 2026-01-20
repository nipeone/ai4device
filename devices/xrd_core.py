from .base import SocketControlledDevice
import config

class XRDController(SocketControlledDevice):
    """XRD衍射仪设备（Socket/ZMQ控制）"""
    
    def __init__(self, device_id: str = "01",
                 target_address: str = None):
        target_address = target_address or config.XRD_TARGET_ADDRESS
        super().__init__("socket_xrd_" + device_id, device_id, target_address)
        self.target_address = target_address
        self.xrd_status_cache = {}
        self._socket_timeout = 1000  # 设置默认超时时间

    def connect(self):
        """连接XRD衍射仪设备"""
        # 调用父类方法创建context和socket
        if not super().connect():
            return False
        
        try:
            # 连接socket到目标地址
            self.socket.connect(self.socket_address)
            
            # 可以在这里添加连接测试逻辑
            # 例如发送测试命令验证连接
            
            self.message = "XRD衍射仪设备连接成功"
            return True
        except Exception as e:
            self.is_connected = False
            self.message = f"XRD衍射仪设备连接失败: {str(e)}"
            self._cleanup_socket()
            return False

    def disconnect(self):
        """断开XRD衍射仪设备"""
        super().disconnect()
        self.message = "XRD衍射仪设备已断开连接"

    def start(self):
        """启动XRD测量"""
        if not self.is_connected or not self.socket:
            self.message = "设备未连接"
            self.result = {"status": "error", "message": "设备未连接"}
            return False
        
        # TODO: 实现具体的启动逻辑
        self.message = "XRD测量已启动"
        self.result = {"status": "success", "message": "测量已启动"}
        return True

    def stop(self):
        """停止XRD测量"""
        if not self.is_connected or not self.socket:
            self.message = "设备未连接"
            self.result = {"status": "error", "message": "设备未连接"}
            return False
        
        # TODO: 实现具体的停止逻辑
        self.message = "XRD测量已停止"
        self.result = {"status": "success", "message": "测量已停止"}
        return True

    def get_status(self) -> dict:
        """获取设备状态"""
        return {
            "name": self.device_name,
            "connected": self.is_connected,
            "status": self.status.value if self.status else "unknown",
            "message": self.message
        }

    def get_result(self) -> dict:
        """获取设备结果"""
        return self.result if self.result else {
            "status": "idle",
            "message": "无操作结果"
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "XRD衍射仪设备就绪"

    def send_command(self, command: str):
        """发送命令到XRD衍射仪设备"""
        if not self.is_connected:
            return {"status": "error", "message": "设备未连接"}
        pass

xrd_controller = XRDController()