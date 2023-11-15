import urequests as requests
import network
from os import uname
import re
import machine
import ntptime
import utime
import json
import mfrc522
import time
from machine import Pin, PWM
import gc

#inicializacion de leds
lead_read = Pin(20, Pin.OUT) 
led_wifi = Pin(19, Pin.OUT)
buzzer_pin = 16  
buzzer = PWM(Pin(buzzer_pin))

#apaga el efecto de la libreria
pin_off = Pin(19, Pin.OUT)

#declaracion de variables NTP (TIME)
year = None
month = None
day = None
hour= None
minute = None
second = None

obtencion_fecha = False
hora = None
Ultimo_registro = None
year = None
month = None
day = None
data_user = ""

#link y llave de firebase
firebase_url = "https://nas-access-2b3a6-default-rtdb.firebaseio.com"
auth_key = "oKZ6wOAwv6pu7RmzBoInx5fg1xDOeftAu84Ysrht"

#declaracion de eventos tiempo
Ultimo_registro = "No hay registro actual"
Registro_Actual = None

#ssid y contraseña wifi
SSID = "INFINITUMDA24"#"RedPrueba"## #SSID
PASSWORD = "yrtkrkRH7q" #"012345678"###contraseña

# Coneccion a red 
wlan = network.WLAN(network.STA_IF)

# Activa la interfaz Wi-Fi
wlan.active(True)

#inicializacion de srfid
rdr =mfrc522.MFRC522(sck=2, miso=4, mosi=3, cs=1, rst=0)
(stat, tag_type) = rdr.request(rdr.REQIDL)
numero = None

#declaracion de eventos tiempo
Ultimo_registro = None
Registro_Actual = None

#inicializacion del ntp server
ntp_server= "us.pool.ntp.org" 

#localizacion de la carpeta flash
archivo_eventos = "/eventos.txt"

def reproducir_sonido(buzzer, frecuencia, duracion_ms):
    buzzer.freq(frecuencia)
    buzzer.duty_u16(32768)
    utime.sleep_ms(duracion_ms)
    buzzer.duty_u16(0)

def Lectura_sinConexion():
    rdr =mfrc522.MFRC522(sck=2, miso=4, mosi=3, cs=1, rst=0)
    (stat, tag_type) = rdr.request(rdr.REQIDL)
    
    if stat == rdr.OK:
        (stat, raw_uid) = rdr.anticoll()
        
        if stat == rdr.OK:
            for _ in range(2):
                #funcion buzzer
                reproducir_sonido(buzzer, 4000, 200) 
                utime.sleep_ms(100)  
            buzzer.deinit() #detiene el buzzer
            
            print("CARD DETECTED")
            print(" -  TAG TYPE : 0x%02x" % tag_type)
            print(" -  UID      : 0x%02x%02x%02x%02x" %
                (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]))
            print("")

            if rdr.select_tag(raw_uid) == rdr.OK: #tarjeta estuvo disponible
                key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
                
                #condicion de extraccion de datos de la tarjeta
                if rdr.auth(rdr.AUTHENT1A, 8, key, raw_uid) == rdr.OK:
                    data = rdr.read(8)
                    datastr = ""
                    hexstr = []
                    
                    #concatenar char de cadena
                    for i in data:
                        datastr = datastr + (chr(i))
                        hexstr.append(hex(i))
                        
                    #busqueda del numero de acceso.
                    print("DATA: " + str(datastr))
                    patron = r"@\d+"
                    resultado = re.search(patron, str(datastr))
                    
                    #condicion para saber si hay datos en la linea hexa
                    if resultado:
                        # Extraer el número de la cadena coincidente
                        numero = resultado.group(0)[1:]
                        print("nivel alto")
                        cadena = str(datastr)
                        partes = cadena.split("@")  # Dividir la cadena en "@"
                        user_ = partes[1].split("#")[0]
                        usuario = user_
                        data_user = json.dumps(usuario) #convertir en json
                        
                        with open("/eventos.txt", "ab") as archivo_flash:  # Utiliza "ab" para agregar datos al archivo existente
                            archivo_flash.write(data_user + '\n')
                        utime.sleep(2)                           
        
    else:
        #condicion para ejecutar la conexion en segundo plano
        wlan.connect(SSID, PASSWORD)
        led_wifi.on()
        utime.sleep(3)
        print("conectando desde funcion")

def subida_periodica():
    led_read = Pin(20, Pin.OUT) 
    obtencion_fecha = False
    
    try:
        #se va a ejecutar hasta que logre una conexion a red 
        while not wlan.isconnected():  
            print("Conectando a Wi-Fi...")
            utime.sleep(1)
            Lectura_sinConexion()
        
        #cuando logre conexion ejecutar la subida de la flash
        subir_Flash_FireBase()    
        led_wifi.off()       
        pin_off = Pin(19, Pin.OUT)
        (stat, tag_type) = rdr.request(rdr.REQIDL)
        numero = None

        if stat == rdr.OK:
            (stat, raw_uid) = rdr.anticoll()

            if stat == rdr.OK:
                print("CARD DETECTED")
                led_read.off()
                print(" -  TAG TYPE : 0x%02x" % tag_type)
                print(" -  UID      : 0x%02x%02x%02x%02x" %
                    (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]))
                print("")

                if rdr.select_tag(raw_uid) == rdr.OK:

                    key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

                    if rdr.auth(rdr.AUTHENT1A, 8, key, raw_uid) == rdr.OK:
                        data = rdr.read(8)
                        datastr = ""
                        hexstr = []
                        #codigo buzzer
                        for _ in range(2):  
                            reproducir_sonido(buzzer, 4000, 200)  
                            utime.sleep_ms(100)  
                        buzzer.deinit()
                        for i in data:
                            datastr = datastr + (chr(i))
                            hexstr.append(hex(i))
                        
                        #busqueda del numero de acceso.
                        patron = r"@\d+"
                        resultado = re.search(patron, str(datastr))
                        #utime.sleep(3)	
                            
                        if wlan.isconnected(): # verifica que hay una conexion y puedo ejecutar un codigo
                            day = None
                            try:
                                ntptime.host = ntp_server
                                ntptime.settime()
                                utc_time = utime.localtime()
                                tijuana_time = utime.mktime(utc_time) - 25200  # Restar 8 horas para PST
                                year, month, day, hour, minute, second = utime.localtime(tijuana_time)[:6]
                            
                            except OSError as e:
                                print("Error al obtener la hora desde el servidor NTP:", e)
                                for _ in range(1):  
                                    reproducir_sonido(buzzer, 2000, 400)  
                                    utime.sleep_ms(100)  
                                buzzer.deinit()
                                
                            if day is not None and 1 <= day <= 31:
                                print("fecha obtenida")
                                obtencion_fecha = True
                                # Imprimir la hora en el formato deseado
                                hora = "Hora actual: {:02d}:{:02d}:{:02d} {}/{}/{}".format(hour, minute, second, day, month, year)
                                Ultimo_registro = "Hora de desconecion: {:02d}:{:02d}:{:02d} {}/{}/{}".format(hour, minute, second, day, month, year)
                                year = year
                                month = month
                                day = day
                                
                                #obtencion de la hora exacta 
                                hora = hora  # Asigna la hora a la variable de instancia
                                hora_part = hora.split(" ")
                                hora = hora_part[2]
                                
                                meses = {
                                    1: "Enero",
                                    2: "Febrero",
                                    3: "Marzo",
                                    4: "Abril",
                                    5: "Mayo",
                                    6: "Junio",
                                    7: "Julio",
                                    8: "Agosto",
                                    9: "Septiembre",
                                    10: "Octubre",
                                    11: "Noviembre",
                                    12: "Diciembre"
                                }
                                if month in meses:
                                    month = meses[month]
                                else:
                                    print("Número de mes no válido. en get de counter")
                            else:
                                print("No se obtuvo la fecha")
                            
                        if resultado!="" and obtencion_fecha==True:
                            # Extraer el número de la cadena coincidente
                            
                            print("esta  es la data entrante ",resultado," hasta aqui")
                            if resultado != None:
                                numero = resultado.group(0)[1:]
                            else :
                                print("lectura incompleta")
                                for _ in range(1):  
                                    reproducir_sonido(buzzer, 2000, 400)  
                                    utime.sleep_ms(100)  
                                buzzer.deinit()
                                
                            if numero =='1':
                                print("nivel alto")
                                cadena = str(datastr)
                                partes = cadena.split("@")  # Dividir la cadena en "@"
                                if len(partes) > 1:
                                    user_ = partes[1].split("#")[0]  # Dividir la segunda parte en "#" y tomar la primera parte
                                    print(user_)
                                    new_counter = None
                                    try:
                                        firebase_url = "https://nas-access-2b3a6-default-rtdb.firebaseio.com"
                                        auth_key = "oKZ6wOAwv6pu7RmzBoInx5fg1xDOeftAu84Ysrht"
                                        response = requests.get(firebase_url + f"/OchoaTech/{year}/{month}/{day}/{user_}/contador.json?auth={auth_key}")

                                        if response.status_code == 200:
                                            current_counter = response.json()
                                            print("Contador "+ json.dumps(current_counter) )
                                        else:
                                            current_counter = None  # Si no se puede obtener el contador, establece el valor en None

                                        response.close()
                                        if current_counter is not None:
                                            new_counter = current_counter + 1
                                        else:
                                            new_counter = 1  # Si no hay contador previo, comienza desde 1
                                        
                                        user_data = {
                                            user_: {
                                                "contador": new_counter,
                                                "hora": hora
                                            }
                                        }

                                        response = requests.put(firebase_url + f"/OchoaTech/{year}/{month}/{day}/{user_}/contador.json?auth={auth_key}", json=new_counter)

                                        if response.status_code != 200:
                                            print(f"Error al actualizar el contador en Firebase. Código de estado: {response.status_code}")
                                        response.close()
                                        codigo = None
                                        
                                        if new_counter % 2 == 0:
                                            codigo =  "outside"
                                        else:
                                            codigo =  "inside"
                                        
                                        response = requests.put(firebase_url + f"/OchoaTech/{year}/{month}/{day}/{user_}/hora/{hora}.json?auth={auth_key}", json=codigo)
                                        response.close()
                                        
                                    except Exception as e:
                                        print(f"Error al obtener/incrementar el contador desde Firebase: {str(e)}")
                                        for _ in range(1):  
                                            reproducir_sonido(buzzer, 2000, 400)  
                                            utime.sleep_ms(100)  
                                        buzzer.deinit()
                                        
                                print("opened")
                                led_read.on()
                                with open("/eventos.txt", "ab") as archivo_flash:  # Utiliza "ab" para agregar datos al archivo existente
                                            archivo_flash.write( data_user + '\n')
                            if numero =='2':
                                print("nivel medio")
                                cadena = str(datastr)
                                partes = cadena.split("@2")  # Dividir la cadena en "@"
                                if len(partes) > 1:
                                    user_ = partes[1].split("#")[0]  # Dividir la segunda parte en "#" y tomar la primera parte
                                    print(user_)
                                    new_counter = None
                                    try:
                                        response = requests.get(firebase_url + f"/Alerta/{year}/{month}/{day}/{user_}/contador.json?auth={auth_key}")

                                        if response.status_code == 200:
                                            current_counter = response.json()
                                            print("hola "+ json.dumps(current_counter) )
                                        else:
                                            current_counter = None  # Si no se puede obtener el contador, establece el valor en None

                                        response.close()
                                        if current_counter is not None:
                                            new_counter = current_counter + 1
                                        else:
                                            new_counter = 1  # Si no hay contador previo, comienza desde 1
                                        
                                        user_data = {
                                            user_: {
                                                "contador": new_counter,
                                                "hora": hora
                                            }
                                        }

                                        response = requests.put(firebase_url + f"/Alerta/{year}/{month}/{day}/{user_}/contador.json?auth={auth_key}", json=new_counter)


                                        if response.status_code != 200:
                                            print(f"Error al actualizar el contador en Firebase. Código de estado: {response.status_code}")
                                        response.close()
                                        
                                        response = requests.put(firebase_url + f"/Alerta/{year}/{month}/{day}/{user_}/hora/{hora}.json?auth={auth_key}", json="Warning")
                                        response.close()
                                        
                                    except Exception as e:
                                        print(f"Error al obtener/incrementar el contador desde Firebase: {str(e)}")
                                        
                                print("ALERT")
                                
                                ALERT = True
                            
                            if numero == '3':
                                cadena = str(datastr)
                                partes = cadena.split("@3")  # Dividir la cadena en "@"
                                if len(partes) > 1:
                                    user_ = partes[1].split("#")[0]  # Dividir la segunda parte en "#" y tomar la primera parte
                                    print(user_)
                                    new_counter = None
                                    try:
                                        response = requests.get(firebase_url + f"/Alerta/{year}/{month}/{day}/{user_}/contador.json?auth={auth_key}")

                                        if response.status_code == 200:
                                            current_counter = response.json()
                                            print("hola "+ json.dumps(current_counter) )
                                        else:
                                            current_counter = None  # Si no se puede obtener el contador, establece el valor en None

                                        response.close()
                                        if current_counter is not None:
                                            new_counter = current_counter + 1
                                        else:
                                            new_counter = 1  # Si no hay contador previo, comienza desde 1
                                        
                                        user_data = {
                                            user_: {
                                                "contador": new_counter,
                                                "hora": hora
                                            }
                                        }

                                        response = requests.put(firebase_url + f"/Alerta/{year}/{month}/{day}/{user_}/contador.json?auth={auth_key}", json=new_counter)


                                        if response.status_code != 200:
                                            print(f"Error al actualizar el contador en Firebase. Código de estado: {response.status_code}")
                                            
                                        response.close()
                                        
                                        response = requests.put(firebase_url + f"/Alerta/{year}/{month}/{day}/{user_}/hora/{hora}.json?auth={auth_key}", json="Warning")
                                        response.close()
                        
                                    except Exception as e:
                                        print(f"Error al obtener/incrementar el contador desde Firebase: {str(e)}")
                                print("nivel bajo")
                                print("NO ACCESS")
                                
                        if numero != '3' and numero != '2' and numero != '1':
                            Warnings = "Alertas"
                            contador = 0
                            uid_bytes = raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]
                            uid_hex = ''.join(['%02x' % b for b in uid_bytes])
                            print("no hay nivel")
                            new_counter = None
                            try: 
                                response = requests.get(firebase_url + f"/Alerta/{year}/{month}/{day}/{uid_hex}/contador.json?auth={auth_key}")

                                if response.status_code == 200:
                                    current_counter = response.json()
                                    print("hola "+ json.dumps(current_counter) )
                                else:
                                    current_counter = None  # Si no se puede obtener el contador, establece el valor en None

                                response.close()
                                if current_counter is not None:
                                    new_counter = current_counter + 1
                                else:
                                    new_counter = 1  # Si no hay contador previo, comienza desde 1
                                
                                user_data = {
                                    uid_hex: {
                                        "contador": new_counter,
                                        "hora": hora
                                    }
                                }

                                response = requests.put(firebase_url + f"/Alerta/{year}/{month}/{day}/{uid_hex}/contador.json?auth={auth_key}", json=new_counter)


                                if response.status_code != 200:
                                    print(f"Error al actualizar el contador en Firebase. Código de estado: {response.status_code}")
                                    
                                response.close()
                                
                                response = requests.put(firebase_url + f"/Alerta/{year}/{month}/{day}/{uid_hex}/hora/{hora}.json?auth={auth_key}", json="Warning")
                                if response.status_code != 200:
                                    print(f"Error al actualizar el contador en Firebase. Código de estado: {response.status_code}")
                                else:
                                    print("enviado con exito")
                                response.close()
                            except Exception as e:
                                print(f"Error al obtener/incrementar el contador desde Firebase: {str(e)}")
                                
                        rdr.stop_crypto1()
                        
                    else:
                        print("AUTH ERR")
                        uid_bytes = raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3]
                        uid_hex = ''.join(['%02x' % b for b in uid_bytes])
                        
                else:
                    print("Failed to select tag - try again")
                    
    

    except KeyboardInterrupt:
        print("EXITING PROGRAM")
    

def subir_Flash_FireBase():
    # Verifica si el archivo eventos.txt tiene datos
    with open(archivo_eventos, "rb") as archivo_flash:
        contenido = archivo_flash.read()
    if '&' in contenido:
        with open(archivo_eventos, "rb") as archivo_flash:
            contenido = archivo_flash.read()
    
        global year, month, day,hora
        if wlan.isconnected(): # verifica que hay una conexion y puedo ejecutar un codigo
                                
            try:
                ntptime.host = ntp_server
                ntptime.settime()
                utc_time = utime.localtime()
                tijuana_time = utime.mktime(utc_time) - 25200  # Restar 8 horas para PST
                year, month, day, hour, minute, second = utime.localtime(tijuana_time)[:6]
            
            except OSError as e:
                print("Error al obtener la hora desde el servidor NTP:", e)
                
                #aqui debe de ir el
                print("es tiempo de espera conexion")
            print("dia actual: ",day)
            
            if day is not None and 1 <= day <= 31:
                print("se accedio a la fecha")
                
                # Imprimir la hora en el formato deseado
                hora = "Hora actual: {:02d}:{:02d}:{:02d} {}/{}/{}".format(hour, minute, second, day, month, year) #corregir bug de hora
                Ultimo_registro = "Hora de desconecion: {:02d}:{:02d}:{:02d} {}/{}/{}".format(hour, minute, second, day, month, year)
                year = year
                month = month
                day = day
                
                #obtencion de la hora exacta 
                hora = hora  # Asigna la hora a la variable de instancia
                hora_part = hora.split(" ")
                hora = hora_part[2]
                
                meses = {
                    1: "Enero",
                    2: "Febrero",
                    3: "Marzo",
                    4: "Abril",
                    5: "Mayo",
                    6: "Junio",
                    7: "Julio",
                    8: "Agosto",
                    9: "Septiembre",
                    10: "Octubre",
                    11: "Noviembre",
                    12: "Diciembre"
                }
                if month in meses:
                    month = meses[month]
                else:
                    print("Número de mes no válido. en get de counter")

                if contenido: #si hay datos en la flash debe subirlos
                    try:
                        print("Hay datos en eventos.txt")
                        print(contenido.decode())

                        # Split the content into lines
                        lines = contenido.decode().splitlines()
                        i = 0

                        try:
                            
                           # data = json.loads(line)\
                           lineas = contenido.decode('utf-8').split('\n')
                           

                           usuarios = []  # Crear una lista para almacenar usuarios únicos
                           utime.sleep(1)

                           for linea in lineas:
                               if '"' in linea:
                                   usuario_flash = linea.split('"')[1]
#                                    if usuario_flash not in usuarios:
                                   usuarios.append(usuario_flash)
                                   print(usuario_flash)
                           utime.sleep(2)

                            # Realizar las solicitudes POST a Firebase para cada usuario en la lista
                           flash_up = False #indica si su subio exitosamente los datos a firebase
                           for usuario_flash in usuarios:
                               response = requests.post(firebase_url + f"/OchoaTech/{year}/{month}/{day}/{usuario_flash}/hora/{hora}.json?auth={auth_key}", json="desconectado")
                               if response.status_code != 200:
                                  print(f"Error de conexión para {usuario_flash}. Código de estado: {response.status_code}")
                                  flash_up =False
                               else:
                                  response.close()
                                  flash_up = True
                                  
                           if flash_up == True:
                               with open(archivo_eventos, "w") as archivo_flash:
                                      archivo_flash.write("")                        
                                    
                        except ValueError as json_error:
                            print(f"Error en el formato JSON en línea {i}: {json_error}")
                    except Exception as e:
                        print(f"Error de conexión inicial: {str(e)}")
                        free_memory = gc.mem_free()
                        print("Memoria libre:", free_memory, "bytes")

                        # Obtener la memoria asignada actualmente
                        allocated_memory = gc.mem_alloc()
                        print("Memoria asignada:", allocated_memory, "bytes")

                        # Realizar la recolección de basura
                        gc.collect()
                        print("Recolección de basura completada")

                        # Obtener la memoria libre después de la recolección
                        free_memory_after_gc = gc.mem_free()
                        print("Memoria libre después de GC:", free_memory_after_gc, "bytes")
                        utime.sleep(10)
                else:
                    print("No hay datos en eventos.txt")
            
def main():
    #inicializacion de leds
    led_read = Pin(20, Pin.OUT) 
    led_wifi = Pin(19, Pin.OUT)
    buzzer_pin = 16  
    buzzer = PWM(Pin(buzzer_pin))
    
    ntp_server= "us.pool.ntp.org" #inicializacion del ntp server
    hora = None #variable para inicializar la hora del ntp server

    # Coneccion a red
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Activa la interfaz Wi-Fi
    wlan.active(True)
    
    print("inicio del main")
    
    #se va a ejecutar hasta que logre una conexion a red 
    while not wlan.isconnected():  
        print("Conectando a Wi-Fi...")
        Lectura_sinConexion()
    led_wifi.off()
    subir_Flash_FireBase()
    
    
    while True:
        print("puedes leer la tarjeta")
        led_read.on()
        subida_periodica()
        
    
            
if __name__ == "__main__":
    main()
        
