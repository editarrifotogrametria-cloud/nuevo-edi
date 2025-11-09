#!/usr/bin/env python3
"""
GNSS.AI Data Collector - Versión Simplificada
Recolecta datos NMEA para entrenar modelos ML
"""

import serial
import json
import csv
import time
from datetime import datetime
from pathlib import Path

class SimpleGNSSCollector:
    """Recolector simple de datos GNSS"""
    
    def __init__(self, output_dir='ml_training_data'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.session = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_file = self.output_dir / f'session_{self.session}.csv'
        
        self.uart = serial.Serial('/dev/serial0', 115200, timeout=1)
        
        # Crear CSV
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'prn', 'constellation', 'elevation', 
                'azimuth', 'snr', 'quality', 'hdop', 'environment'
            ])
        
        self.satellites = {}
        self.quality = 0
        self.hdop = 0
        self.epochs = 0
        
        print(f"📊 GNSS Data Collector")
        print(f"📁 Output: {self.csv_file}")
        print(f"Session: {self.session}")
        print("="*60)
    
    def parse_gsv(self, line):
        """Parse GSV sentence"""
        parts = line.split(',')
        if len(parts) < 8:
            return
        
        # GSV has 4 satellites per sentence
        for i in range(4):
            try:
                base = 4 + (i * 4)
                if base + 3 >= len(parts):
                    break
                
                prn = int(parts[base]) if parts[base] else None
                if not prn:
                    continue
                
                elevation = float(parts[base + 1]) if parts[base + 1] else 0
                azimuth = float(parts[base + 2]) if parts[base + 2] else 0
                snr = float(parts[base + 3].split('*')[0]) if parts[base + 3] else 0
                
                # Determine constellation
                if line.startswith('$GPGSV'):
                    constellation = 'GPS'
                elif line.startswith('$GLGSV'):
                    constellation = 'GLONASS'
                elif line.startswith('$GAGSV'):
                    constellation = 'Galileo'
                elif line.startswith('$GBGSV') or line.startswith('$BDGSV'):
                    constellation = 'BeiDou'
                else:
                    constellation = 'Unknown'
                
                self.satellites[prn] = {
                    'prn': prn,
                    'constellation': constellation,
                    'elevation': elevation,
                    'azimuth': azimuth,
                    'snr': snr
                }
            except (ValueError, IndexError):
                continue
    
    def parse_gga(self, line):
        """Parse GGA sentence"""
        parts = line.split(',')
        if len(parts) < 9:
            return
        
        try:
            self.quality = int(parts[6]) if parts[6] else 0
            self.hdop = float(parts[8]) if parts[8] else 0
        except (ValueError, IndexError):
            pass
    
    def save_epoch(self, environment='unknown'):
        """Save current epoch to CSV"""
        if not self.satellites:
            return
        
        timestamp = datetime.now().isoformat()
        
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            for sat in self.satellites.values():
                writer.writerow([
                    timestamp,
                    sat['prn'],
                    sat['constellation'],
                    sat['elevation'],
                    sat['azimuth'],
                    sat['snr'],
                    self.quality,
                    self.hdop,
                    environment
                ])
        
        self.epochs += 1
        self.satellites.clear()
    
    def collect(self, duration_seconds=3600, environment='urban'):
        """Collect data for specified duration"""
        print(f"🕐 Collecting for {duration_seconds}s in '{environment}' environment")
        print("Press Ctrl+C to stop early\n")
        
        start_time = time.time()
        last_save = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                line = self.uart.readline().decode('ascii', errors='ignore').strip()
                
                if line.startswith('$'):
                    if 'GSV' in line:
                        self.parse_gsv(line)
                    elif 'GGA' in line:
                        self.parse_gga(line)
                
                # Save every 5 seconds
                if time.time() - last_save > 5:
                    self.save_epoch(environment)
                    last_save = time.time()
                    
                    elapsed = int(time.time() - start_time)
                    progress = (elapsed / duration_seconds) * 100
                    print(f"\r⏳ {progress:.1f}% | Epochs: {self.epochs} | "
                          f"Sats: {len(self.satellites)}", end='', flush=True)
            
            print("\n✅ Collection complete!")
            
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
        
        finally:
            self.uart.close()
            print(f"\n📁 Data saved to: {self.csv_file}")
            print(f"📊 Total epochs: {self.epochs}")

if __name__ == '__main__':
    import sys
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300  # 5 min default
    environment = sys.argv[2] if len(sys.argv) > 2 else 'urban'
    
    collector = SimpleGNSSCollector()
    collector.collect(duration, environment)
