# Fr4meLuc — Framework Educativo de Pentesting

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Plataforma](https://img.shields.io/badge/Plataforma-Kali%20Linux-557C94?logo=linux)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)
![Estado](https://img.shields.io/badge/Estado-Activo-brightgreen)

> **Un framework educativo de pentesting interactivo por CLI para entornos de laboratorio controlados.**  
> Diseñado para jugadores de CTF, estudiantes de ciberseguridad y aprendices de red team.

---

## ¿Qué es esto?

`motor.py` es un script de Python completamente interactivo que **orquesta herramientas estándar de pruebas de penetración** a través de un menú estructurado por fases, explicando qué hace cada herramienta y por qué se usa.

No es solo un script. Es un **compañero de aprendizaje** para laboratorios de hacking ético.

```
   ███████╗██████╗ ██╗  ██╗███╗   ███╗███████╗██╗      ██╗   ██╗ ██████╗
   ██╔════╝██╔══██╗██║  ██║████╗ ████║██╔════╝██║      ██║   ██║██╔════╝
   █████╗  ██████╔╝███████║██╔████╔██║█████╗  ██║      ██║   ██║██║     
   ██╔══╝  ██╔══██╗╚════██║██║╚██╔╝██║██╔══╝  ██║      ██║   ██║██║     
   ██║     ██║  ██║     ██║██║ ╚═╝ ██║███████╗███████╗ ╚██████╔╝╚██████╗
   ╚═╝     ╚═╝  ╚═╝     ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝  ╚═════╝  ╚═════╝
  ═══════════════════  Fr4meLuc  v2.0  |  Linux Only  ═══════════════════
```

---

## Funcionalidades detalladas

### FASE 1 — Reconocimiento y Descubrimiento

#### ARP-Scan — Descubrimiento de red local
- Lista **todas las interfaces de red** disponibles en la máquina y permite elegir una.
- Lanza `arp-scan` sobre la interfaz seleccionada para descubrir hosts activos en la red local.
- Muestra IP, dirección MAC y fabricante de cada dispositivo encontrado.

#### Fingerprint de SO por Ping TTL
- Envía un `ping` al objetivo y analiza el valor **TTL** de la respuesta.
- Deduce el sistema operativo probable:
  - TTL ≈ 64 → **Linux / Unix**
  - TTL ≈ 128 → **Windows**
  - TTL ≈ 255 → **Cisco / routers**
- Guarda el resultado en el workspace del objetivo.

#### Escaneo de Puertos con Nmap — Dos Fases (estilo OSCP)

El escaneo de Nmap se realiza en **dos fases encadenadas automáticamente**:

1. **Fase rápida** — Escanea los 65535 puertos (`-p-`) con velocidades configurables:
   - **T4 (Rápido/Ruidoso):** Optimizado para laboratorios, más veloz.
   - **T2 (Lento/Sigiloso):** Menos detectable por IDS/firewall.
2. **Fase profunda** — Sobre los puertos abiertos detectados, lanza `-sC -sV` para identificar servicios, versiones y ejecutar scripts de detección.

**Detección automática de dominio y VHost:**
- Analiza la salida de Nmap en busca de menciones a dominios mediante varias heurísticas:
  - Redirecciones HTTP: `Did not follow redirect to http://maquina.htb/`
  - Certificados SSL/TLS: `Subject Alternative Name: DNS:maquina.htb`
- Si detecta un dominio, **ofrece automáticamente inyectarlo en `/etc/hosts`** para que todas las herramientas puedan resolverlo.
- El dominio queda activo en la sesión como **VHost** y se muestra en la barra de estado del panel.

#### Enum4Linux — Reconocimiento de entornos Windows/SMB
- Enumera usuarios, grupos, shares, políticas de contraseñas y dominios en redes Active Directory.
- Ideal para máquinas Windows o entornos con Samba.

---

### FASE 2 — Enumeración Web

> Las herramientas web se activan automáticamente en HTTP o HTTPS según lo detectado por Nmap.

#### Gobuster — Enumeración de directorios y rutas
- Realiza fuerza bruta de rutas sobre el servidor web objetivo.
- Usa el diccionario `directory-list-2.3-medium.txt` por defecto (configurable).
- Muestra un **spinner animado** con tiempo transcurrido en tiempo real.
- Guarda los resultados en `workspace/web/gobuster_directorios.txt`.

#### FFuF — Descubrimiento de subdominios virtuales (VHost fuzzing)

Esta es una de las funcionalidades más avanzadas del framework:

- Requiere un **dominio activo** (detectado por Nmap o configurado manualmente).
- Envía miles de peticiones HTTP modificando la cabecera `Host: FUZZ.dominio.htb` con cada palabra del diccionario.
- Permite hallar paneles ocultos en el mismo servidor como:
  - `admin.maquina.htb`
  - `ftp.maquina.htb`
  - `dev.maquina.htb`
- Filtra automáticamente redirecciones y falsos positivos (`-fc 301,302,400`).
- Guarda los resultados en formato JSON para su integración en el informe HTML.
- Muestra un **spinner animado** durante la ejecución.

#### WPScan — Scanner de WordPress
- Actualiza su base de datos antes de escanear.
- Detecta vulnerabilidades, plugins desactualizados, usuarios y temas en sites WordPress.

#### SQLMap — Inyección SQL automatizada
- Solicita la URL objetivo con el parámetro vulnerable.
- Ejecuta detección y extracción automática de bases de datos.

#### Nuclei — Scanner de CVEs modernos
- Usa plantillas actualizadas de la comunidad para detectar vulnerabilidades conocidas (CVEs).
- Clasifica los hallazgos por **severidad** (critical, high, medium, low, info).
- Guarda resultados en JSON para el informe HTML con código de colores.
- Muestra un **spinner animado** durante la ejecución.

#### Nikto — Vulnerabilidades web clásicas
- Detecta cabeceras inseguras, configuraciones por defecto, archivos sensibles expuestos, etc.
- Muestra un **spinner animado** durante la ejecución.
- Guarda los resultados en `workspace/web/nikto_resultados.txt`.

---

### FASE 3 — Explotación y Post-Explotación

#### SearchSploit — Búsqueda automática de exploits públicos
- Lee automáticamente el XML generado por Nmap.
- Extrae **servicios y versiones** detectadas y lanza búsquedas en la base de datos de Exploit-DB.
- Muestra los exploits disponibles para cada servicio identificado.

#### Hydra — Fuerza bruta de autenticación
- Soporta protocolos **SSH** y **FTP**.
- Permite especificar usuario, diccionario de contraseñas y número de hilos paralelos.
- Guarda los resultados en `workspace/exploits/hydra_ssh_bruteforce.txt`.

#### Cracking de Hashes Offline (John The Ripper)
- Permite introducir directamente un hash encontrado en la víctima (ej. hash de `/etc/shadow` o volcados de BD).
- Lanza automáticamente **John The Ripper** contra el hash usando el diccionario indicado (por defecto `rockyou.txt`).
- Descifra la contraseña offline sin interactuar más con el objetivo.

#### Descarga automática de PEAS (Escalada de Privilegios)
- Descarga la última versión oficial de **LinPEAS** (Linux) y **WinPEAS** (Windows) directamente desde GitHub.
- Los guarda automáticamente en la carpeta `workspace/payloads`, dejándolos listos para ser transferidos a la víctima mediante el Servidor HTTP.

#### Servidor HTTP de transferencia de payloads
- Levanta un servidor HTTP temporal en la máquina local.
- Permite transferir archivos (LinPEAS, scripts, payloads) al objetivo de forma sencilla usando `wget` o `curl` desde la víctima.

#### Netcat — Listener para Reverse Shell
- Abre un puerto de escucha local con `nc -lvnp`.
- Permite recibir conexiones de reverse shell una vez ejecutado un payload en el objetivo.
- El listener se cierra automáticamente cuando finaliza la conexión.

---

### Reporting

#### Informe HTML automático
Generado tras cualquier sesión de escaneo con un solo comando. Contiene:

- **Dashboard de estadísticas** — puertos abiertos, hallazgos de Nuclei, subdominios de FFuF
- **Tabla de puertos** desde el XML de Nmap (servicio, versión, estado)
- **Tabla de CVEs** desde el JSON de Nuclei (código de colores por severidad: rojo=crítico, naranja=alto...)
- **Tabla de subdominios** desde el JSON de FFuF
- **Volcados de logs** completos de cada herramienta ejecutada
- Se abre automáticamente en el navegador al generarse.

---

## Barra de estado del panel

El panel de ataque muestra en todo momento el estado de la sesión:

```
 Estado > [OK] Nmap   [OK] Web (http)   [OK] VHost (maquina.htb)
 Workspace: workspace_10_0_2_7/
```

| Indicador | Significado |
|-----------|-------------|
| `[OK] Nmap` | Nmap ejecutado, puertos y servicios conocidos |
| `[OK] Web (http/https)` | Protocolo web detectado automáticamente |
| `[OK] VHost (dominio)` | Dominio activo en la sesión, inyectado en `/etc/hosts` |

---

## Instalación

### Sistema (Kali Linux / Debian)

**1. Da permisos de ejecución al instalador:**
```bash
sudo chmod +x install.sh
```

**2. Ejecuta el instalador con privilegios de superusuario:**
```bash
sudo ./install.sh
```

O manualmente:
```bash
sudo apt install nmap gobuster nikto ffuf wpscan hydra sqlmap enum4linux exploitdb netcat-traditional arp-scan nuclei
```

### Python — Entorno Virtual

Se recomienda usar un entorno virtual para aislar las dependencias del proyecto.

**1. Crea el entorno virtual:**
```bash
python3 -m venv venv
```

**2. Activa el entorno virtual:**
```bash
# En Linux / macOS:
source venv/bin/activate

# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

**3. Instala las dependencias de Python:**
```bash
pip install -r requirements.txt
```

**4. Para desactivar el entorno virtual cuando termines:**
```bash
deactivate
```

---

## Uso

```bash
# Clona el repositorio
git clone https://github.com/luchernan/FrameWorkLucas

# Entra en el directorio del proyecto
cd FrameWorkLucas/

# Da permisos de ejecución al script de instalación (solo la primera vez)
sudo chmod +x install.sh

# Instala todas las dependencias del sistema
sudo ./install.sh

# Crea y activa el entorno virtual de Python
python3 -m venv venv
source venv/bin/activate

# Instala las dependencias de Python
pip install -r requirements.txt

# Ejecuta el framework
sudo python3 motor.py
```

---

## Estructura de salida

Cada objetivo crea automáticamente un espacio de trabajo organizado:

```
workspace_10_0_2_7/
├── nmap/
│   ├── nmap.xml                        ← Usado por SearchSploit y el informe HTML
│   └── escaneo_principal.txt
├── web/
│   ├── gobuster_directorios.txt
│   ├── nuclei.json                     ← CVEs con severidad para el informe
│   ├── nikto_resultados.txt
│   ├── ffuf_subdominios_maquina_htb.txt
│   └── ffuf_maquina_htb.json           ← Subdominios para el informe HTML
├── exploits/
│   └── hydra_ssh_bruteforce.txt
└── report_10_0_2_7_<timestamp>.html    ← Dashboard HTML final
```

---

## Flujo de trabajo recomendado

```
1. ARP-Scan → descubrir IPs en la red
2. Seleccionar objetivo → se crea el workspace
3. Ping TTL → identificar SO
4. Nmap (2 fases) → puertos, servicios, dominio automático
       └── Si detecta dominio → lo inyecta en /etc/hosts automáticamente
5. Gobuster → enumerar rutas web
6. FFuF → descubrir subdominios virtuales (requiere dominio activo)
7. Nuclei + Nikto → escanear vulnerabilidades web
8. SearchSploit → buscar exploits para los servicios encontrados
9. Hydra → fuerza bruta si hay credenciales que probar
10. Netcat listener → esperar reverse shell
11. Servidor HTTP → transferir herramientas al objetivo
12. Informe HTML → documentar toda la sesión
```

---

## Aviso Legal

> ⚠️ **Esta herramienta está diseñada EXCLUSIVAMENTE para uso educativo en entornos controlados:**  
> CTFs, máquinas virtuales propias, HackTheBox, TryHackMe o redes de laboratorio autorizadas.  
>  
> **Usar esta herramienta contra sistemas que no son de tu propiedad o para los que no tienes permiso escrito explícito es ilegal** y puede acarrear consecuencias penales.  
>  
> El autor no asume ninguna responsabilidad por el mal uso de esta herramienta.

---

## Probado en
- Kali Linux 2024.x
- Metasploitable 2/3
- Máquinas de HackTheBox / TryHackMe
- Configuraciones personalizadas con DVWA en Docker

---

## Licencia

MIT — ver [LICENSE](LICENSE)
