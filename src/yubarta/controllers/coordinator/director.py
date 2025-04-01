import asyncio


class Director:
    def __init__(self, polling_interval: float = 1.0, batch_size: int = 10):
        self.polling_interval = polling_interval
        self.batch_size = batch_size

    async def start(self):
        while True:
            await self.process_pending_alarms()
            await asyncio.sleep(self.polling_interval)

    async def process_pending_alarms(self):
        pass
        # print("[Director] Processing pending alarms...")

def main():
    print("[Director] Starting loop...")
    asyncio.run(Director().start())

if __name__ == "__main__":
    main()



    # async def process_pending_alarms(self):
    #     session: Session = DBSession()

    #     try:
    #         alarms = session.execute(
    #             select(Alarm)
    #             .where(Alarm.status == "pending")
    #             .order_by(Alarm.received_at)
    #             .with_for_update(skip_locked=True)
    #             .limit(self.batch_size)
    #         ).scalars().all()

    #         if not alarms:
    #             return

    #         for alarm in alarms:
    #             alarm.status = "processing"
    #             alarm.status_updated_at = datetime.utcnow()
    #             session.add(alarm)

    #         session.commit()

    #         for alarm in alarms:
    #             enqueue_alarm(alarm)

    #     except Exception as e:
    #         session.rollback()
    #         print(f"[Director] Error: {e}")
    #     finally:
    #         session.close()
