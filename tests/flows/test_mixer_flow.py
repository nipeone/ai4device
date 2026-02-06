import json

d = '''
{
  "task_name": "test",
  "layout_list": [
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 0,
      "unit_row": 1,
      "unit_id": null,
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Sb",
        "chemical_id": null,
        "add_weight": 100,
        "SSSI": "2-00-25-9",
        "offset": 0.3,
        "custom": {
          "unit": "mg",
          "unitOptions": [
            "mg",
            "g"
          ]
        }
      }
    }
  ],
  "task_template_id_list": []
}
'''
import requests

def main():
    # mixer_controller = MixerController(
    #     api_base_url="http://192.168.3.5:4669",
    #     username="admin",
    #     password="admin"
    #     )

    # mixer_task_model = AddTaskRequest(**json.loads(d))
    # rtn = mixer_controller.add_task(mixer_task_model)
    # print(rtn)
    # flow_manager.run(mixer_task_model)

    payload = {"username": "admin", "password": "admin"}
    response = requests.post(f"http://192.168.3.5:4669/api/Token", json=payload.model_dump(), timeout=5)

    api_headers = {
            "Content-Type": "application/json",
        }
    access_token = response.json().get('access_token')
    token_type = response.json().get('token_type')
    api_headers["Authorization"] = f"{token_type} {access_token}"
    print(api_headers)

    response = requests.post(
            f"http://192.168.3.5:4669/api/AddTask",
            json=d,
            timeout=30,
            headers=api_headers
        )

    print(response.json())

if __name__ == "__main__":
    main()