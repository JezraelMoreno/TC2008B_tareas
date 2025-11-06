from mesa.discrete_space import FixedAgent

class Cell(FixedAgent):
    """Representa una celda viva o muerta en la simulación."""

    DEAD = 0
    ALIVE = 1

    @property
    def x(self):
        return self.cell.coordinate[0]

    @property
    def y(self):
        return self.cell.coordinate[1]

    @property
    def is_alive(self):
        return self.state == self.ALIVE

    @property
    def neighbors(self):
        # Vecinos del grid 
        return self.cell.neighborhood.agents
    
    def __init__(self, model, cell, init_state=DEAD):
        """Inicializa la celda en la posición dada con el estado indicado."""
        super().__init__(model)
        self.cell = cell
        self.pos = cell.coordinate
        self.state = init_state
        self._next_state = None

    def determine_state(self):
        """Calcula el siguiente estado según los vecinos vivos (reglas de Conway)."""
        # Cuenta vecinos vivos y aplica reglas de sobrepoblación y nacimiento
        live_neighbors = sum(neighbor.is_alive for neighbor in self.neighbors)

        self._next_state = self.state

        if self.is_alive:
            if live_neighbors < 2 or live_neighbors > 3:
                self._next_state = self.DEAD
        else:
            if live_neighbors == 3:
                self._next_state = self.ALIVE

    def assume_state(self):
        """Aplica el estado previamente calculado en determine_state()."""
        self.state = self._next_state
