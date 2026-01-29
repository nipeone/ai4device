"""pytest 公共配置：保证从项目根或 tests 目录运行都能正确导入"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，便于 `from devices.xxx import ...`
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
