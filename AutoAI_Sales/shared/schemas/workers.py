from pydantic import BaseModel

class WorkerConfigResponse(BaseModel):
    dealership_id: str
    worker_key: str
    name: str
    status: str
    tagline: str
    description: str

    model_config = {"from_attributes": True}
