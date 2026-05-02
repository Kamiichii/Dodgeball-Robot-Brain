import cv2
import tkinter as tk
from PIL import Image, ImageTk

# Import the detached Backend Engine
from vision_core import VisionCore

class DodgeballGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dodgeball Vision - Mission Control")
        
        # --- NEW: WIDER AND SHORTER DIMENSIONS ---
        self.root.geometry("1400x800") 
        self.root.resizable(False, False)

        # Initialize Backend Engine
        self.engine = VisionCore(src=0)

        # --- GUI Layout ---
        self.video_label = tk.Label(root)
        self.video_label.grid(row=0, column=0, padx=10, pady=10)

        # --- THE TWO-COLUMN FIX ---
        # We cut the single tall panel into two side-by-side columns
        self.panel_left = tk.Frame(root, width=360, height=680)
        self.panel_left.grid(row=0, column=1, sticky="n", padx=5, pady=10)
        self.panel_left.pack_propagate(False)

        self.panel_right = tk.Frame(root, width=360, height=680)
        self.panel_right.grid(row=0, column=2, sticky="n", padx=5, pady=10)
        self.panel_right.pack_propagate(False)

        # ================= LEFT COLUMN (Telemetry & Config) =================
        self.cmd_label = tk.Label(self.panel_left, text="SCANNING...", font=("Arial", 22, "bold"), fg="green")
        self.cmd_label.place(x=0, y=5, width=260, height=40)

        self.data_label = tk.Label(self.panel_left, text="Waiting for target...", font=("Courier", 11), justify="left", anchor="nw")
        self.data_label.place(x=10, y=50, width=240, height=80)

        self.fps_label = tk.Label(self.panel_left, text="FPS: 0", font=("Arial", 12))
        self.fps_label.place(x=0, y=130, width=260, height=20)

        tk.Label(self.panel_left, text="AI Confidence Threshold", font=("Arial", 10, "bold")).place(x=0, y=150, width=260)
        self.conf_slider = tk.Scale(self.panel_left, from_=0.1, to=1.0, resolution=0.05, orient="horizontal")
        self.conf_slider.set(0.90) 
        self.conf_slider.place(x=30, y=175, width=200)

        tk.Label(self.panel_left, text="Impact Area Threshold", font=("Arial", 10, "bold")).place(x=0, y=215, width=260)
        self.impact_slider = tk.Scale(self.panel_left, from_=10000, to=150000, resolution=5000, orient="horizontal")
        self.impact_slider.set(60000) 
        self.impact_slider.place(x=30, y=240, width=200)

        tk.Label(self.panel_left, text="Reaction Trigger (Frames)", font=("Arial", 10, "bold")).place(x=0, y=280, width=260)
        self.reaction_slider = tk.Scale(self.panel_left, from_=0, to=70, resolution=1, orient="horizontal")
        self.reaction_slider.set(40)
        self.reaction_slider.place(x=30, y=305, width=200)

        tk.Label(self.panel_left, text="Shape Distortion Tolerance", font=("Arial", 10, "bold")).place(x=0, y=345, width=260)
        self.shape_slider = tk.Scale(self.panel_left, from_=0.1, to=0.8, resolution=0.05, orient="horizontal")
        self.shape_slider.set(0.3) 
        self.shape_slider.place(x=30, y=370, width=200)

        # --- NEW: HITBOX BOUNDARIES ---
        tk.Label(self.panel_left, text="Hitbox Left Edge (X)", font=("Arial", 10, "bold")).place(x=0, y=410, width=260)
        self.left_bound_slider = tk.Scale(self.panel_left, from_=0, to=320, resolution=10, orient="horizontal")
        self.left_bound_slider.set(150) # Default is the edge of the screen
        self.left_bound_slider.place(x=30, y=435, width=200)

        tk.Label(self.panel_left, text="Hitbox Right Edge (X)", font=("Arial", 10, "bold")).place(x=0, y=475, width=260)
        self.right_bound_slider = tk.Scale(self.panel_left, from_=320, to=640, resolution=10, orient="horizontal")
        self.right_bound_slider.set(490) # Default is the edge of the screen
        self.right_bound_slider.place(x=30, y=500, width=200)

        # ================= RIGHT COLUMN (Kalman Tuning & System) =================
        tk.Label(self.panel_right, text="Sensor Jitter (Measurement Noise)", font=("Arial", 10, "bold")).place(x=0, y=20, width=260)
        self.meas_slider = tk.Scale(self.panel_right, from_=1, to=100, resolution=1, orient="horizontal")
        self.meas_slider.set(10) 
        self.meas_slider.place(x=30, y=40, width=200)

        tk.Label(self.panel_right, text="Erratic Movement (Process Noise)", font=("Arial", 10, "bold")).place(x=0, y=100, width=260)
        self.proc_slider = tk.Scale(self.panel_right, from_=0.01, to=1.0, resolution=0.01, orient="horizontal")
        self.proc_slider.set(0.05) 
        self.proc_slider.place(x=30, y=120, width=200)

        tk.Label(self.panel_right, text="Auto Cooldown (Seconds)", font=("Arial", 10, "bold")).place(x=0, y=180, width=260)
        self.cooldown_slider = tk.Scale(self.panel_right, from_=0.5, to=5.0, resolution=0.1, orient="horizontal")
        self.cooldown_slider.set(1.5) 
        self.cooldown_slider.place(x=30, y=200, width=200)
        
        self.replay_index = -1  # -1 means we are watching the LIVE feed
        
        self.db_btn = tk.Button(self.panel_right, text="OPEN THROW DATABASE", command=self.open_database, bg="#9C27B0", fg="white", font=("Arial", 10, "bold"), height=2)
        self.db_btn.place(x=30, y=480, width=200, height=40)

        self.auto_reset = tk.BooleanVar(value=True) 
        self.mode_cb = tk.Checkbutton(self.panel_right, text="Enable Auto-Reset", variable=self.auto_reset, font=("Arial", 10, "bold"))
        self.mode_cb.place(x=30, y=270)

        self.reset_btn = tk.Button(self.panel_right, text="MANUAL RESET", command=self.engine.force_reset, bg="orange", font=("Arial", 10, "bold"))
        self.reset_btn.place(x=30, y=340, width=200, height=40)

        self.quit_btn = tk.Button(self.panel_right, text="SHUTDOWN SYSTEM", command=self.on_close, bg="red", fg="white", font=("Arial", 10, "bold"))
        self.quit_btn.place(x=30, y=410, width=200, height=40)

        self.update_frame()
    
    def open_database(self):
        # Create a new pop-up window
        db_win = tk.Toplevel(self.root)
        db_win.title("Throw Database")
        db_win.geometry("300x450")
        db_win.resizable(False, False)

        tk.Label(db_win, text="Saved Throws (Last 20)", font=("Arial", 14, "bold")).pack(pady=10)

        # Create a scrollable listbox
        list_frame = tk.Frame(db_win)
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 12), selectbackground="#9C27B0")
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        # Ask the engine how many throws are saved, and populate the list
        num_throws = len(self.engine.throw_database)
        if num_throws == 0:
            listbox.insert(tk.END, "No throws recorded yet.")
        else:
            for i in range(num_throws):
                listbox.insert(tk.END, f"Throw {i + 1}")

        # The function that runs when you click "PLAY SELECTED"
        def play_selected():
            selection = listbox.curselection()
            if selection and num_throws > 0:
                self.replay_index = selection[0] # Tell the engine which throw to draw

        # The function that runs when you click "RESUME LIVE"
        def resume_live():
            self.replay_index = -1 # -1 means go back to live mode
            db_win.destroy()       # Close the pop-up

        tk.Button(db_win, text="PLAY SELECTED", command=play_selected, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill="x", padx=20, pady=5)
        tk.Button(db_win, text="RESUME LIVE FEED", command=resume_live, bg="#F44336", fg="white", font=("Arial", 10, "bold"), height=2).pack(fill="x", padx=20, pady=10)
    
    def update_frame(self):
        # Gather all current UI slider values
        conf = self.conf_slider.get()
        m_noise = self.meas_slider.get()
        p_noise = self.proc_slider.get()
        shape_tol = self.shape_slider.get()
        impact_thresh = self.impact_slider.get()
        reaction_frames = self.reaction_slider.get()
        auto_res = self.auto_reset.get()
        cooldown_sec = self.cooldown_slider.get()

        left_bound = self.left_bound_slider.get()
        right_bound = self.right_bound_slider.get()

        replay_index = self.replay_index

        # Pass them to the backend engine to process the frame
        success, frame, data = self.engine.process_frame(
            conf, m_noise, p_noise, shape_tol, impact_thresh, reaction_frames, auto_res, cooldown_sec, left_bound, right_bound,replay_index
        )

        if success:
            self.fps_label.config(text=f"FPS: {data.get('fps', 0)}")
            self.data_label.config(text=data.get('text', ''))

            if data.get('state') == "SCANNING":
                self.cmd_label.config(text="SCANNING...", fg="green")
            else:
                self.cmd_label.config(text=f"LOCKED:\n{data.get('command')}", fg="red")

            # Render the image
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(10, self.update_frame)

    def on_close(self):
        self.engine.shutdown()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DodgeballGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()