from django import forms
from .models import Conduce, CentroEducativo, Empresa, MenuDiario


class ConduceForm(forms.ModelForm):
    class Meta:
        model = Conduce
        fields = '__all__'


class CentroEducativoForm(forms.ModelForm):
    class Meta:
        model = CentroEducativo
        fields = '__all__'


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = '__all__'


class MenuDiarioForm(forms.ModelForm):
    class Meta:
        model = MenuDiario
        fields = '__all__'