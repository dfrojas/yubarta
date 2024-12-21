from enum import Enum


class DeploymentStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    FAILED = "Failed"


# class AlertSeverity(Enum):
#     LOW = "Low"
#     MEDIUM = "Medium"
#     HIGH = "High"
#     CRITICAL = "Critical"


# class UserRole(Enum):
#     ADMIN = "Admin"
#     OPERATOR = "Operator"
#     VIEWER = "Viewer"


# class EBPFDeploymentStatus(Enum):
#     PENDING = "Pending"
#     DEPLOYING = "Deploying"
#     DEPLOYED = "Deployed"
#     FAILED = "Failed"


# class EBPFProgramStatus(Enum):
#     PENDING = "Pending"
#     COMPILING = "Compiling"
#     LOADING = "Loading"
#     ATTACHING = "Attaching"
#     DONE = "Done"
#     FAILED = "Failed"


# class EBPFProgramStep(Enum):
#     COMPILE = "Compile"
#     LOAD = "Load"
#     ATTACH = "Attach"


# class EBPFProgramStepResult(Enum):
#     SUCCESS = "Success"
#     FAILURE = "Failure"


# class DetectorRules(Enum):
#     tipo (CPU, MEM, NET, FILE)
#     regla (porcentaje de uso de cpu, porcentaje de uso de
#     memoria, porcentaje de uso de red, tamaño de archivo)
#     valor (20, 80, 100, 1024)
#     operador (>, <, >=, <=, ==, !=)
