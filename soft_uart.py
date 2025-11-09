import pigpio
import time

RX_GPIO = 18   # GPIO que usará como RX (al TX del adaptador)
TX_GPIO = 17   # GPIO que usará como TX (al RX del adaptador)
BAUD = 9600    # Puedes probar con 9600 o 19200

pi = pigpio.pi()
if not pi.connected:
    exit()

# Abre serial bit-bang en RX
pi.bb_serial_read_open(RX_GPIO, BAUD)

# Función para enviar texto
def send_text(text):
    for c in text:
        pi.wave_clear()
        pi.wave_add_serial(TX_GPIO, BAUD, c)
        wid = pi.wave_create()
        pi.wave_send_once(wid)
        while pi.wave_tx_busy():
            time.sleep(0.01)
        pi.wave_delete(wid)

# Ejemplo: enviar saludo
send_text("Hola desde la Pi!\r\n")

# Intentar leer 2 segundos
time.sleep(2)
(count, data) = pi.bb_serial_read(RX_GPIO)
if count > 0:
    print("Recibido:", data.decode(errors="ignore"))

pi.bb_serial_read_close(RX_GPIO)
pi.stop()
