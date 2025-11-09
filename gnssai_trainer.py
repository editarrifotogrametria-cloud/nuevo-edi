#!/usr/bin/env python3
"""
GNSS.AI ML Trainer
Entrena modelos de clasificación de calidad de señal
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from pathlib import Path
import json

class GNSSMLTrainer:
    """Entrenador de modelos ML para GNSS"""
    
    def __init__(self, data_dir='ml_training_data'):
        self.data_dir = Path(data_dir)
        self.model_dir = Path('ml_models')
        self.model_dir.mkdir(exist_ok=True)
        
        self.model = None
        self.feature_names = ['elevation', 'snr', 'hdop']
        
        print("🧠 GNSS.AI ML Trainer")
        print("="*60)
    
    def load_data(self):
        """Cargar datos de entrenamiento"""
        csv_files = list(self.data_dir.glob('session_*.csv'))
        
        if not csv_files:
            raise FileNotFoundError(f"No training data in {self.data_dir}")
        
        print(f"📁 Found {len(csv_files)} session files")
        
        # Combinar todos los CSVs
        dfs = []
        for f in csv_files:
            df = pd.read_csv(f)
            dfs.append(df)
        
        self.data = pd.concat(dfs, ignore_index=True)
        print(f"📊 Total samples: {len(self.data)}")
        print(f"🛰️  Unique satellites: {self.data['prn'].nunique()}")
        
        return self.data
    
    def label_data(self):
        """Etiquetar datos automáticamente basado en métricas"""
        # Reglas simples para etiquetado
        def classify_signal(row):
            # LOS (Line of Sight) - Buena señal
            if row['snr'] > 35 and row['elevation'] > 25:
                return 'LOS'
            
            # NLOS (Non Line of Sight) - Señal bloqueada
            elif row['snr'] < 25 or row['elevation'] < 15:
                return 'NLOS'
            
            # Multipath - Señal con rebotes
            else:
                return 'Multipath'
        
        self.data['label'] = self.data.apply(classify_signal, axis=1)
        
        print("\n🏷️  Labels:")
        print(self.data['label'].value_counts())
        
        return self.data
    
    def prepare_features(self):
        """Preparar features para entrenamiento"""
        # Eliminar filas con valores faltantes
        self.data = self.data.dropna(subset=self.feature_names + ['label'])
        
        X = self.data[self.feature_names].values
        y = self.data['label'].values
        
        print(f"\n📈 Features shape: {X.shape}")
        print(f"🎯 Labels shape: {y.shape}")
        
        return X, y
    
    def train(self, test_size=0.2):
        """Entrenar modelo"""
        print("\n🏋️  Training model...")
        
        X, y = self.prepare_features()
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"\n✅ Training complete!")
        print(f"   Train accuracy: {train_score:.3f}")
        print(f"   Test accuracy:  {test_score:.3f}")
        
        # Detailed report
        y_pred = self.model.predict(X_test)
        print("\n📊 Classification Report:")
        print(classification_report(y_test, y_pred))
        
        # Feature importance
        importances = self.model.feature_importances_
        print("\n🔍 Feature Importance:")
        for name, imp in zip(self.feature_names, importances):
            print(f"   {name:12s}: {imp:.3f}")
        
        return self.model
    
    def save_model(self):
        """Guardar modelo entrenado"""
        if self.model is None:
            raise ValueError("No model to save. Train first!")
        
        model_path = self.model_dir / 'gnssai_classifier.joblib'
        metadata_path = self.model_dir / 'model_metadata.json'
        
        # Save model
        joblib.dump(self.model, model_path)
        
        # Save metadata
        metadata = {
            'feature_names': self.feature_names,
            'classes': list(self.model.classes_),
            'n_samples': len(self.data),
            'train_date': pd.Timestamp.now().isoformat()
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n💾 Model saved to: {model_path}")
        print(f"📋 Metadata saved to: {metadata_path}")
    
    def full_pipeline(self):
        """Pipeline completo: cargar, etiquetar, entrenar, guardar"""
        self.load_data()
        self.label_data()
        self.train()
        self.save_model()
        
        print("\n" + "="*60)
        print("✅ ML Training Pipeline Complete!")
        print("="*60)

if __name__ == '__main__':
    trainer = GNSSMLTrainer()
    trainer.full_pipeline()
