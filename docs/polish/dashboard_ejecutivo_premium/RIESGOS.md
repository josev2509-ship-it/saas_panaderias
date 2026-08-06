# Riesgos

- Chart.js se sirve desde CDN; si no hay red, los datos y estados vacíos permanecen legibles.
- Los importes se consolidan en moneda operativa sin conversión adicional; no se inventan tasas.
- El selector conserva el período certificado del mes actual; ampliar períodos exige una historia funcional posterior.
- La UAT visual autenticada depende de disponer de una sesión local válida.
