import pandas as pd
import joblib

class FuelConsumptionPredictor:
    def __init__(self):
        self.model = joblib.load(r'C:\Users\Aakhil\Desktop\hackathons\khacks\CARLA_0.9.14\WindowsNoEditor\Scripts\models\model_checkpoints\gradient_boosting_model.pkl')

    def preprocess_data(self, distance, speed, gas_type, AC, rain, sun):
        data = pd.DataFrame({
            'distance': [distance],
            'speed': [speed],
            'gas_type_E10': [1 if gas_type == 0 else 0],
            'gas_type_SP98': [1 if gas_type == 1 else 0],
            'AC_0': [1 if AC == 0 else 0],
            'AC_1': [1 if AC == 1 else 0],
            'rain_0': [1 if rain == 0 else 0],
            'rain_1': [1 if rain == 1 else 0],
            'sun_0': [1 if sun == 0 else 0],
            'sun_1': [1 if sun == 1 else 0],
        })
        return data

    def predict(self, distance, speed, gas_type, AC, rain, sun):
        preprocessed_data = self.preprocess_data(distance, speed, gas_type, AC, rain, sun)
        prediction = self.model.predict(preprocessed_data)
        return prediction[0]
