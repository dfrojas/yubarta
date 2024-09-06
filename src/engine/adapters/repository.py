# import abc

# from ..domain import model


# class AbstractRepository(abc.ABC):
#     @abc.abstractmethod
#     def add(self, deployment: model.EBPFDeployment):
#         raise NotImplementedError

#     @abc.abstractmethod
#     def get(self, reference: str) -> model.EBPFDeployment:
#         raise NotImplementedError

#     @abc.abstractmethod
#     def list(self) -> list[model.EBPFDeployment]:
#         raise NotImplementedError


# class SqlAlchemyRepository(AbstractRepository):
#     def __init__(self, session):
#         self.session = session

#     def add(self, deployment):
#         self.session.add(deployment)

#     def get(self, reference):
#         return (
#             self.session.query(model.EBPFDeployment)
#             .filter_by(reference=reference)
#             .first()
#         )

#     def list(self):
#         return self.session.query(model.EBPFDeployment).all()
