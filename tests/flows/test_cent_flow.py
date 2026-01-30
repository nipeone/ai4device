from devices.centrifuge_core import CentrifugeController
from flows.cent_flow import CentrifugeFlowManager


if __name__ == "__main__":
    centrifuge_controller = CentrifugeController(
        host="192.168.0.140",
        port=8000,
        timeout=5
        )

    centrifuge_flow = CentrifugeFlowManager(centrifuge_controller)
    centrifuge_flow.run()