import cv2
import time

# Iniciar webcam
cap = cv2.VideoCapture(0)  # 0 = cámara principal

# Validar si abrió
if not cap.isOpened():
    print("No se pudo abrir la webcam :(")
    exit()

# Variables para calcular FPS
prev_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("No se pudo leer un frame")
        break

    # Calcular FPS
    current_time = time.time()
    fps = 1 / (current_time - prev_time) if prev_time != 0 else 0
    prev_time = current_time

    # Mostrar FPS en pantalla
    cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Mostrar frame
    cv2.imshow("Webcam", frame)

    # Salir con 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar recursos
cap.release()
cv2.destroyAllWindows()
