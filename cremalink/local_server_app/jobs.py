import asyncio
from typing import List

from cremalink.local_server_app.device_adapter import DeviceAdapter
from cremalink.local_server_app.state import LocalServerState
from cremalink.local_server_app.config import ServerSettings


class JobManager:
    def __init__(self):
        self.tasks: List[asyncio.Task] = []

    def start(self, coro, name: str):
        task = asyncio.create_task(coro, name=name)
        self.tasks.append(task)

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        for task in self.tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.tasks.clear()


async def nudger_job(st: LocalServerState, adapter: DeviceAdapter, settings: ServerSettings, stop_event: asyncio.Event):
    interval = settings.nudger_poll_interval
    while not stop_event.is_set():
        try:
            async with st.lock:
                should_nudge = len(st.command_queue) > 0 or not st.registered
            if should_nudge:
                await adapter.register_with_device(st)
        except Exception as exc:
            st.log("local_reg_nudge_failed", {"error": str(exc)})
            await st.rekey()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


async def monitor_job(st: LocalServerState, settings: ServerSettings, stop_event: asyncio.Event):
    interval = settings.monitor_poll_interval
    while not stop_event.is_set():
        try:
            async with st.lock:
                ready = st.is_configured() and not st._monitor_request_pending
            if ready:
                await st.queue_monitor()
        except Exception as exc:
            st.log("monitor_poll_failed", {"error": str(exc)})
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


async def rekey_job(state: LocalServerState, adapter: DeviceAdapter, settings: ServerSettings, stop_event: asyncio.Event):
    interval = settings.rekey_interval_seconds
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            pass
        try:
            await state.rekey()
            await adapter.register_with_device(state)
            state.log("rekey_triggered", {"interval": interval})
        except Exception as exc:  # pragma: no cover - network side effects
            state.log("rekey_failed", {"error": str(exc)})
