import datetime
import getpass
import glob
import os
import pathlib
import psutil
import shutil
import speech_recognition as sr
import subprocess
import urllib.parse
# Librería recomendada para consultas en segundo plano (puedes instalarla con: pip install google-genai)
import webbrowser

try:
  from google import genai
except ImportError:
  genai = None

# --- Configuración de Piper TTS ---
RUTA_PIPER = "/home/thiago/piper/piper"
RUTA_MODELO = "/home/thiago/piper/es_AR-daniela-high.onnx"
ARCHIVO_TEMP = "/tmp/trinity_voz.wav"

# --- Diccionario de aplicaciones personalizadas y enlaces ---
APLICACIONES_PERSONALIZADAS = {
    "cemu": "/home/thiago/cemu/Cemu",
    "emulador": "/home/thiago/cemu/Cemu",
    "navegador": "/usr/bin/firefox",
    "youtube music": "https://music.youtube.com",
    "música": "https://music.youtube.com",
}


def hablar(texto):
  """Función de voz optimizada para Piper TTS con limpieza de buffer."""
  print(f"TRINITY: {texto}")

  try:
    if os.path.exists(ARCHIVO_TEMP):
      os.remove(ARCHIVO_TEMP)

    proceso_piper = subprocess.Popen(
        [
            RUTA_PIPER,
            "--model",
            RUTA_MODELO,
            "--output_file",
            ARCHIVO_TEMP,
            "--length_scale",
            "0.88",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proceso_piper.communicate(input=texto)

    if os.path.exists(ARCHIVO_TEMP) and os.path.getsize(ARCHIVO_TEMP) > 0:
      subprocess.run(
          ["aplay", "-D", "default", ARCHIVO_TEMP],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
    else:
      print(f"[ERROR Piper]: No se pudo generar el audio. Detalle: {stderr}")
  except Exception as e:
    print(f"[ERROR Piper]: {e}")


def abrir_aplicacion_personalizada(comando):
  """Busca en el diccionario de rutas personalizadas o enlaces web."""
  comando_lower = comando.lower().strip()

  for nombre_app, destino in APLICACIONES_PERSONALIZADAS.items():
    if nombre_app in comando_lower:
      hablar(f"Abriendo {nombre_app}.")
      try:
        if destino.startswith("http"):
          webbrowser.open(destino)
        else:
          subprocess.Popen(
              [destino],
              stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL,
          )
        return True
      except Exception as e:
        hablar("No pude iniciar el destino especificado.")
        print(f"[ERROR Destino]: {e}")
        return True

  return False


def preguntale_a_internet(comando=""):
  """Consulta a Gemini en segundo plano sin abrir ventanas y responde por voz."""
  pregunta = ""

  for prefijo in [
      "pregúntale a internet",
      "preguntale a internet",
      "pregúntale a gemini",
      "preguntale a gemini",
      "pregúntale",
      "preguntale",
  ]:
    if comando.lower().startswith(prefijo):
      pregunta = comando.lower().replace(prefijo, "", 1).strip()
      break

  if not pregunta:
    hablar("¿Qué deseas consultarle a internet?")
    pregunta = escuchar()

  if not pregunta:
    hablar("No entendí tu pregunta. Cancelando.")
    return

  hablar("Consultando en segundo plano. Un momento.")

  try:
    # Verificamos si la librería de GenAI está disponible y configurada
    if genai is not None and "GEMINI_API_KEY" in os.environ:
      client = genai.Client()
      # Usamos el modelo estándar rápido para asistentes
      response = client.models.generate_content(
          model="gemini-2.5-flash",
          contents=pregunta,
      )
      respuesta_texto = response.text
      # Acortamos un poco la respuesta si es muy extensa para que no sea tedioso escucharla
      if len(respuesta_texto) > 350:
        respuesta_texto = (
            respuesta_texto[:350] + "... La respuesta es muy extensa."
        )
      hablar(respuesta_texto)
    else:
      # Alternativa por respaldo si no hay API Key configurada: realiza búsqueda web interna invisible o emite aviso
      hablar(
          "Para realizar consultas directas en segundo plano, por favor"
          " configura tu clave de API de Gemini en el sistema."
      )
  except Exception as e:
    print(f"[ERROR IA en segundo plano]: {e}")
    hablar("Ocurrió un error al procesar la consulta en segundo plano.")


def buscar_en_internet(comando=""):
  """Busca términos en internet o abre un sitio web específico solicitado por voz."""
  termino = ""

  for prefijo in [
      "busca en internet",
      "buscar en internet",
      "busca en google",
      "buscar en google",
      "busca",
      "buscar",
      "navega a",
      "navegar a",
  ]:
    if comando.lower().startswith(prefijo):
      termino = comando.lower().replace(prefijo, "", 1).strip()
      break

  if not termino:
    hablar("¿Qué deseas buscar o qué sitio quieres abrir?")
    termino = escuchar()

  if not termino:
    hablar("No entendí la petición. Cancelando.")
    return

  if (
      "." in termino
      and " " not in termino
      or termino.startswith("http://")
      or termino.startswith("https://")
  ):
    if not termino.startswith("http://") and not termino.startswith("https://"):
      termino = "https://" + termino
    hablar(f"Abriendo el sitio {termino}.")
    url_destino = termino
  else:
    hablar(f"Buscando {termino} en internet.")
    query_encoded = urllib.parse.quote_plus(termino)
    url_destino = f"https://www.google.com/search?q={query_encoded}"

  try:
    try:
      subprocess.Popen(
          ["google-chrome", url_destino],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
    except FileNotFoundError:
      webbrowser.open(url_destino)
  except Exception as e:
    print(f"[ERROR Navegador]: {e}")
    hablar("Ocurrió un error al intentar abrir Google Chrome.")


def escribir_en_pantalla(comando=""):
  """Simula un clic del mouse en la posición actual y escribe el texto dictado usando xdotool."""
  texto_a_escribir = ""

  for prefijo in [
      "escribe en pantalla",
      "escribir en pantalla",
      "escribe",
      "escribir",
  ]:
    if comando.lower().startswith(prefijo):
      texto_a_escribir = comando.lower().replace(prefijo, "", 1).strip()
      break

  if not texto_a_escribir:
    hablar("¿Qué quieres que escriba?")
    texto_a_escribir = escuchar()

  if not texto_a_escribir:
    hablar("No entendí el texto. Cancelando.")
    return

  hablar("Escribiendo.")

  try:
    subprocess.run(["xdotool", "click", "1"])
    subprocess.run(["xdotool", "type", "--delay", "50", texto_a_escribir])
  except FileNotFoundError:
    hablar(
        "La herramienta xdotool no está instalada. Ejecuta sudo apt install"
        " xdotool."
    )
  except Exception as e:
    print(f"[ERROR xdotool]: {e}")
    hablar("No pude escribir el texto en la pantalla.")


def apagar_equipo():
  """Apaga el dispositivo Linux Mint de forma segura y detiene el script."""
  hablar("Apagando el equipo. Hasta pronto.")
  try:
    subprocess.run(
        ["systemctl", "poweroff"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
  except Exception:
    hablar("No pude apagar el equipo automáticamente.")


def cerrar_sesion():
  """Cierra la sesión actual del usuario en Linux Mint de forma segura y detiene el script."""
  hablar("Cerrando sesión en el dispositivo. Hasta luego.")
  try:
    usuario_actual = getpass.getuser()
    subprocess.run(
        ["loginctl", "terminate-user", usuario_actual],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
  except Exception:
    try:
      subprocess.run(
          ["cinnamon-session-quit", "--logout", "--force"],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
    except Exception:
      hablar("No pude cerrar la sesión automáticamente.")


def escuchar():
  """Escucha a través del micrófono con menor latencia optimizada."""
  recognizer = sr.Recognizer()
  recognizer.energy_threshold = 300
  recognizer.dynamic_energy_threshold = True

  with sr.Microphone(sample_rate=16000, chunk_size=512) as source:
    print("\n[Escuchando...]")
    recognizer.adjust_for_ambient_noise(source, duration=0.2)

    try:
      audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
      print("Procesando audio...")
      texto = recognizer.recognize_google(audio, language="es-ES")
      print(f"Tú: {texto}")
      return texto
    except sr.UnknownValueError:
      return ""
    except sr.RequestError:
      hablar("Error de conexión con el servicio de reconocimiento de voz.")
      return ""


# --- Funciones de control del dispositivo y archivos ---


def decir_hora():
  ahora = datetime.datetime.now().strftime("%H:%M")
  hablar(f"Son las {ahora} horas.")


def verificar_bateria():
  bateria = psutil.sensors_battery()
  if bateria:
    porcentaje = bateria.percent
    enchufe = (
        "conectado a la corriente"
        if bateria.power_plugged
        else "funcionando con batería"
    )
    hablar(f"El nivel de batería es del {porcentaje} por ciento y está {enchufe}.")
  else:
    hablar("No se detectó información de batería en este dispositivo.")


def verificar_espacio_disco():
  uso = shutil.disk_usage("/")
  gb_libres = uso.free // (2**30)
  gb_totales = uso.total // (2**30)
  hablar(
      f"Te quedan {gb_libres} gigabytes libres de un total de {gb_totales}"
      " gigabytes en el disco principal."
  )


def controlar_volumen(comando):
  try:
    if "subir" in comando:
      subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "15%+"])
      hablar("Volumen incrementado.")
    elif "bajar" in comando:
      subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "15%-"])
      hablar("Volumen reducido.")
    elif "silenciar" in comando or "mutear" in comando:
      subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "mute"])
      hablar("Sistema silenciado.")
    elif "activar" in comando or "desmutear" in comando:
      subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "unmute"])
      hablar("Audio activado.")
  except Exception:
    hablar("No pude ajustar el volumen debido a un error de audio.")


def verificar_rendimiento():
  uso_cpu = psutil.cpu_percent(interval=1)
  memoria = psutil.virtual_memory()
  hablar(
      f"La CPU está al {uso_cpu} por ciento de uso, y la memoria RAM está al"
      f" {memoria.percent} por ciento."
  )


def abrir_aplicacion(comando):
  """Busca y abre dinámicamente cualquier aplicación instalada en Linux Mint."""
  app_solicitada = (
      comando.replace("abre", "")
      .replace("abrir", "")
      .replace("la aplicación", "")
      .replace("la ", "")
      .replace("el ", "")
      .replace("las ", "")
      .replace("los ", "")
      .strip()
      .lower()
  )

  directorios_desktop = [
      "/usr/share/applications",
      os.path.expanduser("~/.local/share/applications"),
  ]

  app_encontrada = None
  nombre_archivo_desktop = None

  for directorio in directorios_desktop:
    if not os.path.exists(directorio):
      continue
    for archivo_desktop in glob.glob(os.path.join(directorio, "*.desktop")):
      try:
        with open(archivo_desktop, "r", encoding="utf-8") as f:
          contenido = f.read().lower()
          nombre_app = ""
          for linea in contenido.splitlines():
            if linea.startswith("name="):
              nombre_app = linea.split("=", 1)[1].strip()
              break

          if (
              app_solicitada in nombre_app
              or app_solicitada in os.path.basename(archivo_desktop).lower()
          ):
            nombre_archivo_desktop = os.path.basename(archivo_desktop).replace(
                ".desktop", ""
            )
            app_encontrada = nombre_app
            break
      except Exception:
        continue
    if nombre_archivo_desktop:
      break

  if nombre_archivo_desktop:
    hablar(f"Abriendo {app_encontrada or app_solicitada}.")
    try:
      subprocess.Popen(
          ["gtk-launch", nombre_archivo_desktop],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
    except Exception:
      hablar("No se pudo iniciar el lanzador de la aplicación.")
  else:
    hablar(f"Abriendo {app_solicitada}.")
    try:
      subprocess.Popen(
          [app_solicitada],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
    except Exception:
      hablar(
          f"No pude encontrar ninguna aplicación llamada {app_solicitada} en el"
          " sistema."
      )


def crear_archivo_texto():
  """Crea un archivo de texto dictando su nombre y contenido."""
  hablar("¿Cómo quieres nombrar el archivo?")
  nombre = escuchar()
  if not nombre:
    hablar("No entendí el nombre. Operación cancelada.")
    return

  nombre_archivo = nombre.lower().replace(" ", "_") + ".txt"
  hablar("¿Qué texto deseas guardar dentro del archivo?")
  contenido = escuchar()

  try:
    ruta_archivo = pathlib.Path.home() / nombre_archivo
    with open(ruta_archivo, "w", encoding="utf-8") as f:
      f.write(contenido if contenido else "")
    hablar(f"He creado y guardado el archivo {nombre_archivo} con éxito.")
  except Exception:
    hablar("Hubo un error al intentar crear el archivo.")


def leer_archivo_texto():
  """Lee un archivo de texto existente en la carpeta personal."""
  hablar("¿Cómo se llama el archivo que deseas leer?")
  nombre = escuchar()
  if not nombre:
    hablar("No entendí el nombre del archivo.")
    return

  nombre_archivo = nombre.lower().replace(" ", "_") + ".txt"
  ruta_archivo = pathlib.Path.home() / nombre_archivo

  if ruta_archivo.exists():
    try:
      with open(ruta_archivo, "r", encoding="utf-8") as f:
        contenido = f.read()
      if contenido.strip():
        hablar(f"El contenido del archivo es: {contenido}")
      else:
        hablar("El archivo está vacío.")
    except Exception:
      hablar("No pude leer el archivo.")
  else:
    hablar(f"No encontré ningún archivo llamado {nombre_archivo}.")


def buscar_archivo(nombre_parcial):
  home_dir = pathlib.Path.home()
  nombre_parcial = nombre_parcial.lower().strip()
  hablar(f"Buscando archivos que coincidan con {nombre_parcial}...")

  try:
    resultado = subprocess.run(
        ["find", str(home_dir), "-iname", f"*{nombre_parcial}*"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=10,
    )
    lineas = resultado.stdout.strip().splitlines()
    if lineas:
      return lineas[0]
  except Exception as e:
    print(f"Error en la búsqueda: {e}")
  return None


def abrir_archivo_especifico(comando):
  comando_lower = comando.lower()
  app_especifica = None
  if " con " in comando_lower:
    partes = comando_lower.split(" con ")
    parte_archivo = partes[0]
    app_especifica = partes[1].strip()
    nombre_busqueda = (
        parte_archivo.replace("abre el archivo", "")
        .replace("abre archivo", "")
        .replace("abre", "")
        .strip()
    )
  else:
    nombre_busqueda = (
        comando_lower.replace("abre el archivo", "")
        .replace("abre archivo", "")
        .replace("abre", "")
        .strip()
    )

  if not nombre_busqueda:
    hablar("No especificaste qué archivo deseas buscar.")
    return

  ruta_archivo = buscar_archivo(nombre_busqueda)
  if not ruta_archivo:
    hablar(f"No encontré ningún archivo que coincida con {nombre_busqueda}.")
    return

  nombre_archivo_corto = os.path.basename(ruta_archivo)
  hablar(f"Encontré el archivo {nombre_archivo_corto}.")

  try:
    if app_especifica:
      hablar(f"Abriéndolo con {app_especifica}.")
      subprocess.Popen(
          [app_especifica, ruta_archivo],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
    else:
      hablar("Abriéndolo con su aplicación predeterminada.")
      subprocess.Popen(
          ["xdg-open", ruta_archivo],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
      )
  except Exception:
    hablar("Ocurrió un error al intentar abrir el archivo con esa aplicación.")


# --- Procesador de Comandos ---


def procesar_comando(comando):
  print(f"\n[DEBUG] Comando recibido por texto: '{comando}'")
  comando = comando.lower().strip()

  if not comando:
    return True

  # Limpiamos la palabra "trinity" del comando si viene incluida al principio o en medio
  comando = comando.replace("trinity", "").strip()

  if not comando:
    return True

  # 1. Comprobar si coincide con alguna ruta o enlace del diccionario (ej. Cemu, YouTube Music)
  if abrir_aplicacion_personalizada(comando):
    return True

  # 2. Comandos para cerrar sesión o apagar equipo (devuelven False para detener el bucle)
  if "cerrar sesión" in comando or "cerrar sesion" in comando:
    cerrar_sesion()
    return False
  elif (
      "apagar equipo" in comando
      or "apagar la computadora" in comando
      or "apagar el sistema" in comando
  ):
    apagar_equipo()
    return False

  # 3. Comando para consultar a internet / IA en segundo plano
  elif "pregúntale" in comando or "preguntale" in comando:
    preguntale_a_internet(comando)

  # 4. Comando para buscar en internet o abrir sitios web directamente en navegador
  elif "busca" in comando or "buscar" in comando or "navega" in comando:
    buscar_en_internet(comando)

  # 5. Comando para dictar y escribir en pantalla con xdotool
  elif comando.startswith("escribe") or comando.startswith("escribir"):
    escribir_en_pantalla(comando)

  # 6. Comandos generales del sistema
  elif "hora" in comando:
    decir_hora()
  elif "batería" in comando or "bateria" in comando:
    verificar_bateria()
  elif "espacio" in comando or "disco" in comando:
    verificar_espacio_disco()
  elif (
      "volumen" in comando
      or "subir" in comando
      or "bajar" in comando
      or "silenciar" in comando
  ):
    controlar_volumen(comando)
  elif "rendimiento" in comando or "memoria" in comando or "cpu" in comando:
    verificar_rendimiento()
  elif "crear archivo" in comando or "nuevo archivo" in comando:
    crear_archivo_texto()
  elif "leer archivo" in comando or "abre archivo" in comando:
    leer_archivo_texto()
  elif "abre" in comando or "abrir" in comando:
    abrir_aplicacion(comando)
  elif "salir" in comando or "adiós" in comando:
    hablar("Desactivando a TRINITY. Hasta luego.")
    return False
  elif "archivo" in comando or "documento" in comando:
    abrir_archivo_especifico(comando)
  else:
    hablar("Lo siento, no reconozco esa orden localmente.")

  return True


if __name__ == "__main__":
  hablar(
      "Sistemas de TRINITY funcionando. Di mi nombre junto a tu instrucción."
  )

  activo = True
  while activo:
    try:
      texto_capturado = escuchar()
      if texto_capturado:
        if "trinity" in texto_capturado.lower():
          # Procesamos la orden en una sola frase
          activo = procesar_comando(texto_capturado)
    except KeyboardInterrupt:
      print("\nDesactivando a TRINITY...")
      break