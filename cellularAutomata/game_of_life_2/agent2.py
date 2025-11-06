from mesa.discrete_space import FixedAgent


class Cell(FixedAgent):
    """Representa una celda viva o muerta actualizada en paralelo."""

    DEAD = 0
    ALIVE = 1

    @property
    def x(self):
        return self.cell.coordinate[0]

    @property
    def y(self):
        return self.cell.coordinate[1]

    def __init__(self, model, cell, init_state=DEAD):
        super().__init__(model)
        self.cell = cell
        self.pos = cell.coordinate
        self.state = init_state
        self._next_state = None

    def determine_state(self):
        """Calcula el próximo estado usando snapshot y 3 vecinos superiores."""
        snap = self.model.prev_state
        width = self.model.grid.dimensions[0]
        height = self.model.grid.dimensions[1]

        x, y = self.x, self.y

        # Coordenadas de la fila superior con wrap-around
        ny = (y - 1) % height
        lx = (x - 1) % width
        rx = (x + 1) % width

        # Estados de (izquierda, centro, derecha) en la fila superior
        left = snap[ny][lx]
        mid = snap[ny][x]
        right = snap[ny][rx]

        # Aplica la regla de transición definida en el modelo
        self._next_state = self.model.rule_map[(left, mid, right)]

    def assume_state(self):
        """Aplica el nuevo estado previamente calculado."""
        self.state = self._next_state
