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

class FiltersRealtimeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Filtros en Tiempo Real - Blur y Binarización")
        
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
        self.mode = "original"  # original, binary, blur, binary_blur
        self.is_running = False
        self.display_width = self.camera_width
        self.display_height = self.camera_height
        
        # Parámetros para Binarización
        self.threshold_value = tk.IntVar(value=127)
        self.threshold_type = tk.StringVar(value="BINARY")  # BINARY, BINARY_INV, TRUNC, TOZERO, TOZERO_INV
        
        # Parámetros para Blur
        self.blur_kernel_size = tk.IntVar(value=5)
        self.blur_sigma_x = tk.DoubleVar(value=0.0)
        
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
        
        # Original
        original_frame = ttk.Frame(mode_buttons_frame)
        original_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(original_frame, text="Original", 
                  command=lambda: self.set_mode("original")).pack(side=tk.LEFT)
        info_label = ttk.Label(original_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Modo Original: Muestra el video de la webcam sin ningún procesamiento. " +
                "Este es el modo predeterminado que muestra la imagen tal como la captura la cámara, " +
                "preservando todos los colores y detalles originales. Útil como referencia para comparar con los filtros aplicados.")
        
        # Binarización
        binary_frame = ttk.Frame(mode_buttons_frame)
        binary_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(binary_frame, text="Binarización", 
                  command=lambda: self.set_mode("binary")).pack(side=tk.LEFT)
        info_label = ttk.Label(binary_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Modo Binarización: Aplica threshold (umbralización) a la imagen. " +
                "Primero convierte la imagen a escala de grises, luego aplica un umbral para crear una imagen binaria (blanco y negro). " +
                "Los píxeles con intensidad mayor al threshold se convierten en blanco (255), los menores en negro (0). " +
                "Útil para segmentación, detección de objetos y eliminación de ruido de fondo.")
        
        # Blur
        blur_frame = ttk.Frame(mode_buttons_frame)
        blur_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(blur_frame, text="Blur", 
                  command=lambda: self.set_mode("blur")).pack(side=tk.LEFT)
        info_label = ttk.Label(blur_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Modo Blur: Aplica un filtro de desenfoque Gaussiano a la imagen. " +
                "Suaviza la imagen reduciendo el ruido y los detalles finos mediante convolución con un kernel Gaussiano. " +
                "El grado de desenfoque se controla mediante el tamaño del kernel y la desviación estándar (sigma). " +
                "Útil para reducir ruido, suavizar texturas y preparar imágenes para procesamiento posterior.")
        
        # Binarización + Blur (Pipeline)
        pipeline_frame = ttk.Frame(mode_buttons_frame)
        pipeline_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(pipeline_frame, text="Binarización + Blur", 
                  command=lambda: self.set_mode("binary_blur")).pack(side=tk.LEFT)
        info_label = ttk.Label(pipeline_frame, text="ℹ", width=2, cursor="hand2")
        info_label.pack(side=tk.LEFT, padx=2)
        ToolTip(info_label, "Pipeline Binarización + Blur: Aplica primero blur Gaussiano y luego binarización. " +
                "Este orden permite suavizar la imagen antes de aplicar el threshold, resultando en bordes más limpios " +
                "y menos ruido en la imagen binaria final. El blur elimina pequeños detalles y ruido, " +
                "mejorando la calidad de la segmentación. Ideal para procesamiento de imágenes con mucho ruido.")
        
        # Frame para descripción del modo actual
        self.mode_description_frame = ttk.Frame(controls_frame)
        self.mode_description_frame.pack(fill=tk.X, pady=5)
        self.mode_description_label = ttk.Label(self.mode_description_frame, 
                                                text="", 
                                                foreground="gray",
                                                wraplength=600,
                                                justify=tk.LEFT)
        self.mode_description_label.pack(anchor=tk.W, padx=5)
        
        # Frame para parámetros de Binarización
        self.binary_frame = ttk.LabelFrame(controls_frame, padding="5")
        self.binary_frame.pack(fill=tk.X, pady=5)
        
        # Threshold Value
        ttk.Label(self.binary_frame, text="Threshold:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.binary_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Threshold (Umbral): Valor umbral para la binarización (0-255). " +
                "Píxeles con intensidad mayor al threshold se convierten en blanco (255), " +
                "los menores se convierten en negro (0). Valores típicos: 100-150. " +
                "Valores bajos (0-100) mantienen más detalles pero incluyen más ruido. " +
                "Valores altos (150-255) eliminan más ruido pero pueden perder detalles importantes.")
        ttk.Scale(self.binary_frame, from_=0, to=255, variable=self.threshold_value, 
                 orient=tk.HORIZONTAL, length=200, command=self.on_threshold_change).grid(row=0, column=2, padx=5, pady=2)
        ttk.Label(self.binary_frame, textvariable=self.threshold_value).grid(row=0, column=3, padx=5, pady=2)
        
        # Threshold Type
        ttk.Label(self.binary_frame, text="Tipo:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.binary_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=1, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Tipo de Binarización: Selecciona el método de umbralización. " +
                "• BINARY: Píxeles > threshold = blanco (255), ≤ threshold = negro (0). " +
                "• BINARY_INV: Inverso de BINARY. " +
                "• TRUNC: Píxeles > threshold = threshold, ≤ threshold = sin cambio. " +
                "• TOZERO: Píxeles > threshold = sin cambio, ≤ threshold = 0. " +
                "• TOZERO_INV: Inverso de TOZERO. BINARY es el más común para segmentación.")
        threshold_type_combo = ttk.Combobox(self.binary_frame, textvariable=self.threshold_type,
                                           values=["BINARY", "BINARY_INV", "TRUNC", "TOZERO", "TOZERO_INV"],
                                           state="readonly", width=15)
        threshold_type_combo.grid(row=1, column=2, padx=5, pady=2, sticky=tk.W)
        threshold_type_combo.bind("<<ComboboxSelected>>", lambda e: self.on_threshold_change())
        
        # Frame para parámetros de Blur
        self.blur_frame = ttk.LabelFrame(controls_frame, padding="5")
        self.blur_frame.pack(fill=tk.X, pady=5)
        
        # Kernel Size
        ttk.Label(self.blur_frame, text="Kernel Size:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.blur_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Kernel Size (Tamaño del Kernel): Tamaño de la matriz de convolución para el blur Gaussiano. " +
                "Debe ser impar (1, 3, 5, 7, 9, 11, 13, 15, etc.). El valor se ajusta automáticamente para ser impar. " +
                "Kernels más grandes producen más desenfoque y suavizado. " +
                "Valores típicos: 3-15. Kernel 3x3 = suave, 5x5 = medio, 9x9+ = muy suave. " +
                "Kernels muy grandes pueden difuminar demasiado la imagen.")
        kernel_scale = ttk.Scale(self.blur_frame, from_=1, to=31, variable=self.blur_kernel_size, 
                                orient=tk.HORIZONTAL, length=200, command=self.on_blur_change)
        kernel_scale.grid(row=0, column=2, padx=5, pady=2)
        kernel_scale.configure(command=lambda v: self.on_blur_kernel_change(v))
        ttk.Label(self.blur_frame, textvariable=self.blur_kernel_size).grid(row=0, column=3, padx=5, pady=2)
        
        # Sigma X
        ttk.Label(self.blur_frame, text="Sigma X:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        info_label = ttk.Label(self.blur_frame, text="ℹ", width=2, cursor="hand2")
        info_label.grid(row=1, column=1, padx=2, pady=2, sticky=tk.W)
        ToolTip(info_label, "Sigma X (Desviación Estándar): Controla la distribución del blur Gaussiano en dirección X. " +
                "Si es 0, se calcula automáticamente basado en el tamaño del kernel (sigma ≈ kernel_size/6). " +
                "Valores más altos producen más desenfoque y una distribución más amplia del filtro. " +
                "Valores típicos: 0-5. Sigma 0 = automático (recomendado), " +
                "Sigma 1-2 = suave, Sigma 3-5 = muy suave. " +
                "Ajustar manualmente permite control fino del grado de desenfoque.")
        ttk.Scale(self.blur_frame, from_=0.0, to=10.0, variable=self.blur_sigma_x, 
                 orient=tk.HORIZONTAL, length=200, command=self.on_blur_change).grid(row=1, column=2, padx=5, pady=2)
        sigma_label = ttk.Label(self.blur_frame, text="")
        sigma_label.grid(row=1, column=3, padx=5, pady=2)
        # Actualizar label de sigma
        def update_sigma_label(*args):
            sigma_label.config(text=f"{self.blur_sigma_x.get():.1f}")
        self.blur_sigma_x.trace_add("write", lambda *args: update_sigma_label())
        update_sigma_label()
        
        # Botón de salida centrado al final (crear pero no empaquetar aún)
        self.exit_frame = ttk.Frame(controls_frame)
        self.exit_button = ttk.Button(self.exit_frame, text="Salir", command=self.on_closing)
        self.exit_button.pack()
        
        # Inicializar visibilidad de frames
        self.update_controls_visibility()
        self.update_mode_description()
        
        # Empaquetar el botón de salida al final
        self.exit_frame.pack(fill=tk.X, pady=10)
        
    def adjust_window_size(self):
        """Ajusta el tamaño de la ventana al tamaño de la imagen más los controles"""
        # Actualizar la ventana para obtener el tamaño real de los controles
        self.root.update_idletasks()
        
        # Obtener dimensiones de la pantalla
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calcular el tamaño total de la ventana
        padding_h = 40  # padding horizontal
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
            "original": "Muestra el video de la webcam sin ningún procesamiento. " +
                        "Este es el modo predeterminado que muestra la imagen tal como la captura la cámara, " +
                        "preservando todos los colores y detalles originales.",
            "binary": "Aplica binarización (threshold) a la imagen. " +
                     "Primero convierte la imagen a escala de grises, luego aplica un umbral para crear una imagen binaria. " +
                     "Los píxeles con intensidad mayor al threshold se convierten en blanco (255), " +
                     "los menores se convierten en negro (0). Este proceso es útil para segmentación y detección de objetos.",
            "blur": "Aplica un filtro de desenfoque Gaussiano a la imagen. " +
                   "El blur Gaussiano suaviza la imagen mediante convolución con un kernel Gaussiano, " +
                   "reduciendo el ruido y los detalles finos. El grado de desenfoque se controla mediante " +
                   "el tamaño del kernel y la desviación estándar (sigma).",
            "binary_blur": "Pipeline de procesamiento: primero aplica blur Gaussiano y luego binarización. " +
                          "Este orden permite suavizar la imagen antes de aplicar el threshold, " +
                          "resultando en bordes más limpios y menos ruido en la imagen binaria final. " +
                          "Es útil para mejorar la calidad de la segmentación."
        }
        
        self.mode_description_label.config(text=descriptions.get(self.mode, ""))
        
    def update_controls_visibility(self):
        # Mostrar/ocultar frames de parámetros según el modo
        if self.mode == "binary" or self.mode == "binary_blur":
            self.binary_frame.pack(fill=tk.X, pady=5, before=self.exit_frame)
        else:
            self.binary_frame.pack_forget()
            
        if self.mode == "blur" or self.mode == "binary_blur":
            self.blur_frame.pack(fill=tk.X, pady=5, before=self.exit_frame)
        else:
            self.blur_frame.pack_forget()
        
        # Asegurar que el botón de salida esté siempre al final
        self.exit_frame.pack(fill=tk.X, pady=10)
        
        # Actualizar scrollregion después de cambiar visibilidad
        self.root.after(10, lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            
    def on_threshold_change(self, value=None):
        # Se actualiza automáticamente en update_frame
        pass
        
    def on_blur_kernel_change(self, value):
        # Asegurar que el kernel sea impar
        kernel_val = int(float(value))
        if kernel_val % 2 == 0:
            kernel_val += 1
        if kernel_val > 31:
            kernel_val = 31
        if kernel_val < 1:
            kernel_val = 1
        self.blur_kernel_size.set(kernel_val)
        self.on_blur_change()
        
    def on_blur_change(self, value=None):
        # Se actualiza automáticamente en update_frame
        pass
        
    def process_frame(self, frame):
        """Procesa el frame según el modo actual y los parámetros"""
        if self.mode == "original":
            return frame
        elif self.mode == "binary":
            # Convertir a escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Aplicar threshold
            threshold_type_map = {
                "BINARY": cv2.THRESH_BINARY,
                "BINARY_INV": cv2.THRESH_BINARY_INV,
                "TRUNC": cv2.THRESH_TRUNC,
                "TOZERO": cv2.THRESH_TOZERO,
                "TOZERO_INV": cv2.THRESH_TOZERO_INV
            }
            _, binary = cv2.threshold(gray, self.threshold_value.get(), 255, threshold_type_map[self.threshold_type.get()])
            return binary
        elif self.mode == "blur":
            # Aplicar blur Gaussiano
            kernel_size = self.blur_kernel_size.get()
            # Asegurar que sea impar
            if kernel_size % 2 == 0:
                kernel_size += 1
            if kernel_size < 1:
                kernel_size = 1
            if kernel_size > 31:
                kernel_size = 31
            sigma_x = self.blur_sigma_x.get()
            blurred = cv2.GaussianBlur(frame, (kernel_size, kernel_size), sigma_x)
            return blurred
        elif self.mode == "binary_blur":
            # Pipeline: primero blur, luego binarización
            # Aplicar blur
            kernel_size = self.blur_kernel_size.get()
            if kernel_size % 2 == 0:
                kernel_size += 1
            if kernel_size < 1:
                kernel_size = 1
            if kernel_size > 31:
                kernel_size = 31
            sigma_x = self.blur_sigma_x.get()
            blurred = cv2.GaussianBlur(frame, (kernel_size, kernel_size), sigma_x)
            # Convertir a escala de grises
            gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
            # Aplicar threshold
            threshold_type_map = {
                "BINARY": cv2.THRESH_BINARY,
                "BINARY_INV": cv2.THRESH_BINARY_INV,
                "TRUNC": cv2.THRESH_TRUNC,
                "TOZERO": cv2.THRESH_TOZERO,
                "TOZERO_INV": cv2.THRESH_TOZERO_INV
            }
            _, binary = cv2.threshold(gray, self.threshold_value.get(), 255, threshold_type_map[self.threshold_type.get()])
            return binary
        
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
            if len(processed.shape) == 2:  # Escala de grises o binaria
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
            if self.mode == "binary" or self.mode == "binary_blur":
                mode_text += f" | Threshold: {self.threshold_value.get()}"
            if self.mode == "blur" or self.mode == "binary_blur":
                mode_text += f" | Kernel: {self.blur_kernel_size.get()} | Sigma: {self.blur_sigma_x.get():.1f}"
            
            # Mostrar información en la ventana
            self.root.title(f"Filtros en Tiempo Real - {mode_text}")
        
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
    app = FiltersRealtimeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

