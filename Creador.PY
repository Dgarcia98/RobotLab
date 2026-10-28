
import copy
import json
import math
from pathlib import Path
import tkinter as tk

from tkinter import (
    colorchooser,
    filedialog,
    messagebox,
    simpledialog
)

from PIL import Image, ImageDraw

from shapely import affinity
from shapely.geometry import (
    Point, Polygon, LineString, box,
    mapping, shape
)
from shapely.ops import split, unary_union


# ==========================================
# CONFIGURACION GENERAL
# ==========================================

FONDO = "#f5f7fb"
PANEL_COLOR = "#1c2637"
BOTON_COLOR = "#e6ebf2"


def partes(geometria):
    """Obtiene los poligonos de una geometria."""

    if geometria.is_empty:
        return []

    if geometria.geom_type == "Polygon":
        return (
            [geometria]
            if geometria.area > 0.01
            else []
        )

    if hasattr(geometria, "geoms"):
        resultado = []

        for g in geometria.geoms:
            resultado.extend(partes(g))

        return resultado

    return []


# ==========================================
# EDITOR PRINCIPAL
# ==========================================

class Editor:

    def __init__(self):

        self.root = tk.Tk()
        self.root.title(
            "EDITOR DE OBJETOS - SIMULADOR"
        )
        self.root.geometry("1250x790")
        self.root.minsize(780, 480)

        # Objetos y seleccion
        self.elementos = []
        self.seleccion = []
        self.grupo_siguiente = 1

        # Herramienta actual
        self.modo = "seleccionar"

        # Propiedades predeterminadas
        self.color = "#e84646"
        self.borde_color = "#000000"
        self.borde_grosor = 3

        # Vista
        self.zoom = 1.0
        self.offset = [75.0, 70.0]

        # Dibujo y movimiento
        self.inicio = None
        self.ultimo = None
        self.mouse_actual = None
        self.puntos_poligono = []

        self.moviendo = False
        self.movio = False

        # Historial
        self.historial = []

        self.crear_interfaz()
        self.configurar_eventos()

        self.cambiar_modo("seleccionar")

        self.root.mainloop()

    # ======================================
    # INTERFAZ
    # ======================================

    def crear_interfaz(self):

        # ==================================
        # PANEL LATERAL
        # ==================================

        self.lateral = tk.Frame(
            self.root,
            bg=PANEL_COLOR,
            width=265
        )

        self.lateral.pack(
            side="left",
            fill="y"
        )

        self.lateral.pack_propagate(False)

        # ==================================
        # BOTON FIJO DE GUARDAR
        # ==================================

        # Se coloca antes del panel desplazable
        # para que siempre quede visible.

        zona_guardar = tk.Frame(
            self.lateral,
            bg=PANEL_COLOR
        )

        zona_guardar.pack(
            side="bottom",
            fill="x"
        )

        tk.Frame(
            zona_guardar,
            bg="#53627a",
            height=1
        ).pack(
            fill="x",
            padx=8,
            pady=(7, 4)
        )

        self.boton_guardar = tk.Button(
            zona_guardar,
            text="GUARDAR Y EXPORTAR",
            command=self.guardar,
            bg="#20a66b",
            fg="white",
            activebackground="#168352",
            activeforeground="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            pady=12,
            cursor="hand2"
        )

        self.boton_guardar.pack(
            fill="x",
            padx=8,
            pady=(4, 9)
        )

        # ==================================
        # BARRA VERTICAL
        # ==================================

        self.barra = tk.Scrollbar(
            self.lateral,
            orient="vertical",
            width=18
        )

        self.barra.pack(
            side="right",
            fill="y"
        )

        # ==================================
        # LIENZO DE OPCIONES DESPLAZABLE
        # ==================================

        self.scroll_canvas = tk.Canvas(
            self.lateral,
            bg=PANEL_COLOR,
            highlightthickness=0,
            yscrollcommand=self.barra.set
        )

        self.scroll_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.barra.config(
            command=self.scroll_canvas.yview
        )

        # Contenedor de todas las opciones
        panel = tk.Frame(
            self.scroll_canvas,
            bg=PANEL_COLOR
        )

        self.panel = panel

        self.ventana_panel = (
            self.scroll_canvas.create_window(
                (0, 0),
                window=panel,
                anchor="nw"
            )
        )

        # Actualizar altura desplazable
        panel.bind(
            "<Configure>",
            self.actualizar_region_scroll
        )

        # Adaptar el ancho
        self.scroll_canvas.bind(
            "<Configure>",
            self.ajustar_ancho_panel
        )

        # ==================================
        # TITULO
        # ==================================

        tk.Label(
            panel,
            text="EDITOR DE OBJETOS",
            bg=PANEL_COLOR,
            fg="white",
            font=("Arial", 13, "bold")
        ).pack(
            pady=(16, 12)
        )

        self.etiqueta_modo = tk.Label(
            panel,
            text="",
            bg="#314158",
            fg="white",
            font=("Arial", 10, "bold"),
            pady=9
        )

        self.etiqueta_modo.pack(
            fill="x",
            padx=8,
            pady=6
        )

        # ==================================
        # HERRAMIENTAS GEOMETRICAS
        # ==================================

        self.titulo_panel(
            panel,
            "FIGURAS GEOMETRICAS"
        )

        herramientas = [
            ("V  Seleccionar / mover", "seleccionar"),
            ("R  Rectangulo", "rectangulo"),
            ("O  Circulo / elipse", "elipse"),
            ("T  Triangulo", "triangulo"),
            ("P  Poligono", "poligono"),
            ("K  Cortar con linea", "cortar"),
        ]

        for titulo, modo in herramientas:

            self.boton(
                panel,
                titulo,
                lambda m=modo: self.cambiar_modo(m)
            )

        self.separador(panel)

        # ==================================
        # COLORES Y BORDES
        # ==================================

        self.titulo_panel(
            panel,
            "COLORES Y BORDES"
        )

        self.boton(
            panel,
            "Color de relleno",
            self.elegir_color
        )

        self.boton(
            panel,
            "Color del borde",
            self.elegir_color_borde
        )

        self.boton(
            panel,
            "Grosor del borde",
            self.cambiar_grosor_borde
        )

        self.boton(
            panel,
            "Quitar borde",
            self.quitar_borde
        )

        self.info_borde = tk.Label(
            panel,
            text="",
            bg=PANEL_COLOR,
            fg="white",
            font=("Consolas", 10),
            justify="left",
            wraplength=230
        )

        self.info_borde.pack(
            fill="x",
            padx=12,
            pady=8
        )

        self.actualizar_info_borde()

        self.separador(panel)

        # ==================================
        # OPERACIONES
        # ==================================

        self.titulo_panel(
            panel,
            "OPERACIONES"
        )

        operaciones = [
            (
                "Cambiar ancho / alto",
                self.dimensionar
            ),
            (
                "Agrupar (Ctrl+G)",
                self.agrupar
            ),
            (
                "Desagrupar",
                self.desagrupar
            ),
            (
                "Unir siluetas (Ctrl+U)",
                self.unir
            ),
            (
                "Restar figuras",
                self.restar
            ),
            (
                "Duplicar",
                self.duplicar
            ),
            (
                "Eliminar (Supr)",
                self.eliminar
            ),
            (
                "Deshacer (Ctrl+Z)",
                self.deshacer
            ),
        ]

        for titulo, funcion in operaciones:
            self.boton(
                panel,
                titulo,
                funcion
            )

        self.separador(panel)

        # ==================================
        # ARCHIVOS
        # ==================================

        self.titulo_panel(
            panel,
            "PROYECTOS"
        )

        self.boton(
            panel,
            "Nuevo diseno",
            self.nuevo
        )

        self.boton(
            panel,
            "Abrir proyecto",
            self.abrir
        )

        # Boton adicional dentro de la lista
        self.boton(
            panel,
            "Guardar (Ctrl+S)",
            self.guardar
        )

        tk.Label(
            panel,
            text=(
                "Usa la barra vertical o la rueda "
                "del mouse para recorrer las opciones."
            ),
            bg=PANEL_COLOR,
            fg="#b8c7dc",
            font=("Arial", 9),
            wraplength=220
        ).pack(
            padx=12,
            pady=16
        )

        # ==================================
        # ZONA DERECHA
        # ==================================

        derecha = tk.Frame(
            self.root,
            bg=FONDO
        )

        derecha.pack(
            side="right",
            expand=True,
            fill="both"
        )

        self.estado = tk.Label(
            derecha,
            text="",
            anchor="w",
            bg="#e3e9f1",
            font=("Consolas", 10),
            padx=8,
            pady=8
        )

        self.estado.pack(
            side="bottom",
            fill="x"
        )

        self.canvas = tk.Canvas(
            derecha,
            bg=FONDO,
            highlightthickness=0
        )

        self.canvas.pack(
            fill="both",
            expand=True
        )

    def boton(self, panel, texto, comando):

        tk.Button(
            panel,
            text=texto,
            command=comando,
            bg=BOTON_COLOR,
            fg="#182235",
            relief="flat",
            padx=5,
            pady=6,
            cursor="hand2"
        ).pack(
            fill="x",
            padx=10,
            pady=2
        )

    def separador(self, panel):

        tk.Frame(
            panel,
            bg="#526076",
            height=1
        ).pack(
            fill="x",
            padx=10,
            pady=10
        )

    def titulo_panel(self, panel, texto):

        tk.Label(
            panel,
            text=texto,
            bg=PANEL_COLOR,
            fg="#88d8ff",
            font=("Arial", 10, "bold")
        ).pack(
            pady=(8, 7)
        )

    # ======================================
    # SCROLL DEL PANEL LATERAL
    # ======================================

    def actualizar_region_scroll(self, evento=None):

        self.scroll_canvas.configure(
            scrollregion=self.scroll_canvas.bbox("all")
        )

    def ajustar_ancho_panel(self, evento):

        self.scroll_canvas.itemconfigure(
            self.ventana_panel,
            width=evento.width
        )

    def mouse_sobre_panel(self, evento):

        widget = self.root.winfo_containing(
            evento.x_root,
            evento.y_root
        )

        # Buscar si el widget pertenece
        # al panel lateral
        while widget is not None:

            if widget == self.lateral:
                return True

            widget = widget.master

        return False

    def scroll_lateral(self, evento):

        if not self.mouse_sobre_panel(evento):
            return None

        if evento.num == 4:
            unidades = -3

        elif evento.num == 5:
            unidades = 3

        else:
            unidades = (
                -3 if evento.delta > 0 else 3
            )

        self.scroll_canvas.yview_scroll(
            unidades,
            "units"
        )

        return "break"

    # ======================================
    # EVENTOS Y ATAJOS
    # ======================================

    def configurar_eventos(self):

        # Mouse del area de dibujo
        self.canvas.bind(
            "<ButtonPress-1>",
            self.presionar
        )

        self.canvas.bind(
            "<B1-Motion>",
            self.arrastrar
        )

        self.canvas.bind(
            "<ButtonRelease-1>",
            self.soltar
        )

        self.canvas.bind(
            "<Motion>",
            self.mover_mouse
        )

        self.canvas.bind(
            "<Button-3>",
            lambda e: self.terminar_poligono()
        )

        self.canvas.bind(
            "<ButtonPress-2>",
            self.iniciar_pan
        )

        self.canvas.bind(
            "<B2-Motion>",
            self.hacer_pan
        )

        self.canvas.bind(
            "<MouseWheel>",
            self.rueda
        )

        self.canvas.bind(
            "<Button-4>",
            lambda e: self.zoom_mouse(e, 1.15)
        )

        self.canvas.bind(
            "<Button-5>",
            lambda e: self.zoom_mouse(e, 1 / 1.15)
        )

        self.canvas.bind(
            "<Configure>",
            lambda e: self.dibujar()
        )

        # Rueda sobre botones, etiquetas
        # y cualquier parte del panel izquierdo
        self.root.bind_all(
            "<MouseWheel>",
            self.scroll_lateral,
            add="+"
        )

        self.root.bind_all(
            "<Button-4>",
            self.scroll_lateral,
            add="+"
        )

        self.root.bind_all(
            "<Button-5>",
            self.scroll_lateral,
            add="+"
        )

        self.root.bind(
            "<Return>",
            lambda e: self.terminar_poligono()
        )

        self.root.bind(
            "<Escape>",
            lambda e: self.cancelar()
        )

        self.root.bind(
            "<Delete>",
            lambda e: self.eliminar()
        )

        self.root.bind(
            "<Control-z>",
            lambda e: self.deshacer()
        )

        self.root.bind(
            "<Control-g>",
            lambda e: self.agrupar()
        )

        self.root.bind(
            "<Control-u>",
            lambda e: self.unir()
        )

        self.root.bind(
            "<Control-s>",
            lambda e: self.guardar()
        )

        self.root.bind(
            "<Control-o>",
            lambda e: self.abrir()
        )

        atajos = [
            ("v", "seleccionar"),
            ("r", "rectangulo"),
            ("o", "elipse"),
            ("t", "triangulo"),
            ("p", "poligono"),
            ("k", "cortar")
        ]

        for tecla, modo in atajos:

            self.root.bind(
                tecla,
                lambda e, m=modo: self.cambiar_modo(m)
            )

        for tecla, dx, dy in [
            ("Left", -1, 0),
            ("Right", 1, 0),
            ("Up", 0, -1),
            ("Down", 0, 1)
        ]:

            self.root.bind(
                "<" + tecla + ">",
                lambda e, x=dx, y=dy: self.nudge(
                    x, y, e
                )
            )

    # ======================================
    # UTILIDADES
    # ======================================

    def aviso(self, texto):
        self.estado.config(text=texto)

    def punto(self, x, y):

        return (
            (x - self.offset[0]) / self.zoom,
            (y - self.offset[1]) / self.zoom
        )

    def pantalla(self, x, y):

        return (
            x * self.zoom + self.offset[0],
            y * self.zoom + self.offset[1]
        )

    def registrar(self):

        self.historial.append((
            copy.deepcopy(self.elementos),
            list(self.seleccion),
            self.grupo_siguiente
        ))

        if len(self.historial) > 35:
            self.historial.pop(0)

    def deshacer(self):

        if not self.historial:
            return

        (
            self.elementos,
            self.seleccion,
            self.grupo_siguiente
        ) = self.historial.pop()

        self.dibujar()

    def nuevo_elemento(self, geometria):

        return {
            "geo": geometria,
            "color": self.color,
            "grupo": None,
            "borde_color": self.borde_color,
            "borde_grosor": self.borde_grosor
        }

    def cambiar_modo(self, modo):

        self.modo = modo
        self.inicio = None
        self.puntos_poligono = []

        self.etiqueta_modo.config(
            text="MODO: " + modo.upper()
        )

        self.dibujar()

    def figuras_de(self, indice):

        grupo = self.elementos[indice]["grupo"]

        if grupo is None:
            return [indice]

        return [
            i for i, el in enumerate(self.elementos)
            if el["grupo"] == grupo
        ]

    # ======================================
    # CONFIGURAR COLORES Y BORDES
    # ======================================

    def actualizar_info_borde(self):

        self.info_borde.config(
            text=(
                f"Relleno: {self.color}\n"
                f"Borde: {self.borde_color}\n"
                f"Grosor: {self.borde_grosor} px"
            )
        )

    def elegir_color(self):

        resultado = colorchooser.askcolor(
            color=self.color,
            title="Color de relleno",
            parent=self.root
        )

        if not resultado[1]:
            return

        self.color = resultado[1]

        if self.seleccion:
            self.registrar()

            for i in self.seleccion:
                self.elementos[i]["color"] = (
                    self.color
                )

        self.actualizar_info_borde()
        self.dibujar()

    def elegir_color_borde(self):

        resultado = colorchooser.askcolor(
            color=self.borde_color,
            title="Color del borde",
            parent=self.root
        )

        if not resultado[1]:
            return

        self.borde_color = resultado[1]

        if self.seleccion:
            self.registrar()

            for i in self.seleccion:
                self.elementos[i]["borde_color"] = (
                    self.borde_color
                )

        self.actualizar_info_borde()
        self.dibujar()

    def cambiar_grosor_borde(self):

        grosor = simpledialog.askinteger(
            "Grosor del borde",
            "Grosor en pixeles (0 = sin borde):",
            initialvalue=self.borde_grosor,
            minvalue=0,
            maxvalue=200,
            parent=self.root
        )

        if grosor is None:
            return

        self.borde_grosor = grosor

        if self.seleccion:
            self.registrar()

            for i in self.seleccion:
                self.elementos[i]["borde_grosor"] = (
                    grosor
                )

        self.actualizar_info_borde()
        self.dibujar()

    def quitar_borde(self):

        self.borde_grosor = 0

        if self.seleccion:
            self.registrar()

            for i in self.seleccion:
                self.elementos[i]["borde_grosor"] = 0

        self.actualizar_info_borde()
        self.dibujar()

    # ======================================
    # SELECCIONAR FIGURAS
    # ======================================

    def seleccionar_en(self, pos, multi=False):

        objetivo = Point(pos)
        encontrado = None

        for i in reversed(range(len(self.elementos))):

            geometria = self.elementos[i]["geo"]

            if geometria.buffer(
                5 / self.zoom
            ).covers(objetivo):

                encontrado = i
                break

        if encontrado is None:

            if not multi:
                self.seleccion = []

            return None

        indices = self.figuras_de(encontrado)

        if multi:

            if all(
                j in self.seleccion
                for j in indices
            ):

                self.seleccion = [
                    j for j in self.seleccion
                    if j not in indices
                ]

            else:

                self.seleccion.extend(
                    j for j in indices
                    if j not in self.seleccion
                )

        elif encontrado not in self.seleccion:

            self.seleccion = indices

        return encontrado

    # ======================================
    # MOUSE: PRESIONAR
    # ======================================

    def presionar(self, evento):

        pos = self.punto(
            evento.x, evento.y
        )

        if self.modo == "seleccionar":

            elegido = self.seleccionar_en(
                pos,
                bool(evento.state & 0x0001)
            )

            self.moviendo = (
                elegido is not None
                and elegido in self.seleccion
            )

            self.movio = False
            self.ultimo = pos

        elif self.modo == "poligono":

            self.puntos_poligono.append(pos)

        else:

            self.inicio = pos
            self.ultimo = pos

        self.dibujar()

    # ======================================
    # MOUSE: ARRASTRAR
    # ======================================

    def arrastrar(self, evento):

        pos = self.punto(
            evento.x, evento.y
        )

        if (
            self.modo == "seleccionar"
            and self.moviendo
        ):

            dx = pos[0] - self.ultimo[0]
            dy = pos[1] - self.ultimo[1]

            if abs(dx) + abs(dy) > 0:

                if not self.movio:
                    self.registrar()
                    self.movio = True

                for j in self.seleccion:

                    geo = self.elementos[j]["geo"]

                    self.elementos[j]["geo"] = (
                        affinity.translate(
                            geo,
                            xoff=dx,
                            yoff=dy
                        )
                    )

            self.ultimo = pos

        else:
            self.ultimo = pos

        self.dibujar()

    # ======================================
    # MOUSE: SOLTAR
    # ======================================

    def soltar(self, evento):

        pos = self.punto(
            evento.x, evento.y
        )

        if (
            self.modo in (
                "rectangulo",
                "elipse",
                "triangulo"
            )
            and self.inicio is not None
        ):

            geo = self.crear_figura(
                self.modo,
                self.inicio,
                pos
            )

            if geo is not None and geo.area > 2:

                self.registrar()

                self.elementos.append(
                    self.nuevo_elemento(geo)
                )

                self.seleccion = [
                    len(self.elementos) - 1
                ]

        elif (
            self.modo == "cortar"
            and self.inicio is not None
        ):

            self.cortar(
                self.inicio,
                pos
            )

        self.inicio = None
        self.moviendo = False

        self.dibujar()

    def mover_mouse(self, evento):

        self.mouse_actual = self.punto(
            evento.x, evento.y
        )

        if (
            self.modo == "poligono"
            and self.puntos_poligono
        ):
            self.dibujar()

    # ======================================
    # CREAR FIGURAS
    # ======================================

    def crear_figura(self, modo, a, b):

        x1, x2 = sorted(
            (a[0], b[0])
        )

        y1, y2 = sorted(
            (a[1], b[1])
        )

        w = x2 - x1
        h = y2 - y1

        if w < 2 or h < 2:
            return None

        if modo == "rectangulo":

            return box(
                x1, y1, x2, y2
            )

        if modo == "triangulo":

            return Polygon([
                ((x1 + x2) / 2, y1),
                (x2, y2),
                (x1, y2)
            ])

        if modo == "elipse":

            circulo = Point(
                0, 0
            ).buffer(
                1,
                resolution=28
            )

            return affinity.translate(
                affinity.scale(
                    circulo,
                    w / 2,
                    h / 2
                ),
                xoff=(x1 + x2) / 2,
                yoff=(y1 + y2) / 2
            )

        return None

    # ======================================
    # POLIGONOS
    # ======================================

    def terminar_poligono(self):

        if (
            self.modo != "poligono"
            or len(self.puntos_poligono) < 3
        ):
            return

        geometria = Polygon(
            self.puntos_poligono
        )

        if not geometria.is_valid:
            geometria = geometria.buffer(0)

        if not partes(geometria):

            messagebox.showwarning(
                "Poligono",
                "La figura no es valida."
            )

        else:

            self.registrar()

            self.elementos.append(
                self.nuevo_elemento(geometria)
            )

            self.seleccion = [
                len(self.elementos) - 1
            ]

        self.puntos_poligono = []
        self.dibujar()

    def cancelar(self):

        self.inicio = None
        self.puntos_poligono = []

        self.dibujar()

    # ======================================
    # CORTAR UNA FIGURA
    # ======================================

    def cortar(self, a, b):

        if not self.seleccion:

            messagebox.showinfo(
                "Cortar",
                "Selecciona una figura, presiona K "
                "y dibuja una linea de corte."
            )
            return

        dx = b[0] - a[0]
        dy = b[1] - a[1]

        distancia = math.hypot(
            dx, dy
        )

        if distancia < 2:
            return

        ux = dx / distancia
        uy = dy / distancia

        largo = 100000

        linea = LineString([
            (
                a[0] - ux * largo,
                a[1] - uy * largo
            ),
            (
                b[0] + ux * largo,
                b[1] + uy * largo
            )
        ])

        reemplazos = {}
        hubo_corte = False

        for i in self.seleccion:

            el = self.elementos[i]
            piezas = []

            for geo in partes(el["geo"]):

                piezas.extend(
                    partes(
                        split(geo, linea)
                    )
                )

            if len(piezas) > len(
                partes(el["geo"])
            ):

                hubo_corte = True

                reemplazos[i] = [
                    {
                        **el,
                        "geo": pieza,
                        "grupo": None
                    }
                    for pieza in piezas
                ]

        if not hubo_corte:

            self.aviso(
                "La linea no atraveso ninguna figura."
            )
            return

        self.registrar()

        nuevos = []

        for i, el in enumerate(self.elementos):

            nuevos.extend(
                reemplazos.get(
                    i,
                    [el]
                )
            )

        self.elementos = nuevos
        self.seleccion = []

        self.aviso(
            "Corte realizado. Los bordes se conservan."
        )

    # ======================================
    # AGRUPAR
    # ======================================

    def agrupar(self):

        if len(self.seleccion) < 2:

            messagebox.showinfo(
                "Agrupar",
                "Selecciona varias figuras "
                "con Shift + clic."
            )
            return

        self.registrar()

        grupo = self.grupo_siguiente
        self.grupo_siguiente += 1

        for i in self.seleccion:

            self.elementos[i]["grupo"] = grupo

        self.aviso(
            "Figuras agrupadas correctamente."
        )

        self.dibujar()

    def desagrupar(self):

        if not self.seleccion:
            return

        self.registrar()

        for i in self.seleccion:

            self.elementos[i]["grupo"] = None

        self.dibujar()

    # ======================================
    # UNIR SILUETAS
    # ======================================

    def unir(self):

        if len(self.seleccion) < 2:

            messagebox.showinfo(
                "Unir",
                "Selecciona al menos dos figuras."
            )
            return

        self.registrar()

        indices = sorted(
            set(self.seleccion)
        )

        geometria = unary_union([
            self.elementos[i]["geo"]
            for i in indices
        ])

        base = self.elementos[indices[0]]

        nuevo = {
            "geo": geometria,
            "color": base["color"],
            "grupo": None,
            "borde_color": base.get(
                "borde_color",
                "#000000"
            ),
            "borde_grosor": base.get(
                "borde_grosor",
                0
            )
        }

        self.elementos = [
            el for i, el in enumerate(self.elementos)
            if i not in indices
        ]

        self.elementos.append(nuevo)

        self.seleccion = [
            len(self.elementos) - 1
        ]

        self.aviso(
            "Siluetas unidas en una sola geometria."
        )

        self.dibujar()

    # ======================================
    # RESTAR FIGURAS
    # ======================================

    def restar(self):

        if len(self.seleccion) != 2:

            messagebox.showinfo(
                "Restar",
                "Selecciona primero la figura base "
                "y despues la figura que corta."
            )
            return

        base, recorte = self.seleccion

        self.registrar()

        geometria = (
            self.elementos[base]["geo"]
            .difference(
                self.elementos[recorte]["geo"]
            )
        )

        nuevos = []

        for i, el in enumerate(self.elementos):

            if i == recorte:
                continue

            if i == base:

                if partes(geometria):

                    nuevos.append({
                        **el,
                        "geo": geometria,
                        "grupo": None
                    })

            else:
                nuevos.append(el)

        self.elementos = nuevos
        self.seleccion = []

        self.aviso("Recorte aplicado.")
        self.dibujar()

    # ======================================
    # CAMBIAR ANCHO Y ALTO
    # ======================================

    def dimensionar(self):

        if not self.seleccion:

            messagebox.showinfo(
                "Dimensiones",
                "Selecciona una figura o grupo."
            )
            return

        geometria = unary_union([
            self.elementos[i]["geo"]
            for i in self.seleccion
        ])

        x1, y1, x2, y2 = geometria.bounds

        ancho = simpledialog.askfloat(
            "Ancho",
            "Nuevo ancho en pixeles:",
            initialvalue=round(
                x2 - x1, 1
            ),
            minvalue=1,
            parent=self.root
        )

        if ancho is None:
            return

        alto = simpledialog.askfloat(
            "Alto",
            "Nuevo alto en pixeles:",
            initialvalue=round(
                y2 - y1, 1
            ),
            minvalue=1,
            parent=self.root
        )

        if alto is None:
            return

        self.registrar()

        for i in self.seleccion:

            self.elementos[i]["geo"] = (
                affinity.scale(
                    self.elementos[i]["geo"],
                    xfact=ancho / max(
                        .001, x2 - x1
                    ),
                    yfact=alto / max(
                        .001, y2 - y1
                    ),
                    origin=(x1, y1)
                )
            )

        self.dibujar()

    # ======================================
    # DUPLICAR
    # ======================================

    def duplicar(self):

        if not self.seleccion:
            return

        self.registrar()

        grupo = self.grupo_siguiente
        self.grupo_siguiente += 1

        nuevos = []

        agrupado = (
            len(self.seleccion) > 1
        )

        for i in self.seleccion:

            el = copy.deepcopy(
                self.elementos[i]
            )

            el["geo"] = affinity.translate(
                el["geo"],
                xoff=25,
                yoff=25
            )

            el["grupo"] = (
                grupo if agrupado else None
            )

            nuevos.append(el)

        inicio = len(self.elementos)

        self.elementos.extend(nuevos)

        self.seleccion = list(
            range(
                inicio,
                len(self.elementos)
            )
        )

        self.dibujar()

    # ======================================
    # ELIMINAR
    # ======================================

    def eliminar(self):

        if not self.seleccion:
            return

        self.registrar()

        self.elementos = [
            el for i, el in enumerate(self.elementos)
            if i not in self.seleccion
        ]

        self.seleccion = []

        self.dibujar()

    # ======================================
    # AJUSTE CON FLECHAS
    # ======================================

    def nudge(self, dx, dy, evento):

        if not self.seleccion:
            return

        paso = (
            10 if evento.state & 0x0001 else 1
        )

        self.registrar()

        for i in self.seleccion:

            self.elementos[i]["geo"] = (
                affinity.translate(
                    self.elementos[i]["geo"],
                    xoff=dx * paso,
                    yoff=dy * paso
                )
            )

        self.dibujar()

    # ======================================
    # MOVER VISTA
    # ======================================

    def iniciar_pan(self, evento):

        self.pan_ultimo = (
            evento.x,
            evento.y
        )

    def hacer_pan(self, evento):

        dx = evento.x - self.pan_ultimo[0]
        dy = evento.y - self.pan_ultimo[1]

        self.offset[0] += dx
        self.offset[1] += dy

        self.pan_ultimo = (
            evento.x,
            evento.y
        )

        self.dibujar()

    # ======================================
    # ZOOM
    # ======================================

    def zoom_mouse(self, evento, factor):

        mx, my = self.punto(
            evento.x,
            evento.y
        )

        self.zoom = max(
            .15,
            min(
                8,
                self.zoom * factor
            )
        )

        self.offset = [
            evento.x - mx * self.zoom,
            evento.y - my * self.zoom
        ]

        self.dibujar()

    def rueda(self, evento):

        factor = (
            1.15
            if evento.delta > 0
            else 1 / 1.15
        )

        self.zoom_mouse(
            evento,
            factor
        )

    # ======================================
    # DIBUJAR FIGURAS Y BORDES
    # ======================================

    def dibujar(self):

        c = self.canvas
        c.delete("all")

        ancho = c.winfo_width()
        alto = c.winfo_height()

        if ancho <= 1 or alto <= 1:
            return

        # ==================================
        # CUADRICULA
        # ==================================

        paso = 50

        xmin = math.floor(
            -self.offset[0] / self.zoom / paso
        )

        xmax = math.ceil(
            (ancho - self.offset[0]) /
            self.zoom / paso
        )

        ymin = math.floor(
            -self.offset[1] / self.zoom / paso
        )

        ymax = math.ceil(
            (alto - self.offset[1]) /
            self.zoom / paso
        )

        for k in range(xmin, xmax + 1):

            x = self.pantalla(
                k * paso, 0
            )[0]

            c.create_line(
                x, 0, x, alto,
                fill="#dbe2ec"
            )

        for k in range(ymin, ymax + 1):

            y = self.pantalla(
                0, k * paso
            )[1]

            c.create_line(
                0, y, ancho, y,
                fill="#dbe2ec"
            )

        # ==================================
        # FIGURAS
        # ==================================

        for i, el in enumerate(self.elementos):

            grosor = max(
                0,
                el.get("borde_grosor", 0)
            )

            color_borde = el.get(
                "borde_color",
                "#000000"
            )

            grosor_vista = (
                max(
                    1,
                    round(grosor * self.zoom)
                )
                if grosor > 0 else 0
            )

            for poligono in partes(el["geo"]):

                exterior = [
                    valor
                    for x, y in poligono.exterior.coords
                    for valor in self.pantalla(x, y)
                ]

                c.create_polygon(
                    exterior,
                    fill=el["color"],
                    outline=(
                        color_borde
                        if grosor > 0
                        else ""
                    ),
                    width=grosor_vista,
                    joinstyle="round"
                )

                # Agujeros del poligono
                for anillo in poligono.interiors:

                    hueco = [
                        valor
                        for x, y in anillo.coords
                        for valor in self.pantalla(x, y)
                    ]

                    c.create_polygon(
                        hueco,
                        fill=FONDO,
                        outline=(
                            color_borde
                            if grosor > 0
                            else ""
                        ),
                        width=grosor_vista,
                        joinstyle="round"
                    )

            # Recuadro de seleccion
            if i in self.seleccion:

                x1, y1, x2, y2 = (
                    el["geo"].bounds
                )

                a = self.pantalla(
                    x1, y1
                )

                b = self.pantalla(
                    x2, y2
                )

                c.create_rectangle(
                    *a,
                    *b,
                    outline="#18a36c",
                    dash=(5, 3),
                    width=2
                )

        # ==================================
        # VISTA PREVIA DE FIGURAS
        # ==================================

        if (
            self.inicio is not None
            and self.ultimo is not None
        ):

            if self.modo in (
                "rectangulo",
                "elipse",
                "triangulo"
            ):

                temporal = self.crear_figura(
                    self.modo,
                    self.inicio,
                    self.ultimo
                )

                if temporal is not None:

                    for poligono in partes(temporal):

                        puntos = [
                            valor
                            for x, y in (
                                poligono.exterior.coords
                            )
                            for valor in self.pantalla(
                                x, y
                            )
                        ]

                        c.create_polygon(
                            puntos,
                            fill="",
                            outline="#018aff",
                            dash=(4, 3),
                            width=2
                        )

            elif self.modo == "cortar":

                c.create_line(
                    *self.pantalla(
                        *self.inicio
                    ),
                    *self.pantalla(
                        *self.ultimo
                    ),
                    fill="#ef344b",
                    width=3
                )

        # ==================================
        # VISTA PREVIA DE POLIGONO LIBRE
        # ==================================

        if (
            self.modo == "poligono"
            and self.puntos_poligono
        ):

            puntos = [
                valor
                for x, y in self.puntos_poligono
                for valor in self.pantalla(x, y)
            ]

            if self.mouse_actual is not None:

                puntos += list(
                    self.pantalla(
                        *self.mouse_actual
                    )
                )

            if len(puntos) >= 4:

                c.create_line(
                    puntos,
                    fill="#018aff",
                    width=2
                )

            for x, y in self.puntos_poligono:

                px, py = self.pantalla(
                    x, y
                )

                c.create_oval(
                    px - 4, py - 4,
                    px + 4, py + 4,
                    fill="#018aff",
                    outline=""
                )

        # ==================================
        # INFORMACION INFERIOR
        # ==================================

        if self.seleccion:

            geometria = unary_union([
                self.elementos[i]["geo"]
                for i in self.seleccion
            ])

            x1, y1, x2, y2 = (
                geometria.bounds
            )

            self.aviso(
                f"{len(self.seleccion)} pieza(s) | "
                f"X={x1:.0f}, Y={y1:.0f} | "
                f"Ancho={x2-x1:.0f}, "
                f"Alto={y2-y1:.0f} | "
                f"Zoom={self.zoom:.2f}x"
            )

        else:

            self.aviso(
                f"{len(self.elementos)} pieza(s) | "
                f"Zoom={self.zoom:.2f}x | "
                "Ctrl+S para guardar"
            )

    # ======================================
    # NUEVO PROYECTO
    # ======================================

    def nuevo(self):

        if self.elementos:

            confirmar = messagebox.askyesno(
                "Nuevo",
                "¿Borrar el diseno actual sin guardar?"
            )

            if not confirmar:
                return

        self.elementos = []
        self.seleccion = []
        self.historial = []
        self.grupo_siguiente = 1

        self.dibujar()

    # ======================================
    # ABRIR PROYECTO
    # ======================================

    def abrir(self):

        ruta = filedialog.askopenfilename(
            title="Abrir proyecto editable",
            filetypes=[
                ("Proyecto JSON", "*.json")
            ]
        )

        if not ruta:
            return

        try:

            datos = json.loads(
                Path(ruta).read_text(
                    encoding="utf-8"
                )
            )

            nuevos = []

            for item in datos["elementos"]:

                nuevos.append({
                    "geo": shape(
                        item["geometria"]
                    ),
                    "color": item["color"],
                    "grupo": item.get("grupo"),
                    "borde_color": item.get(
                        "borde_color",
                        "#000000"
                    ),
                    "borde_grosor": item.get(
                        "borde_grosor",
                        0
                    )
                })

        except (
            OSError,
            ValueError,
            KeyError,
            TypeError
        ) as error:

            messagebox.showerror(
                "Error",
                f"No se pudo abrir:\n{error}"
            )
            return

        self.elementos = nuevos
        self.seleccion = []

        self.grupo_siguiente = 1 + max(
            (
                el["grupo"] or 0
                for el in nuevos
            ),
            default=0
        )

        self.historial = []

        self.dibujar()

        self.aviso(
            "Proyecto abierto correctamente."
        )

    # ======================================
    # GUARDAR PROYECTO
    # ======================================

    def guardar(self):

        if not self.elementos:

            messagebox.showinfo(
                "Guardar",
                "Dibuja al menos una figura."
            )
            return

        nombre = filedialog.asksaveasfilename(
            title="Guardar objeto",
            defaultextension=".editor.json",
            initialfile="objeto.editor.json",
            filetypes=[
                (
                    "Proyecto del editor",
                    "*.editor.json"
                )
            ]
        )

        if not nombre:
            return

        ruta = Path(nombre)

        if str(ruta).endswith(".editor.json"):

            prefijo = Path(
                str(ruta)[:-len(".editor.json")]
            )

        else:

            prefijo = ruta.with_suffix("")

        proyecto = Path(
            str(prefijo) + ".editor.json"
        )

        png = Path(
            str(prefijo) + ".png"
        )

        svg = Path(
            str(prefijo) + ".svg"
        )

        metadata = Path(
            str(prefijo) + ".json"
        )

        try:

            # =================================
            # GUARDAR PROYECTO EDITABLE
            # =================================

            elementos_json = []

            for el in self.elementos:

                elementos_json.append({
                    "geometria": mapping(
                        el["geo"]
                    ),
                    "color": el["color"],
                    "grupo": el["grupo"],
                    "borde_color": el.get(
                        "borde_color",
                        "#000000"
                    ),
                    "borde_grosor": el.get(
                        "borde_grosor",
                        0
                    )
                })

            proyecto.write_text(
                json.dumps(
                    {
                        "formato": "editor_objetos_v2",
                        "elementos": elementos_json
                    },
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

            # =================================
            # DIMENSIONES DEL OBJETO
            # =================================

            geometrias = [
                poligono
                for el in self.elementos
                for poligono in partes(
                    el["geo"]
                )
            ]

            x1, y1, x2, y2 = (
                unary_union(geometrias).bounds
            )

            max_borde = max(
                el.get(
                    "borde_grosor", 0
                )
                for el in self.elementos
            )

            margen = (
                math.ceil(max_borde / 2) + 2
                if max_borde > 0
                else 0
            )

            x0 = math.floor(x1) - margen
            y0 = math.floor(y1) - margen

            ancho = max(
                1,
                math.ceil(x2) + margen - x0
            )

            alto = max(
                1,
                math.ceil(y2) + margen - y0
            )

            # Suavizado para figuras pequenas
            factor = (
                2
                if ancho * alto <= 1_500_000
                else 1
            )

            imagen = Image.new(
                "RGBA",
                (
                    ancho * factor,
                    alto * factor
                ),
                (0, 0, 0, 0)
            )

            rutas_svg = []
            detalles = []

            # =================================
            # EXPORTAR CADA PIEZA
            # =================================

            for i, el in enumerate(
                self.elementos
            ):

                normal = affinity.translate(
                    el["geo"],
                    xoff=-x0,
                    yoff=-y0
                )

                color = el["color"]

                color_borde = el.get(
                    "borde_color",
                    "#000000"
                )

                grosor = max(
                    0,
                    int(
                        el.get(
                            "borde_grosor", 0
                        )
                    )
                )

                detalles.append({
                    "id": i + 1,
                    "color": color,
                    "grupo": el["grupo"],
                    "borde_color": color_borde,
                    "borde_grosor": grosor,
                    "geometria": mapping(normal)
                })

                for poligono in partes(normal):

                    # -------------------------
                    # MASCARA PNG
                    # -------------------------

                    mascara = Image.new(
                        "L",
                        (
                            ancho * factor,
                            alto * factor
                        ),
                        0
                    )

                    dib = ImageDraw.Draw(
                        mascara
                    )

                    exterior = [
                        (
                            round(x * factor),
                            round(y * factor)
                        )
                        for x, y in (
                            poligono.exterior.coords
                        )
                    ]

                    dib.polygon(
                        exterior,
                        fill=255
                    )

                    # Huecos transparentes
                    for agujero in poligono.interiors:

                        puntos = [
                            (
                                round(x * factor),
                                round(y * factor)
                            )
                            for x, y in agujero.coords
                        ]

                        dib.polygon(
                            puntos,
                            fill=0
                        )

                    capa = Image.new(
                        "RGBA",
                        (
                            ancho * factor,
                            alto * factor
                        ),
                        color
                    )

                    capa.putalpha(mascara)

                    imagen = Image.alpha_composite(
                        imagen,
                        capa
                    )

                    # -------------------------
                    # BORDES PNG
                    # -------------------------

                    if grosor > 0:

                        capa_borde = Image.new(
                            "RGBA",
                            (
                                ancho * factor,
                                alto * factor
                            ),
                            (0, 0, 0, 0)
                        )

                        pincel = ImageDraw.Draw(
                            capa_borde
                        )

                        anillos = [
                            poligono.exterior,
                            *poligono.interiors
                        ]

                        for anillo in anillos:

                            puntos = [
                                (
                                    round(x * factor),
                                    round(y * factor)
                                )
                                for x, y in (
                                    anillo.coords
                                )
                            ]

                            pincel.line(
                                puntos,
                                fill=color_borde,
                                width=max(
                                    1,
                                    grosor * factor
                                ),
                                joint="curve"
                            )

                        imagen = Image.alpha_composite(
                            imagen,
                            capa_borde
                        )

                    # -------------------------
                    # SVG
                    # -------------------------

                    secciones = []

                    for anillo in [
                        poligono.exterior,
                        *poligono.interiors
                    ]:

                        coordenadas = list(
                            anillo.coords
                        )

                        if coordenadas:

                            comando = (
                                "M "
                                + " L ".join(
                                    f"{x:.2f} {y:.2f}"
                                    for x, y in coordenadas
                                )
                                + " Z"
                            )

                            secciones.append(
                                comando
                            )

                    ruta_svg = " ".join(
                        secciones
                    )

                    if grosor > 0:

                        atributo_borde = (
                            f'stroke="{color_borde}" '
                            f'stroke-width="{grosor}" '
                            'stroke-linejoin="round" '
                            'stroke-linecap="round" '
                        )

                    else:

                        atributo_borde = (
                            'stroke="none" '
                        )

                    rutas_svg.append(
                        f'<path d="{ruta_svg}" '
                        f'fill="{color}" '
                        'fill-rule="evenodd" '
                        f'{atributo_borde}/>'
                    )

            # =================================
            # GUARDAR PNG
            # =================================

            if factor > 1:

                imagen = imagen.resize(
                    (ancho, alto),
                    Image.Resampling.LANCZOS
                )

            imagen.save(png)

            # =================================
            # GUARDAR SVG
            # =================================

            svg.write_text(
                "\n".join([
                    (
                        '<svg '
                        'xmlns="http://www.w3.org/2000/svg" '
                        f'width="{ancho}" '
                        f'height="{alto}" '
                        f'viewBox="0 0 {ancho} {alto}">'
                    ),
                    *rutas_svg,
                    "</svg>"
                ]),
                encoding="utf-8"
            )

            # =================================
            # JSON PARA EL SIMULADOR
            # =================================

            metadata.write_text(
                json.dumps(
                    {
                        "nombre": prefijo.name,
                        "imagen": png.name,
                        "ancho": ancho,
                        "alto": alto,
                        "piezas": detalles
                    },
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )

        except (
            OSError,
            ValueError
        ) as error:

            messagebox.showerror(
                "Error al guardar",
                str(error)
            )
            return

        messagebox.showinfo(
            "Guardado correctamente",
            (
                "Objeto guardado:\n\n"
                f"{png.name}\n"
                f"{svg.name}\n"
                f"{metadata.name}\n"
                f"{proyecto.name}"
            )
        )

        self.aviso(
            "Objeto guardado y exportado correctamente."
        )


# ==========================================
# INICIAR PROGRAMA
# ==========================================

if __name__ == "__main__":
    Editor()
