---
name: user-dev-context
description: Contexto de desarrollo del proyecto Fr4meLuc — plataforma y flujo de trabajo
metadata:
  type: user
---

El usuario desarrolla Fr4meLuc en **Windows** y luego despliega/prueba en **Linux** (Kali).
Todo el desarrollo de código y GUI se hace en Windows. Las pruebas reales de las herramientas
de pentesting (nmap, nuclei, gobuster, etc.) solo se ejecutan en Linux.

**How to apply:** No asumir que herramientas Linux están disponibles durante desarrollo.
Los imports de sistema (shutil.which, subprocess a nmap/gobuster etc.) están en core/tools
y no se ejecutan en Windows. La GUI y la lógica de DB sí son cross-platform.
