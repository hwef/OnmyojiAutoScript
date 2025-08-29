from deploy.patch import pre_checks

pre_checks()

from deploy.process import ProcessManager
from deploy.config import ExecutionError


class KillOAS(ProcessManager):
    def install(self):
        try:
            self.process_kill()
        except ExecutionError:
            exit(1)


if __name__ == '__main__':
    KillOAS().install()
