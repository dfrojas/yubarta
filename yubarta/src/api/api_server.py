from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import yaml
# from .ebpf_deployment import deploy_ebpf

app = FastAPI()

class EBPFProgram(BaseModel):
    name: str
    code: str
    attach_to: str

class TargetMachine(BaseModel):
    hostname: str
    username: str
    ssh_key_path: str

class EBPFDeployment(BaseModel):
    metadata: dict
    spec: dict

class EBPFDeploymentList(BaseModel):
    items: List[EBPFDeployment]

# In-memory storage for deployments (replace with a database in production)
deployments = {}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# @app.post("/api/v1/namespaces/{namespace}/ebpfdeployments", status_code=201)
# async def create_deployment(namespace: str, deployment: EBPFDeployment):
#     key = f"{namespace}/{deployment.metadata['name']}"
#     if key in deployments:
#         raise HTTPException(status_code=409, detail="Deployment already exists")
#     deployments[key] = deployment
#     # Trigger the actual deployment
#     await deploy_ebpf(deployment.spec['ebpf_program'], deployment.spec['target_machine'])
#     return {"message": "Deployment created successfully"}

# @app.get("/api/v1/namespaces/{namespace}/ebpfdeployments/{name}")
# async def get_deployment(namespace: str, name: str):
#     key = f"{namespace}/{name}"
#     if key not in deployments:
#         raise HTTPException(status_code=404, detail="Deployment not found")
#     return deployments[key]

# @app.get("/api/v1/namespaces/{namespace}/ebpfdeployments")
# async def list_deployments(namespace: str) -> EBPFDeploymentList:
#     namespace_deployments = [dep for key, dep in deployments.items() if key.startswith(f"{namespace}/")]
#     return EBPFDeploymentList(items=namespace_deployments)

# @app.delete("/api/v1/namespaces/{namespace}/ebpfdeployments/{name}")
# async def delete_deployment(namespace: str, name: str):
#     key = f"{namespace}/{name}"
#     if key not in deployments:
#         raise HTTPException(status_code=404, detail="Deployment not found")
#     del deployments[key]
#     # TODO: Implement actual removal of the eBPF program from the target machine
#     return {"message": "Deployment deleted successfully"}

# # ... (you can add more endpoints as needed, such as update, patch, etc.)