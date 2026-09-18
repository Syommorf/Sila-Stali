import json
import os
import subprocess
import tempfile
import urllib.request


def parse_version(value):
    parts = []
    for piece in str(value or "").split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(latest, current):
    a = parse_version(latest)
    b = parse_version(current)
    length = max(len(a), len(b), 1)
    a = a + (0,) * (length - len(a))
    b = b + (0,) * (length - len(b))
    return a > b


def fetch_latest(base_url):
    url = base_url.rstrip("/") + "/desktop/update"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download(url, dest, on_progress=None):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "SilaStaliUpdater"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
    return dest


def _ps_quote(path):
    return "'" + str(path).replace("'", "''") + "'"


def _build_script(target_exe, new_exe, log_file):
    target = _ps_quote(target_exe)
    new = _ps_quote(new_exe)
    log = _ps_quote(log_file)
    return f"""$ErrorActionPreference = 'Stop'
$target = {target}
$new = {new}
$log = {log}

function Write-Log($message) {{
    try {{ Add-Content -LiteralPath $log -Value ("{{0}} {{1}}" -f (Get-Date -Format s), $message) }} catch {{}}
}}

$deadline = (Get-Date).AddMinutes(5)
while ((Get-Date) -lt $deadline) {{
    try {{
        $stream = [System.IO.File]::Open($target, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        $stream.Close()
        break
    }} catch {{
        Start-Sleep -Milliseconds 700
    }}
}}
Start-Sleep -Milliseconds 500
try {{
    Copy-Item -LiteralPath $new -Destination $target -Force
    Write-Log "updated ok"
}} catch {{
    Write-Log ("copy failed: " + $_.Exception.Message)
}}
Start-Process -FilePath $target -WorkingDirectory (Split-Path -Parent $target) | Out-Null
Remove-Item -LiteralPath $new -Force -ErrorAction SilentlyContinue
"""


def schedule_update(target_exe, new_exe):
    target_exe = os.path.abspath(target_exe)
    new_exe = os.path.abspath(new_exe)
    work_dir = tempfile.mkdtemp(prefix="silastali_upd_")
    script = os.path.join(work_dir, "apply_update.ps1")
    log_file = os.path.join(work_dir, "apply_update.log")
    with open(script, "w", encoding="utf-8-sig") as f:
        f.write(_build_script(target_exe, new_exe, log_file))
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-WindowStyle", "Hidden", "-File", script],
        creationflags=creationflags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    return script
