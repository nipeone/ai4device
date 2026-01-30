from devices.oven_core import OvenController, OvenActionCode, OvenLidActionCode
from schemas.oven import CurvePoint
import time


def main():
    oven_controller = OvenController(
        req_addr="tcp://192.168.0.2:49206",
        sub_addr="tcp://192.168.0.2:49200",
        ctrl_addr="tcp://192.168.0.2:49201"
        )

    # 针对单个炉子进行
    spec_oven_id = 3

    # 1. 连接
    b = oven_controller.connect()
    print(oven_controller.result)
    if not b:
        return

    # 2. 开盖
    result = oven_controller.control_lid(spec_oven_id, OvenLidActionCode.open)
    print(result)

    time.sleep(5)

    # 2.1 获取状态
    status = oven_controller.get_running_status()
    print(status)
    print("-"*20)

    # TODO 放样

    # 3. 关盖
    oven_controller.control_lid(3, OvenLidActionCode.close)


    time.sleep(5)

    status = oven_controller.get_running_status()

    print(status)
    print("-"*20)

    # 3.1 设置曲线点

    points = [
        CurvePoint(temperature=245, time=3),
        CurvePoint(temperature=260, time=1), 
        CurvePoint(temperature=275, time=-1)
    ]
    result = oven_controller.set_curve_points(spec_oven_id, points)
    print(result)

    time.sleep(5)

    # 4. 启动

    oven_controller.start(spec_oven_id)

    # 计算燃烧时间
    time.sleep(sum([p.time*60 for p in points[:-1]]) + 60)

    status = oven_controller.get_running_status()
    print(status)

    # 5. 停止
    oven_controller.stop(spec_oven_id)

    while True:
        if status.get("status"):
            if status.get("data").get("实际温度") < 500:
                oven_controller.control_lid(spec_oven_id, OvenLidActionCode.open)
                break

        time.sleep(5)


if __name__ == "__main__":
    main()

