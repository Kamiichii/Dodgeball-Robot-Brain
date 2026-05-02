import cv2
import tkinter as tk
from PIL import Image, ImageTk

# Import the detached Backend Engine
from vision_core import VisionCore

class DodgeballGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dodgeball Vision - Mission Control")
        
        # --- THE MASTER DIMENSIONS ---
        self.root.geometry("1400x800") 
        self.root.resizable(False, False)

        self.engine = VisionCore(src=0)

        # ================= THE 3-COLUMN GRID SETUP =================
        # Zone 1: Camera
        self.video_label = tk.Label(root, bg="black")
        self.video_label.grid(row=0, column=0, padx=30, pady=160) 

        # Zone 2: Telemetry Column
        self.panel_left = tk.Frame(root, width=320, height=760)
        self.panel_left.grid(row=0, column=1, sticky="n", padx=10, pady=20)
        self.panel_left.pack_propagate(False) # Stops the column from shrinking

        # Zone 3: Physics Column
        self.panel_right = tk.Frame(root, width=320, height=760)
        self.panel_right.grid(row=0, column=2, sticky="n", padx=10, pady=20)
        self.panel_right.pack_propagate(False) 

        # ================= ZONE 2: TELEMETRY & HITBOX (.pack stacking) =================
        self.cmd_label = tk.Label(self.panel_left, text="SCANNING...", font=("Arial", 26, "bold"), fg="green")
        self.cmd_label.pack(pady=(10, 20))

        self.data_label = tk.Label(self.panel_left, text="Waiting...", font=("Courier", 12), justify="left", anchor="nw", relief="sunken", bd=2)
        self.data_label.pack(fill="x", padx=20, pady=10, ipady=30) # ipady makes the box taller internally

        self.fps_label = tk.Label(self.panel_left, text="FPS: 0", font=("Arial", 14))
        self.fps_label.pack(pady=5)

        # Helper function to auto-stack sliders perfectly
        def create_slider(parent, label, min_val, max_val, res, default):
            tk.Label(parent, text=label, font=("Arial", 10, "bold")).pack(pady=(15, 0))
            s = tk.Scale(parent, from_=min_val, to=max_val, resolution=res, orient="horizontal")
            s.set(default)
            s.pack(fill="x", padx=40)
            return s

        self.conf_slider = create_slider(self.panel_left, "AI Confidence Threshold", 0.1, 1.0, 0.05, 0.90)
        self.impact_slider = create_slider(self.panel_left, "Impact Area (Target Size)", 10000, 150000, 5000, 60000)
        self.reaction_slider = create_slider(self.panel_left, "Reaction Trigger (Frames)", 5, 60, 1, 15)
        self.left_bound_slider = create_slider(self.panel_left, "Hitbox Left Edge (X)", 0, 320, 10, 150)
        self.right_bound_slider = create_slider(self.panel_left, "Hitbox Right Edge (X)", 320, 640, 10, 490)


        # ================= ZONE 3: PHYSICS & SYSTEM (.pack stacking) =================
        self.meas_slider = create_slider(self.panel_right, "Sensor Jitter (Measurement Noise)", 1, 100, 1, 10)
        self.proc_slider = create_slider(self.panel_right, "Erratic Movement (Process Noise)", 0.01, 1.0, 0.01, 0.05)
        self.shape_slider = create_slider(self.panel_right, "Shape Distortion Tolerance", 0.1, 0.8, 0.05, 0.3)
        self.cooldown_slider = create_slider(self.panel_right, "Auto Cooldown (Seconds)", 0.5, 5.0, 0.1, 1.5)

        self.auto_reset = tk.BooleanVar(value=True) 
        tk.Checkbutton(self.panel_right, text="Enable Auto-Reset", variable=self.auto_reset, font=("Arial", 11, "bold")).pack(pady=20)

        # Action Buttons (The massive pady=(30, 10) pushes the database button down)
        self.replay_index = -1
        self.db_btn = tk.Button(self.panel_right, text="OPEN THROW DATABASE", command=self.open_database, bg="#9C27B0", fg="white", font=("Arial", 12, "bold"), height=2)
        self.db_btn.pack(fill="x", padx=40, pady=(30, 10))

        self.reset_btn = tk.Button(self.panel_right, text="MANUAL RESET", command=self.engine.force_reset, bg="#FF9800", font=("Arial", 12, "bold"), height=2)
        self.reset_btn.pack(fill="x", padx=40, pady=10)

        self.quit_btn = tk.Button(self.panel_right, text="SHUTDOWN SYSTEM", command=self.on_close, bg="#f44336", fg="white", font=("Arial", 12, "bold"), height=2)
        self.quit_btn.pack(fill="x", padx=40, pady=10)

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