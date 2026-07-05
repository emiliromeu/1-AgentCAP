# Guia d'instal·lació Windows — Generador de Horarios CAP

**Per a qui és aquesta guia:** per a mi (el tècnic), per desplegar el projecte en un PC Windows
nou (casa o oficina). No és per a la Rosa.

---

## 1. Requisits previs

### Python 3.11 o superior

La app requereix Python 3.11+. Comprova si ja està instal·lat:

```
Win + R → escriu "cmd" → Enter
python --version
```

- Si surt `Python 3.11.x` o superior → ✅ ja tens Python, passa al punt 2.
- Si surt `'python' no se reconoce...` o una versió 3.9/3.10 → cal instal·lar o actualitzar.

**Instal·lació de Python:**
1. Ves a https://www.python.org/downloads/
2. Descarrega la versió més recent de Python 3.11 o 3.12 (evita la 3.13, menys testada).
3. Executa l'instal·lador.
4. ⚠️ **IMPORTANT:** durant la instal·lació, marca la casella **"Add Python to PATH"** abans de
   fer clic a *Install Now*. Si no la marques, el .bat no trobarà Python.
5. Un cop instal·lat, obre una CMD nova i comprova amb `python --version`.

---

## 2. Instal·lació (primera vegada, PC nou)

### Checklist pas a pas

- [ ] **2.1 — Copia la carpeta del projecte al PC**

  Copia la carpeta `agente_cap` (sencera, amb tots els fitxers) a una ubicació permanent.
  Recomanat: `C:\Users\<nom_usuari>\Documents\agente_cap`
  (evita el Escritorio — alguns PCs en sync amb OneDrive poden causar problemes).

- [ ] **2.2 — Crea el fitxer `.env` amb la API key**

  Dins la carpeta `agente_cap`, crea un fitxer de text anomenat exactament `.env`
  (sense extensió .txt) amb aquest contingut:

  ```
  ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
  ```

  Substitueix `sk-ant-xxx...` per la clau real d'Anthropic.

  **Com crear el .env a Windows:**
  - Obre el Bloc de notas (Notepad).
  - Escriu `ANTHROPIC_API_KEY=sk-ant-...` (la clau real).
  - Fitxer → Guardar como → navega a la carpeta `agente_cap`.
  - Al camp "Nombre de archivo" escriu: `.env` (amb el punt al davant).
  - Al camp "Tipo" selecciona "Todos los archivos (*.*)" — important, si no, guardarà `.env.txt`.
  - Guardar.

  Comprova que a la carpeta es veu un fitxer `.env` (no `.env.txt`).

- [ ] **2.3 — Executa l'instal·lador**

  Doble clic a `1_Instalar_CAP.bat`.

  Apareixerà una finestra negra. Esperarà uns 3-5 minuts mentre instal·la les dependències.
  Al final hauries de veure:

  ```
  ============================================================
    Instalacion completada correctamente.
    Ya puedes cerrar esta ventana.
    Para abrir la aplicacion, usa el archivo:
    "2_Abrir_CAP.bat"
  ============================================================
  ```

  Si la finestra es tanca sola sense mostrar "completada correctamente" → mira l'apartat 4
  (Solució de problemes).

- [ ] **2.4 — Verifica la instal·lació**

  Comprova que s'ha creat la carpeta `.venv` dins `agente_cap`. Si existeix, la instal·lació
  va bé.

---

## 3. Ús diari (per a Rosa)

1. Doble clic a **`2_Abrir_CAP.bat`**.
2. Apareix una finestra negra uns 5-10 segons.
3. El navegador s'obre sol a `http://localhost:8501` amb la app.
4. Quan la Rosa acabi, tanca la finestra negra (això atura la app).

> **Nota per a Rosa:** no cal fer res més. Mai tocar la finestra negra mentre la app estigui
> oberta; tancar-la atura la app.

---

## 4. Solució de problemes

### "No se ha encontrado Python en este ordenador"

Python no està instal·lat o no és al PATH.
→ Segueix el punt 1 d'aquesta guia per instal·lar Python.
→ Recorda marcar "Add Python to PATH" durant la instal·lació.
→ Tanca i torna a obrir la CMD (o el .bat) després d'instal·lar.

---

### "El entorno virtual no esta instalado" (en obrir `2_Abrir_CAP.bat`)

No s'ha executat l'instal·lador, o va fallar.
→ Executa `1_Instalar_CAP.bat` i espera que acabi correctament.

---

### "No se encuentra el archivo .env con la clave de API"

El fitxer `.env` no existeix o té un nom incorrecte (p.ex. `.env.txt`).
→ Comprova que a la carpeta del projecte hi ha un fitxer `.env` (sense extensió .txt).
→ Obre'l amb el Notepad i comprova que conté `ANTHROPIC_API_KEY=sk-ant-...`.
→ Per veure extensions d'arxiu a Windows: Explorador → Vista → mostra "Extensiones de nombre
  de archivo".

---

### La app s'obre però el navegador no apareix

→ Obre manualment el navegador i ves a: `http://localhost:8501`
→ Si tampoc carrega, comprova que la finestra negra del .bat segueix oberta.

---

### Error "port already in use" o "Address already in use"

Una altra instància de la app ja s'està executant.
→ Tanca totes les finestres negres de la app i torna a obrir `2_Abrir_CAP.bat`.
→ Si el problema persisteix, reinicia el PC.

---

### La instal·lació falla al mig del `pip install`

Pot ser un problema de xarxa o de permisos.
→ Comprova que el PC té connexió a internet.
→ Torna a executar `1_Instalar_CAP.bat` (el .bat detecta si el .venv ja existeix i no el
  recrea, però sí torna a fer el `pip install` per completar el que faltava).
→ Si hi ha errors de permisos, prova a executar el .bat fent clic dret → "Ejecutar como
  administrador".

---

### Antivirus bloqueja el .bat o la app

Alguns antivirus (Windows Defender, Avast, etc.) bloquegen fitxers .bat nous.
→ Fes clic dret al .bat → Propiedades → si surt el botó "Desbloquear", fes-hi clic i aplica.
→ Si l'antivirus quarantena algun fitxer, afegeix la carpeta `agente_cap` a les exclusions.

---

## 5. Seguretat de la API key (.env)

⚠️ **El fitxer `.env` conté la clau secreta d'Anthropic. Tracta-la com una contrasenya.**

- **No** comparteixis el `.env` per email, WhatsApp ni cap altre canal.
- **No** el pujis a GitHub, Google Drive, OneDrive ni cap repositori o núvol compartit.
- **No** l'incloguis en còpies de seguretat que es sincronitzin automàticament al núvol
  (si la carpeta `agente_cap` és a Documents i tens OneDrive actiu, exclou el `.env`
  de la sincronització, o mou la carpeta fora de Documents).
- El `.gitignore` del projecte ja exclou el `.env` del control de versions — mai el comitegis.
- Si creus que la clau s'ha exposat, regenera-la des de https://console.anthropic.com

---

## Resum ràpid (checklist de desplegament)

```
[ ] Python 3.11+ instal·lat i al PATH
[ ] Carpeta agente_cap copiada a C:\Users\...\Documents\agente_cap
[ ] Fitxer .env creat amb ANTHROPIC_API_KEY=sk-ant-...
[ ] 1_Instalar_CAP.bat executat i finalitzat correctament
[ ] Prova: doble clic a 2_Abrir_CAP.bat → navegador s'obre a localhost:8501
[ ] La Rosa sap que: doble clic a 2_Abrir_CAP.bat, i tancar la finestra negra per sortir
```
