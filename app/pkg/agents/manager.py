import threading
from app.pkg.agents.audit import Client
from queue import Queue, Empty
from app.models.order import Order, db
import asyncio
from flask import Flask


class ClientManager:
    def __init__(self, model: str, api_key: str, app: Flask):
        self.model = model
        self.api_key = api_key
        self.clients = {}
        self.queue = Queue()
        self._stop_event = threading.Event()
        self._worker = None
        self._queue_timeout = 1
        self.app = app
        self.logger = app.logger

    def create(self, order_id: str, directory: str):
        client = Client(model=self.model, api_key=self.api_key, directory=directory, order_id=order_id, logger=self.logger)
        self.clients[order_id] = client
        self.queue.put(client)
        self.logger.info(f"Created new client for order {order_id}")

    def get(self, order_id: str):
        return self.clients.get(order_id)
    
    def delete(self, order_id: str):
        if order_id in self.clients:
            del self.clients[order_id]
            self.logger.info(f"Deleted client for order {order_id}")

    async def _process_queue(self):
        while not self._stop_event.is_set():
            try:
                client = self.queue.get(timeout=self._queue_timeout)
                if client is None:
                    continue
                order_id = client.getOrderId()
                self.logger.info("Starting to process client task")
                try:
                    blob_id = await client.begin()
                    with self.app.app_context():
                        db.session.query(Order).filter_by(order_id=order_id).update({'blob_id': blob_id})
                        db.session.commit()
                    self.logger.info("Successfully completed client task %s, %s", blob_id, order_id)

                except asyncio.CancelledError:
                    self.logger.warning("Task was cancelled")
                    raise
                except Exception as e:
                    self.logger.error(f"Error processing client task: {str(e)}", exc_info=True)
                finally:
                    self.queue.task_done()
                    await client.close()
                    self.delete(order_id)

            except Empty:
                continue
            except asyncio.CancelledError:
                self.logger.info("Queue processor was cancelled")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in queue processor: {str(e)}", exc_info=True)
                await asyncio.sleep(1)

    def run(self):
        if self._worker and self._worker.is_alive():
            self.logger.warning("Worker thread is already running")
            return

        self._stop_event.clear()
        self._worker = threading.Thread(
            target=lambda: asyncio.run(self._process_queue()),
            daemon=True
        )
        self._worker.start()
        self.logger.info("Started queue processor worker")

    def stop(self):
        self.logger.info("Stopping queue processor")
        self._stop_event.set()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=5)
            if self._worker.is_alive():
                self.logger.warning("Worker thread did not stop gracefully")