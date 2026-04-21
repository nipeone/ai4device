from fastapi import Query, File, UploadFile, Request, APIRouter
from logger import sys_logger as logger
from typing import List
from devices.mixer_core import mixer_controller
from schemas.mixer import BatchStartTaskRequest, AddChemicalRequest, AddTaskRequest
from apis.base_api import _wrap_success, _wrap_error

router = APIRouter(prefix="/api/mixer", tags=["配料"])
from services.mixer import mixer_service

@router.get("/status", tags=["配料"])
def get_mixer_status():
    """获取配料设备状态（连接状态、当前任务、消息）"""
    status = mixer_controller.get_status()
    status_value = status.name if hasattr(status, "name") else str(status)
    status_dict = {
        "1": {
            "connection": status_value,
            "message": mixer_controller.get_message(),
            "current_task_id": getattr(mixer_controller, "current_task_id", None),
        }
    }
    return _wrap_success("获取配料设备状态成功", status_dict)

@router.post("/add_chemical", tags=["配料"])
def add_chemical(request: AddChemicalRequest):
    """添加化学品"""
    result = mixer_controller.add_chemical(request.name)
    if result.get("status") == "success":
        return _wrap_success("化学品添加成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

@router.get("/get_chemicals", tags=["配料"])
def get_chemicals(
    limit = Query(default=1000, description="每页数量"),
    offset = Query(default=0, description="偏移量"),
    sort = Query(default="desc", description="排序方式"),
    query_key = Query(default=None, description="查询关键字"),
):
    """获取化学品列表"""
    result = mixer_controller.get_chemicals(limit=limit, offset=offset, sort=sort, query_key=query_key)
    if result.get("status") == "success":
        return _wrap_success("获取化学品列表成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

@router.post("/add_task", tags=["配料"])
def add_task(request: AddTaskRequest):
    """添加任务"""
    result = mixer_controller.add_task(request)
    if result.get("status") == "success":
        return _wrap_success("任务添加成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

async def add_task_from_excel(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        return _wrap_error("只支持上传 Excel 文件(.xlsx, .xls)", 400)

    contents = await file.read()
    add_task_request = await mixer_service.parse_mixer_tasks_from_excel(contents)
    result = mixer_controller.add_task(add_task_request)
    if result.get("status") == "success":
        return _wrap_success("任务添加成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

@router.post("/task/batch_check", tags=["配料"])
def batch_check_task(request: BatchStartTaskRequest):
    """批量检查任务"""
    result = mixer_controller.batch_check_task(request.task_ids)
    if result.get("status") == "success":
        return _wrap_success("任务批量检查成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

@router.post("/task/batch_start", tags=["配料"])
def batch_start_task(request: BatchStartTaskRequest):
    """批量启动任务"""
    result = mixer_controller.batch_start_task(request.task_ids)
    if result.get("status") == "success":
        return _wrap_success("任务批量启动成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

@router.post("/task/stop", tags=["配料"])
def stop_task(task_id: int):
    """停止任务"""
    result = mixer_controller.stop_task(task_id)
    if result.get("status") == "success":
        return _wrap_success("任务停止成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

@router.post("/task/delete", tags=["配料"])
def delete_task(task_id: int):
    """删除任务"""
    result = mixer_controller.del_task(task_id)
    if result.get("status") == "success":
        return _wrap_success("任务删除成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)

@router.post("/task/cancel", tags=["配料"])
def cancel_task(task_id: int):
    """取消任务"""
    result = mixer_controller.cancel_task(task_id)
    if result.get("status") == "success":
        return _wrap_success("任务取消成功", result.get("data"))
    else:
        return _wrap_error(result.get("message"), 500)