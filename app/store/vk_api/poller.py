import asyncio
from asyncio import Task
from typing import Optional

from app import asyncpool
from app.store import Store


class Poller:
    def __init__(self, store: Store):
        self.store = store
        self.is_running = False
        self.poll_task: Optional[Task] = None

    async def start(self):
        self.is_running = True
        self.poll_task = asyncio.create_task(self.poll())

    async def stop(self):
        self.is_running = False
        await self.poll_task

    async def poll(self):
        async with asyncpool.AsyncPool(loop=None, num_workers=10, name="HandlersPool",
                                       logger=self.store.bots_manager.logger,
                                       worker_co=self.store.bots_manager.handle_update,
                                       max_task_time=300,
                                       log_every_n=10) as pool:
            while self.is_running:
                updates = await self.store.vk_api.poll()
                for update in updates:
                    await pool.push(update)
