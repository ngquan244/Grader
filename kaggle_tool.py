# kaggle_tool.py
import os
import json
import time
import subprocess
import tempfile
import shutil
from dotenv import load_dotenv

load_dotenv()
KERNEL_REF = "nguyenmanhquan244/grading-timing-mark"  # kernel của bạn


def run_cmd(cmd, timeout=600):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        encoding='utf-8',
        errors='ignore'
    )
    out, err = proc.communicate(timeout=timeout)
    return proc.returncode, out, err


def setup_kaggle_credentials():
    user = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")
    if not user or not key:
        raise RuntimeError("KAGGLE_USERNAME hoặc KAGGLE_KEY không có trong env.")
    kaggle_dir = os.path.expanduser("~/.kaggle")
    os.makedirs(kaggle_dir, exist_ok=True)
    path = os.path.join(kaggle_dir, "kaggle.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"username": user, "key": key}, f)
    os.chmod(path, 0o600)


def download_latest_kernel_output(kernel_ref=KERNEL_REF, dest=None):
    setup_kaggle_credentials()
    if dest is None:
        dest = tempfile.mkdtemp()
    cmd = ["kaggle", "kernels", "output", kernel_ref, "-p", dest]
    rc, out, err = run_cmd(cmd)
    if rc != 0:
        # nếu result.json có sẵn vẫn return
        if find_result_json(dest):
            return dest
        raise RuntimeError(f"kaggle kernels output failed.\nstdout:{out}\nstderr:{err}")
    return dest


def push_and_run_local_kernel(local_kernel_path, timeout=900):
    setup_kaggle_credentials()
    cmd = ["kaggle", "kernels", "push", "-p", local_kernel_path]
    rc, _, _ = run_cmd(cmd)
    if rc != 0:
        raise RuntimeError("Kaggle push failed.")

    start = time.time()
    while True:
        rc, out, _ = run_cmd(["kaggle", "kernels", "status", KERNEL_REF])
        if rc == 0:
            low = out.lower()
            if "complete" in low or "finished" in low:
                break
            if "failed" in low:
                raise RuntimeError(f"Kernel failed:\n{out}")
        if time.time() - start > timeout:
            raise TimeoutError("Kernel run timed out")
        time.sleep(5)

    return download_latest_kernel_output(KERNEL_REF)


def find_result_json(output_dir):
    for root, dirs, files in os.walk(output_dir):
        for fn in files:
            if fn.lower() == "result.json" or fn.endswith("_result.json"):
                return os.path.join(root, fn)
    for root, dirs, files in os.walk(output_dir):
        for fn in files:
            if fn.endswith((".zip", ".tar.gz", ".tgz")):
                archive = os.path.join(root, fn)
                extract_dir = tempfile.mkdtemp()
                shutil.unpack_archive(archive, extract_dir)
                res = find_result_json(extract_dir)
                if res:
                    return res
    return None


def get_score_from_kaggle(run_local_kernel=False, local_kernel_path=None):
    if run_local_kernel and local_kernel_path:
        outdir = push_and_run_local_kernel(local_kernel_path)
    else:
        outdir = download_latest_kernel_output(KERNEL_REF)

    res_path = find_result_json(outdir)
    if not res_path:
        raise FileNotFoundError(f"result.json không tìm thấy tại {outdir}")

    with open(res_path, "r", encoding="utf-8") as f:
        return json.load(f)
