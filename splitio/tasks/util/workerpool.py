"""Worker pool module."""

import logging
from threading import Thread, Event
from six.moves import queue


class WorkerPool(object):
    """Worker pool class to implement single producer/multiple consumer."""

    def __init__(self, worker_count, worker_func):
        """
        Class constructor.

        :param worker_count: Number of workers for the pool.
        :type worker_func: Function to be executed by the workers whenever a messages is fetched.
        """
        self._logger = logging.getLogger(self.__class__.__name__)
        self._incoming = queue.Queue()
        self._should_be_working = [True for _ in range(0, worker_count)]
        self._worker_events = [Event() for _ in range(0, worker_count)]
        self._threads = [
            Thread(target=self._wrapper, args=(i, worker_func))
            for i in range(0, worker_count)
        ]
        for thread in self._threads:
            thread.setDaemon(True)

    def start(self):
        """Start the workers."""
        for thread in self._threads:
            thread.start()

    def _safe_run(self, func, message):
        """
        Execute the user funcion for a given message without raising exceptions.

        :param func: User defined function.
        :type func: callable
        :param message: Message fetched from the queue.
        :param message: object

        :return True if no everything goes well. False otherwise.
        :rtype bool
        """
        try:
            func(message)
            return True
        except Exception:  #pylint: disable=broad-except
            self._logger.error("Something went wrong when processing message %s", message)
            self._logger.debug('Original traceback: ', exc_info=True)
            return False

    def _wrapper(self, worker_number, func):
        """
        Fetch message, execute tasks, and acknowledge results.

        :param worker_number: # (id) of worker whose function will be executed.
        :type worker_number: int
        :param func: User defined function.
        :type func: callable.
        """
        while self._should_be_working[worker_number]:
            try:
                message = self._incoming.get(True, 0.5)
                self._incoming.task_done()

                # For some reason message can be None in python2 implementation of queue.
                # This method must be both ignored and acknowledged with .task_done()
                # otherwise .join() will halt.
                if message is None:
                    continue

                ok = self._safe_run(func, message)  #pylint: disable=invalid-name
                if not ok:
                    self._logger.error(
                        ("Something went wrong during the execution, "
                         "removing message \"%s\" from queue."),
                        message
                    )
            except queue.Empty:
                # No message was fetched, just keep waiting.
                pass

        # Set my flag indicating that i have finished
        self._worker_events[worker_number].set()

    def submit_work(self, message):
        """
        Add a new message to the work-queue.

        :param message: New message to add.
        :type message: object.
        """
        self._incoming.put(message)

    def wait_for_completion(self):
        """Block until the work queue is empty."""
        self._incoming.join()

    def stop(self, event=None):
        """Stop all worker nodes."""
        async_stop = Thread(target=self._wait_workers_shutdown, args=(event,))
        async_stop.setDaemon(True)
        async_stop.start()

    def _wait_workers_shutdown(self, event):
        """
        Wait until all workers have finished, and set the event.

        :param event: Event to set as soon as all the workers have shut down.
        :type event: threading.Event
        """
        self.wait_for_completion()
        for index, _ in enumerate(self._should_be_working):
            self._should_be_working[index] = False

        if event is not None:
            for worker_event in self._worker_events:
                worker_event.wait()
            event.set()
