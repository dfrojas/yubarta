from sqlalchemy import select

from yubarta.core.models import Alert


class SqlAlchemyAlarmRepository:
    def __init__(self, session):
        self.session = session

    async def add(self, alert: Alert):
        try:
            self.session.add(alert)
            await self.session.commit()
            return alert
        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_all(self):
        query = select(Alert)
        result = await self.session.execute(query)
        return result.scalars().all()
