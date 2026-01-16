# 配料设备API
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
| task_id | string | 否       | 任务id，若不传，则返回第一个任务 | 1    |


### 请求参数示例
```json
{
  "task_id": 10
}
```


### 返回参数
| 变量名         | 类型      | 描述                               | 示例      |
| -------------- | --------- | ---------------------------------- | --------- |
| task_id        | int       | 任务id                             | 1         |
| task_name      | string    | 任务名称                           | test      |
| status         | int       | 任务状态                           | 2         |
| creator        | string    | 创建人                             | admin     |
| task_begin_time| timestamp | 任务开始时间                       | 1671860870|
| task_end_time  | timestamp | 任务结束时间                       | 1671870521|
| unit_save_list | array     | 存放提交任务的列表，存放实验详细信息 | -         |
| unit_list      | array     | 任务单元列表                       | -         |


### 返回示例
```json
{
  "fid": 1,
  "name": "加粉-移液-转移-球磨",
  "status": 0,
  "unit_save_json": [
    {
      "layout_code": "MJ-3:0",
      "src_layout_code": "",
      "resource_type": "MJT_V2",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_solid",
      "unit_column": 1,
      "unit_row": 0,
      "unit_id": "unit-18db44434a",
      "process_json": {
        "src_layout_code": "S5-3A:0",
        "resource_type": "DHP30",
        "substance": "未知",
        "chemical_id": 2,
        "add_weight": 100,
        "offset": 0.1,
        "custom": {
          "unit": "mg",
          "unitOptions": [
            "mg",
            "g"
          ]
        },
        "layout_code": "MJ-3:0",
        "tray_QR_code": ""
      },
      "task_template_id": 0
    },
    {
      "layout_code": "MJ-4:0",
      "src_layout_code": "",
      "resource_type": "MJT_V2",
      "tray_QR_code": "",
      "status": 0,
      "QR_code": "",
      "unit_type": "exp_add_solid",
      "unit_column": 3,
      "unit_row": 0,
      "unit_id": "unit-18dbb44435b",
      "process_json": {
        "src_layout_code": "S5-3A:0",
        "resource_type": "DHP30",
        "substance": "未知",
        "chemical_id": 2,
        "add_weight": 100,
        "offset": 0.1,
        "custom": {
          "unit": "mg",
          "unitOptions": [
            "mg",
            "g"
          ]
        },
        "layout_code": "MJ-4:0",
        "tray_QR_code": ""
      },
      "task_template_id": 0
    }
  ]
}
```

----------------------------------------------

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
| task_id              | int     | 是       | 任务id，如果是新增任务，task_id填0           | 1              |
| task_name            | string  | 是       | 任务名称                                     | test           |
| layout_list          | array   | 是       | 任务单元列表                                 | -              |
| task_template_id_list| array   | 否       | 任务模板id列表，有填表示是通过模板配置的实验 | [1,2]          |
| is_audit_log         | boolean | 否       | 是否审计                                     | true           |
| is_copy              | boolean | 否       | 是否从其他任务复制                           | false          |


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
  "task_name": "test",
  "layout_list": [
    {
      "layout_code": "N-1-1:0",
      "substance": "实验用物质cas",
      "resource_type": "TT8T",
      "tray_QR_code": "tb09782653",
      "QR_code": "sg09782653",
      "unit_column": 0,
      "unit_row": 1,
      "unit_type": "exp_add_solid",
      "unit_id": "unit-186392addr6",
      "process_json": {
        "src_layout_code": "L2-2:0",
        "resource_type": "",
        "substance": "DCC",
        "chemical_id": null,
        "add_weight": 100,
        "offset": 1.1,
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
  "task_template_id_list": [1,2]
}
```


### 返回参数
| 变量名               | 类型 | 描述                             | 示例   |
| -------------------- | ---- | -------------------------------- | ------ |
| code                 | int  | 返回码                           | 200    |
| msg                  | string | 返回信息                        | success|
| task_id              | int  | 任务id                           | 10     |
| workflow_id          | int  | 多工位任务id，特定设备才可用     | 10     |
| substance_shortage_list | json | 不足的资源                   | []     |


### 返回示例
```json
{
  "code": 200,
  "task_id": 1,
  "workflow_id": 1,
  "msg": "200",
  "substance_shortage_list": []
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