# 文件名：door_core.py
import zmq
import time


class DoorController:
    def __init__(self):
        # 底层服务地址
        self.target_address = "tcp://127.0.0.1:49202"

    def _get_socket(self):
        """创建一个新的socket连接"""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(self.target_address)
        # 设置超时 1000ms
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        return context, socket

    def get_door_status(self, door_index: int):
        """
        获取门的实时状态
        发送: [0x02, SlaveID, 0, 0, 0]
        """
        if not (1 <= door_index <= 6):
            return "无效编号"

        slave_id = (door_index + 1) // 2
        is_channel_1 = (door_index % 2 == 0)
        buffer = bytes([0x02, slave_id, 0, 0, 0])

        context, socket = self._get_socket()
        try:
            socket.send(buffer)
            response_bytes = socket.recv()

            if len(response_bytes) == 2:
                target_byte = response_bytes[1] if is_channel_1 else response_bytes[0]
                is_open = (target_byte & 1) == 1
                return "开启" if is_open else "关闭"
            else:
                return "数据异常"

        except zmq.Again:
            return "通信超时"
        except Exception as e:
            return f"错误:{str(e)}"
        finally:
            socket.close()
            context.term()

    def send_command(self, door_index: int, action: str):
        """
        控制开门/关门
        ** 新增逻辑：同组互斥 **
        """
        if not (1 <= door_index <= 6):
            return {"status": "error", "message": "门编号必须是 1-6"}

        # === 1. 新增：互斥逻辑检查 ===
        # 只有在请求 "开门" (open) 时才需要检查同组的另一个门
        if action == "open":
            # 1.1 寻找同组的搭档 (Partner)
            if door_index % 2 != 0:
                # 如果是奇数门(1,3,5)，搭档是下一个(2,4,6)
                partner_index = door_index + 1
            else:
                # 如果是偶数门(2,4,6)，搭档是上一个(1,3,5)
                partner_index = door_index - 1

            # 1.2 读取搭档的状态
            # 注意：这里调用自己的 get_door_status 方法
            partner_status = self.get_door_status(partner_index)

            # 1.3 如果搭档是开着的，必须先把它关掉
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

                # 可选：稍微停顿一下，给硬件反应时间（0.5秒）
                time.sleep(0.5)

        # === 2. 原有控制逻辑 ===
        slave_id = (door_index + 1) // 2
        channel = 0 if door_index % 2 == 1 else 1
        value = 1 if action == "open" else 2

        # 控制指令: 0x01 ...
        buffer = bytes([0x01, slave_id, channel, 0, value])

        context, socket = self._get_socket()
        try:
            socket.send(buffer)
            frame_string = socket.recv_string()

            if frame_string == "True":
                return {"status": "success", "door": door_index, "action": action}
            else:
                return {"status": "fail", "message": "底层返回False"}
        except zmq.Again:
            return {"status": "error", "message": "通信超时"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            socket.close()
            context.term()

door_ctrl = DoorController()