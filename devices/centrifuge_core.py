# 文件名：centrifuge_core.py
import socket
import struct
import binascii
import time

class ModbusSender:
    def __init__(self, host, port, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout

    def calculate_crc(self, data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return struct.pack('<H', crc)

    def build_write_command(self, address, value):
        cmd_part = struct.pack('>BBHH', 0x01, 0x06, address, value)
        crc = self.calculate_crc(cmd_part)
        return cmd_part + crc

    def send_raw(self, hex_cmd):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.host, self.port))
            
            # 1. 发送前先清空缓冲区（防止读到旧数据）
            sock.settimeout(0.1)
            try:
                while sock.recv(1024): pass
            except:
                pass
            sock.settimeout(self.timeout)

            # 2. 发送指令
            sock.sendall(hex_cmd)

            # 3. 循环接收数据
            buffer = b''
            start_time = time.time()
            
            # 计算预期的最小长度 (头部3字节: ID+Func+Len)
            # 如果是读指令(03)，我们期望收到 01 03 1C ... (1+1+1+28+2 = 33 bytes)
            expected_header = b'\x01\x03\x1C' 
            is_read_cmd = (hex_cmd[1] == 0x03)
            
            while time.time() - start_time < self.timeout:
                try:
                    chunk = sock.recv(1024)
                    if not chunk: break
                    buffer += chunk
                    
                    # === 核心修复：数据帧自动对齐 ===
                    if is_read_cmd:
                        # 在缓冲区里寻找正确的帧头 01 03 1C
                        # 01(Slave) 03(Func) 1C(28 bytes data)
                        start_idx = buffer.find(expected_header)
                        
                        if start_idx != -1:
                            # 找到了！丢弃前面的垃圾数据
                            buffer = buffer[start_idx:]
                            
                            # 检查长度是否足够 (33字节)
                            if len(buffer) >= 33:
                                # 截取完整的33字节
                                valid_frame = buffer[:33]
                                response_hex = binascii.hexlify(valid_frame).decode('utf-8')
                                return {"status": "success", "hex": response_hex, "bytes": list(valid_frame)}
                        else:
                            # 没找到帧头，如果缓冲区太大还是没找到，说明全是垃圾，清空一部分防止内存溢出
                            if len(buffer) > 100:
                                buffer = buffer[-20:] # 只保留最后20个字节碰运气
                                
                    else:
                        # 如果是写指令(06)，长度固定为8，且头部是 01 06
                        if len(buffer) >= 8 and buffer.startswith(b'\x01\x06'):
                            valid_frame = buffer[:8]
                            response_hex = binascii.hexlify(valid_frame).decode('utf-8')
                            return {"status": "success", "hex": response_hex, "bytes": list(valid_frame)}
                            
                except socket.timeout:
                    break
            
            # 如果超时还没拼出正确的数据
            return {
                "status": "error", 
                "message": f"数据对齐失败，缓冲区: {binascii.hexlify(buffer).decode('utf-8')}"
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            sock.close()

cent_sender = ModbusSender("192.168.0.140", 8000)