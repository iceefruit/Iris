"""System Status and Hardware Telemetry Tool."""

import json
from typing import Dict, Any
import psutil
from tools.base import BaseTool, ToolResult
from vision.context import SystemContextExtractor


class SystemStatusTool(BaseTool):
    """Retrieves real-time system performance, battery, memory, disk, and window metrics."""

    name = "get_system_status"
    description = (
        "Queries real-time OS telemetry: CPU utilization, RAM usage, Battery level, "
        "Disk spaces, active foreground window, and top resource-consuming processes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "include_top_processes": {
                "type": "boolean",
                "default": True,
                "description": "Whether to include top 5 processes by memory usage.",
            },
        },
    }

    def execute(self, include_top_processes: bool = True, **kwargs) -> ToolResult:
        try:
            # 1. CPU & Memory
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()

            # 2. Battery
            battery = psutil.sensors_battery()
            battery_info = None
            if battery:
                battery_info = {
                    "percent": f"{battery.percent}%",
                    "power_plugged": battery.power_plugged,
                    "status": "Charging" if battery.power_plugged else "On Battery",
                }

            # 3. Disks
            disks = []
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mount": part.mountpoint,
                        "total_gb": round(usage.total / (1024**3), 1),
                        "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1),
                        "percent": f"{usage.percent}%",
                    })
                except (PermissionError, OSError):
                    continue

            # 4. Active Window
            active_win = SystemContextExtractor.get_active_window_context()

            # 5. Top processes
            top_procs = []
            if include_top_processes:
                for p in sorted(
                    psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                    key=lambda x: x.info.get("memory_percent") or 0,
                    reverse=True,
                )[:5]:
                    top_procs.append({
                        "name": p.info["name"],
                        "pid": p.info["pid"],
                        "memory_percent": f"{round(p.info['memory_percent'] or 0.0, 1)}%",
                    })

            data = {
                "cpu_utilization": f"{cpu_pct}%",
                "cpu_count": psutil.cpu_count(logical=True),
                "ram_usage": f"{round(mem.used / (1024**3), 1)}GB / {round(mem.total / (1024**3), 1)}GB ({mem.percent}%)",
                "battery": battery_info or "Desktop AC / No Battery",
                "disks": disks,
                "active_window": {
                    "title": active_win.active_window_title,
                    "process": active_win.process_name,
                    "pid": active_win.process_id,
                },
                "top_processes": top_procs,
            }

            return ToolResult(success=True, output=json.dumps(data, indent=2))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to gather system metrics: {str(e)}")
