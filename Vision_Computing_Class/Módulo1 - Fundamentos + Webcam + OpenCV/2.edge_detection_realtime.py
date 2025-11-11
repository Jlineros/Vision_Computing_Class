import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class ToolTip:
    """Clase para crear tooltips que aparecen al hacer hover"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self):
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("tahoma", "8", "normal"), wraplength=250)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class EdgeDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Detección de Bordes en Tiempo Real")
        
        # Inicializar webcam
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("No se pudo abrir la webcam")
            self.root.destroy()
            return
        
        # Obtener dimensiones de la cámara
        ret, test_frame = self.cap.read()
        if not ret:
            print("No se pudo leer de la webcam")
            self.cap.release()
            self.root.destroy()
            return
        
        self.camera_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.camera_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Variables de estado
        self.mode = "color"  # color, grayscale, canny, sobel
        self.is_running = False
        self.display_width = self.camera_width
        self.display_height = self.camera_height
        
        # Parámetros para Canny
        self.canny_threshold1 = tk.IntVar(value=50)
        self.canny_threshold2 = tk.IntVar(value=150)
        
        # Parámetros para Sobel
        self.sobel_kernel = tk.IntVar(value=3)
        self.sobel_scale = tk.DoubleVar(value=1.0)
        self.sobel_delta = tk.IntVar(value=0)
        
        # Crear interfaz
        self.create_ui()
        
        # Ajustar tamaño de ventana después de crear la UI
        self.adjust_window_size()
        
        # Iniciar captura de video
        self.is_running = True
        self.update_frame()
        
    def create_ui(self):
        # Frame principal con scroll
        self.canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Ajustar ancho del canvas cuando cambie el tamaño del frame
        def configure_canvas_width(event):
            canvas_width = event.width
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        self.canvas.bind('<Configure>', configure_canvas_width)
        
        # Configurar scroll con mouse wheel
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Frame principal dentro del scrollable
        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Frame para el video
        video_frame = ttk.Frame(main_frame)
        video_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        main_frame.rowconfigure(0, weight=0)  # No expandir, tamaño fijo
        
        # Label para mostrar el video
        self.video_label = ttk.Label(video_frame, background="black")
        self.video_label.pack()
        
        # Frame para controles
        self.controls_frame = ttk.LabelFrame(main_frame, text="Controles", padding="10")
        self.controls_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        controls_frame = self.controls_frame
        
        # Botones de modo
        mode_frame = ttk.LabelFrame(controls_frame, text="Modos de Visualización", padding="5")
        mode_frame.pack(fill=tk.X, pady=5)
        
        # Frame para botones de modo con información
        mode_buttons_frame = ttk.Frame(mode_frame)
        mode_buttons_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Color Original
        color_frame = ttk.Frame(mode_buttons_frame)
        color_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(color_frame, text="Color Original", 
                  command=lambda: self.set_mode("color")).pack(side=tk.LEFT)
        info_label = ttk.Label(color_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Muestra el video de la webcam en color original sin ningún procesamiento. " +
                "Este es el modo predeterminado que muestra la imagen tal como la captura la cámara.")
        
        # Escala de Grises
        gray_frame = ttk.Frame(mode_buttons_frame)
        gray_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(gray_frame, text="Escala de Grises", 
                  command=lambda: self.set_mode("grayscale")).pack(side=tk.LEFT)
        info_label = ttk.Label(gray_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Convierte el video a escala de grises (blanco y negro). " +
                "Este modo elimina la información de color y representa la imagen usando solo valores de intensidad de gris.")
        
        # Canny
        canny_frame = ttk.Frame(mode_buttons_frame)
        canny_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(canny_frame, text="Canny", 
                  command=lambda: self.set_mode("canny")).pack(side=tk.LEFT)
        info_label = ttk.Label(canny_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Aplica el algoritmo de detección de bordes Canny. " +
                "Utiliza suavizado Gaussiano, detección de gradientes, supresión de no-máximos y umbralización con histéresis.")
        
        # Sobel
        sobel_frame = ttk.Frame(mode_buttons_frame)
        sobel_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(sobel_frame, text="Sobel", 
                  command=lambda: self.set_mode("sobel")).pack(side=tk.LEFT)
        info_label = ttk.Label(sobel_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Aplica el operador Sobel para detectar bordes. " +
                "Calcula el gradiente en direcciones X e Y y los combina para detectar bordes en todas las orientaciones.")
        
        # Frame para descripción del modo actual (donde estaban los títulos de parámetros)
        self.mode_description_frame = ttk.Frame(controls_frame)
        self.mode_description_frame.pack(fill=tk.X, pady=5)
        self.mode_description_label = ttk.Label(self.mode_description_frame, 
                                                text="", 
                                                foreground="gray",
                                                wraplength=600,
                                                justify=tk.LEFT)
        self.mode_description_label.pack(anchor=tk.W, padx=5)
        
        # Frame para parámetros de Canny
        self.canny_frame = ttk.LabelFrame(controls_frame, padding="5")
        self.canny_frame.pack(fill=tk.X, pady=5)
        
        # Threshold 1
        ttk.Label(self.canny_frame, text="Threshold 1:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.canny_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Umbral inferior para detección de bordes. " +
                "Valores bajos (0-50) detectan más bordes incluyendo ruido. " +
                "Valores medios (50-100) balance entre detección y eliminación de ruido. " +
                "Valores altos (100-255) solo detectan bordes muy fuertes.")
        ttk.Scale(self.canny_frame, from_=0, to=255, variable=self.canny_threshold1, 
                 orient=tk.HORIZONTAL, length=200, command=self.on_canny_change).grid(row=0, column=2, padx=5, pady=2)
        ttk.Label(self.canny_frame, textvariable=self.canny_threshold1).grid(row=0, column=3, padx=5, pady=2)
        
        # Threshold 2
        ttk.Label(self.canny_frame, text="Threshold 2:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.canny_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=1, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Umbral superior para detección de bordes. " +
                "Valores bajos (0-100) detectan muchos bordes. " +
                "Valores medios (100-200) detectan bordes significativos con buen balance. " +
                "Valores altos (200-255) solo bordes muy prominentes. Ratio típico: Threshold 2 ≈ 3 × Threshold 1")
        ttk.Scale(self.canny_frame, from_=0, to=255, variable=self.canny_threshold2, 
                 orient=tk.HORIZONTAL, length=200, command=self.on_canny_change).grid(row=1, column=2, padx=5, pady=2)
        ttk.Label(self.canny_frame, textvariable=self.canny_threshold2).grid(row=1, column=3, padx=5, pady=2)
        
        # Frame para parámetros de Sobel
        self.sobel_frame = ttk.LabelFrame(controls_frame, padding="5")
        self.sobel_frame.pack(fill=tk.X, pady=5)
        
        # Kernel Size
        ttk.Label(self.sobel_frame, text="Kernel Size:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.sobel_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Tamaño de la matriz de convolución (debe ser impar: 1, 3, 5, 7). " +
                "Kernel 3x3 es estándar con buen balance. Kernels más grandes proporcionan más suavizado pero pueden difuminar los bordes.")
        kernel_scale = ttk.Scale(self.sobel_frame, from_=1, to=7, variable=self.sobel_kernel, 
                                orient=tk.HORIZONTAL, length=200, command=self.on_sobel_change)
        kernel_scale.grid(row=0, column=2, padx=5, pady=2)
        # Asegurar que el kernel sea impar
        kernel_scale.configure(command=lambda v: self.on_sobel_kernel_change(v))
        ttk.Label(self.sobel_frame, textvariable=self.sobel_kernel).grid(row=0, column=3, padx=5, pady=2)
        
        # Scale
        ttk.Label(self.sobel_frame, text="Scale:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.sobel_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=1, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Factor de escala para los valores del gradiente. " +
                "Valores bajos (0.1-0.5) reducen la intensidad. Valor 1.0 sin escalado. " +
                "Valores altos (2.0-5.0) aumentan la intensidad de los bordes.")
        ttk.Scale(self.sobel_frame, from_=0.1, to=5.0, variable=self.sobel_scale, 
                 orient=tk.HORIZONTAL, length=200, command=self.on_sobel_change).grid(row=1, column=2, padx=5, pady=2)
        ttk.Label(self.sobel_frame, textvariable=self.sobel_scale).grid(row=1, column=3, padx=5, pady=2)
        
        # Delta
        ttk.Label(self.sobel_frame, text="Delta:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.sobel_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=2, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Valor que se suma al resultado antes de convertir a 8 bits. " +
                "Valor 0 sin desplazamiento. Valores positivos (1-100) aclaran la imagen de bordes y aumentan el brillo.")
        ttk.Scale(self.sobel_frame, from_=0, to=100, variable=self.sobel_delta, 
                 orient=tk.HORIZONTAL, length=200, command=self.on_sobel_change).grid(row=2, column=2, padx=5, pady=2)
        ttk.Label(self.sobel_frame, textvariable=self.sobel_delta).grid(row=2, column=3, padx=5, pady=2)
        
        # Botón de salida centrado al final
        exit_frame = ttk.Frame(controls_frame)
        exit_frame.pack(fill=tk.X, pady=10)
        ttk.Button(exit_frame, text="Salir", command=self.on_closing).pack()
        
        # Inicializar visibilidad de frames
        self.update_controls_visibility()
        self.update_mode_description()
        
    def adjust_window_size(self):
        """Ajusta el tamaño de la ventana al tamaño de la imagen más los controles"""
        # Actualizar la ventana para obtener el tamaño real de los controles
        self.root.update_idletasks()
        
        # Obtener dimensiones de la pantalla
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calcular el tamaño total de la ventana
        # Agregar padding y espacio para los controles
        padding_h = 40  # padding horizontal
        padding_v = 60  # padding vertical
        total_width = self.camera_width + padding_h + 20  # +20 para scrollbar
        total_height = int(screen_height * 0.9)  # Usar 90% de la altura de pantalla para permitir scroll
        
        # Limitar ancho máximo de pantalla si es necesario
        max_width = int(screen_width * 0.9)
        
        if total_width > max_width:
            # Calcular escala para el ancho
            scale = max_width / total_width
            self.display_width = int(self.camera_width * scale)
            self.display_height = int(self.camera_height * scale)
            total_width = max_width
        else:
            self.display_width = self.camera_width
            self.display_height = self.camera_height
        
        # Establecer geometría de la ventana
        self.root.geometry(f"{total_width}x{total_height}")
        self.root.minsize(total_width, 400)  # Altura mínima razonable
        
        # Actualizar scrollregion después de ajustar tamaño
        self.root.after(100, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
    def set_mode(self, mode):
        self.mode = mode
        self.update_controls_visibility()
        self.update_mode_description()
        
    def update_mode_description(self):
        """Actualiza la descripción del modo actual"""
        descriptions = {
            "color": "Muestra el video de la webcam en color original sin ningún procesamiento. " +
                    "Este es el modo predeterminado que muestra la imagen tal como la captura la cámara, " +
                    "preservando todos los colores y detalles originales.",
            "grayscale": "Convierte el video a escala de grises (blanco y negro). " +
                        "Este modo elimina la información de color y representa la imagen usando solo " +
                        "valores de intensidad de gris (0-255). Es útil como paso previo para muchos " +
                        "algoritmos de procesamiento de imágenes, ya que reduce la complejidad de los datos.",
            "canny": "Aplica el algoritmo de detección de bordes Canny. " +
                    "El algoritmo Canny es uno de los métodos más populares para detectar bordes en imágenes. " +
                    "Utiliza un proceso de múltiples etapas: suavizado con filtro Gaussiano, detección de gradientes, " +
                    "supresión de no-máximos y umbralización con histéresis. Es especialmente efectivo para " +
                    "detectar bordes finos y eliminar ruido.",
            "sobel": "Aplica el operador Sobel para detectar bordes. " +
                    "El operador Sobel calcula el gradiente de la imagen en las direcciones horizontal (X) " +
                    "y vertical (Y). Luego combina ambas direcciones para detectar bordes en todas las orientaciones. " +
                    "A diferencia de Canny, Sobel es más simple y rápido, pero puede ser más sensible al ruido."
        }
        
        self.mode_description_label.config(text=descriptions.get(self.mode, ""))
        
    def update_controls_visibility(self):
        # Mostrar/ocultar frames de parámetros según el modo
        if self.mode == "canny":
            self.canny_frame.pack(fill=tk.X, pady=5)
            self.sobel_frame.pack_forget()
        elif self.mode == "sobel":
            self.canny_frame.pack_forget()
            self.sobel_frame.pack(fill=tk.X, pady=5)
        else:
            self.canny_frame.pack_forget()
            self.sobel_frame.pack_forget()
        
        # Actualizar scrollregion después de cambiar visibilidad
        self.root.after(10, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            
    def on_canny_change(self, value=None):
        # Se actualiza automáticamente en update_frame
        pass
        
    def on_sobel_kernel_change(self, value):
        # Asegurar que el kernel sea impar
        kernel_val = int(float(value))
        if kernel_val % 2 == 0:
            kernel_val += 1
        if kernel_val > 7:
            kernel_val = 7
        if kernel_val < 1:
            kernel_val = 1
        self.sobel_kernel.set(kernel_val)
        self.on_sobel_change()
        
    def on_sobel_change(self, value=None):
        # Se actualiza automáticamente en update_frame
        pass
        
    def process_frame(self, frame):
        """Procesa el frame según el modo actual"""
        if self.mode == "color":
            return frame
        elif self.mode == "grayscale":
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif self.mode == "canny":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 
                             self.canny_threshold1.get(), 
                             self.canny_threshold2.get())
            return edges
        elif self.mode == "sobel":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            kernel_size = self.sobel_kernel.get()
            # Asegurar que sea impar
            if kernel_size % 2 == 0:
                kernel_size += 1
            if kernel_size < 1:
                kernel_size = 1
            if kernel_size > 7:
                kernel_size = 7
                
            # Aplicar Sobel en X e Y
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=kernel_size, 
                              scale=self.sobel_scale.get(), 
                              delta=self.sobel_delta.get())
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=kernel_size, 
                              scale=self.sobel_scale.get(), 
                              delta=self.sobel_delta.get())
            
            # Combinar magnitudes
            sobel_combined = np.sqrt(sobelx**2 + sobely**2)
            sobel_combined = np.uint8(np.absolute(sobel_combined))
            
            return sobel_combined
        
        return frame
        
    def update_frame(self):
        """Actualiza el frame del video"""
        if not self.is_running:
            return
            
        ret, frame = self.cap.read()
        if ret:
            # Procesar frame
            processed = self.process_frame(frame)
            
            # Convertir a RGB si es necesario para mostrar en tkinter
            if len(processed.shape) == 2:  # Escala de grises
                processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
            else:
                processed_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            
            # Redimensionar al tamaño de visualización (manteniendo relación de aspecto)
            height, width = processed_rgb.shape[:2]
            
            # Si el tamaño de visualización es diferente al tamaño de la cámara, escalar
            if self.display_width != width or self.display_height != height:
                processed_rgb = cv2.resize(processed_rgb, (self.display_width, self.display_height))
            
            # Convertir a ImageTk
            image = Image.fromarray(processed_rgb)
            photo = ImageTk.PhotoImage(image=image)
            
            # Actualizar label
            self.video_label.configure(image=photo)
            self.video_label.image = photo  # Mantener referencia
            
            # Agregar texto con el modo actual
            mode_text = f"Modo: {self.mode.upper()}"
            if self.mode == "canny":
                mode_text += f" | Threshold1: {self.canny_threshold1.get()} | Threshold2: {self.canny_threshold2.get()}"
            elif self.mode == "sobel":
                mode_text += f" | Kernel: {self.sobel_kernel.get()} | Scale: {self.sobel_scale.get():.2f}"
            
            # Mostrar información en la ventana
            self.root.title(f"Detección de Bordes en Tiempo Real - {mode_text}")
        
        # Programar próxima actualización
        self.root.after(10, self.update_frame)
        
    def on_closing(self):
        """Maneja el cierre de la aplicación"""
        self.is_running = False
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = EdgeDetectionApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

