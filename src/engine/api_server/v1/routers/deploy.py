from http import HTTPStatus

from fastapi import APIRouter, Response

from engine.controllers.deployment import DeploymentController
from engine.entities.models import EBPFDeployment

router = APIRouter()


@router.post("/api/v1/deployments")
async def create_deployment(config: dict):
    try:
        deployment = EBPFDeployment.parse_obj(config)
        result = DeploymentController(deployment).run()

        return Response(
            status_code=HTTPStatus.OK,
            media_type="application/json",
        )
    except Exception as e:
        return Response(
            status_code=HTTPStatus.BAD_REQUEST,
            content=str(e),
            media_type="application/json",
        )
