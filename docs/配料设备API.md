# 配料设备API

## 执行顺序
1. 点击创建任务时
  1. GetSetUp
2. 点击保存任务时
  1. AddTask
  2. GetResourceInfo
  3. GetTaskInfo
  4. GetResourceInfo
  5. GetSetUp

## 获取资源信息 （GetResourceInfo）

### 基本信息
| 项         | 内容                               |
| ---------- | ---------------------------------- |
| 接口地址   | http://127.0.0.1:4669/api/GetResourceInfo |
| 请求方式   | POST                               |
| 说明       | 获取所有任务信息                   |

### 请求参数
| 变量名  | 类型   | 是否必填 | 描述                               | 示例 |
| ------- | ------ | -------- | ---------------------------------- | ---- |
| roll    | int    | 是      |  默认值0                       | 0    |

### 请求参数示例
```json
{"roll":0}
```

### 返回参数示例
```json
{
    "code": 200,
    "msg": "success",
    "result": null,
    "data": null,
    "resource_list": [
        {
            "fid": 1,
            "layout_code": "IPF1-1:-1",
            "working_code": "",
            "resource_type": "PF100M5R1C_2",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IPF1-1:-1",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1769063050,
            "updated_at": 1773381468,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 17,
            "layout_code": "IPF1-1:0",
            "working_code": "",
            "resource_type": "PF100M5R1C_2",
            "substance": "Te",
            "chemical_id": 37,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 20000.0,
            "cur_volume": 0.0,
            "cur_weight": 25000.0,
            "available_volume": 0.0,
            "available_weight": 25000.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "g",
            "source_layout_code": "IPF1-1:0",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1769064153,
            "updated_at": 1773381468,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 2,
            "layout_code": "IPF1-1:1",
            "working_code": "",
            "resource_type": "PF100M5R1C_2",
            "substance": "Se",
            "chemical_id": 45,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 50000.0,
            "cur_volume": 0.0,
            "cur_weight": 36653.0,
            "available_volume": 0.0,
            "available_weight": 36853.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "g",
            "source_layout_code": "IPF1-1:1",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1769063050,
            "updated_at": 1774938444,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 3,
            "layout_code": "IPF1-1:2",
            "working_code": "",
            "resource_type": "PF100M5R1C_2",
            "substance": "Bi",
            "chemical_id": 43,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 50000.0,
            "cur_volume": 0.0,
            "cur_weight": 44656.8,
            "available_volume": 0.0,
            "available_weight": 44656.8,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "g",
            "source_layout_code": "IPF1-1:2",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1769063050,
            "updated_at": 1773381468,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 18,
            "layout_code": "IPF1-1:4",
            "working_code": "",
            "resource_type": "PF100M5R1C_2",
            "substance": "Ge",
            "chemical_id": 41,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 10000.0,
            "cur_volume": 0.0,
            "cur_weight": 7061.7,
            "available_volume": 0.0,
            "available_weight": 7061.7,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "g",
            "source_layout_code": "IPF1-1:4",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1769064177,
            "updated_at": 1773381468,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 15,
            "layout_code": "IPF2-1:-1",
            "working_code": "",
            "resource_type": "PF30M5R1C_2",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IPF2-1:-1",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1769063112,
            "updated_at": 1773380804,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 41,
            "layout_code": "IPF2-1:1",
            "working_code": "",
            "resource_type": "PF30M5R1C_2",
            "substance": "Ti",
            "chemical_id": 55,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 15000.0,
            "cur_volume": 0.0,
            "cur_weight": 14004.0,
            "available_volume": 0.0,
            "available_weight": 15000.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "g",
            "source_layout_code": "IPF2-1:1",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1773380804,
            "updated_at": 1773382957,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 16,
            "layout_code": "IPF2-1:2",
            "working_code": "",
            "resource_type": "PF30M5R1C_2",
            "substance": "Sb",
            "chemical_id": 44,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 50000.0,
            "cur_volume": 0.0,
            "cur_weight": 45651.2,
            "available_volume": 0.0,
            "available_weight": 45651.2,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "g",
            "source_layout_code": "IPF2-1:2",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1769063112,
            "updated_at": 1773380804,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 55,
            "layout_code": "IT-1:-1",
            "working_code": "",
            "resource_type": "CC10R10C",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IT-1:-1",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1774938494,
            "updated_at": 1774938494,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 56,
            "layout_code": "IT-1:0",
            "working_code": "",
            "resource_type": "CC10R10C",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IT-1:0",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1774938494,
            "updated_at": 1774938494,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 57,
            "layout_code": "IT-1:1",
            "working_code": "",
            "resource_type": "CC10R10C",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IT-1:1",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1774938494,
            "updated_at": 1774938494,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 58,
            "layout_code": "IT-1:2",
            "working_code": "",
            "resource_type": "CC10R10C",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IT-1:2",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1774938494,
            "updated_at": 1774938494,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 59,
            "layout_code": "IT-1:10",
            "working_code": "",
            "resource_type": "CC10R10C",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IT-1:10",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1774938494,
            "updated_at": 1774938494,
            "with_cap": false,
            "used": false
        },
        {
            "fid": 60,
            "layout_code": "IT-1:11",
            "working_code": "",
            "resource_type": "CC10R10C",
            "substance": "",
            "chemical_id": null,
            "material_batch_number": null,
            "initial_volume": 0.0,
            "initial_weight": 0.0,
            "cur_volume": 0.0,
            "cur_weight": 0.0,
            "available_volume": 0.0,
            "available_weight": 0.0,
            "tray_QR_code": "",
            "QR_code": "",
            "unit": "",
            "source_layout_code": "IT-1:11",
            "with_magneton": false,
            "usage_times": 0,
            "status": 0,
            "color": null,
            "created_at": 1774938494,
            "updated_at": 1774938494,
            "with_cap": false,
            "used": false
        }
    ]
}
```

## 获取单个任务详情（GetTaskInfo）

### 基本信息
| 项         | 内容                               |
| ---------- | ---------------------------------- |
| 接口地址   | http://127.0.0.1:4669/api/GetTaskInfo |
| 请求方式   | POST                               |
| 说明       | 获取所有任务信息                   |


### 请求参数
| 变量名  | 类型   | 是否必填 | 描述                               | 示例 |
| ------- | ------ | -------- | ---------------------------------- | ---- |
| task_id | string | 是      | 任务id，若不传，则返回第一个任务 | 1    |
| roll    | int    | 是      |  默认值0                       | 0    |


### 请求参数示例
```json
{
  "task_id": 10,
  "roll": 0
}
```


### 返回参数
| 变量名         | 类型      | 描述                               | 示例      |
| -------------- | --------- | ---------------------------------- | --------- |
| task_id        | int       | 任务id                             | 1         |
| task_name      | string    | 任务名称                           | test      |
| unit_save_json | string    | 保存的unit                         | [{"layout_code": ""}] |
| status         | int       | 任务状态                           | 2         |
| creator        | string    | 创建人                             | admin     |
| task_begin_time| timestamp | 任务开始时间                       | null |
| task_end_time  | timestamp | 任务结束时间                       | null |
| created_at     | timestamp | 任务创建时间                       | 1775098180.0|
| updated_at     | timestamp | 任务更新时间                       | 1774514176.0|
| unit_list      | array     | 任务单元列表                       | -         |


### 返回示例
```json
{
    "task_id": 163,
    "task_name": "xy001",
    "unit_save_json": "[{\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 0, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b03d\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Sb\", \"chemical_id\": 44, \"SSSI\": \"2-00-25-9\", \"add_weight\": 535.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 1, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b03e\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Sb\", \"chemical_id\": 44, \"SSSI\": \"2-00-25-9\", \"add_weight\": 535.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 2, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b03f\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Sb\", \"chemical_id\": 44, \"SSSI\": \"2-00-25-9\", \"add_weight\": 459.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 3, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b040\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Sb\", \"chemical_id\": 44, \"SSSI\": \"2-00-25-9\", \"add_weight\": 535.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 4, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b041\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Sb\", \"chemical_id\": 44, \"SSSI\": \"2-00-25-9\", \"add_weight\": 535.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 5, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b042\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Sb\", \"chemical_id\": 44, \"SSSI\": \"2-00-25-9\", \"add_weight\": 535.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 6, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b043\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Bi\", \"chemical_id\": 43, \"SSSI\": \"2-00-23-7\", \"add_weight\": 767, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 7, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b044\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Bi\", \"chemical_id\": 43, \"SSSI\": \"2-00-23-7\", \"add_weight\": 767, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 8, \"unit_row\": 0, \"unit_id\": \"unit-19d4c18b045\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Bi\", \"chemical_id\": 43, \"SSSI\": \"2-00-23-7\", \"add_weight\": 767, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 0, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b046\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Ge\", \"chemical_id\": 41, \"SSSI\": \"2-00-21-5\", \"add_weight\": 319.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 1, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b047\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Ge\", \"chemical_id\": 41, \"SSSI\": \"2-00-21-5\", \"add_weight\": 319.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 2, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b048\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Ge\", \"chemical_id\": 41, \"SSSI\": \"2-00-21-5\", \"add_weight\": 273.9, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 3, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b049\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Ge\", \"chemical_id\": 41, \"SSSI\": \"2-00-21-5\", \"add_weight\": 319.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 4, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b04a\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Ge\", \"chemical_id\": 41, \"SSSI\": \"2-00-21-5\", \"add_weight\": 319.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 5, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b04b\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Ge\", \"chemical_id\": 41, \"SSSI\": \"2-00-21-5\", \"add_weight\": 319.2, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 6, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b04c\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Te\", \"chemical_id\": 37, \"SSSI\": \"2-00-17-9\", \"add_weight\": 3746.4, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 7, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b04d\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Te\", \"chemical_id\": 37, \"SSSI\": \"2-00-17-9\", \"add_weight\": 3746.4, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 8, \"unit_row\": 1, \"unit_id\": \"unit-19d4c18b04e\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Te\", \"chemical_id\": 37, \"SSSI\": \"2-00-17-9\", \"add_weight\": 3746.4, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 0, \"unit_row\": 2, \"unit_id\": \"unit-19d4c18b04f\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Se\", \"chemical_id\": 45, \"SSSI\": \"2-00-26-0\", \"add_weight\": 2082.6, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 1, \"unit_row\": 2, \"unit_id\": \"unit-19d4c18b050\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Se\", \"chemical_id\": 45, \"SSSI\": \"2-00-26-0\", \"add_weight\": 2082.6, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 2, \"unit_row\": 2, \"unit_id\": \"unit-19d4c18b051\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Se\", \"chemical_id\": 45, \"SSSI\": \"2-00-26-0\", \"add_weight\": 2082.6, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 3, \"unit_row\": 2, \"unit_id\": \"unit-19d4c18b052\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Te\", \"chemical_id\": 37, \"SSSI\": \"2-00-17-9\", \"add_weight\": 2406.3, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 4, \"unit_row\": 2, \"unit_id\": \"unit-19d4c18b053\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Te\", \"chemical_id\": 37, \"SSSI\": \"2-00-17-9\", \"add_weight\": 2406.3, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}, {\"layout_code\": \"\", \"src_layout_code\": \"\", \"resource_type\": \"CC10R10C\", \"tray_QR_code\": \"\", \"status\": 0, \"QR_code\": \"\", \"unit_type\": \"exp_add_powder\", \"unit_column\": 5, \"unit_row\": 2, \"unit_id\": \"unit-19d4c18b054\", \"process_json\": {\"resource_type\": \"CC10R10C\", \"substance\": \"Te\", \"chemical_id\": 37, \"SSSI\": \"2-00-17-9\", \"add_weight\": 2406.3, \"offset\": 0.3, \"custom\": {\"unit\": \"mg\", \"unitOptions\": [\"mg\", \"g\"]}}}]",
    "status": 0,
    "creator": "admin",
    "task_begin_time": null,
    "task_end_time": null,
    "created_at": 1775098180.0,
    "updated_at": 1774514176.0,
    "is_audit_log": 1,
    "task_template_id_list": [],
    "task_setup": {
        "subtype": null,
        "powder_100_30": false,
        "powder_30_100": false,
        "added_slots": ""
    },
    "unit_list": [
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 0,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b03d",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Sb",
                "chemical_id": 44,
                "SSSI": "2-00-25-9",
                "add_weight": 535.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 1,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b03e",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Sb",
                "chemical_id": 44,
                "SSSI": "2-00-25-9",
                "add_weight": 535.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 2,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b03f",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Sb",
                "chemical_id": 44,
                "SSSI": "2-00-25-9",
                "add_weight": 459.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 3,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b040",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Sb",
                "chemical_id": 44,
                "SSSI": "2-00-25-9",
                "add_weight": 535.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 4,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b041",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Sb",
                "chemical_id": 44,
                "SSSI": "2-00-25-9",
                "add_weight": 535.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 5,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b042",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Sb",
                "chemical_id": 44,
                "SSSI": "2-00-25-9",
                "add_weight": 535.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 6,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b043",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Bi",
                "chemical_id": 43,
                "SSSI": "2-00-23-7",
                "add_weight": 767,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 7,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b044",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Bi",
                "chemical_id": 43,
                "SSSI": "2-00-23-7",
                "add_weight": 767,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 8,
            "unit_row": 0,
            "unit_id": "unit-19d4c18b045",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Bi",
                "chemical_id": 43,
                "SSSI": "2-00-23-7",
                "add_weight": 767,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 0,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b046",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Ge",
                "chemical_id": 41,
                "SSSI": "2-00-21-5",
                "add_weight": 319.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 1,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b047",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Ge",
                "chemical_id": 41,
                "SSSI": "2-00-21-5",
                "add_weight": 319.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 2,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b048",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Ge",
                "chemical_id": 41,
                "SSSI": "2-00-21-5",
                "add_weight": 273.9,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 3,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b049",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Ge",
                "chemical_id": 41,
                "SSSI": "2-00-21-5",
                "add_weight": 319.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 4,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b04a",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Ge",
                "chemical_id": 41,
                "SSSI": "2-00-21-5",
                "add_weight": 319.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 5,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b04b",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Ge",
                "chemical_id": 41,
                "SSSI": "2-00-21-5",
                "add_weight": 319.2,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 6,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b04c",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Te",
                "chemical_id": 37,
                "SSSI": "2-00-17-9",
                "add_weight": 3746.4,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 7,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b04d",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Te",
                "chemical_id": 37,
                "SSSI": "2-00-17-9",
                "add_weight": 3746.4,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 8,
            "unit_row": 1,
            "unit_id": "unit-19d4c18b04e",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Te",
                "chemical_id": 37,
                "SSSI": "2-00-17-9",
                "add_weight": 3746.4,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 0,
            "unit_row": 2,
            "unit_id": "unit-19d4c18b04f",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Se",
                "chemical_id": 45,
                "SSSI": "2-00-26-0",
                "add_weight": 2082.6,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 1,
            "unit_row": 2,
            "unit_id": "unit-19d4c18b050",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Se",
                "chemical_id": 45,
                "SSSI": "2-00-26-0",
                "add_weight": 2082.6,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 2,
            "unit_row": 2,
            "unit_id": "unit-19d4c18b051",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Se",
                "chemical_id": 45,
                "SSSI": "2-00-26-0",
                "add_weight": 2082.6,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 3,
            "unit_row": 2,
            "unit_id": "unit-19d4c18b052",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Te",
                "chemical_id": 37,
                "SSSI": "2-00-17-9",
                "add_weight": 2406.3,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 4,
            "unit_row": 2,
            "unit_id": "unit-19d4c18b053",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Te",
                "chemical_id": 37,
                "SSSI": "2-00-17-9",
                "add_weight": 2406.3,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        },
        {
            "layout_code": "",
            "src_layout_code": "",
            "resource_type": "CC10R10C",
            "tray_QR_code": "",
            "status": 0,
            "QR_code": "",
            "unit_type": "exp_add_powder",
            "unit_column": 5,
            "unit_row": 2,
            "unit_id": "unit-19d4c18b054",
            "process_json": {
                "resource_type": "CC10R10C",
                "substance": "Te",
                "chemical_id": 37,
                "SSSI": "2-00-17-9",
                "add_weight": 2406.3,
                "offset": 0.3,
                "custom": {
                    "unit": "mg",
                    "unitOptions": [
                        "mg",
                        "g"
                    ]
                }
            },
            "layout_code_ref": ""
        }
    ]
}
```

----------------------------------------------


## 创建任务之前的请求，暂时不知道用途 (GetSetUp)

### 基本信息
| 项         | 内容                               |
| ---------- | ---------------------------------- |
| 接口地址   | http://127.0.0.1:4669/api/GetSetUp |
| 请求方式   | POST                               |
| 说明       | 获取创建任务的信息                   |

### 请求参数
  无

### 返回参数
  -

### 返回示例

```json
{
    "required_tray_code": false,
    "required_medium_code": false,
    "method_audit_log": true,
    "task_audit_log": true,
    "addition_timeout": 360,
    "accuracy": 0.5,
    "substance_shortage_nums": 5,
    "created_at": "2023-02-06T16:00:27",
    "updated_at": "2026-03-13T14:08:33",
    "weight_node": 45,
    "accuracy_30mL": 0.3,
    "accuracy_100mL": 0.3,
    "small_substance_shortage_nums": 100,
    "big_substance_shortage_nums": 500
}
```

## 创建任务（AddTask）

### 基本信息
| 项         | 内容                               |
| ---------- | ---------------------------------- |
| 接口地址   | http://127.0.0.1:4669/api/AddTask  |
| 请求方式   | POST                               |
| 说明       | 添加任务，如果有task_id，则更新    |


### 请求参数
| 变量名               | 类型    | 是否必填 | 描述                                         | 示例           |
| -------------------- | ------- | -------- | -------------------------------------------- | -------------- |
| task_setup           | object  | 是       | -                                           | 1              |
| task_id              | int     | 是       | 任务id，如果是新增任务，task_id填0           | 1              |
| task_name            | string  | 是       | 任务名称                                     | test           |
| is_audit_log         | boolean | 否       | 是否审计                                     | true           |
| type                 | int     | 是       | 类型                                         | 2              |
| layout_list          | array   | 是       | 任务单元列表                                 | -              |
| added_slots          | string  | 是       | -                                           |            |
| task_template_id_list| array   | 否       | 任务模板id列表，有填表示是通过模板配置的实验 | []          |



### layout_list参数说明
| 变量名     | 类型   | 是否必填 | 描述                                                         | 示例           |
| ---------- | ------ | -------- | ------------------------------------------------------------ | -------------- |
| layout_code| string | 否       | 资源位置编码，为托盘中的试管位置，从0开始                   | N-1-1:1        |
| substance  | string | 否       | 资源类型                                                     | PB50           |
| resource_type| string | 否      | 资源类型                                                     | TT8T           |
| tray_QR_code| string | 否      | 托盘二维码                                                   | sg09782653     |
| unit_column| int    | 是       | 任务单元所在列                                               | 0              |
| unit_row   | int    | 是       | 任务单元所在行                                               | 1              |
| unit_type  | string | 是       | 任务单元类型，不同设备类型不同，请参考上位机软件创建任务时支持的任务单元类型 | exp_add_solid  |
| unit_id    | string | 是       | 任务单元id，唯一，不能重复，必须以"unit-"开头                | unit-186392addr6 |
| process_json| json  | 是       | 任务单元数据                                                 | -              |


### process_json参数说明
| 变量名           | 类型   | 是否必填 | 描述                                                     | 示例                     |
| ---------------- | ------ | -------- | -------------------------------------------------------- | ------------------------ |
| src_layout_code  | string | 否       | 原始资源位置编码                                         | N-1-1:1                  |
| resource_type    | string | 否       | 资源类型，需和上料时对应位置上的资源类型相同             | -                        |
| substance        | string | 否       | 物质，需和上料时对应位置上的物质相同                     | DCC                      |
| chemical_id      | int    | 否       | 化学品id，需和上料时对应位置上的化学品id相同             | 10                       |
| add_weight       | float  | 否       | 添加重量，add_weight和add_volume必须要有一个              | 10.5                     |
| add_volume       | float  | 否       | 添加体积                                                 | 10.5                     |
| offset           | float  | 否       | 起始量                                                   | 1.1                      |
| custom           | json   | 否       | 任务单元单位显示描述，可参考上位机软件创建任务时的描述   | {"unit":"mg","unitOptions":["mg","g"]} |


### 请求参数示例
```json
{
  "task_setup": {
    "subtype": null,
    "powder_100_30": false,
    "powder_30_100": false,
    "added_slots": ""
  },
  "task_id": 0,
  "task_name": "xy001",
  "is_audit_log": 1,
  "type": 2,
  "layout_list": [
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 0,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b03d",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Sb",
        "chemical_id": 44,
        "SSSI": "2-00-25-9",
        "add_weight": 535.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 1,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b03e",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Sb",
        "chemical_id": 44,
        "SSSI": "2-00-25-9",
        "add_weight": 535.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 2,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b03f",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Sb",
        "chemical_id": 44,
        "SSSI": "2-00-25-9",
        "add_weight": 459.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 3,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b040",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Sb",
        "chemical_id": 44,
        "SSSI": "2-00-25-9",
        "add_weight": 535.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 4,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b041",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Sb",
        "chemical_id": 44,
        "SSSI": "2-00-25-9",
        "add_weight": 535.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 5,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b042",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Sb",
        "chemical_id": 44,
        "SSSI": "2-00-25-9",
        "add_weight": 535.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 6,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b043",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Bi",
        "chemical_id": 43,
        "SSSI": "2-00-23-7",
        "add_weight": 767,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 7,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b044",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Bi",
        "chemical_id": 43,
        "SSSI": "2-00-23-7",
        "add_weight": 767,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 8,
      "unit_row": 0,
      "unit_id": "unit-19d4c18b045",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Bi",
        "chemical_id": 43,
        "SSSI": "2-00-23-7",
        "add_weight": 767,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 0,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b046",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Ge",
        "chemical_id": 41,
        "SSSI": "2-00-21-5",
        "add_weight": 319.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 1,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b047",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Ge",
        "chemical_id": 41,
        "SSSI": "2-00-21-5",
        "add_weight": 319.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 2,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b048",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Ge",
        "chemical_id": 41,
        "SSSI": "2-00-21-5",
        "add_weight": 273.9,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 3,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b049",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Ge",
        "chemical_id": 41,
        "SSSI": "2-00-21-5",
        "add_weight": 319.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 4,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b04a",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Ge",
        "chemical_id": 41,
        "SSSI": "2-00-21-5",
        "add_weight": 319.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 5,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b04b",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Ge",
        "chemical_id": 41,
        "SSSI": "2-00-21-5",
        "add_weight": 319.2,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 6,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b04c",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Te",
        "chemical_id": 37,
        "SSSI": "2-00-17-9",
        "add_weight": 3746.4,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 7,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b04d",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Te",
        "chemical_id": 37,
        "SSSI": "2-00-17-9",
        "add_weight": 3746.4,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 8,
      "unit_row": 1,
      "unit_id": "unit-19d4c18b04e",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Te",
        "chemical_id": 37,
        "SSSI": "2-00-17-9",
        "add_weight": 3746.4,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 0,
      "unit_row": 2,
      "unit_id": "unit-19d4c18b04f",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Se",
        "chemical_id": 45,
        "SSSI": "2-00-26-0",
        "add_weight": 2082.6,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 1,
      "unit_row": 2,
      "unit_id": "unit-19d4c18b050",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Se",
        "chemical_id": 45,
        "SSSI": "2-00-26-0",
        "add_weight": 2082.6,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 2,
      "unit_row": 2,
      "unit_id": "unit-19d4c18b051",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Se",
        "chemical_id": 45,
        "SSSI": "2-00-26-0",
        "add_weight": 2082.6,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 3,
      "unit_row": 2,
      "unit_id": "unit-19d4c18b052",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Te",
        "chemical_id": 37,
        "SSSI": "2-00-17-9",
        "add_weight": 2406.3,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 4,
      "unit_row": 2,
      "unit_id": "unit-19d4c18b053",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Te",
        "chemical_id": 37,
        "SSSI": "2-00-17-9",
        "add_weight": 2406.3,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    },
    {
      "layout_code": "",
      "src_layout_code": "",
      "resource_type": "CC10R10C",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_powder",
      "unit_column": 5,
      "unit_row": 2,
      "unit_id": "unit-19d4c18b054",
      "process_json": {
        "resource_type": "CC10R10C",
        "substance": "Te",
        "chemical_id": 37,
        "SSSI": "2-00-17-9",
        "add_weight": 2406.3,
        "offset": 0.3,
        "custom": { "unit": "mg", "unitOptions": ["mg", "g"] }
      }
    }
  ],
  "added_slots": "",
  "task_template_id_list": []
}

```


### 返回参数
| 变量名               | 类型 | 描述                             | 示例   |
| -------------------- | ---- | -------------------------------- | ------ |
| code                 | int  | 返回码                           | 200    |
| msg                  | string | 返回信息                        | success|
| result               | string | 结果信息                        | null |
| data                 | string | 数据信息                        | null |
| task_id              | int  | 任务id                           | 10     |
| substance_shortage_list | json | 不足的资源                   | {}     |


### 返回示例
```json
{
	"code": 200,
	"msg": "success",
	"result": null,
	"data": null,
	"task_id": 163,
	"substance_shortage_list": {}
}
```
------------------------------

## 启动任务（StartTask）

### 基本信息
| 项         | 内容                                       |
| ---------- | ------------------------------------------ |
| 接口地址   | http://127.0.0.1:4669/api/StartTask        |
| 请求方式   | POST                                       |
| 说明       | 启动任务，也可用于任务暂停后恢复           |


### 请求参数
| 变量名               | 类型   | 是否必填 | 描述                                                                                                                         | 示例 |
| -------------------- | ------ | -------- | ---------------------------------------------------------------------------------------------------------------------------- | ---- |
| task_id              | int    | 是       | 任务id                                                                                                                       | 1    |
| skip_curr_taskunit   | int    | 否       | 此参数用在暂停任务或者任务异常修复后用，可以不填，默认为1。<br>参数含义：<br>0 原地恢复<br>1 重跑当前操作，暂停或者操作异常时有效<br>2 跳过当前操作，暂停或者操作异常时有效<br>3 重跑当前任务单元<br>4 跳过当前任务单元 | 1    |
| run_by_single_tube   | int    | 否       | 此参数可以不填，默认为0，用户指定按单管顺序执行时，此参数值需要为1                                                           | 0    |
| quick_cap            | int    | 否       | 此参数可以不填，默认为1，用户指定批量开关盖，此参数值需要为0                                                                 | 1    |
| use_tip_type         | string | 否       | 此参数可以不填，默认为空，用户指定使用的tip类型                                                                               | -    |


### 请求参数示例
```json
{
  "task_id": 1,
  "skip_curr_taskunit": 1,
  "run_by_single_tube": 0,
  "quick_cap": 1,
  "use_tip_type": ""
}
```


### 返回参数
| 变量名 | 类型   | 描述     | 示例   |
| ------ | ------ | -------- | ------ |
| code   | int    | 返回码   | 200    |
| msg    | string | 返回信息 | success|


### 返回示例
```json
{
  "code": 200,
  "msg": "success"
}
```

----------------------------

## 暂停任务（StopTask）

### 基本信息
| 项         | 内容                                       |
| ---------- | ------------------------------------------ |
| 接口地址   | http://127.0.0.1:4669/api/StopTask         |
| 请求方式   | POST                                       |
| 说明       | 暂停后任务可编辑，同时任务可以重新运行；普通用户只能暂停自己创建的任务；暂停不会立刻停止，需要等当前操作结束 |


### 请求参数
| 变量名 | 类型 | 是否必填 | 描述 | 示例 |
| ------ | ---- | -------- | ---- | ---- |
| task_id | int | 是 | 任务id | 1 |


### 请求参数示例
```json
{
  "task_id": 1
}
```


### 返回参数
| 变量名 | 类型   | 描述     | 示例   |
| ------ | ------ | -------- | ------ |
| code   | int    | 返回码   | 200    |
| msg    | string | 返回信息 | success |


### 返回示例
```json
{
  "code": 200,
  "msg": "success"
}
```

-----------------------

## 取消任务（CancelTask）

### 基本信息
| 项         | 内容                                       |
| ---------- | ------------------------------------------ |
| 接口地址   | http://127.0.0.1:4669/api/CancelTask       |
| 请求方式   | POST                                       |
| 说明       | 取消（终止）任务，不允许再编辑和再运行；普通用户只能取消自己创建的任务；取消任务会触发资源复位 |


### 请求参数
| 变量名 | 类型 | 是否必填 | 描述 | 示例 |
| ------ | ---- | -------- | ---- | ---- |
| task_id | int | 是 | 任务id | 1 |


### 请求参数示例
```json
{
  "task_id": 1
}
```


### 返回参数
| 变量名 | 类型   | 描述     | 示例   |
| ------ | ------ | -------- | ------ |
| code   | int    | 返回码   | 200    |
| msg    | string | 返回信息 | success |


### 返回示例
```json
{
  "code": 200,
  "msg": "success"
}
```

## 删除任务 (DeleteTask)
### 基本信息
| 项         | 内容                                       |
| ---------- | ------------------------------------------ |
| 接口地址   | http://127.0.0.1:4669/api/DeleteTask       |
| 请求方式   | POST                                       |
| 说明       | 取消（终止）任务，不允许再编辑和再运行；普通用户只能取消自己创建的任务；取消任务会触发资源复位 |

### 请求参数
| 变量名 | 类型 | 是否必填 | 描述 | 示例 |
| ------ | ---- | -------- | ---- | ---- |
| task_id | int | 是 | 任务id | 1 |

### 返回示例
```json
{
  "code":200,
  "msg":"success",
  "result":null,
  "data":null
}
```

