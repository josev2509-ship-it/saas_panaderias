# Errores encontrados

1. El generador O2C y el demo administrativo eran mensajes sin efectos funcionales.
2. La demo no incluía datos INABIE ni Producción.
3. El 606 era un stub y su pantalla dependía de captura legacy.
4. Extractos y Conciliaciones producían `VariableDoesNotExist` por encadenar `default` sobre atributos inexistentes.
5. CxC móvil desbordaba porque JavaScript convertía un formulario de tabla en barra sticky.
6. La cabecera del dashboard contable desbordaba en móvil.
