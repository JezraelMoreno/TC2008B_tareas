from mesa import Model
from mesa.discrete_space import OrthogonalMooreGrid
from .agent2 import Cell


class ConwaysGameOfLife(Model):
    """
    Autómata celular 2D con actualización paralela (snapshot)
    usando los 3 vecinos superiores (izquierda, centro, derecha)
    y una tabla de transiciones.
    """

    def __init__(self, width=50, height=50, initial_fraction_alive=0.3, seed=None):
        """Crea el grid y coloca celdas vivas/muertas aleatoriamente."""
        super().__init__(seed=seed)
        self.width = width
        self.height = height

        self.grid = OrthogonalMooreGrid((width, height), capacity=1, torus=True)

        # Inicializa un agente por celda con estado aleatorio
        for cell in self.grid.all_cells:
            alive = 1 if self.random.random() < initial_fraction_alive else 0
            Cell(self, cell, init_state=alive)

        # Tabla de transición sacada de la tarea
        self.rule_map = {
            (1, 1, 1): 0,
            (1, 1, 0): 1,
            (1, 0, 1): 0,
            (1, 0, 0): 1,
            (0, 1, 1): 1,
            (0, 1, 0): 0,
            (0, 0, 1): 1,
            (0, 0, 0): 0,
        }

        self.prev_state = None
        self.running = True

    def _take_snapshot(self):
        """Copia el estado actual a una matriz 2D (snapshot)."""
        width = self.grid.dimensions[0]
        height = self.grid.dimensions[1]
        snap = [[0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                agents = self.grid[(x, y)].agents
                snap[y][x] = agents[0].state if agents else 0
        self.prev_state = snap

    def step(self):
        """Actualiza todas las celdas en paralelo usando snapshot."""
        # Toma snapshot global
        self._take_snapshot()

        width = self.grid.dimensions[0]
        height = self.grid.dimensions[1]

        #calcular los nuevos estados
        for y in range(height):
            for x in range(width):
                cell = self.grid[(x, y)]
                if cell.agents:
                    cell.agents[0].determine_state()

        #aplicar simultáneamente los nuevos estados
        for y in range(height):
            for x in range(width):
                cell = self.grid[(x, y)]
                if cell.agents:
                    cell.agents[0].assume_state()
