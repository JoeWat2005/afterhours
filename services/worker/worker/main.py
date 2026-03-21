from arq import run_worker as arq_run_worker

from worker.queue import WorkerSettings


def run_worker_process() -> None:
    arq_run_worker(WorkerSettings)
