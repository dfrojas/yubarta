from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import Response
# from ..service_layer import services
# from ..adapters import unit_of_work
from ...domain import models
import uvicorn
app = FastAPI()

class DeploymentCreate(BaseModel):
    metadata: dict
    spec: dict


@app.get("/")
def home():
    whale_ascii = """
             .
            ":"
          ___:____     |"\/"|
        ,'        `.    \  /
        |  O        \___/  |
    ~^~^~^~^~^~^~^~^~^~^~^~^~
    """
    return Response(content=whale_ascii, media_type="text/plain", headers={"Content-Type": "text/plain; charset=utf-8"})


@app.post("/api/v1/namespaces/{namespace}/ebpfdeployments")
async def create_deployment(namespace: str, deployment: DeploymentCreate):
    # print(deployment.spec, "SPEC")
    try:
        ebpf_program = models.EBPFProgram(**deployment.spec['program'])
        target_machine = models.TargetMachine(**deployment.spec['target'])
        # uow = unit_of_work.SqlAlchemyUnitOfWork()
        # result = services.create_deployment(
        #     reference=deployment.metadata['name'],
        #     ebpf_program=ebpf_program,
        #     target_machine=target_machine,
        #     namespace=namespace,
        #     uow=uow
        # )
        # print(deployment)
        return {"message": "Deployment created successfully", "reference": 1}#result.reference}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

# # @app.get("/api/v1/namespaces/{namespace}/ebpfdeployments/{name}")
# # async def get_deployment(namespace: str, name: str):
# #     uow = unit_of_work.SqlAlchemyUnitOfWork()
# #     deployment = services.get_deployment(name, uow)
# #     if deployment and deployment.namespace == namespace:
# #         return deployment
# #     raise HTTPException(status_code=404, detail="Deployment not found")

# # @app.get("/api/v1/namespaces/{namespace}/ebpfdeployments")
# # async def list_deployments(namespace: str):
# #     uow = unit_of_work.SqlAlchemyUnitOfWork()
# #     deployments = services.list_deployments(uow)
# #     return [d for d in deployments if d.namespace == namespace]
