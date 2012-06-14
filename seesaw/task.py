import contextlib
import os
import traceback

from .event import Event
from .item import Item, realize

class Task(object):
  def __init__(self, name):
    self.name = name
    self.cwd = os.getcwd()
    self.on_start_item = Event()
    self.on_complete_item = Event()
    self.on_fail_item = Event()
    self.on_finish_item = Event()

  def start_item(self, item):
    item.set_task_status(self, Item.TaskStatus.running)
    self.on_start_item.fire(self, item)

  def fail_item(self, item):
    item.set_task_status(self, Item.TaskStatus.failed)
    self.on_fail_item.fire(self, item)
    self.on_finish_item.fire(self, item)

  def complete_item(self, item):
    item.set_task_status(self, Item.TaskStatus.completed)
    self.on_complete_item.fire(self, item)
    self.on_finish_item.fire(self, item)

  @contextlib.contextmanager
  def task_cwd(self):
    curdir = os.getcwd()
    try:
      os.chdir(self.cwd)
      yield
    finally:
      os.chdir(curdir)

  def __str__(self):
    return self.name

class SimpleTask(Task):
  def __init__(self, name):
    Task.__init__(self, name)

  def enqueue(self, item):
    self.start_item(item)
    item.log_output("Starting %s for %s\n" % (self, item.description()))
    try:
      with self.task_cwd():
        self.process(item)
    except Exception, e:
      item.log_output("Failed %s for %s\n" % (self, item.description()))
      item.log_output("%s\n" % traceback.format_exc())
      item.log_error(self, e)
      self.fail_item(item)
    else:
      item.log_output("Finished %s for %s\n" % (self, item.description()))
      self.complete_item(item)

  def process(self, item):
    pass

  def __str__(self):
    return self.name

class LimitConcurrent(Task):
  def __init__(self, concurrency, inner_task):
    Task.__init__(self, "LimitConcurrent")
    self.concurrency = concurrency
    self.inner_task = inner_task
    self.inner_task.on_complete_item.handle(self._inner_task_complete_item)
    self.inner_task.on_fail_item.handle(self._inner_task_fail_item)
    self._queue = []
    self._working = 0

  def enqueue(self, item):
    if self._working < realize(self.concurrency, item):
      self._working += 1
      self.inner_task.enqueue(item)
    else:
      self._queue.append(item)
  
  def _inner_task_complete_item(self, task, item):
    self._working -= 1
    if len(self._queue) > 0:
      self._working += 1
      self.inner_task.enqueue(self._queue.pop(0))
    self.complete_item(item)
  
  def _inner_task_fail_item(self, task, item):
    self._working -= 1
    if len(self._queue) > 0:
      self._working += 1
      self.inner_task.enqueue(self.queue.pop(0))
    self.fail_item(item)

  def __str__(self):
    return "LimitConcurrent(" + str(self.concurrency) + " x " + str(self.inner_task) + ")"

class SetItemKey(SimpleTask):
  def __init__(self, key, value):
    SimpleTask.__init__(self, "SetItemKey")
    self.key = key
    self.value = value

  def process(self, item):
    item[self.key] = self.value

  def __str__(self):
    return "SetItemKey(" + str(self.key) + ": " + str(self.value) + ")"

class PrintItem(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "PrintItem")

  def process(self, item):
    item.log_output("%s\n" % str(item))
