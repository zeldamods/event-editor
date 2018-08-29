import eventeditor.util as util
from evfl import EventFlow
from pathlib import Path
import PyQt5.QtCore as qc # type: ignore
import queue
import sys
import threading
import traceback
import typing

class TaskQueue(queue.Queue):
    def __init__(self):
        super().__init__()
        t = threading.Thread(target=self._thread_func)
        t.daemon = True
        t.start()

    def add_task(self, task):
        self.put(task)

    def _thread_func(self):
        while True:
            item = self.get()
            item()
            self.task_done()

class AutoSaveSystem:
    def __init__(self) -> None:
        self._save_dir: typing.Optional[Path] = None
        save_dir = qc.QStandardPaths.writableLocation(qc.QStandardPaths.AppLocalDataLocation)
        if not save_dir:
            return
        self._save_dir = Path(save_dir)
        self._save_dir.mkdir(parents=True, exist_ok=True)
        self._queue = TaskQueue()
        self.reset()

    def get_directory(self) -> typing.Optional[Path]:
        return self._save_dir

    def reset(self) -> None:
        if not self._save_dir:
            return

        self._queue.join()
        self._current_save_idx = 0

    def save(self, flow: typing.Optional[EventFlow]) -> None:
        if not self._save_dir:
            return

        def do_write():
            if not flow or not self._save_dir:
                return
            path = self._save_dir/f'autosave_{flow.name}__{self._current_save_idx}.bfevfl.gz'
            try:
                util.write_flow(str(path), flow)
                self._current_save_idx = (self._current_save_idx + 1) % 10
            except:
                sys.stderr.write(f'!!! Autosave failed !!!\n{traceback.format_exc()}\n\n')

        self._queue.add_task(do_write)
