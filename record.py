import cv2

def main():
    # 1. Open your external camera
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) 

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # 2. Get the camera's resolution
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # We will record at 15 Frames Per Second. 
    # This keeps the file size small and makes Roboflow uploads lightning fast.
    fps = 30

    # 3. Set up the Video Writer (Saves as an MP4)
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter('dodgeball_training.mp4', fourcc, fps, (width, height))

    print("🔴 RECORDING STARTED! Press 'q' to stop recording and save.")

    while True:
        success, frame = cap.read()
        if not success:
            print("Error: Camera disconnected.")
            break

        # Write the frame to the video file
        out.write(frame)

        # Show you what is being recorded
        cv2.imshow('Recording Custom Dataset', frame)

        # Press 'q' to quit and save
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 4. Clean up and save the file properly
    print("Recording saved as 'dodgeball_training.mp4'!")
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()