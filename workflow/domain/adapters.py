from abc import ABC, abstractmethod
from .exceptions import WorkflowConfigurationError

class WorkflowDocumentAdapter(ABC):
    allowed_context_fields=frozenset()
    @abstractmethod
    def get_empresa(self,document): ...
    @abstractmethod
    def get_solicitante(self,document): ...
    @abstractmethod
    def build_context(self,document): ...
    @abstractmethod
    def can_start(self,document): ...
    @abstractmethod
    def snapshot(self,document): ...
    def document_url(self,document,user): return ""
    def resolve_dynamic_assignees(self,document,parameter): return []
    def on_state_change(self,document,state): return None
    def on_final_result(self,document,result): return None

class AdapterRegistry:
    def __init__(self): self._adapters={}
    def register(self,key,adapter):
        if not isinstance(adapter,WorkflowDocumentAdapter): raise TypeError("El adaptador debe implementar WorkflowDocumentAdapter.")
        self._adapters[key]=adapter
    def unregister(self,key): self._adapters.pop(key,None)
    def get(self,key):
        try:return self._adapters[key]
        except KeyError as exc: raise WorkflowConfigurationError(f"Adaptador no registrado: {key}.") from exc
adapter_registry=AdapterRegistry()
