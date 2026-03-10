## 试验调用API

### 实验流程梳理（与代码一致）

1. **启动**：`POST /api/experiment/flux` 入参为大模型输出的「推荐实验方案列表」等。试管序号 = 列表下标（0,1,2,…），整条链路一致。
2. **配料**：按「推荐实验方案列表」顺序，每列一个方案，产出 N 支试管（如 6 种方案 → 6 支试管），列序 = 试管序。
3. **熔封**：熔封后将试管放到货架1，调用 `POST /api/experiment/flux/confirm_seal`。
4. **上料**：流程进入“等待加热炉上料确认”。
5. **指定炉号并确认上料**：人工或机械臂将 N 支试管放入**指定高温炉**后，调用 `POST /api/experiment/flux/confirm_thermal_load`，body 中可传 `oven_id`（炉子编号）、`qty`（数量）；不传则沿用启动时的值（启动时 qty = 推荐实验方案列表长度）。
6. **热处理**：同一炉内加热（一条温度曲线），完成后**离心**（thermal_flow 内部：炉子取 → 离心机放 → 离心运行 → 离心机取 → 货架2放），试管顺序保持不变。
7. **样品制备**：离心后成品需人工线下取样，不在本 API 流程内。
8. **XRD 上样**：人工将样品放入 XRD 试验台后调用 `POST /api/experiment/flux/confirm_xrd_ready`。
9. **XRD 测试**：按试管序号依次测试。单试管用 `run_single_sample_test`（已在现场设备验证）；多试管用 `run_multi_sample_test`（**尚未在现场设备上完整验证**，上线前需现场联调）。结果通过 `scheme_id`/`scheme_index` 与配方关联，供大模型按配方总结。
  - **多样品时的多次确认**：多试管（如 6 支）时，`run_multi_sample_test` 在循环内对**每个样品**依次执行「等待人工上样 → 调用 `send_sample_ready`」，即第 1 支上样并确认 → 第 2 支上样并确认 → … → 第 6 支；测试结束后再对每支做「下样确认」。每次等待时需调用 `**POST /api/flow/xrd/confirm`** 一次，前端可根据 `GET /api/experiment/status` 返回的 `step_info` 展示当前提示（如「请将样品方案2放到工位2，然后点击确认」）。6 支试管共需 6 次上样确认 + 6 次下样确认。

**逻辑自洽要点**：配料列序 = 试管序 = 加热/离心顺序 = XRD 的 station/结果顺序；炉号由 `confirm_thermal_load` 的 `oven_id` 指定；温度曲线取第一个方案的「温度程序」。

### 启动试验

- url
/api/experiment/start
- method
post
- body

```json
{
    "目标材料": {
      "化学式": "AlInSe3",
      "结构原型": "Chalcopyrite-type",
      "是否二维": false,
      "是否半导体": true,
      "材料族系": []
    },
    "推荐实验方案列表": [
      {
        "方案ID": "方案_A",
        "方案类型": "baseline",
        "方案给人的一句话说明": "中规中矩方案：基于统计窗口的推荐值，平衡了生长时间与晶体质量，适合首轮探索。",
        "工艺参数": {
          "原料信息": "Al, In, Se (按化学计量比 1:1:3)",
          "原料标准化": "Al:In:Se=1:1:3",
          "助熔剂信息": "Na 助熔剂",
          "助熔剂标准化": "Na:(Al+In+Se)=2.7:1",
          "容器": "Alumina crucible",
          "籽晶": "Not specified",
          "温度程序": {
            "是否存在次高温预反应段": "否",
            "升温到次高温时间_h": 11.5,
            "次高温段温度_摄氏": 600.0,
            "次高温段保温时间_h": 2.0,
            "升温到最高温时间_h": 1.0,
            "最高温段保温温度_摄氏": 870.0,
            "最高温段保温时间_h": 24.0,
            "降温速率_主降温_℃每小时": 1.8,
            "降温时间_主降温_h": 150.0,
            "低温段保温温度_摄氏": 600.0,
            "低温段保温时间_h": 0.0,
            "冷却速率_至室温_标签": "炉冷"
          },
          "分离与后处理": {
            "分离方式": "Dissolution in ethanol and water",
            "分离温度_摄氏": 25.0,
            "晶体的进一步处理": "Washing with ethanol and water, dried at 65°C"
          }
        },
        "预期结果标签": {
          "预期晶体尺寸": "mm 级",
          "预期风险水平": "低",
          "风险来源简述": [
            "参数接近统计均值，风险可控。",
            "降温速率适中，不易产生热应力开裂。"
          ]
        },
        "溯源信息": {
          "主要参考配方ID": [
            "rec_0282",
            "rec_0322"
          ],
          "参考材料ID-化学式": [
            "mat_273-ZnSiP2",
            "mat_315-ZnSnP2"
          ],
          "参考方案类型ID-名称": [
            "scheme_001-高助熔剂稀释慢冷方案"
          ]
        }
      },
      {
        "方案ID": "方案_B",
        "方案类型": "高助熔剂稀释慢冷方案",
        "方案给人的一句话说明": "大尺寸优化方案：高助熔剂比例配合慢速降温，旨在获得大尺寸、低缺陷的单晶。",
        "工艺参数": {
          "原料信息": "Al, In, Se (按化学计量比 1:1:3)",
          "原料标准化": "Al:In:Se=1:1:3",
          "助熔剂信息": "Na 助熔剂 (高比例稀释)",
          "助熔剂标准化": "Na:(Al+In+Se)=10.0:1",
          "容器": "Alumina crucible",
          "籽晶": "Not specified",
          "温度程序": {
            "是否存在次高温预反应段": "否",
            "升温到次高温时间_h": 10.0,
            "次高温段温度_摄氏": 600.0,
            "次高温段保温时间_h": 2.0,
            "升温到最高温时间_h": 2.0,
            "最高温段保温温度_摄氏": 900.0,
            "最高温段保温时间_h": 24.0,
            "降温速率_主降温_℃每小时": 2.0,
            "降温时间_主降温_h": 150.0,
            "低温段保温温度_摄氏": 600.0,
            "低温段保温时间_h": 0.0,
            "冷却速率_至室温_标签": "炉冷"
          },
          "分离与后处理": {
            "分离方式": "Dissolution in ethanol and water",
            "分离温度_摄氏": 25.0,
            "晶体的进一步处理": "Washing with ethanol and water, dried at 65°C"
          }
        },
        "预期结果标签": {
          "预期晶体尺寸": "cm 级 (大尺寸)",
          "预期风险水平": "中等",
          "风险来源简述": [
            "高助熔剂比例可能降低产率。",
            "实验时长较长，需严格控制气氛防止挥发。"
          ]
        },
        "溯源信息": {
          "主要参考配方ID": [
            "rec_0282",
            "rec_0026"
          ],
          "参考材料ID-化学式": [
            "mat_273-ZnSiP2",
            "mat_022-FeBO3"
          ],
          "参考方案类型ID-名称": [
            "scheme_001-高助熔剂稀释慢冷方案"
          ]
        }
      },
      {
        "方案ID": "方案_C",
        "方案类型": "高温长保温溶解法方案",
        "方案给人的一句话说明": "高温均匀化方案：在接近极限温度下长时保温，促进溶质充分扩散，随后快速冷却获取晶体。",
        "工艺参数": {
          "原料信息": "Al, In, Se (按化学计量比 1:1:3)",
          "原料标准化": "Al:In:Se=1:1:3",
          "助熔剂信息": "Na 助熔剂",
          "助熔剂标准化": "Na:(Al+In+Se)=2.7:1",
          "容器": "Platinum crucible",
          "籽晶": "Not specified",
          "温度程序": {
            "是否存在次高温预反应段": "否",
            "升温到次高温时间_h": 10.0,
            "次高温段温度_摄氏": 600.0,
            "次高温段保温时间_h": 2.0,
            "升温到最高温时间_h": 2.0,
            "最高温段保温温度_摄氏": 980.0,
            "最高温段保温时间_h": 100.0,
            "降温速率_主降温_℃每小时": 5.0,
            "降温时间_主降温_h": 10.0,
            "低温段保温温度_摄氏": 600.0,
            "低温段保温时间_h": 0.0,
            "冷却速率_至室温_标签": "快冷"
          }
        },
        "预期结果标签": {
          "预期晶体尺寸": "mm 级",
          "预期风险水平": "中等偏高",
          "风险来源简述": [
            "温度接近实验室上限 (1000℃)，对设备要求高。",
            "长时保温可能加剧组分挥发或坩埚反应。"
          ]
        },
        "溯源信息": {
          "主要参考配方ID": [
            "rec_0001",
            "rec_0698"
          ],
          "参考材料ID-化学式": [
            "mat_001-GaN",
            "mat_689-PtSb2"
          ],
          "参考方案类型ID-名称": [
            "scheme_002-高温长保温溶解法方案"
          ]
        }
      },
      {
        "方案ID": "方案_D",
        "方案类型": "低助熔剂比例极慢冷方案",
        "方案给人的一句话说明": "高纯度方案：低助熔剂比例减少杂质引入，极慢冷保证晶体结晶质量，适合获取高完整性小单晶。",
        "工艺参数": {
          "原料信息": "Al, In, Se (按化学计量比 1:1:3)",
          "原料标准化": "Al:In:Se=1:1:3",
          "助熔剂信息": "Na 助熔剂 (低比例)",
          "助熔剂标准化": "Na:(Al+In+Se)=1.5:1",
          "容器": "Alumina crucible",
          "籽晶": "Not specified",
          "温度程序": {
            "是否存在次高温预反应段": "否",
            "升温到次高温时间_h": 10.0,
            "次高温段温度_摄氏": 600.0,
            "次高温段保温时间_h": 2.0,
            "升温到最高温时间_h": 2.0,
            "最高温段保温温度_摄氏": 950.0,
            "最高温段保温时间_h": 10.0,
            "降温速率_主降温_℃每小时": 0.6,
            "降温时间_主降温_h": 166.0,
            "低温段保温温度_摄氏": 850.0,
            "低温段保温时间_h": 0.0,
            "冷却速率_至室温_标签": "炉冷"
          },
          "分离与后处理": {
            "分离方式": "Dissolution in ethanol and water",
            "分离温度_摄氏": 25.0,
            "晶体的进一步处理": "Washing with ethanol and water, dried at 65°C"
          }
        },
        "预期结果标签": {
          "预期晶体尺寸": "mm 级",
          "预期风险水平": "中等",
          "风险来源简述": [
            "低助熔剂比例可能导致成核密度高，尺寸受限。",
            "极慢冷导致实验周期长，能耗高。"
          ]
        },
        "溯源信息": {
          "主要参考配方ID": [
            "rec_0016",
            "rec_0121"
          ],
          "参考材料ID-化学式": [
            "mat_013-Ni3V2O8",
            "mat_114-B12As2"
          ],
          "参考方案类型ID-名称": [
            "scheme_003-低助熔剂比例极慢冷方案"
          ]
        }
      },
      {
        "方案ID": "方案_E",
        "方案类型": "酸溶/化学蚀刻分离方案",
        "方案给人的一句话说明": "易分离方案：使用碱金属卤化物助熔剂，生长后通过酸溶轻松去除助熔剂，获取洁净晶体。",
        "工艺参数": {
          "原料信息": "Al, In, Se (按化学计量比 1:1:3)",
          "原料标准化": "Al:In:Se=1:1:3",
          "助熔剂信息": "NaCl-KCl 混合助熔剂",
          "助熔剂标准化": "NaCl:(Al+In+Se)=5.0:1",
          "容器": "Alumina crucible",
          "籽晶": "Not specified",
          "温度程序": {
            "是否存在次高温预反应段": "否",
            "升温到次高温时间_h": 10.0,
            "次高温段温度_摄氏": 600.0,
            "次高温段保温时间_h": 2.0,
            "升温到最高温时间_h": 2.0,
            "最高温段保温温度_摄氏": 850.0,
            "最高温段保温时间_h": 24.0,
            "降温速率_主降温_℃每小时": 2.5,
            "降温时间_主降温_h": 140.0,
            "低温段保温温度_摄氏": 500.0,
            "低温段保温时间_h": 0.0,
            "冷却速率_至室温_标签": "炉冷"
          },
          "分离与后处理": {
            "分离方式": "Dissolution in water (or dilute HCl)",
            "分离温度_摄氏": 60.0,
            "晶体的进一步处理": "Washing with distilled water, sonication if needed"
          }
        },
        "预期结果标签": {
          "预期晶体尺寸": "mm 级",
          "预期风险水平": "低",
          "风险来源简述": [
            "水溶性助熔剂分离简便，对晶体损伤小。",
            "需注意晶体是否耐酸/水腐蚀。"
          ]
        },
        "溯源信息": {
          "主要参考配方ID": [
            "rec_0322",
            "rec_0074"
          ],
          "参考材料ID-化学式": [
            "mat_315-ZnSnP2",
            "mat_070-Ge doped Yb14MnSb11"
          ],
          "参考方案类型ID-名称": [
            "scheme_005-酸溶/化学蚀刻分离方案"
          ]
        }
      }
    ],
    "整体备注": [
      "所有方案均满足实验室温度与降温速率约束，具体配比仍需根据目标化学式微调。",
      "建议先从方案 A + 方案 B 起步，根据首轮晶体尺寸和副相情况再收缩窗口。",
      "AlInSe3 含有挥发性元素 Se，建议在密封容器（如石英管封装后放入坩埚）或惰性气氛保护下进行，尽管参数表中未强制提及，但这是硒化物生长的通用安全准则。"
    ]
  }
```

- response

```json
{
    "status": "started",
    "message": "实验已启动，可通过 GET /api/experiment/status 查询进度",
    "experiment_id": "f10782d5-417b-410e-a493-19b0d5d8c946",
    "phase": "mixing",
    "phase_label": "配料进行中",
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ]
}
```

### 停止试验

- url
/api/experiment/stop
- method
post
- body
空
- response

```json
{
    "stopped": true,
    "message": "已请求停止实验"
}
```

### 获取试验状态

- url
/api/experiment/status
- method
post
- body
空
- response
  1. phase=mixing //配料中
  ```json
  {
    "experiment_id": "c2957b0b-cf2f-468f-bdbc-0379fe7eafd2",
    "phase": "mixing",
    "phase_label": "配料进行中",
    "is_paused": false,
    "pending_action": "",
    "step_info": "配料流程启动 [Mock]",
    "sub_flow": "mix",
    "sub_flow_summaries": {
        "status": true,
        "summary": {
            "mixer": {
                "status": "success",
                "data": {
                    "task_id": 9001,
                    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
                    "status": 1,
                    "creator": "mock",
                    "task_begin_time": 1773129624.3390176,
                    "task_end_time": null,
                    "created_at": 0,
                    "updated_at": 0,
                    "scheme_list": [
                        {
                            "scheme_name": "方案0",
                            "ingredients": [
                                {
                                    "substance": "Al",
                                    "weight": 195.78,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "In",
                                    "weight": 833.02,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Se",
                                    "weight": 1719.09,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Na",
                                    "weight": 2252.11,
                                    "unit": "mg"
                                }
                            ]
                        },
                        {
                            "scheme_name": "方案1",
                            "ingredients": [
                                {
                                    "substance": "Al",
                                    "weight": 88.27,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "In",
                                    "weight": 375.61,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Se",
                                    "weight": 775.13,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Na",
                                    "weight": 3760.99,
                                    "unit": "mg"
                                }
                            ]
                        },
                        {
                            "scheme_name": "方案2",
                            "ingredients": [
                                {
                                    "substance": "Al",
                                    "weight": 195.78,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "In",
                                    "weight": 833.02,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Se",
                                    "weight": 1719.09,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Na",
                                    "weight": 2252.11,
                                    "unit": "mg"
                                }
                            ]
                        },
                        {
                            "scheme_name": "方案3",
                            "ingredients": [
                                {
                                    "substance": "Al",
                                    "weight": 244.78,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "In",
                                    "weight": 1041.52,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Se",
                                    "weight": 2149.37,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Na",
                                    "weight": 1564.33,
                                    "unit": "mg"
                                }
                            ]
                        },
                        {
                            "scheme_name": "方案4",
                            "ingredients": [
                                {
                                    "substance": "Al",
                                    "weight": 73.33,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "In",
                                    "weight": 312.01,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "Se",
                                    "weight": 643.89,
                                    "unit": "mg"
                                },
                                {
                                    "substance": "NaCl",
                                    "weight": 3970.78,
                                    "unit": "mg"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    },
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": null,
    "xrd_running_sample": null
  }
  ```
  2. phase=waiting_seal_confirm //等待熔封完成确认
  ```json
  {
    "experiment_id": "c2957b0b-cf2f-468f-bdbc-0379fe7eafd2",
    "phase": "waiting_seal_confirm",
    "phase_label": "等待熔封完成：请完成熔封后调用 POST /api/experiment/flux/confirm_seal",
    "is_paused": true,
    "pending_action": "等待熔封完成：请完成熔封后调用 POST /api/experiment/flux/confirm_seal",
    "step_info": "配料已完成，等待熔封确认",
    "sub_flow": null,
    "sub_flow_summaries": null,
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": {
        "method": "POST",
        "path": "/api/experiment/confirm_seal",
        "body_data": {},
        "body_schema": []
    },
    "xrd_running_sample": null
  }
  ```
  3. phase=loading //上料中
  ```json
  {
    "experiment_id": "c2957b0b-cf2f-468f-bdbc-0379fe7eafd2",
    "phase": "loading",
    "phase_label": "上料进行中",
    "is_paused": false,
    "pending_action": "",
    "step_info": "上料流程启动 [Mock]",
    "sub_flow": "load",
    "sub_flow_summaries": null,
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": null,
    "xrd_running_sample": null
  }
  ```
  4. phase=waiting_thermal_load //等待加热炉上料确认
  ```json
  {
    "experiment_id": "c2957b0b-cf2f-468f-bdbc-0379fe7eafd2",
    "phase": "waiting_thermal_load",
    "phase_label": "等待上料完成：请将样品放入加热炉后调用 POST /api/experiment/flux/confirm_thermal_load",
    "is_paused": true,
    "pending_action": "等待上料完成：请将样品放入加热炉后调用 POST /api/experiment/flux/confirm_thermal_load",
    "step_info": "请将样品放入加热炉后调用 confirm_thermal_load",
    "sub_flow": null,
    "sub_flow_summaries": null,
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": {
        "method": "POST",
        "path": "/api/experiment/confirm_thermal_load",
        "body_data": {
            "oven_assignments": [
                {
                    "scheme_index": 0,
                    "oven_id": null,
                },
                {
                    "scheme_index": 1,
                    "oven_id": null,
                },
                {
                    "scheme_index": 2,
                    "oven_id": null,
                },
                {
                    "scheme_index": 3,
                    "oven_id": null,
                },
                {
                    "scheme_index": 4,
                    "oven_id": null,
                }
            ]
        },
        "body_schema": [
            {
                "name": "oven_id",
                "type": "int",
                "required": true,
                "description": "炉子ID，需用户填写（单炉）或 oven_assignments[].oven_id（多炉）",
                "default": null
            }
        ]
    },
    "xrd_running_sample": null
  }
  ```
  5. phase=thermal_running //热处理（加热炉+离心机）执行中
  ```json
  {
    "experiment_id": "c2957b0b-cf2f-468f-bdbc-0379fe7eafd2",
    "phase": "thermal_running",
    "phase_label": "热处理进行中（加热炉与离心机）",
    "is_paused": false,
    "pending_action": "",
    "step_info": "热处理执行中 [Mock]",
    "sub_flow": "thermal",
    "sub_flow_summaries": {
        "status": true,
        "summary": {
            "robot": {
                "status": "success",
                "data": {
                    "plc_connected": true,
                    "m_signals": [
                        false,
                        false,
                        false,
                        false,
                        false,
                        true,
                        false
                    ],
                    "task_data": {
                        "tid": 1,
                        "st": 1,
                        "qty": 1
                    },
                    "robot": {
                        "home_status": true,
                        "fixture_status": true,
                        "system_status": 2,
                        "robot_status": true,
                        "task_status": 1
                    }
                }
            },
            "oven": {
                "status": "success",
                "data": [
                    {
                        "设备名称": "炉1",
                        "设备地址": 1,
                        "仪表型号": "858P",
                        "在线状态": "在线",
                        "实际温度": 450.5,
                        "设定温度": 500.0,
                        "状态显示": "阶段2 剩余0.5h",
                        "结束时间": "2025-02-09 15:30",
                        "状态": "开始",
                        "运行曲线": "Mock曲线"
                    }
                ]
            },
            "centrifuge": {
                "status": "success",
                "data": {
                    "actual_rpm": 500,
                    "centrifuge_force": 120,
                    "run_time": 300,
                    "fault_code": 0,
                    "run_state": 2,
                    "door_window": 2,
                    "setted_rpm": 500,
                    "setted_time": 10,
                    "door_lid": 2,
                    "rotor_state": 2,
                    "remain_time": 180
                }
            },
            "temperature_curve": [
                {
                    "temperature": 20.0,
                    "time": 11.5
                },
                {
                    "temperature": 600.0,
                    "time": 2.0
                },
                {
                    "temperature": 600.0,
                    "time": 1.0
                },
                {
                    "temperature": 870.0,
                    "time": 24.0
                },
                {
                    "temperature": 870.0,
                    "time": 150.0
                },
                {
                    "temperature": 600.0,
                    "time": -121.0
                }
            ]
        }
    },
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": null,
    "xrd_running_sample": {
        "scheme_index": 0,
        "scheme_id": "方案_A",
        "sample_id": "方案_A_0dee6c74"
    }
  }
  ```
  6. phase=waiting_xrd_ready //等待人工将样品放入XRD试验台后确认
  ```json
  {
    "experiment_id": "c2957b0b-cf2f-468f-bdbc-0379fe7eafd2",
    "phase": "waiting_xrd_ready",
    "phase_label": "等待XRD上样：请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready",
    "is_paused": true,
    "pending_action": "等待XRD上样：请将样品放入XRD试验台后调用 POST /api/experiment/flux/confirm_xrd_ready",
    "step_info": "请将炉3的样品放入XRD试验台后调用 confirm_xrd_ready",
    "sub_flow": null,
    "sub_flow_summaries": null,
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": {
        "method": "POST",
        "path": "/api/experiment/confirm_xrd_ready",
        "body_data": {
            "start_theta": 5.1,
            "end_theta": 120.0,
            "increment": 0.01,
            "exp_time": 0.1,
            "scheme_index": 0
        },
        "body_schema": [
            {
                "name": "start_theta",
                "type": "float",
                "required": false,
                "description": "起始角度，默认已填",
                "default": 5.1
            },
            {
                "name": "end_theta",
                "type": "float",
                "required": false,
                "description": "结束角度，默认已填",
                "default": 120.0
            },
            {
                "name": "increment",
                "type": "float",
                "required": false,
                "description": "步长，默认已填",
                "default": 0.01
            },
            {
                "name": "exp_time",
                "type": "float",
                "required": false,
                "description": "曝光时间，默认已填",
                "default": 0.1
            },
            {
                "name": "scheme_index",
                "type": "int",
                "required": false,
                "description": "本次XRD对应的方案索引（默认0）",
                "default": 0
            }
        ]
    },
    "xrd_running_sample": null
  }
  ```
  7. phase=xrd_running //XRD测试执行中
  ```json
  {
    "experiment_id": "c2957b0b-cf2f-468f-bdbc-0379fe7eafd2",
    "phase": "xrd_running",
    "phase_label": "XRD测试进行中",
    "is_paused": false,
    "pending_action": "",
    "step_info": "XRD测试执行中（炉3）[Mock]",
    "sub_flow": "xrd",
    "sub_flow_summaries": {
        "status": true,
        "summary": {
            "xrd": {
                "name": "XRD衍射仪",
                "connected": true,
                "host": "192.168.1.100",
                "port": 8000,
                "status": "running",
                "xray_status": true,
                "power_status": true,
                "current_voltage": 45.0,
                "current_current": 40.0,
                "untest_station": [],
                "ready_station": [
                    "1"
                ]
            }
        }
    },
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101600_7f4cf0ef",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": null,
    "xrd_running_sample": {
        "scheme_index": 0,
        "scheme_id": "方案_A",
        "sample_id": "方案_A_b7208c"
    }
  }
  ```
  8. phase=completed //实验已完成
  ```json
  {
    "experiment_id": "6a046814-a1d8-4ac8-9aff-72a80260af43",
    "phase": "completed",
    "phase_label": "实验已完成",
    "is_paused": false,
    "pending_action": "",
    "step_info": "实验流程已全部完成",
    "sub_flow": null,
    "sub_flow_summaries": {
        "status": true,
        "summary": {
            "xrd": {
                "name": "XRD衍射仪",
                "connected": true,
                "host": "192.168.1.100",
                "port": 8000,
                "status": "running",
                "xray_status": true,
                "power_status": true,
                "current_voltage": 45.0,
                "current_current": 40.0,
                "untest_station": [],
                "ready_station": [
                    "1"
                ]
            }
        }
    },
    "error_message": null,
    "task_name": "AlInSe3_多方案_202603101752_87c15714",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": [
        {
            "experiment_id": "6a046814-a1d8-4ac8-9aff-72a80260af43",
            "sample_id": "方案_A_0dee6c74",
            "scheme_id": "方案_A",
            "scheme_index": 0,
            "scheme_type": "baseline",
            "theta2": [],
            "intensity": [],
            "timestamp": null
        },
        {
            "experiment_id": "6a046814-a1d8-4ac8-9aff-72a80260af43",
            "sample_id": "方案_B_f6b74f0a",
            "scheme_id": "方案_B",
            "scheme_index": 1,
            "scheme_type": "高助熔剂稀释慢冷方案",
            "theta2": [],
            "intensity": [],
            "timestamp": null
        },
        {
            "experiment_id": "6a046814-a1d8-4ac8-9aff-72a80260af43",
            "sample_id": "方案_C_24daa313",
            "scheme_id": "方案_C",
            "scheme_index": 2,
            "scheme_type": "高温长保温溶解法方案",
            "theta2": [],
            "intensity": [],
            "timestamp": null
        },
        {
            "experiment_id": "6a046814-a1d8-4ac8-9aff-72a80260af43",
            "sample_id": "方案_D_fd630ccf",
            "scheme_id": "方案_D",
            "scheme_index": 3,
            "scheme_type": "低助熔剂比例极慢冷方案",
            "theta2": [],
            "intensity": [],
            "timestamp": null
        },
        {
            "experiment_id": "6a046814-a1d8-4ac8-9aff-72a80260af43",
            "sample_id": "方案_E_a3bac415",
            "scheme_id": "方案_E",
            "scheme_index": 4,
            "scheme_type": "酸溶/化学蚀刻分离方案",
            "theta2": [],
            "intensity": [],
            "timestamp": null
        }
    ],
    "next_action": null,
    "xrd_running_sample": null
  }
  ```
  9. phase=error //实验异常结束
  ```json
  {
    "experiment_id": "09b0a431-3bd7-4212-b398-185b08e1c2b1",
    "phase": "error",
    "phase_label": "实验异常结束",
    "is_paused": false,
    "pending_action": "",
    "step_info": "配料已完成，等待熔封确认",
    "sub_flow": null,
    "sub_flow_summaries": {
        "status": false,
        "message": "等待熔封确认超时",
        "summary": {}
    },
    "error_message": "等待熔封确认超时",
    "task_name": "AlInSe3_多方案_202603101812_d17e2f06",
    "scheme_ids": null,
    "scheme_manifest": [
        {
            "scheme_index": 0,
            "scheme_id": "方案_A",
            "scheme_type": "baseline"
        },
        {
            "scheme_index": 1,
            "scheme_id": "方案_B",
            "scheme_type": "高助熔剂稀释慢冷方案"
        },
        {
            "scheme_index": 2,
            "scheme_id": "方案_C",
            "scheme_type": "高温长保温溶解法方案"
        },
        {
            "scheme_index": 3,
            "scheme_id": "方案_D",
            "scheme_type": "低助熔剂比例极慢冷方案"
        },
        {
            "scheme_index": 4,
            "scheme_id": "方案_E",
            "scheme_type": "酸溶/化学蚀刻分离方案"
        }
    ],
    "result": null,
    "next_action": null,
    "xrd_running_sample": null
  }
  ```
  10. phase=idle //空闲
  ```json
  {
      "experiment_id": "none",
      "phase": "idle",
      "phase_label": "空闲，可启动实验",
      "is_paused": false,
      "pending_action": "",
      "step_info": "",
      "sub_flow": null,
      "sub_flow_summaries": null,
      "error_message": null,
      "task_name": null,
      "scheme_ids": null,
      "scheme_manifest": null,
      "result": null,
      "next_action": null,
      "xrd_running_sample": null
  }
  ```

### 确认熔封完成

- url
/api/experiment/flux/confirm_seal
- method
post
- body
空
- response
  ```json
  {
    "message": "熔封确认已接收，流程继续"
  }
  ```

### 确认加热炉上料完成

- url
/api/experiment/flux/confirm_thermal_load
- method
post
- body
可选，用于指定炉号和数量（不传则沿用启动时的 oven_id、qty）：
  ```json
  {
    "oven_assignments": [
        {
            "scheme_index": 0,
            "oven_id": 3,
            "qty": 3
        },
        {
            "scheme_index": 1,
            "oven_id": 4,
            "qty": 2
        },
        {
            "scheme_index": 2,
            "oven_id": 5,
            "qty": 2
        },
        {
            "scheme_index": 3,
            "oven_id": 6,
            "qty": 2
        },
        {
            "scheme_index": 4,
            "oven_id": 6,
            "qty": 2
        }
    ]
  }
  ```
- response
  ```json
  {
    "message": "上料确认已接收，开始热处理"
  }
  ```

### 确认XRD上样

- url
/api/experiment/flux/confirm_xrd_ready
- method
post
- body
  根据status接口返回的next_action传参
  ```json
  {
    "start_theta": 5.1,
    "end_theta": 120,
    "increment": 0.01,
    "exp_time": 0.1,
    "sample_assignments": [
        {
            "scheme_index": 0,
            "qty": 1
        }
    ]
  }
  ```
- response
  ```json
  {
    "message": "XRD上样确认已接收，开始XRD测试"
  }
  ```

