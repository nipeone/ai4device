def _wrap_success(message: str, data=None, code: int = 200):
    """统一成功响应：{"code": 200, "status": "success", "message": "...", "data": {...}}"""
    return {"code": code, "status": "success", "message": message, "data": data}


def _wrap_error(message: str, code: int = 400, data=None):
    """统一错误响应：{"code": 4xx/5xx, "status": "error", "message": "...", "data": {...}}"""
    return {"code": code, "status": "error", "message": message, "data": data}