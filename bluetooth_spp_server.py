#!/usr/bin/env python3
"""
Bluetooth SPP Server para GNSS.AI
Lee de /tmp/gnssai_smart y transmite por Bluetooth SPP
"""

import bluetooth
import os
import sys
import time
import threading
import select

FIFO_PATH = '/tmp/gnssai_smart'
SERVER_UUID = "00001101-0000-1000-8000-00805F9B34FB"  # SPP UUID

class BluetoothSPPServer:
    def __init__(self):
        self.server_sock = None
        self.client_sock = None
        self.running = True
        
    def start_server(self):
        """Iniciar servidor Bluetooth SPP"""
        self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        
        try:
            self.server_sock.bind(("", bluetooth.PORT_ANY))
            self.server_sock.listen(1)
            
            port = self.server_sock.getsockname()[1]
            
            bluetooth.advertise_service(
                self.server_sock,
                "GNSS-AI",
                service_id=SERVER_UUID,
                service_classes=[SERVER_UUID, bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE]
            )
            
            print(f"✅ Bluetooth SPP Server listening on RFCOMM channel {port}")
            print(f"📱 Waiting for connection...")
            
            while self.running:
                try:
                    self.client_sock, client_info = self.server_sock.accept()
                    print(f"✅ Connected from {client_info}")
                    
                    # Iniciar transmisión de datos
                    self.handle_client()
                    
                except bluetooth.BluetoothError as e:
                    print(f"⚠️  Bluetooth error: {e}")
                    time.sleep(2)
                    
        except Exception as e:
            print(f"❌ Error starting server: {e}")
        finally:
            self.cleanup()
    
    def handle_client(self):
        """Manejar cliente conectado"""
        print("📡 Starting data transmission...")
        
        # Abrir FIFO para lectura
        try:
            fifo = open(FIFO_PATH, 'rb', buffering=0)
            print(f"✅ Connected to FIFO: {FIFO_PATH}")
        except Exception as e:
            print(f"❌ Error opening FIFO: {e}")
            return
        
        try:
            while self.running:
                # Leer de FIFO con timeout
                ready = select.select([fifo], [], [], 0.1)
                
                if ready[0]:
                    data = fifo.read(1024)
                    
                    if data:
                        try:
                            self.client_sock.send(data)
                        except bluetooth.BluetoothError:
                            print("❌ Client disconnected")
                            break
                            
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
        finally:
            fifo.close()
            if self.client_sock:
                self.client_sock.close()
                self.client_sock = None
            print("📱 Waiting for new connection...")
    
    def cleanup(self):
        """Limpiar recursos"""
        self.running = False
        if self.client_sock:
            self.client_sock.close()
        if self.server_sock:
            self.server_sock.close()
        print("👋 Bluetooth SPP Server stopped")

if __name__ == '__main__':
    # Esperar a que FIFO exista
    while not os.path.exists(FIFO_PATH):
        print(f"⏳ Waiting for FIFO: {FIFO_PATH}")
        time.sleep(2)
    
    print("="*60)
    print("🛰️  GNSS.AI Bluetooth SPP Server")
    print("="*60)
    print()
    
    server = BluetoothSPPServer()
    server.start_server()
