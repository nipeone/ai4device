"""
XRD衍射仪控制模块
基于TCP Socket通信，使用JSON协议
参考文档：xrd衍射仪api手册.pdf
"""
import socket
import json
import struct
import time
from typing import Dict, Any, Optional
from .base import BaseDevice
import config


class XRDController(BaseDevice):
    """XRD衍射仪设备（TCP Socket控制）"""
    
    def __init__(self, device_id: str = "01",
                 host: str = None,
                 port: int = None,
                 timeout: int = None):
        # 从环境变量获取配置
        host = host or config.XRD_HOST
        port = port or config.XRD_PORT
        timeout = timeout or config.XRD_TIMEOUT
        super().__init__("socket_xrd_" + device_id, "Socket", device_id)
        self.host = host
        self.port = port
        self.socket = None  # TCP Socket对象
        self.socket_timeout = timeout  # Socket超时时间（秒）
        self.xrd_status_cache = {}

    def _send_command(self, command: str, content: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送命令到XRD设备并接收响应
        :param command: 命令名称
        :param content: 命令内容（可选）
        :return: 响应字典
        """
        if not self.is_connected or not self.socket:
            return {
                "status": False,
                "message": "设备未连接"
            }
        
        try:
            # 构建命令字典
            cmd_dict = {"command": command}
            if content:
                cmd_dict["content"] = content
            
            # 序列化为JSON
            cmd_json = json.dumps(cmd_dict, ensure_ascii=False).encode('utf-8')
            
            # 发送命令长度（4字节，大端序）
            cmd_length = struct.pack('>I', len(cmd_json))
            self.socket.sendall(cmd_length)
            
            # 发送命令数据
            self.socket.sendall(cmd_json)
            
            # 接收响应数据
            response = self._recv_response()
            return response
            
        except socket.timeout:
            return {
                "status": False,
                "message": "通信超时"
            }
        except json.JSONDecodeError as e:
            return {
                "status": False,
                "message": f"JSON解析失败: {str(e)}"
            }
        except Exception as e:
            self.is_connected = False
            return {
                "status": False,
                "message": f"通信错误: {str(e)}"
            }

    def _recv_response(self) -> Dict[str, Any]:
        """
        接收响应数据
        :return: 响应字典
        """
        # 接收响应长度（4字节，大端序）
        try:
            header = self.socket.recv(4)
            if not header:
                return {
                    "status": False,
                    "message": "接收响应长度失败"
                }
                
            length_bytes = struct.unpack('>I', header)[0]
            data = b''
            while len(data) < length_bytes:
                chunk = self.socket.recv(length_bytes - len(data))
                if not chunk:
                    raise Exception("接收响应数据失败")
                data += chunk
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            return {
                "status": False,
                "message": f"接收响应数据失败: {str(e)}"
            }

    def connect(self):
        """连接XRD衍射仪设备"""
        # 如果已经连接，先断开
        if self.is_connected:
            self.disconnect()
        
        try:
            # 创建TCP Socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.socket_timeout)
            
            # 连接到设备
            self.socket.connect((self.host, self.port))
            
            # 测试连接：获取设备状态
            test_response = self.get_sample_status()
            if test_response.get("status"):
                self.is_connected = True
                self.message = f"XRD衍射仪设备连接成功 ({self.host}:{self.port})"
                return True
            else:
                self.socket.close()
                self.socket = None
                self.is_connected = False
                self.message = f"XRD衍射仪连接测试失败: {test_response.get('message', '未知错误')}"
                return False
        except socket.timeout:
            self.is_connected = False
            self.message = "XRD衍射仪连接超时"
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False
        except Exception as e:
            self.is_connected = False
            self.message = f"XRD衍射仪设备连接失败: {str(e)}"
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False

    def disconnect(self):
        """断开XRD衍射仪设备连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.is_connected = False
        self.message = "XRD衍射仪设备已断开连接"

    # ===================== API命令实现 =====================
    
    def start_auto_mode(self, status: bool) -> Dict[str, Any]:
        """
        启动或停止自动模式
        :param status: True-启动自动模式，False-停止自动模式
        :return: 响应字典
        """
        response = self._send_command("START_AUTO_MODE", {"status": status})
        if response.get("status"):
            self.message = response.get("message", "自动模式设置成功")
            self.result = response
        else:
            self.message = response.get("message", "自动模式设置失败")
            self.result = response
        return response

    def get_sample_request(self) -> Dict[str, Any]:
        """
        上样请求，检查是否允许上样
        :return: 响应字典，status=True表示允许上样
        """
        response = self._send_command("GET_SAMPLE_REQUEST")
        if response.get("status"):
            self.message = "允许上样"
        else:
            self.message = response.get("message", "不允许上样")
        return response

    def send_sample_ready(self, sample_id: str, start_theta: float, 
                          end_theta: float, increment: float, exp_time: float) -> Dict[str, Any]:
        """
        送样完成后，发送样品信息和采集参数
        :param sample_id: 样品标识符
        :param start_theta: 起始角度（≥5°）
        :param end_theta: 结束角度（≥5.5°，且必须大于start_theta）
        :param increment: 角度增量（≥0.005）
        :param exp_time: 曝光时间（0.1-5.0秒）
        :return: 响应字典
        """
        content = {
            "sample_id": sample_id,
            "start_theta": start_theta,
            "end_theta": end_theta,
            "increment": increment,
            "exp_time": exp_time
        }
        response = self._send_command("SEND_SAMPLE_READY", content)
        if response.get("status"):
            self.message = "采集参数发送成功"
            self.result = response
        else:
            self.message = response.get("message", "采集参数发送失败")
            self.result = response
        return response

    def get_current_acquire_data(self) -> Dict[str, Any]:
        """
        获取当前正在采集的样品数据
        :return: 响应字典，包含Energy和Intensity数组
        """
        response = self._send_command("GET_CURRENT_ACQUIRE_DATA")
        return response

    def get_sample_status(self) -> Dict[str, Any]:
        """
        获取工位样品状态及设备状态
        :return: 响应字典，包含Station信息
        """
        response = self._send_command("GET_SAMPLE_STATUS")
        if response.get("status") and "Station" in response:
            self.xrd_status_cache = response.get("Station", {})
        return response

    def get_sample_down(self, sample_station: int) -> Dict[str, Any]:
        """
        下样请求
        :param sample_station: 下样工位（1-30）
        :return: 响应字典，包含样品数据
        """
        content = {"Sample station": sample_station}
        response = self._send_command("GET_SAMPLE_DOWN", content)
        if response.get("status"):
            self.message = f"下样成功，工位{sample_station}"
            self.result = response
        else:
            self.message = response.get("message", f"下样失败，工位{sample_station}")
            self.result = response
        return response

    def send_sample_down_ready(self) -> Dict[str, Any]:
        """
        下样完成命令，在下样全部完成后必须发送
        :return: 响应字典
        """
        response = self._send_command("SEND_SAMPLE_DOWN_READY")
        if response.get("status"):
            self.message = "下样完成信号发送成功"
            self.result = response
        else:
            self.message = response.get("message", "下样完成信号发送失败")
            self.result = response
        return response

    def set_power_on(self) -> Dict[str, Any]:
        """
        高压电源开启
        :return: 响应字典
        """
        response = self._send_command("SET_POWER_ON")
        if response.get("status"):
            self.message = "高压打开信号发送成功"
            self.result = response
        else:
            self.message = response.get("message", "高压打开失败")
            self.result = response
        return response

    def set_power_off(self) -> Dict[str, Any]:
        """
        高压电源关闭
        :return: 响应字典
        """
        response = self._send_command("SET_POWER_OFF")
        if response.get("status"):
            self.message = "高压关闭信号发送成功"
            self.result = response
        else:
            self.message = response.get("message", "高压关闭失败")
            self.result = response
        return response

    def set_voltage_current(self, voltage: float, current: float) -> Dict[str, Any]:
        """
        设置高压电源电压和电流
        :param voltage: 电压值 (kV)
        :param current: 电流值 (mA)
        :return: 响应字典
        """
        content = {
            "voltage": voltage,
            "current": current
        }
        response = self._send_command("SET_VOLTAGE_CURRENT", content)
        if response.get("status"):
            self.message = f"设置电压电流成功 (电压:{voltage}kV, 电流:{current}mA)"
            self.result = response
        else:
            self.message = response.get("message", "设置电压电流失败")
            self.result = response
        return response

    # ===================== 基类抽象方法实现 =====================

    def start(self):
        """启动设备（启动自动模式）"""
        if not self.is_connected:
            self.message = "设备未连接"
            self.result = {"status": False, "message": "设备未连接"}
            return False
        
        response = self.start_auto_mode(True)
        return response.get("status", False)

    def stop(self):
        """停止设备（停止自动模式）"""
        if not self.is_connected:
            self.message = "设备未连接"
            self.result = {"status": False, "message": "设备未连接"}
            return False
        
        response = self.start_auto_mode(False)
        return response.get("status", False)

    def get_status(self) -> dict:
        """获取设备状态"""
        status_info = {
            "name": self.device_name,
            "connected": self.is_connected,
            "host": self.host,
            "port": self.port,
            "status": self.status.value if self.status else "unknown"
        }
        
        # 如果已连接，获取详细状态
        if self.is_connected:
            sample_status = self.get_sample_status()
            if sample_status.get("status") and "Station" in sample_status:
                station = sample_status["Station"]
                status_info.update({
                    "xray_status": station.get("xray status", False),
                    "power_status": station.get("power status", False),
                    "current_voltage": station.get("current voltage", 0.0),
                    "current_current": station.get("current current", 0.0),
                    "untest_station": station.get("untest station", []),
                    "ready_station": station.get("ready station", [])
                })
        
        return status_info

    def get_result(self) -> dict:
        """获取设备结果"""
        return self.result if self.result else {
            "status": False,
            "message": "无操作结果"
        }

    def get_message(self) -> str:
        """获取设备消息"""
        return self.message if self.message else "XRD衍射仪设备就绪"


# 创建全局实例（保持向后兼容）
xrd_controller = XRDController()
