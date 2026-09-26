# GRH0652 · Paquetes SCORM 1.2

Versión estable del módulo **0652 · Gestión de Recursos Humanos**.

- UT1 / RA1 — Gestión de la contratación laboral.
- UT2 / RA2 — Modificación, suspensión y extinción de la relación laboral.
- UT3 / RA3 — Obligaciones empresariales con la Seguridad Social.
- UT4 / RA4 — Retribución, nóminas, cotización e IRPF.

Cada carpeta `ut1`–`ut4` contiene un SCO autónomo con `imsmanifest.xml` en formato SCORM 1.2.

El workflow `.github/workflows/build-grh0652-scorm.yml` valida todos los recursos declarados y genera un ZIP independiente por RA. El manifiesto es la fuente de verdad del empaquetado.

## Estado de cierre

- RA1–RA4 disponibles desde la aplicación principal.
- Reproductor único y dinámico para las cuatro UT.
- Persistencia SCORM y local.
- Práctica interactiva y evaluación por criterios.
- UT1 incorpora laboratorio de contratos con estructura didáctica similar a los modelos SEPE y ayuda contextual por campo.
- UT4 incorpora laboratorio de nóminas y ayuda contextual por campo.
- No existe RA5/UT5 en esta versión del módulo.
