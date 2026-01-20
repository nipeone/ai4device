import json
import struct

class XRDController:
    def __init__(self):
        self.client_socket = None

    def send_command(self, command, content=None):
        if not self.client_socket:
            return False
        try:
            #构建命令字典
            cmd_dict = {"command": command}
            if content:
                cmd_dict["content"] = content
            #序列化为JS0N
            cmd_json = json.dumps(cmd_dict).encode('utf-8')

            #发送命令长度
            cmd_length = struct.pack('>I', len(cmd_json))
            self.client_socket.sendall(cmd_length)
            #发送命令数据
            self.client_socket.sendall(cmd_json)
            return True
        except Exception as e:
            self.connection_status.emit(False, f"发送命令失败:{str(e)}")
            return False