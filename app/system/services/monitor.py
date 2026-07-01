"""基于 psutil 的系统指标采集器。"""

from __future__ import annotations

import platform
import socket
import sys
import time
from datetime import datetime
from typing import Any

import psutil  # type: ignore[import-untyped]


class ServerInfoCollector:
    """系统指标采集器，采集 CPU、内存、磁盘、网络、进程等信息。"""

    def __init__(self) -> None:
        self._last_net_io: Any = None
        self._last_disk_io: Any = None
        self._last_time: float = 0
        self._process_snapshot: dict[str, Any] | None = None
        self._process_snapshot_time: float = 0
        self._process_snapshot_ttl: float = 5
        self._process_scan_budget: float = 0.5

    def get_basic_info(self) -> dict:
        uname = platform.uname()
        return {
            "hostname": uname.node,
            "ip_address": self._get_ip(),
            "system": uname.system,
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "processor": platform.processor() or uname.processor or "Unknown",
            "python_version": sys.version.split()[0],
        }

    def get_cpu_info(self) -> dict:
        return {
            "usage": psutil.cpu_percent(interval=0.1),
            "cores": psutil.cpu_count(logical=False) or 0,
            "threads": psutil.cpu_count(logical=True) or 0,
        }

    def get_memory_info(self) -> dict:
        vm = psutil.virtual_memory()
        return {
            "usage": vm.percent,
            "used": self._bytes_to_gb(vm.used),
            "total": self._bytes_to_gb(vm.total),
            "available": self._bytes_to_gb(vm.available),
        }

    def get_disk_io(self) -> dict:
        now = time.monotonic()
        try:
            counters = psutil.disk_io_counters()
        except Exception:
            counters = None

        # 磁盘使用率
        try:
            disk_usage = psutil.disk_usage("/")
            usage_percent = disk_usage.percent
            used_gb = self._bytes_to_gb(disk_usage.used)
            total_gb = self._bytes_to_gb(disk_usage.total)
        except Exception:
            usage_percent = 0.0
            used_gb = 0.0
            total_gb = 0.0

        if counters is None:
            return {"usage": usage_percent, "used": used_gb, "total": total_gb, "read_speed": "0 B/s", "write_speed": "0 B/s", "total_read": "0 B", "total_write": "0 B"}

        read_speed = 0.0
        write_speed = 0.0
        if self._last_disk_io and (now - self._last_time) > 0:
            dt = now - self._last_time
            read_speed = (counters.read_bytes - self._last_disk_io.read_bytes) / dt
            write_speed = (counters.write_bytes - self._last_disk_io.write_bytes) / dt

        self._last_disk_io = counters

        return {
            "usage": usage_percent,
            "used": used_gb,
            "total": total_gb,
            "read_speed": self._format_speed(max(read_speed, 0)),
            "write_speed": self._format_speed(max(write_speed, 0)),
            "total_read": self._format_bytes(counters.read_bytes),
            "total_write": self._format_bytes(counters.write_bytes),
        }

    def get_network_io(self) -> dict:
        now = time.monotonic()
        net = psutil.net_io_counters()

        # 活跃网络连接数
        try:
            connections = psutil.net_connections(kind="inet")
            active_connections = sum(1 for c in connections if c.status == "ESTABLISHED")
            total_connections = len(connections)
        except (psutil.AccessDenied, OSError):
            active_connections = 0
            total_connections = 0

        if net is None:
            return {"active_connections": active_connections, "total_connections": total_connections, "upload_speed": "0 B/s", "download_speed": "0 B/s", "total_sent": "0 B", "total_recv": "0 B"}

        upload_speed = 0.0
        download_speed = 0.0
        if self._last_net_io and (now - self._last_time) > 0:
            dt = now - self._last_time
            upload_speed = (net.bytes_sent - self._last_net_io.bytes_sent) / dt
            download_speed = (net.bytes_recv - self._last_net_io.bytes_recv) / dt

        self._last_net_io = net
        self._last_time = now

        return {
            "active_connections": active_connections,
            "total_connections": total_connections,
            "upload_speed": self._format_speed(max(upload_speed, 0)),
            "download_speed": self._format_speed(max(download_speed, 0)),
            "total_sent": self._format_bytes(net.bytes_sent),
            "total_recv": self._format_bytes(net.bytes_recv),
        }

    def get_system_status(self) -> dict:
        boot = psutil.boot_time()
        boot_dt = datetime.fromtimestamp(boot)
        uptime_seconds = int(time.time() - boot)

        # 负载均值
        try:
            load = psutil.getloadavg()
            load_1, load_5, load_15 = round(load[0], 2), round(load[1], 2), round(load[2], 2)
        except (AttributeError, OSError):
            cpu_pct = psutil.cpu_percent() / 100
            cores = psutil.cpu_count() or 1
            load_1 = load_5 = load_15 = round(cpu_pct * cores, 2)

        process_snapshot = self._get_process_snapshot()

        # 在线用户
        users = psutil.users()

        return {
            "load_1min": load_1,
            "load_5min": load_5,
            "load_15min": load_15,
            "uptime": self._format_uptime(uptime_seconds),
            "uptime_seconds": uptime_seconds,
            "boot_time": boot_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "total_processes": process_snapshot["total_processes"],
            "running_processes": process_snapshot["running_processes"],
            "sleeping_processes": process_snapshot["sleeping_processes"],
            "online_users": len(users),
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_network_trend(self) -> dict:
        """获取当前网络 I/O 快照，供前端构建趋势图使用。"""
        net = psutil.net_io_counters()
        if net is None:
            return {"bytes_sent": 0, "bytes_recv": 0, "timestamp": datetime.now().strftime("%H:%M:%S")}
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }

    def get_top_processes(self, limit: int = 10) -> list[dict]:
        return self._get_process_snapshot(limit)["top_processes"][:limit]

    def _get_process_snapshot(self, limit: int = 10) -> dict[str, Any]:
        now = time.monotonic()
        if self._process_snapshot and now - self._process_snapshot_time < self._process_snapshot_ttl:
            return self._process_snapshot

        # Windows can spend seconds walking every process; keep realtime polling bounded.
        procs: list[dict] = []
        running = 0
        sleeping = 0

        try:
            pids = psutil.pids()
        except Exception:
            pids = []

        scan_start = time.perf_counter()
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                with proc.oneshot():
                    name = proc.name()
                    status = proc.status()
                    if status == psutil.STATUS_RUNNING:
                        running += 1
                    elif status == psutil.STATUS_SLEEPING:
                        sleeping += 1

                    create_time = proc.create_time()
                    cpu_percent = proc.cpu_percent(interval=None)
                    memory_percent = proc.memory_percent()

                procs.append({
                    "pid": pid,
                    "name": name or "Unknown",
                    "cpu_percent": round(cpu_percent or 0, 1),
                    "memory_percent": round(memory_percent or 0, 1),
                    "status": status or "unknown",
                    "create_time": datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S") if create_time else "",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            if time.perf_counter() - scan_start >= self._process_scan_budget:
                break

        procs.sort(key=lambda p: (p["cpu_percent"], p["memory_percent"]), reverse=True)
        self._process_snapshot = {
            "total_processes": len(pids),
            "running_processes": running,
            "sleeping_processes": sleeping,
            "sampled_processes": len(procs),
            "top_processes": procs,
        }
        self._process_snapshot_time = now
        return self._process_snapshot

    def get_overview(self) -> dict:
        return {
            "basic_info": self.get_basic_info(),
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk_io": self.get_disk_io(),
            "network_io": self.get_network_io(),
            "system_status": self.get_system_status(),
            "top_processes": self.get_top_processes(),
        }

    def get_realtime(self) -> dict:
        return {
            "cpu": self.get_cpu_info(),
            "memory": self.get_memory_info(),
            "disk_io": self.get_disk_io(),
            "network_io": self.get_network_io(),
            "system_status": self.get_system_status(),
            "top_processes": self.get_top_processes(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def _get_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    @staticmethod
    def _bytes_to_gb(b: int | float) -> float:
        return round(b / (1024**3), 2)

    @staticmethod
    def _format_bytes(b: int | float) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(b) < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"

    @staticmethod
    def _format_speed(bps: float) -> str:
        for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
            if abs(bps) < 1024:
                return f"{bps:.1f} {unit}"
            bps /= 1024
        return f"{bps:.1f} TB/s"

    @staticmethod
    def _format_uptime(seconds: int) -> str:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        parts = []
        if days > 0:
            parts.append(f"{days}天")
        if hours > 0:
            parts.append(f"{hours}小时")
        parts.append(f"{minutes}分钟")
        return " ".join(parts)


# 全局单例
collector = ServerInfoCollector()
