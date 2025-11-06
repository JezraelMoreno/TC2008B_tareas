from mesa import Model
from mesa.discrete_space import OrthogonalMooreGrid
from .agent import Cell


class ConwaysGameOfLife(Model):
    """
    Autómata celular 2D que se actualiza de arriba hacia abajo
    usando las tres celdas superiores (mapeo tipo Regla 90).
    La fila superior se inicializa aleatoriamente y actúa como semilla
    para calcular en secuencia las filas inferiores.
    """
    def __init__(self, width=50, height=50, initial_fraction_alive=0.2, seed=None):
        """Crea un área de (width, height) celdas.
        - Solo la fila superior (y==height-1) se inicializa aleatoriamente
          con `initial_fraction_alive`.
        - El resto de las filas inicia muerta.
        - Grid sin wrap (torus=False); fuera de límites se considera muerto.
        """
        super().__init__(seed=seed)

        self.width = width
        self.height = height
        # Grid sin wrap
        self.grid = OrthogonalMooreGrid((width, height), capacity=1, torus=False)
        # Crea un agente por celda
        self.agent_at = {}

        for cell in self.grid.all_cells:
            x, y = cell.coordinate
            init_state = (
                Cell.ALIVE if (y == self.height - 1 and self.random.random() < initial_fraction_alive) else Cell.DEAD
            )
            agent = Cell(self, cell, init_state=init_state)
            self.agent_at[(x, y)] = agent

      
        self._next_row_to_fill = self.height - 2
        self.running = True

    def step(self):
        """
        Crea una nueva fila por tick usando las tres celdas superiores (visual arriba → abajo).
        La fila superior (y==height-1) es la semilla y no cambia. Bordes cuentan como 0 (muerto).
        """
        # Mapeo de tres celdas superiores = nuevo estado
        rule_map = {
            (1, 1, 1): 0,
            (1, 1, 0): 1,
            (1, 0, 1): 0,
            (1, 0, 0): 1,
            (0, 1, 1): 1,
            (0, 1, 0): 0,
            (0, 0, 1): 1,
            (0, 0, 0): 0,
        }
        if not hasattr(self, "_next_row_to_fill"):
            self._next_row_to_fill = self.height - 2
        if self._next_row_to_fill < 0:
            self.running = False
            return

        y = self._next_row_to_fill
        for x in range(self.width):
            sl, sm, sr = (
                (self.agent_at.get((x - 1, y + 1)).state if self.agent_at.get((x - 1, y + 1)) else Cell.DEAD),
                (self.agent_at.get((x, y + 1)).state if self.agent_at.get((x, y + 1)) else Cell.DEAD),
                (self.agent_at.get((x + 1, y + 1)).state if self.agent_at.get((x + 1, y + 1)) else Cell.DEAD),
            )
            new_state = rule_map[(sl, sm, sr)]
            self.agent_at[(x, y)].state = new_state

        self._next_row_to_fill -= 1
        self.running = self._next_row_to_fill >= 0
