#!/usr/bin/env python3
"""Fr4meLuc — shim de compatibilidad.

A partir de v3.0 el código vive en el paquete `fr4meluc/`. Este archivo se
mantiene para que `sudo python3 motor.py` siga funcionando como siempre.

Recomendado para nuevos usos:
    pip install -e .
    fr4meluc           # entry point
    fr4meluc --quiet   # sin capa educativa
"""
from fr4meluc.cli.main import main

if __name__ == "__main__":
    main()
