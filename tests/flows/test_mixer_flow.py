from devices.mixer_core import MixerController
from schemas.mixer import AddTaskRequest
from flows.mix_flow import MixFlowManager

import json

def main():
    mixer_controller = MixerController(
        api_base_url="http://192.168.3.5:4669",
        username="admin",
        password="admin"
        )


    flow_manager = MixFlowManager(mixer_controller)

    with open("data/add_task_body.json", "r") as f:
        mixer_task_model = AddTaskRequest(**json.load(f))

    flow_manager.run(mixer_task_model)

if __name__ == "__main__":
    main()