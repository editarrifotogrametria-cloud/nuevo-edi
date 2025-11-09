#!/usr/bin/env python3
"""
ML Classifier para GNSS.AI - Versión completa y robusta
Clasificación de señales GNSS en tiempo real usando ML
"""

import os
import sys
import time
import logging
from collections import deque, defaultdict
import math

# =============================================================================
# CONFIGURACIÓN DE NUMPY - MANEJO ROBUSTO DE IMPORTACIONES
# =============================================================================

try:
    import numpy as np
    NUMPY_AVAILABLE = True
    NP_VERSION = np.__version__
except ImportError as e:
    print(f"❌ Error importando numpy: {e}")
    NUMPY_AVAILABLE = False
    NP_VERSION = "No disponible"
except Exception as e:
    print(f"❌ Error inesperado importando numpy: {e}")
    NUMPY_AVAILABLE = False
    NP_VERSION = "No disponible"

# =============================================================================
# CLASE PRINCIPAL DEL CLASIFICADOR ML
# =============================================================================

class SignalClassifier:
    """
    Clasificador ML para señales GNSS que detecta:
    - LOS (Line of Sight): Señales directas
    - NLOS (Non-Line of Sight): Señales obstruidas  
    - MULTIPATH: Señales con rebotes
    """
    
    def __init__(self, model_type="hybrid"):
        """
        Inicializar el clasificador
        
        Args:
            model_type: Tipo de modelo ("rules", "ml", "hybrid")
        """
        self.model_type = model_type
        self.numpy_available = NUMPY_AVAILABLE
        self.signal_history = defaultdict(lambda: deque(maxlen=50))
        self.classification_history = defaultdict(lambda: deque(maxlen=20))
        
        # Umbrales para clasificación por reglas
        self.thresholds = {
            'snr_los_min': 35,
            'snr_nlos_max': 25,
            'elevation_los_min': 20,
            'elevation_nlos_max': 15,
            'snr_multipath_min': 25,
            'snr_multipath_max': 35,
            'elevation_multipath_min': 10
        }
        
        # Estadísticas
        self.stats = {
            'total_classifications': 0,
            'los_count': 0,
            'nlos_count': 0,
            'multipath_count': 0,
            'avg_confidence': 0.0
        }
        
        # Configurar logging
        self.logger = self._setup_logger()
        self._log_startup_info()
    
    def _setup_logger(self):
        """Configurar el sistema de logging"""
        logger = logging.getLogger('GNSS_ML_Classifier')
        logger.setLevel(logging.INFO)
        
        # Evitar múltiples handlers
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.propagate = False
            
        return logger
    
    def _log_startup_info(self):
        """Log información de inicio"""
        self.logger.info("=" * 50)
        self.logger.info("🚀 GNSS.AI ML Classifier Inicializado")
        self.logger.info(f"📊 Modelo: {self.model_type}")
        self.logger.info(f"🔢 Numpy: {NP_VERSION}")
        self.logger.info(f"📈 Umbrales: SNR_LOS>{self.thresholds['snr_los_min']}, "
                        f"SNR_NLOS<{self.thresholds['snr_nlos_max']}")
        self.logger.info("=" * 50)
    
    def extract_features(self, satellite_data):
        """
        Extraer características de las señales de satélites
        
        Args:
            satellite_data: Diccionario con datos de satélites
            
        Returns:
            Dict con vectores de características por PRN
        """
        features = {}
        
        for prn, data in satellite_data.items():
            try:
                # Características básicas
                elevation = float(data.get('elevation', 0))
                snr = float(data.get('snr', 25)) if data.get('snr', 0) > 0 else 25.0
                azimuth = float(data.get('azimuth', 0))
                
                # Características derivadas
                time_of_day = time.time() % 86400  # Segundos desde medianoche
                snr_quality = min(snr / 50.0, 1.0)  # Normalizado 0-1
                elevation_quality = elevation / 90.0  # Normalizado 0-1
                
                # Características históricas
                history = self.signal_history[prn]
                if history:
                    snr_trend = self._calculate_trend([h['snr'] for h in history])
                    elevation_trend = self._calculate_trend([h['elevation'] for h in history])
                else:
                    snr_trend = 0.0
                    elevation_trend = 0.0
                
                # Vector de características
                feature_vector = [
                    elevation,           # 0: Elevación en grados
                    snr,                 # 1: Relación señal-ruido
                    azimuth,             # 2: Azimuth en grados
                    time_of_day,         # 3: Tiempo del día
                    snr_quality,         # 4: Calidad de SNR (0-1)
                    elevation_quality,   # 5: Calidad de elevación (0-1)
                    snr_trend,           # 6: Tendencia de SNR
                    elevation_trend      # 7: Tendencia de elevación
                ]
                
                features[prn] = {
                    'vector': feature_vector,
                    'basic_features': [elevation, snr, azimuth]
                }
                
                # Actualizar historial
                self.signal_history[prn].append({
                    'elevation': elevation,
                    'snr': snr,
                    'azimuth': azimuth,
                    'timestamp': time.time()
                })
                
            except (ValueError, TypeError, KeyError) as e:
                self.logger.debug(f"⚠️ Error extrayendo features PRN {prn}: {e}")
                continue
        
        return features
    
    def _calculate_trend(self, values):
        """Calcular tendencia de una serie de valores"""
        if len(values) < 2:
            return 0.0
        
        if self.numpy_available:
            try:
                x = np.arange(len(values))
                slope = np.polyfit(x, values, 1)[0]
                return float(slope)
            except:
                pass
        
        # Fallback sin numpy
        return (values[-1] - values[0]) / len(values) if values else 0.0
    
    def classify_by_rules(self, features):
        """
        Clasificación basada en reglas heurísticas
        
        Args:
            features: Diccionario de características por PRN
            
        Returns:
            Dict con clasificaciones por PRN
        """
        classifications = {}
        
        for prn, feature_data in features.items():
            try:
                feature_vector = feature_data['vector']
                elevation, snr, azimuth = feature_data['basic_features']
                
                # REGLAS DE CLASIFICACIÓN
                
                # 1. LOS (Line of Sight) - Condiciones ideales
                if (elevation >= self.thresholds['elevation_los_min'] and 
                    snr >= self.thresholds['snr_los_min']):
                    confidence = 0.85 + (snr - 35) * 0.01
                    classification = 'LOS'
                
                # 2. NLOS (Non-Line of Sight) - Condiciones pobres
                elif (elevation <= self.thresholds['elevation_nlos_max'] and 
                      snr <= self.thresholds['snr_nlos_max']):
                    confidence = 0.70 + (15 - elevation) * 0.02
                    classification = 'NLOS'
                
                # 3. MULTIPATH - Condiciones sospechosas
                elif (self.thresholds['snr_multipath_min'] <= snr <= self.thresholds['snr_multipath_max'] and
                      elevation >= self.thresholds['elevation_multipath_min']):
                    # SNR medio con buena elevación sugiere multipath
                    confidence = 0.65 + abs(30 - snr) * 0.01
                    classification = 'MULTIPATH'
                
                # 4. LOS por defecto (condiciones normales)
                else:
                    base_confidence = 0.6
                    elevation_boost = (elevation / 90.0) * 0.2
                    snr_boost = min((snr - 20) / 30.0, 0.2)
                    confidence = base_confidence + elevation_boost + snr_boost
                    classification = 'LOS'
                
                # Ajustar confianza basado en historial
                confidence = self._adjust_confidence_by_history(prn, classification, confidence)
                
                # Limitar confianza entre 0.5 y 0.99
                confidence = max(0.5, min(0.99, confidence))
                
                classifications[prn] = {
                    'class': classification,
                    'confidence': round(confidence, 3),
                    'features': feature_vector,
                    'basic_features': [elevation, snr, azimuth],
                    'timestamp': time.time()
                }
                
            except Exception as e:
                self.logger.error(f"❌ Error clasificando PRN {prn}: {e}")
                continue
        
        return classifications
    
    def _adjust_confidence_by_history(self, prn, current_class, current_confidence):
        """Ajustar confianza basado en historial de clasificaciones"""
        history = self.classification_history[prn]
        
        if len(history) >= 3:
            # Verificar consistencia en el tiempo
            recent_classes = [h['class'] for h in list(history)[-3:]]
            same_class_count = recent_classes.count(current_class)
            
            if same_class_count >= 2:  # Consistente
                current_confidence *= 1.1
            else:  # Inconsistente
                current_confidence *= 0.9
        
        # Guardar clasificación actual en historial
        history.append({
            'class': current_class,
            'confidence': current_confidence,
            'timestamp': time.time()
        })
        
        return min(current_confidence, 0.95)  # Limitar máximo
    
    def classify_with_ml(self, features):
        """
        Clasificación usando modelo ML (placeholder para futuro)
        
        Args:
            features: Diccionario de características por PRN
            
        Returns:
            Dict con clasificaciones por PRN
        """
        # Por ahora usa clasificación por reglas
        # En el futuro aquí iría un modelo ML entrenado
        return self.classify_by_rules(features)
    
    def classify_signals(self, satellite_data):
        """
        Clasificar señales de satélites (método principal)
        
        Args:
            satellite_data: Diccionario con datos brutos de satélites
            
        Returns:
            Dict con clasificaciones por PRN
        """
        if not satellite_data:
            return {}
        
        try:
            # 1. Extraer características
            features = self.extract_features(satellite_data)
            
            if not features:
                return {}
            
            # 2. Clasificar según el modelo seleccionado
            if self.model_type == "ml" and self.numpy_available:
                classifications = self.classify_with_ml(features)
            else:
                classifications = self.classify_by_rules(features)
            
            # 3. Actualizar estadísticas
            self._update_stats(classifications)
            
            # 4. Log periódico de estadísticas
            self._log_periodic_stats(classifications)
            
            return classifications
            
        except Exception as e:
            self.logger.error(f"💥 Error en classify_signals: {e}")
            return {}
    
    def _update_stats(self, classifications):
        """Actualizar estadísticas de clasificación"""
        if not classifications:
            return
        
        self.stats['total_classifications'] += len(classifications)
        
        los_count = sum(1 for c in classifications.values() if c['class'] == 'LOS')
        nlos_count = sum(1 for c in classifications.values() if c['class'] == 'NLOS')
        multipath_count = sum(1 for c in classifications.values() if c['class'] == 'MULTIPATH')
        
        self.stats['los_count'] += los_count
        self.stats['nlos_count'] += nlos_count
        self.stats['multipath_count'] += multipath_count
        
        avg_confidence = sum(c['confidence'] for c in classifications.values()) / len(classifications)
        self.stats['avg_confidence'] = round(avg_confidence, 3)
    
    def _log_periodic_stats(self, classifications):
        """Log estadísticas periódicamente"""
        if not hasattr(self, '_last_log_time'):
            self._last_log_time = 0
        
        current_time = time.time()
        if current_time - self._last_log_time >= 30:  # Cada 30 segundos
            total = len(classifications)
            if total > 0:
                los_pct = (sum(1 for c in classifications.values() if c['class'] == 'LOS') / total) * 100
                nlos_pct = (sum(1 for c in classifications.values() if c['class'] == 'NLOS') / total) * 100
                multipath_pct = (sum(1 for c in classifications.values() if c['class'] == 'MULTIPATH') / total) * 100
                
                self.logger.info(
                    f"📊 ML Stats: LOS={los_pct:.1f}% | NLOS={nlos_pct:.1f}% | "
                    f"Multipath={multipath_pct:.1f}% | Conf={self.stats['avg_confidence']:.2f} | "
                    f"Sats={total}"
                )
            
            self._last_log_time = current_time
    
    def get_stats(self):
        """Obtener estadísticas actuales"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reiniciar estadísticas"""
        self.stats = {
            'total_classifications': 0,
            'los_count': 0,
            'nlos_count': 0,
            'multipath_count': 0,
            'avg_confidence': 0.0
        }

# =============================================================================
# FUNCIÓN DE TEST Y EJECUCIÓN DIRECTA
# =============================================================================

def test_classifier():
    """Función de prueba del clasificador"""
    print("🧪 Probando GNSS.AI ML Classifier...")
    print("=" * 60)
    
    # Crear clasificador
    classifier = SignalClassifier()
    
    # Datos de prueba realistas
    test_satellites = {
        # Satélites de alta calidad (LOS)
        1: {'elevation': 45, 'snr': 42, 'azimuth': 120},
        2: {'elevation': 60, 'snr': 48, 'azimuth': 45},
        
        # Satélites de baja calidad (NLOS)
        3: {'elevation': 10, 'snr': 22, 'azimuth': 300},
        4: {'elevation': 8, 'snr': 18, 'azimuth': 210},
        
        # Satélites sospechosos (Multipath)
        5: {'elevation': 25, 'snr': 28, 'azimuth': 150},
        6: {'elevation': 30, 'snr': 32, 'azimuth': 60},
        
        # Satélites normales
        7: {'elevation': 35, 'snr': 38, 'azimuth': 270},
    }
    
    # Procesar clasificación
    results = classifier.classify_signals(test_satellites)
    
    # Mostrar resultados
    print("\n📈 RESULTADOS DE CLASIFICACIÓN:")
    print("-" * 60)
    
    for prn, result in results.items():
        print(f"PRN {prn:2d}: {result['class']:10s} "
              f"(Conf: {result['confidence']:.3f}) - "
              f"Elev: {result['basic_features'][0]:2.0f}° "
              f"SNR: {result['basic_features'][1]:2.0f} dBHz")
    
    # Mostrar estadísticas
    stats = classifier.get_stats()
    print("-" * 60)
    print(f"📊 Estadísticas: Total={stats['total_classifications']} | "
          f"Confianza promedio={stats['avg_confidence']:.3f}")
    
    print("✅ Test completado exitosamente!")
    return results

if __name__ == "__main__":
    # Ejecutar test si se ejecuta directamente
    test_classifier()
