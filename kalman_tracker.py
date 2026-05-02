import cv2
import numpy as np
import math

class DodgeballKalman:
    def __init__(self):
        self.kf = cv2.KalmanFilter(6, 3)

        self.kf.transitionMatrix = np.array([
            [1, 0, 0, 1, 0, 0], 
            [0, 1, 0, 0, 1, 0], 
            [0, 0, 1, 0, 0, 1], 
            [0, 0, 0, 1, 0, 0], 
            [0, 0, 0, 0, 1, 0], 
            [0, 0, 0, 0, 0, 1]  
        ], dtype=np.float32)

        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ], dtype=np.float32)

        self.kf.processNoiseCov = np.eye(6, dtype=np.float32) * 0.05
        self.kf.measurementNoiseCov = np.array([
            [10, 0, 0],
            [0, 10, 0],
            [0, 0, 100] 
        ], dtype=np.float32)

        self.initialized = False

    def update_tuning(self, process_noise, measurement_noise):
        # FIX 1: Force the Python GUI floats into strict 32-bit NumPy floats
        p_noise = np.float32(process_noise)
        m_noise = np.float32(measurement_noise)

        self.kf.processNoiseCov = np.eye(6, dtype=np.float32) * p_noise
        
        # Ensure the whole array is built strictly as float32
        self.kf.measurementNoiseCov = np.array([
            [m_noise, 0, 0],
            [0, m_noise, 0],
            [0, 0, m_noise] 
        ], dtype=np.float32)

    def predict(self):
        state = self.kf.predict()
        return state

    def correct(self, x, y, area):
        # FIX 2: Force the incoming YOLO coordinates to be 32-bit floats
        measurement = np.array([[x], [y], [area]], dtype=np.float32)
        
        if not self.initialized:
            # FIX 3: Force the initial memory state to be 32-bit floats
            self.kf.statePost = np.array([[x], [y], [area], [0], [0], [0]], dtype=np.float32)
            self.initialized = True
            return self.kf.statePost
        
        state = self.kf.correct(measurement)
        return state

    def get_impact_prediction(self, center_of_screen, impact_area=20000):
            if not self.initialized:
                return None

            import math
            target_diameter = math.sqrt(impact_area)

            current_x = self.kf.statePost[0, 0]
            current_y = self.kf.statePost[1, 0] # We need the current Y!
            current_diameter = self.kf.statePost[2, 0]

            velocity_x = self.kf.statePost[3, 0]
            velocity_y = self.kf.statePost[4, 0] # We need the Y velocity (Gravity/Angle)
            velocity_diameter = self.kf.statePost[5, 0]

            # 1. Growth Gate (Must be approaching at a decent speed)
            if velocity_diameter < 1.5:
                return None

            if current_diameter >= target_diameter:
                return None

            # 2. Calculate stable Time to Impact
            frames_until_impact = (target_diameter - current_diameter) / velocity_diameter

            # Limit prediction to prevent wild swings (assume max 2 seconds ahead)
            if frames_until_impact < 0 or frames_until_impact > 60:
                return None

            # 3. TRUE 2D KINEMATICS
            # Predict both X and Y coordinates upon impact
            impact_x = int(current_x + (velocity_x * frames_until_impact))
            impact_y = int(current_y + (velocity_y * frames_until_impact))

            # Return all THREE variables!
            return (impact_x, impact_y, int(frames_until_impact))