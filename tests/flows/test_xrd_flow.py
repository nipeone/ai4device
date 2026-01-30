from devices.xrd_core import XRDController
from flows.xrd_flow import XRDFlowManager
import time

def main():
    controller = XRDController(
        device_id="99",
        host="192.168.0.144",
        port=8009,
        timeout=10
    )

    # flow = XRDFlowManager(controller)
    # flow.run()


    controller.connect()

    status = controller.get_sample_status()
    print(status)

    # # return

    # # 1. 自动模式
    # self.xrd_controller.start_auto_mode(True)

    # # 判断高压模式是否开启
    # status = self.xrd_controller.get_sample_status()
    # success = status.get("status")
    # power_status = status.get("power status")
    # if success and  not power_status:
    #     self.xrd_controller.set_power_on()


    # # 判断高压是否完成，必须等于ready才能往下执行
    # while(True):
    #     status = self.xrd_controller.get_sample_status()
    #     success = status.get("status")
    #     xray_status = status.get("xray status")
    #     power_status = status.get("power status")
    #     if success and xray_status == "ready" and power_status:
    #         break

    # # 2. 设置电压电流
    # volcur = self.xrd_controller.set_voltage_current(40.0, 40.0)
    # print(volcur)

    # while(True):
    #     status = self.xrd_controller.get_sample_status()
    #     success = status.get("status")
    #     vol = status.get("current voltage")
    #     cur = status.get("current current")
    #     if success and vol > 39.0 and cur > 39.0:
    #         break
    #     else:
    #         print(f"需要电压>40.0、电流>40.0，当前电压：{vol}, 电流：{cur}")

    # # 3. 发送上样请求状态
    # req = self.xrd_controller.get_sample_request()

    # if not req.get("status"):
    #     print(req)
    #     if req.get("message") != "送样位置存在样品，请下样后重新上样":
    #         return

    # # 4. 上样
    # ready = self.xrd_controller.send_sample_ready(
    #     "XY072", 6.0, 80.0, 0.01, 0.1
    # )

    # print(ready)

    # if not ready.get("status"):
    #     print("测试流程失败")
    #     return

    # total_samples = 1
    # while(True):
    #     status = self.xrd_controller.get_sample_status()
    #     if status.get("status"):
    #         print(status)
    #         ready_stations = status.get("ready station", [])
    #         if len(ready_stations) >= total_samples: # 检测完成
    #             print("检测完成")
    #             break
    #         else: 
    #             data_response = self.xrd_controller.get_current_acquire_data() #检测中获取实时数据
    #             if data_response.get("status"):
    #                 energy = data_response.get("Energy")
    #                 intensity = data_response.get("Intensity")

    #     time.sleep(3)

    # # 5. 获取下样请求状态
    # down_response = self.xrd_controller.get_sample_down(1)
    # print(down_response)


    # # 6. 下样
    # down_ready = self.xrd_controller.send_sample_down_ready()

    # print(down_ready)

    # volcur = self.xrd_controller.set_voltage_current(20.0, 5.0)
    # print(volcur)

    


if __name__ == "__main__":
    main()