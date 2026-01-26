from typing import Literal
from datetime import datetime, timedelta
import zmq
import json
import time
import struct
from enum import Enum

from .base import SocketControlledDevice
import config

from schemas.oven import OvenStatus

class OvenActionCode(Enum):
    start = 0
    stop = 1
    pause = 2

class OvenLidActionCode(Enum):
    open = 1
    close = 2

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
            self.result = {"status": "success", "message": self.message}
            return True
        except Exception as e:
            self.is_connected = False
            self.message = f"高温炉设备连接失败: {str(e)}"
            self.result = {"status": "error", "message": self.message}
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
        self.result = {"status": "success", "message": self.message}

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

    def get_specific_device_info(self, sid)->dict:
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
            else:
                return {}
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

    def set_curve_points(self, oven_id: int, curve_points: list):
        """
        设置炉子温度运行曲线
        :param oven_id: 炉子ID
        :param curve_points: 运行曲线点列表
        """
        if not self.is_connected:
            self.result = {"status": "error", "message": "设备未连接"}
            return self.result
        
        # CTRL socket需要独立管理，因为它连接到不同的地址
        # 如果CTRL socket不存在或已断开，重新创建
        if not self._ctrl_socket or not self._ctrl_context:
            try:
                self._ctrl_context, self._ctrl_socket = self._create_socket(zmq.REQ, 5000)  # 创建CTRL socket
                self._ctrl_socket.connect(self.CTRL_ADDR)  # 连接到控制地址
            except Exception as e:
                self.message = f"CTRL Socket创建失败: {str(e)}"
                self.result = {"status": "error", "message": str(e)}
                return self.result

        try:
            current_addr = 80  # 858P 固定起始地址
            for i, point in enumerate(curve_points):
                # 温度下传 (倍率 10)
                temp_bytes = struct.pack('>h', int(point['temp'] * 10.0))
                self._ctrl_socket.send(struct.pack("BBB", 0x01, oven_id, current_addr & 0xFF) + temp_bytes)
                if self._ctrl_socket.recv_string() != "True":
                    self.message = f"第{i + 1}段温度写入失败"
                    self.result = {"status": "error", "message": self.message}
                    return self.result
                time.sleep(0.02)

                # 时间下传 (倍率 10)
                time_addr = current_addr + 1
                time_bytes = struct.pack('>h', int(point['time'] * 10.0))
                self._ctrl_socket.send(struct.pack("BBB", 0x01, oven_id, time_addr & 0xFF) + time_bytes)
                if self._ctrl_socket.recv_string() != "True":
                    self.message = f"第{i + 1}段时间写入失败"
                    self.result = {"status": "error", "message": self.message}
                    return self.result
                time.sleep(0.02)
                current_addr = time_addr + 1
            self.message = f"设置温度曲线成功, 实际发送段数: {len(curve_points)}"
            self.result = {"status": "success", "message": self.message}
            return self.result
        except Exception as e:
            self.message = f"炉{oven_id}运行曲线设置异常: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    def control_lid(self, oven_id: int, action_code: OvenLidActionCode):
        """
        控制炉盖
        :param oven_id: 炉子ID
        :param action_code: 动作代码
            - open=开
            - close=关
        """
        if not self.is_connected:
            self.result = {"status": "error", "message": "设备未连接"}
            return self.result
        
        # CTRL socket需要独立管理，因为它连接到不同的地址
        # 如果CTRL socket不存在或已断开，重新创建
        if not self._ctrl_socket or not self._ctrl_context:
            try:
                self._ctrl_context, self._ctrl_socket = self._create_socket(zmq.REQ, 3000)  # 创建CTRL socket
                self._ctrl_socket.connect(self.CTRL_ADDR)  # 连接到控制地址
            except Exception as e:
                self.message = f"CTRL Socket创建失败: {str(e)}"
                self.result = {"status": "error", "message": str(e)}
                return self.result
        
        try:
            buffer = bytes([0x03, oven_id, 250, 0, action_code.value])
            self._ctrl_socket.send(buffer)
            response = self._ctrl_socket.recv_string()
            success = response != "False"
            if success:
                self.message = f"炉{oven_id}盖控制成功，动作: {action_code}"
                self.result = {"status": "success", "message": self.message}
            else:
                self.message = f"炉{oven_id}盖控制失败"
                self.result = {"status": "error", "message": self.message}
            return self.result
        except Exception as e:
            self.message = f"炉{oven_id}盖控制异常: {str(e)}"
            self.result = {"status": "error", "message": self.message}
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
            return self.result

    def control_oven(self, oven_id: int, action_code: OvenActionCode):
        """控制炉子
        
        :param oven_id: 炉子ID
        :param action_code: 动作代码
            - start=启动
            - stop=停止
            - pause=暂停
        """
        if not self.is_connected:
            self.message = "设备未连接"
            self.result = {"status": "error", "message": self.message}
            return self.result
        
        # CTRL socket需要独立管理，因为它连接到不同的地址
        # 如果CTRL socket不存在或已断开，重新创建
        if not self._ctrl_socket or not self._ctrl_context:
            try:
                self._ctrl_context, self._ctrl_socket = self._create_socket(zmq.REQ, 3000)  # 创建CTRL socket
                self._ctrl_socket.connect(self.CTRL_ADDR)  # 连接到控制地址
            except Exception as e:
                self.message = f"CTRL Socket创建失败: {str(e)}"
                self.result = {"status": "error", "message": self.message}
                return self.result
        
        try:
            packet = struct.pack("BBBBB", 0x01, oven_id, 27, 0, action_code.value)
            self._ctrl_socket.send(packet)
            response = self._ctrl_socket.recv_string()
            if response != "True":
                self.message = f"炉{oven_id}执行{action_code}命令失败"
                self.result = {"status": "error", "message": self.message}
                return self.result
            else:
                self.message = f"炉{oven_id}执行{action_code}命令成功"
                self.result = {"status": "success", "message": self.message}
                return self.result
        except Exception as e:
            self.message = f"炉{oven_id}控制异常: {str(e)}"
            self.result = {"status": "error", "message": self.message}
            return self.result

    def start(self, oven_id: int):
        """启动设备（高温炉启动需要指定具体参数）
        
        :param oven_id: 炉子ID
        """
        return self.control_oven(oven_id, OvenActionCode.start)

    def stop(self, oven_id: int):
        """停止设备
        :param oven_id: 炉子ID
        """
        return self.control_oven(oven_id, OvenActionCode.stop)

    def pause(self, oven_id: int):
        """暂停设备
        :param oven_id: 炉子ID
        """
        return self.control_oven(oven_id, OvenActionCode.pause)

    def get_status(self) -> dict:
        """获取设备状态"""
        # 获取实时数据（短时间采样）
        return self.status

    def get_running_status(self) -> dict:
        """获取设备运行状态"""
        realtime_map = self.get_realtime_data(duration=1.0)
        device_list = self.get_device_list()
        summary_result = []
        for device in device_list:
            sid = int(device.get('SlaveID') or device.get('SlaveId') or device.get('ID') or 0)
            name = device.get('DeviceName') or f"Slave{sid}"
            dtype = device.get('DeviceType') or ""
            rt_data = realtime_map.get(sid)
            item = {
                "设备名称": name, 
                "设备地址": sid,
                "仪表型号": dtype,
                "在线状态": "离线",
                "实际温度": None, 
                "设定温度": None, 
                "状态显示": "无数据",
                "结束时间": "-", 
                "状态": None
            }
            if rt_data:
                device_info = self.get_specific_device_info(sid)
                item["运行曲线"] = device_info.get('CurrentRunName') or device_info.get('CurrentRun') or device_info.get('CurrentWave') or "-"
                item["在线状态"] = "在线"
                item["实际温度"] = rt_data['pv']
                item["设定温度"] = rt_data['sv']
                item["状态"] = "停止" if rt_data['status'] == 1 else "开始"
                minutes_remaining = rt_data['runtime_raw']
                if dtype == "858P": minutes_remaining /= 10.0
                item["结束时间"] = (datetime.now() + timedelta(minutes=minutes_remaining)).strftime("%Y-%m-%d %H:%M") if minutes_remaining > 0 else "-"
                item["状态显示"] = f"阶段{rt_data['step']} 剩余{minutes_remaining / 60.0:.1f}h"

                summary_result.append(item)
        return {"status": "success", "data": summary_result}

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
