import zmq
import json
import time
from .base import SocketControlledDevice
import config


class OvenController(SocketControlledDevice):
    """Socket（ZMQ）控制的高温炉设备"""
    
    def __init__(self, device_id: str = "01", 
                 req_addr: str = None,
                 sub_addr: str = None,
                 ctrl_addr: str = None):
        # 从环境变量获取配置，如果没有提供参数则使用默认值
        # 请求地址，用于获取设备列表
        req_addr = req_addr or config.FURNACE_REQ_ADDR
        # 订阅地址，用于获取实时数据
        sub_addr = sub_addr or config.FURNACE_SUB_ADDR
        # 控制地址，用于控制炉盖
        ctrl_addr = ctrl_addr or config.FURNACE_CTRL_ADDR
        # ZMQ Socket通信，使用req_addr作为主地址
        super().__init__("socket_oven_" + device_id, device_id, req_addr)
        self.REQ_ADDR = req_addr
        self.SUB_ADDR = sub_addr
        self.CTRL_ADDR = ctrl_addr
        self.SUB_TOPIC = b"Oven"
        self._socket_timeout = 2000  # 设置默认超时时间
        self.temperature = 0.0
        self.target_temperature = 0.0
        self.runtime = 0
        self.status = 0
        self.step = 0
        self.device_list = []
        self.realtime_data = {}
        # 用于SUB socket的临时context（因为SUB socket需要独立管理）
        self._sub_context = None
        self._sub_socket = None
        # 用于CTRL socket的临时context（因为CTRL socket需要独立管理）
        self._ctrl_context = None
        self._ctrl_socket = None

    def connect(self):
        """连接ZMQ设备"""
        # 调用父类方法创建主context和socket（用于REQ操作）
        if not super().connect():
            return False
        
        try:
            # 连接主socket到REQ地址
            self.socket.connect(self.REQ_ADDR)
            
            # 测试连接：获取设备列表
            self.socket.send_string("DeviceDal.GetList@@@")
            data = json.loads(self.socket.recv_string())
            self.device_list = data if isinstance(data, list) else []
            
            self.message = "高温炉设备连接成功"
            return True
        except Exception as e:
            self.is_connected = False
            self.message = f"高温炉设备连接失败: {str(e)}"
            self._cleanup_socket()
            return False

    def disconnect(self):
        """断开ZMQ设备连接"""
        # 清理SUB socket
        if self._sub_socket:
            try:
                self._sub_socket.close()
            except:
                pass
            self._sub_socket = None
        if self._sub_context:
            try:
                self._sub_context.term()
            except:
                pass
            self._sub_context = None
        
        # 清理CTRL socket
        if self._ctrl_socket:
            try:
                self._ctrl_socket.close()
            except:
                pass
            self._ctrl_socket = None
        if self._ctrl_context:
            try:
                self._ctrl_context.term()
            except:
                pass
            self._ctrl_context = None
        
        # 调用父类方法清理主socket
        super().disconnect()
        self.message = "高温炉设备已断开连接"

    def get_device_list(self):
        """获取所有设备的基础列表"""
        if not self.is_connected or not self.socket:
            return []
        
        try:
            self.socket.send_string("DeviceDal.GetList@@@")
            data = json.loads(self.socket.recv_string())
            self.device_list = data if isinstance(data, list) else []
            return self.device_list
        except Exception as e:
            # 如果socket出错，标记为未连接
            self.is_connected = False
            return []

    def get_specific_device_info(self, sid):
        """
        获取特定设备的详细信息
        用于读取：运行曲线名称、仪表型号等详细字段
        """
        if not self.is_connected or not self.socket:
            return {}
        
        try:
            self.socket.send_string(f"DeviceDal.GetList@@@SlaveID = {sid}")
            data = json.loads(self.socket.recv_string())
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return data
        except Exception as e:
            # 如果socket出错，标记为未连接
            self.is_connected = False
            return {}

    def get_realtime_data(self, duration=10.0):
        """
        获取实时数据 (SUB模式)
        :param duration: 搜集数据的持续时间(秒)
        """
        if not self.is_connected:
            return {}
        
        # SUB socket需要独立管理，因为它是SUB类型，与主REQ socket不同
        # 如果SUB socket不存在或已断开，重新创建
        if not self._sub_socket or not self._sub_context:
            try:
                self._sub_context, self._sub_socket = self._create_socket(zmq.SUB)  # 创建SUB socket
                self._sub_socket.setsockopt(zmq.SUBSCRIBE, self.SUB_TOPIC)  # 订阅主题
                self._sub_socket.connect(self.SUB_ADDR)  # 连接到订阅地址
            except Exception as e:
                print(f"Oven Sub Socket创建失败: {e}")
                return {}
        
        latest_data = {}
        try:
            time.sleep(0.1)  # 等待连接建立
            
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    parts = self._sub_socket.recv_multipart(flags=zmq.NOBLOCK)
                    if len(parts) >= 2:
                        data = parts[1]
                        if len(data) >= 9:
                            slave_id = data[0]
                            pv = ((data[3] << 8) + data[4]) / 10.0
                            sv = ((data[5] << 8) + data[6]) / 10.0
                            runtime_raw = (data[7] << 8) + data[8]
                            status = data[1]
                            step = data[2]
                            latest_data[slave_id] = {
                                "pv": pv, "sv": sv, "runtime_raw": runtime_raw,
                                "status": status, "step": step
                            }
                except zmq.Again:
                    time.sleep(0.01)
        except Exception as e:
            print(f"Oven Sub Error: {e}")
            # SUB socket出错时清理
            if self._sub_socket:
                try:
                    self._sub_socket.close()
                except:
                    pass
                self._sub_socket = None
            if self._sub_context:
                try:
                    self._sub_context.term()
                except:
                    pass
                self._sub_context = None
        
        self.realtime_data = latest_data
        return latest_data

    def control_lid(self, rid, action_code):
        """
        控制炉盖
        :param rid: 炉子ID
        :param action_code: 动作代码 (1=开, 2=关)
        """
        if not self.is_connected:
            return False, "设备未连接"
        
        # CTRL socket需要独立管理，因为它连接到不同的地址
        # 如果CTRL socket不存在或已断开，重新创建
        if not self._ctrl_socket or not self._ctrl_context:
            try:
                self._ctrl_context, self._ctrl_socket = self._create_socket(zmq.REQ, 3000)  # 创建CTRL socket
                self._ctrl_socket.connect(self.CTRL_ADDR)  # 连接到控制地址
            except Exception as e:
                self.message = f"CTRL Socket创建失败: {str(e)}"
                self.result = {"status": "error", "message": str(e)}
                return False, str(e)
        
        try:
            buffer = bytes([0x03, rid, 250, 0, action_code])
            self._ctrl_socket.send(buffer)
            response = self._ctrl_socket.recv_string()
            success = response != "False"
            if success:
                self.message = f"炉{rid}盖控制成功，动作: {action_code}"
                self.result = {"status": "success", "rid": rid, "action": action_code}
            else:
                self.message = f"炉{rid}盖控制失败"
                self.result = {"status": "fail", "message": "底层返回False"}
            return success, response
        except Exception as e:
            self.message = f"炉{rid}盖控制异常: {str(e)}"
            self.result = {"status": "error", "message": str(e)}
            # CTRL socket出错时清理，下次使用时重新创建
            if self._ctrl_socket:
                try:
                    self._ctrl_socket.close()
                except:
                    pass
                self._ctrl_socket = None
            if self._ctrl_context:
                try:
                    self._ctrl_context.term()
                except:
                    pass
                self._ctrl_context = None
            return False, str(e)

    def start(self):
        """启动设备（高温炉启动需要指定具体参数）"""
        self.message = "高温炉设备就绪，请使用control_lid控制具体炉子"
        self.result = {"status": "success", "message": "设备就绪"}

    def stop(self):
        """停止设备"""
        self.message = "高温炉设备已停止"
        self.result = {"status": "success", "message": "设备已停止"}

    def get_status(self) -> dict:
        """获取设备状态"""
        # 获取实时数据（短时间采样）
        realtime_data = self.get_realtime_data(duration=1.0)
        
        return {
            "name": self.device_name,
            "connected": self.is_connected,
            "device_list": self.device_list,
            "realtime_data": realtime_data,
            "device_count": len(self.device_list)
        }

    def get_result(self) -> dict:
        """获取设备结果"""
        return self.result if self.result else {
            "status": "idle",
            "message": "无操作结果"
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "高温炉设备就绪"


# 创建全局实例（保持向后兼容）
oven_controller = OvenController()
