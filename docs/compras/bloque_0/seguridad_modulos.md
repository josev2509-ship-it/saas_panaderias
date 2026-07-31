# Seguridad de módulos

`modulo_requerido` exige autenticación, empresa asociada y activa, bandera de
módulo y permiso opcional. Un superusuario sin empresa también falla de forma
segura. La relación vigente sigue siendo `User` ↔ `Empresa` uno a uno; una
membresía multiusuario robusta queda pendiente.
