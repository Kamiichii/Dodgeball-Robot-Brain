import cv2
import time
import serial
import threading
from collections import deque
from ultralytics import YOLO
from src.kalman_tracker import DodgeballKalman

class ThreadedCamera:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.grabbed, self.frame = self.cap.read()
        self.started = False

    def start(self):
        if self.started:
            return self
        self.started = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        return self

    def update(self):
        while self.started:
            self.grabbed, self.frame = self.cap.read()

    def read(self):
        return self.grabbed, self.frame.copy()

    def get(self, prop_id):
        return self.cap.get(prop_id)

    def release(self):
        self.started = False
        self.cap.release()

class VisionCore:
    def __init__(self, src=0):
        # --- HARDWARE CONNECTION ---
        try:
            self.arduino = serial.Serial('COM3', 9600, timeout=1)
            time.sleep(2) 
            print("SUCCESS: Connected to Arduino!")
        except Exception as e:
            print(f"WARNING: Could not connect to Arduino. Running in simulation mode. ({e})")
            self.arduino = None

        print("Loading custom model...")
        self.model = YOLO('best.pt')
        self.cap = ThreadedCamera(src).start() 
        
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.center_of_screen = self.frame_width // 2

        self.tracker = DodgeballKalman()
        self.missed_frames = 0
        self.ball_history = deque(maxlen=15) 
        self.prev_time = time.time()

        self.robot_state = "SCANNING"  
        self.locked_command = ""       
        self.cooldown_timer = 0

        self.current_throw = []
        self.current_throw_decision = "NO THREAT DETECTED"
        self.throw_database = [] # This will hold all saved throws
        self.max_throws = 50        

    def force_reset(self):
        if len(self.current_throw) > 0:
            throw_data = {
                "path": list(self.current_throw),
                "decision": self.current_throw_decision
            }
            self.throw_database.append(throw_data)
            if len(self.throw_database) > self.max_throws:
                self.throw_database.pop(0)

            self.current_throw.clear()
            self.current_throw_decision = "NO THREAT DETECTED"

        if self.robot_state == "DODGING":
            print("System manually reset.")
            self.robot_state = "SCANNING"
            self.ball_history.clear() 
            self.tracker = DodgeballKalman() 
            self.missed_frames = 0
            self.locked_command = ""

    def _is_shape_corrupted(self, width, height, tolerance):
        """Checks if the bounding box is a valid square shape."""
        # Prevent math crashes if height is somehow 0
        if height == 0: 
            return True, 0.0
            
        aspect_ratio = width / float(height)
        
        # If it's too skinny or too wide, it's corrupted
        if aspect_ratio < (1.0 - tolerance) or aspect_ratio > (1.0 + tolerance):
            return True, aspect_ratio
            
        return False, aspect_ratio

    def process_frame(self, conf, m_noise, p_noise, shape_tolerance, impact_threshold, reaction_frames, auto_reset, cooldown_seconds, left_bound, right_bound,replay_index):
        success, frame = self.cap.read()
        if not success:
            return False, None, {}

        curr_time = time.time()
        fps = int(1 / (curr_time - self.prev_time))
        self.prev_time = curr_time

        # Data dictionary to send back to the GUI
        telemetry_data = {
            "fps": fps,
            "state": self.robot_state,
            "command": self.locked_command,
            "text": "Waiting for target...",
            "cooldown_left": 0.0
        }

        self.tracker.update_tuning(p_noise, m_noise)

        if self.robot_state == "DODGING":
            if auto_reset:
                self.cooldown_timer -= 1
                seconds_left = self.cooldown_timer / 30.0
                telemetry_data["cooldown_left"] = seconds_left
                telemetry_data["text"] = f"EVASION LOCKED...\nAuto Cooldown: {seconds_left:.1f}s"
                
                if self.cooldown_timer <= 0:
                    self.force_reset() 
            else:
                telemetry_data["text"] = "EVASION LOCKED...\nAwaiting Manual Reset!"

            cv2.rectangle(frame, (0,0), (self.frame_width, self.frame_height), (0, 0, 255), 15)
            return True, frame, telemetry_data 

        results = self.model(frame, conf=conf, verbose=False)
        annotated_frame = frame.copy() 
        boxes = results[0].boxes
        
        telemetry_text = "Status: Area Safe.\nTarget Area: 0 px"
        current_area_val = 0

        predicted_state = self.tracker.predict()

        if len(boxes) > 0:
            best_box_index = boxes.conf.argmax().item()
            best_box = boxes[best_box_index]
            coords = best_box.xyxy[0].cpu().numpy()
            x_min, y_min, x_max, y_max = coords
            
            width = x_max - x_min
            height = y_max - y_min
            diameter = min(width, height)
            current_area_val = int(width * height)
            

            is_corrupted, aspect_ratio = self._is_shape_corrupted(width, height, shape_tolerance)
            
            if not is_corrupted:
                telemetry_text = f"Status: Tracking...\nTarget Area: {current_area_val} px"
                
                raw_center_x = int((x_min + x_max) / 2)
                raw_center_y = int((y_min + y_max) / 2)
                
                cv2.rectangle(annotated_frame, (int(x_min), int(y_min)), (int(x_max), int(y_max)), (0, 255, 0), 2)
                
                corrected_state = self.tracker.correct(raw_center_x, raw_center_y, diameter)
                
                smooth_x = int(corrected_state[0, 0])
                smooth_y = int(corrected_state[1, 0])
                
                self.ball_history.append((smooth_x, smooth_y))
                
                cv2.circle(annotated_frame, (raw_center_x, raw_center_y), 5, (255, 0, 0), -1) 
                cv2.circle(annotated_frame, (smooth_x, smooth_y), 5, (0, 0, 255), -1)
                

                self.missed_frames = 0
            else:
                # Bouncer triggered: Filter out the bad shape!
                telemetry_text = f"Status: Bad Shape Filtered ({aspect_ratio:.2f})"
                self.missed_frames += 1
                
                if self.tracker.initialized and self.missed_frames < 15:
                    pred_x = int(predicted_state[0, 0])
                    pred_y = int(predicted_state[1, 0])
                    pred_area = int(predicted_state[2, 0])
                    current_area_val = pred_area
                    
                    self.ball_history.append((pred_x, pred_y))
                    cv2.circle(annotated_frame, (pred_x, pred_y), 5, (0, 165, 255), -1) 
                else:
                    self.ball_history.append(None)

        else:
            self.missed_frames += 1
            
            if self.tracker.initialized and self.missed_frames < 15:
                pred_x = int(predicted_state[0, 0])
                pred_y = int(predicted_state[1, 0])
                pred_area = int(predicted_state[2, 0])
                current_area_val = pred_area
                
                self.ball_history.append((pred_x, pred_y))
                cv2.circle(annotated_frame, (pred_x, pred_y), 5, (0, 165, 255), -1) 
                
                telemetry_text = f"Status: BLIND TRACKING\nPred Area: {pred_area} px"
            else:
                self.ball_history.append(None)

        if self.missed_frames > 15:
            if len(self.current_throw) > 0:
                throw_data = {
                    "path": list(self.current_throw),
                    "decision": self.current_throw_decision
                }
                self.throw_database.append(throw_data)
                if len(self.throw_database) > self.max_throws:
                    self.throw_database.pop(0)
            self.current_throw.clear()
            self.current_throw_decision = "NO THREAT DETECTED"
            self.tracker = DodgeballKalman()

        impact_data = self.tracker.get_impact_prediction(self.center_of_screen,impact_area=impact_threshold)

        if impact_data is not None:
            # Unpack all 3 variables!
            impact_x, impact_y, frames_until_hit = impact_data
            
            telemetry_text = f"THREAT DETECTED!\nArea: {current_area_val} px\nImpact: X:{impact_x} Y:{impact_y}\nTime: {frames_until_hit} f"
            
            current_x = int(self.tracker.kf.statePost[0, 0])
            current_y = int(self.tracker.kf.statePost[1, 0])

            self.current_throw.append(((current_x, current_y), (impact_x, impact_y)))
            
            cv2.line(annotated_frame, (current_x, current_y), (impact_x, impact_y), (0, 255, 255), 3)
            cv2.circle(annotated_frame, (impact_x, impact_y), 10, (0, 255, 255), -1)
            
            # --- THE RENDERING FIX ---
            # Draw the line to impact_y, NOT self.frame_height//2
            cv2.line(annotated_frame, (current_x, current_y), (impact_x, impact_y), (0, 255, 255), 3)
            cv2.circle(annotated_frame, (impact_x, impact_y), 10, (0, 255, 255), -1)
            

            if frames_until_hit < reaction_frames: 
                
                # Check Hitbox bounds
                if impact_x < left_bound or impact_x > right_bound:
                    telemetry_text = f"TRAJECTORY CLEAR!\nBall will miss.\nImpact X: {impact_x}"
                    self.current_throw_decision = "IGNORED (SAFE TRAJECTORY)" # <--- RECORD DECISION
                else:
                    self.robot_state = "DODGING"
                    telemetry_data["state"] = self.robot_state
                    self.cooldown_timer = int(cooldown_seconds * 30) 
                    
                    if impact_x > self.center_of_screen:
                        self.locked_command = "DODGE LEFT"
                        self.current_throw_decision = "TRIGGERED: DODGE LEFT" # <--- RECORD DECISION
                        if self.arduino:
                            self.arduino.write(b'L')
                            print("--> Serial Sent: L")
                    else:
                        self.locked_command = "DODGE RIGHT"
                        self.current_throw_decision = "TRIGGERED: DODGE RIGHT" # <--- RECORD DECISION
                        if self.arduino:
                            self.arduino.write(b'R')
                            print("--> Serial Sent: R")
                    
                    telemetry_data["command"] = self.locked_command

        if replay_index >= 0 and replay_index < len(self.throw_database):
            selected_data = self.throw_database[replay_index]
            selected_path = selected_data["path"]
            saved_decision = selected_data["decision"]

            for start, end in selected_path:
                cv2.line(annotated_frame, start, end, (255, 0, 255), 2)
                cv2.circle(annotated_frame, end, 5, (255, 0, 255), -1)
            
            cv2.putText(annotated_frame, f"REVIEWING THROW {replay_index + 1}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
            cv2.putText(annotated_frame, f"AI DECISION: {saved_decision}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
            

        telemetry_data["text"] = telemetry_text
        
        cv2.line(annotated_frame, (self.center_of_screen, 0), (self.center_of_screen, self.frame_height), (255, 255, 255), 2)

        # The Hitbox Boundaries (Orange)
        cv2.line(annotated_frame, (int(left_bound), 0), (int(left_bound), self.frame_height), (0, 140, 255), 2)
        cv2.line(annotated_frame, (int(right_bound), 0), (int(right_bound), self.frame_height), (0, 140, 255), 2)
        
        return True, annotated_frame, telemetry_data

    def shutdown(self):
        print("Shutting down camera and hardware...")
        if self.arduino:
            self.arduino.close()
        self.cap.release()