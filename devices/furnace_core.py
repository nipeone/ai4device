# 文件名：luzi_core.py
import zmq
import json
import time

class OvenDriver:
    def __init__(self):
        # 你的配置
        self.REQ_ADDR = "tcp://127.0.0.1:49206"
        self.SUB_ADDR = "tcp://127.0.0.1:49200"
        self.CTRL_ADDR = "tcp://127.0.0.1:49201"
        self.SUB_TOPIC = b"Oven"

    def get_device_list(self):
        """获取所有设备的基础列表"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.RCVTIMEO = 2000
        socket.LINGER = 0
        try:
            socket.connect(self.REQ_ADDR)
            socket.send_string("DeviceDal.GetList@@@")
            return json.loads(socket.recv_string())
        except:
            return []
        finally:
            socket.close()
            context.term()

    def get_specific_device_info(self, sid):
        """
        [新增] 获取特定设备的详细信息
        用于读取：运行曲线名称、仪表型号等详细字段
        """
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.RCVTIMEO = 1000
        socket.LINGER = 0
        try:
            socket.connect(self.REQ_ADDR)
            # 发送特定指令查询单个设备详情
            socket.send_string(f"DeviceDal.GetList@@@SlaveID = {sid}")
            data = json.loads(socket.recv_string())
            # 返回列表中的第一个对象，或者对象本身
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
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.RCVTIMEO = 1000
        socket.LINGER = 0
        latest_data = {}

        try:
            socket.connect(self.SUB_ADDR)
            socket.setsockopt(zmq.SUBSCRIBE, self.SUB_TOPIC)
            
            # 稍微等待连接建立
            time.sleep(0.1)
            
            start_time = time.time()
            # 循环读取，直到达到指定的持续时间
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
                    time.sleep(0.01) # 短暂休眠避免CPU满载
        except Exception as e:
            print(f"Oven Sub Error: {e}")
        finally:
            socket.close()
            context.term()
        return latest_data

    def control_lid(self, rid, action_code):
        """控制逻辑"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.RCVTIMEO = 3000
        try:
            socket.connect(self.CTRL_ADDR)
            buffer = bytes([0x03, rid, 250, 0, action_code])
            socket.send(buffer)
            response = socket.recv_string()
            return response != "False", response
        except Exception as e:
            return False, str(e)
        finally:
            socket.close()
            context.term()

oven_driver = OvenDriver()