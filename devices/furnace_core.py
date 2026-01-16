# 文件名：furnace_core.py
import zmq
import json
import time
from .base import SocketControlledDevice


class OvenDriver(SocketControlledDevice):
    """Socket（ZMQ）控制的高温炉设备"""
    
    def __init__(self, device_id: str = "01", 
                 req_addr: str = "tcp://127.0.0.1:49206",
                 sub_addr: str = "tcp://127.0.0.1:49200",
                 ctrl_addr: str = "tcp://127.0.0.1:49201"):
        # ZMQ Socket通信，使用req_addr作为主地址
        super().__init__("socket_oven_" + device_id, device_id, req_addr)
        self.REQ_ADDR = req_addr
        self.SUB_ADDR = sub_addr
        self.CTRL_ADDR = ctrl_addr
        self.SUB_TOPIC = b"Oven"
        self.temperature = 0.0
        self.target_temperature = 0.0
        self.runtime = 0
        self.status = 0
        self.step = 0
        self.device_list = []
        self.realtime_data = {}

    def connect(self):
        """连接ZMQ设备"""
        try:
            # 测试连接：获取设备列表
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.RCVTIMEO = 2000
            socket.LINGER = 0
            try:
                socket.connect(self.REQ_ADDR)
                socket.send_string("DeviceDal.GetList@@@")
                data = json.loads(socket.recv_string())
                self.is_connected = True
                self.device_list = data if isinstance(data, list) else []
                self.message = "高温炉设备连接成功"
                return True
            except Exception as e:
                raise
            finally:
                socket.close()
                context.term()
        except Exception as e:
            self.is_connected = False
            self.message = f"高温炉设备连接失败: {str(e)}"
            return False

    def disconnect(self):
        """断开ZMQ设备连接"""
        super().disconnect()  # 调用基类的断开逻辑
        self.message = "高温炉设备已断开连接"

    def get_device_list(self):
        """获取所有设备的基础列表"""
        if not self.is_connected:
            return []
        
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.RCVTIMEO = 2000
        socket.LINGER = 0
        try:
            socket.connect(self.REQ_ADDR)
            socket.send_string("DeviceDal.GetList@@@")
            data = json.loads(socket.recv_string())
            self.device_list = data if isinstance(data, list) else []
            return self.device_list
        except:
            return []
        finally:
            socket.close()
            context.term()

    def get_specific_device_info(self, sid):
        """
        获取特定设备的详细信息
        用于读取：运行曲线名称、仪表型号等详细字段
        """
        if not self.is_connected:
            return {}
        
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.RCVTIMEO = 1000
        socket.LINGER = 0
        try:
            socket.connect(self.REQ_ADDR)
            socket.send_string(f"DeviceDal.GetList@@@SlaveID = {sid}")
            data = json.loads(socket.recv_string())
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return data
        except:
            return {}
        finally:
            socket.close()
            context.term()

    def get_realtime_data(self, duration=10.0):
        """
        获取实时数据 (SUB模式)
        :param duration: 搜集数据的持续时间(秒)
        """
        if not self.is_connected:
            return {}
        
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.RCVTIMEO = 1000
        socket.LINGER = 0
        latest_data = {}

        try:
            socket.connect(self.SUB_ADDR)
            socket.setsockopt(zmq.SUBSCRIBE, self.SUB_TOPIC)
            
            time.sleep(0.1)
            
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    parts = socket.recv_multipart(flags=zmq.NOBLOCK)
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
        finally:
            socket.close()
            context.term()
        
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
        
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.RCVTIMEO = 3000
        try:
            socket.connect(self.CTRL_ADDR)
            buffer = bytes([0x03, rid, 250, 0, action_code])
            socket.send(buffer)
            response = socket.recv_string()
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
            return False, str(e)
        finally:
            socket.close()
            context.term()

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
oven_driver = OvenDriver()
