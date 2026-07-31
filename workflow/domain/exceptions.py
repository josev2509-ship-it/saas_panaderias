from django.core.exceptions import ValidationError
class WorkflowError(ValidationError): pass
class WorkflowConfigurationError(WorkflowError): pass
class WorkflowStateError(WorkflowError): pass
class WorkflowAssignmentError(WorkflowError): pass
class WorkflowAmbiguityError(WorkflowConfigurationError): pass
