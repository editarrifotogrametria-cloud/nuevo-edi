#!/usr/bin/env python3
"""
GNSS.AI Smart Processor v3.1 - FIXED FOR SURVEY MASTER
Envía TODAS las sentencias NMEA por Bluetooth (GGA, GSA, GSV, RMC, etc.)
"""

import serial
import os
import time
import json
import signal
from collections import defaultdict

FIFO_PATH = "/tmp/gnssai_smart"
JSON_PATH = "/tmp/gnssai_dashboard_data.json"
UART_PORT = "/dev/serial0"
UART_BAUD = 115200

class MLClassifier:
    """Clasificador ML para señales GNSS"""
    
    def __init__(self):
        self.stats = {
            'los_count': 0,
            'multipath_count': 0,
            'nlos_count': 0,
            'total_classifications': 0
        }
    
    def classify_satellite(self, snr, elevation, azimuth=0):
        self.stats['total_classifications'] += 1
        
        if snr >= 35 and elevation >= 30:
            self.stats['los_count'] += 1
            return 'LOS', 0.95
        elif snr >= 25 and elevation >= 15:
            self.stats['multipath_count'] += 1
            return 'Multipath', 0.75
        else:
            self.stats['nlos_count'] += 1
            return 'NLOS', 0.50
    
    def get_average_confidence(self):
        if self.stats['total_classifications'] == 0:
            return 0.0
        
        weighted = (
            self.stats['los_count'] * 0.95 +
            self.stats['multipath_count'] * 0.75 +
            self.stats['nlos_count'] * 0.50
        )
        return (weighted / self.stats['total_classifications']) * 100
    
    def get_distribution(self):
        return {
            'los': self.stats['los_count'],
            'multipath': self.stats['multipath_count'],
            'nlos': self.stats['nlos_count']
        }
    
    def reset_stats(self):
        self.stats = {
            'los_count': 0,
            'multipath_count': 0,
            'nlos_count': 0,
            'total_classifications': 0
        }


class SmartProcessor:
    def __init__(self):
        self.running = True
        self.stats = {
            "satellites": 0,
            "quality": 0,
            "hdop": 0.0,
            "nmea_sent": 0,
            "rtcm_sent": 0,
            "ml_corrections": 0,
            "format_switches": 0
        }
        self.pos = {"lat": 0.0, "lon": 0.0, "alt": 0.0}
        self.fifo_fd = None
        self.satellites = {}
        self.ml = MLClassifier()
        
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

    def stop(self, *_):
        print("🛑 Deteniendo SmartProcessor ML...")
        self.running = False

    def open_fifo(self):
        print(f"📂 FIFO: {FIFO_PATH}")
        try:
            self.fifo_fd = os.open(FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK)
            print(f"   ✅ FIFO abierto (fd={self.fifo_fd})")
        except OSError:
            print("⚠️  FIFO sin lector. Reintentaré después.")
            self.fifo_fd = None

    def open_uart(self):
        print(f"🔌 UART {UART_PORT} @ {UART_BAUD}...")
        self.uart = serial.Serial(UART_PORT, UART_BAUD, timeout=1)
        print("   ✅ UART abierto")

    def write_fifo(self, line):
        """Enviar línea al FIFO (Bluetooth) - CRÍTICO PARA SURVEY MASTER"""
        try:
            if self.fifo_fd is not None:
                os.write(self.fifo_fd, line.encode())
                self.stats["nmea_sent"] += 1
        except OSError as e:
            if e.errno == 6:  # ENXIO
                try:
                    self.fifo_fd = os.open(FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK)
                except OSError:
                    self.fifo_fd = None

    def parse_coord(self, val, direction):
        if not val:
            return 0.0
        try:
            parts = val.split('.')
            if len(parts[0]) <= 4:
                deg = float(val[:2])
                mins = float(val[2:])
            else:
                deg = float(val[:3])
                mins = float(val[3:])
            
            dec = deg + mins / 60.0
            if direction in ['S', 'W']:
                dec = -dec
            return dec
        except:
            return 0.0

    def parse_gga(self, line):
        try:
            parts = line.split(',')
            if len(parts) < 15:
                return
            
            self.pos["lat"] = self.parse_coord(parts[2], parts[3])
            self.pos["lon"] = self.parse_coord(parts[4], parts[5])
            self.pos["alt"] = float(parts[9] or 0)
            self.stats["quality"] = int(parts[6] or 0)
            self.stats["satellites"] = int(parts[7] or 0)
            self.stats["hdop"] = float(parts[8] or 0)
        except Exception as e:
            pass

    def parse_gsv(self, line):
        try:
            parts = line.split(',')
            if len(parts) < 8:
                return
            
            for i in range(4):
                base = 4 + (i * 4)
                if base + 3 >= len(parts):
                    break
                
                prn = parts[base].strip()
                if not prn:
                    continue
                
                prn = int(prn)
                elevation = float(parts[base + 1] or 0)
                azimuth = float(parts[base + 2] or 0)
                snr_str = parts[base + 3].split('*')[0]
                snr = float(snr_str or 0)
                
                self.satellites[prn] = {
                    'snr': snr,
                    'elevation': elevation,
                    'azimuth': azimuth,
                    'constellation': self.get_constellation(prn)
                }
                
                if snr > 0:
                    signal_type, confidence = self.ml.classify_satellite(snr, elevation, azimuth)
                    self.satellites[prn]['signal_type'] = signal_type
                    self.satellites[prn]['confidence'] = confidence
                    
                    if signal_type in ['Multipath', 'NLOS']:
                        self.stats['ml_corrections'] += 1
                        
        except Exception as e:
            pass

    def get_constellation(self, prn):
        if 1 <= prn <= 32:
            return 'GPS'
        elif 65 <= prn <= 96:
            return 'GLONASS'
        elif 161 <= prn <= 197:
            return 'BeiDou'
        elif 201 <= prn <= 236:
            return 'Galileo'
        else:
            return 'Unknown'

    def update_json(self):
        quality_map = {
            0: "NO_FIX",
            1: "GPS",
            2: "DGPS",
            4: "RTK_FIXED",
            5: "RTK_FLOAT",
            6: "RTK_FIXED",
            7: "RTK_FIXED"
        }
        
        rtk_status = quality_map.get(self.stats["quality"], "UNKNOWN")
        ml_dist = self.ml.get_distribution()
        
        data = {
            "position": self.pos,
            "satellites": self.stats["satellites"],
            "quality": self.stats["quality"],
            "hdop": self.stats["hdop"],
            "nmea_sent": self.stats["nmea_sent"],
            "rtcm_sent": self.stats["rtcm_sent"],
            "ml_corrections": self.stats["ml_corrections"],
            "format_switches": self.stats["format_switches"],
            "los_sats": ml_dist['los'],
            "multipath_sats": ml_dist['multipath'],
            "nlos_sats": ml_dist['nlos'],
            "avg_confidence": self.ml.get_average_confidence(),
            "estimated_accuracy": self.estimate_accuracy(),
            "rtk_status": rtk_status,
            "format": "NMEA",
            "last_update": time.time()
        }
        
        with open(JSON_PATH, "w") as f:
            json.dump(data, f)

    def estimate_accuracy(self):
        q = self.stats["quality"]
        hdop = self.stats["hdop"]
        
        if q >= 4:
            return 2.0 + (hdop * 0.5)
        elif q == 5:
            return 10.0 + (hdop * 2)
        elif q == 2:
            return 50.0 + (hdop * 10)
        elif q == 1:
            return 200.0 + (hdop * 50)
        else:
            return 999.0

    def run(self):
        print("=" * 60)
        print("🛰️  GNSS.AI Smart Processor v3.1 (Survey Master Fixed)")
        print("=" * 60)
        
        self.open_fifo()
        self.open_uart()
        
        print("🧠 Clasificador ML: ACTIVO")
        print("📡 Enviando TODAS las sentencias NMEA por Bluetooth...")
        print("🚀 Procesando...")
        
        last_json = time.time()
        last_stats = time.time()
        last_ml_reset = time.time()
        
        while self.running:
            if self.uart.in_waiting:
                line = self.uart.readline().decode('ascii', errors='ignore').strip()
                
                # Parsear para dashboard (solo GGA y GSV)
                if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                    self.parse_gga(line)
                elif line.startswith("$GPGSV") or line.startswith("$GNGSV"):
                    self.parse_gsv(line)
                
                # ⭐ ENVIAR TODAS LAS SENTENCIAS AL FIFO (BLUETOOTH)
                # Esto incluye: GGA, GSA, GSV, RMC, VTG, etc.
                if line and line.startswith('$'):
                    self.write_fifo(line + "\r\n")
            
            # Actualizar JSON cada 2s
            if time.time() - last_json > 2:
                self.update_json()
                last_json = time.time()
            
            # Resetear stats ML cada 60s
            if time.time() - last_ml_reset > 60:
                self.ml.reset_stats()
                last_ml_reset = time.time()
            
            # Stats cada 30s
            if time.time() - last_stats > 30:
                ml_dist = self.ml.get_distribution()
                print(f"📊 Sats={self.stats['satellites']} "
                      f"Q={self.stats['quality']} "
                      f"HDOP={self.stats['hdop']:.1f} "
                      f"NMEA_out={self.stats['nmea_sent']} "
                      f"ML: LOS={ml_dist['los']} MP={ml_dist['multipath']} "
                      f"NLOS={ml_dist['nlos']}")
                last_stats = time.time()
            
            time.sleep(0.01)
        
        self.cleanup()

    def cleanup(self):
        print("\n🧹 Limpiando...")
        if hasattr(self, 'uart'):
            self.uart.close()
        if self.fifo_fd:
            os.close(self.fifo_fd)
        print("👋 Fin.")


if __name__ == "__main__":
    print("🧠 Inicializando clasificador ML...")
    sp = SmartProcessor()
    sp.run()
