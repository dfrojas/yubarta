# import abc
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from . import repository, orm

# class AbstractUnitOfWork(abc.ABC):
#     deployments: repository.AbstractRepository

#     def __enter__(self):
#         return self

#     def __exit__(self, *args):
#         self.rollback()

#     @abc.abstractmethod
#     def commit(self):
#         raise NotImplementedError

#     @abc.abstractmethod
#     def rollback(self):
#         raise NotImplementedError

# class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
#     def __init__(self):
#         self.session_factory = sessionmaker(
#             bind=create_engine("sqlite:///yubarta.db")
#         )

#     def __enter__(self):
#         self.session = self.session_factory()
#         self.deployments = repository.SqlAlchemyRepository(self.session)
#         return super().__enter__()

#     def __exit__(self, *args):
#         super().__exit__(*args)
#         self.session.close()

#     def commit(self):
#         self.session.commit()

#     def rollback(self):
#         self.session.rollback()
