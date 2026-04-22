from devices.cent_core import CentController
from flows.cent_flow import CentrifugeFlowManager


if __name__ == "__main__":
    cent_controller = CentController(
        host="192.168.0.140",
        port=8000,
        timeout=5
        )

    centrifuge_flow = CentrifugeFlowManager(cent_controller)
    centrifuge_flow.run()