"""断网验证：禁用一切 socket 后跑完整转换流程。"""
import os
import socket
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))


class _Blocked(Exception):
    pass


def _deny(*_a, **_k):
    raise _Blocked("网络访问已被测试脚本禁用")


# 彻底堵死网络：任何 socket 创建 / 域名解析 / 连接都会抛异常
socket.socket = _deny          # type: ignore[assignment]
socket.create_connection = _deny  # type: ignore[assignment]
socket.getaddrinfo = _deny     # type: ignore[assignment]
socket.gethostbyname = _deny   # type: ignore[assignment]

SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "offline_out")
os.makedirs(OUT, exist_ok=True)

import engine  # noqa: E402
from utils import Options, SUPPORTED_EXTS  # noqa: E402

files = [
    os.path.join(SAMPLES, f)
    for f in sorted(os.listdir(SAMPLES))
    if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
]

print("网络状态：socket 已被禁用")
ok = 0
for f in files:
    dst = os.path.join(OUT, os.path.basename(f) + ".pdf")
    if os.path.exists(dst):
        os.remove(dst)
    try:
        engine.convert_one(f, dst, Options(out_dir=OUT))
        print(f"  OK   {os.path.basename(f):22s} {os.path.getsize(dst)/1024:7.1f} KB")
        ok += 1
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {os.path.basename(f)}: {type(exc).__name__}: {exc}")

merged = engine.run(files, Options(merge=True, out_dir=OUT))
print(f"  合并 -> {os.path.basename(merged[0])}  {os.path.getsize(merged[0])/1024:.1f} KB")
print(f"\n断网环境下成功转换 {ok}/{len(files)} 个文件，合并正常")
