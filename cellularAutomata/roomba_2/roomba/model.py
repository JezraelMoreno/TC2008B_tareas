import mesa
from mesa.discrete_space import OrthogonalMooreGrid

from .agent import ChargingStation, DirtPatch, Obstacle, RoombaAgent


def report_remaining_dirty(model):
    return model.remaining_dirty()


def report_clean_percentage(model):
    return model.clean_percentage


def make_battery_reporter(index):
    def reporter(model):
        return model.roombas[index].battery

    return reporter


def make_moves_reporter(index):
    def reporter(model):
        return model.moves[index]

    return reporter


def make_cleaned_reporter(index):
    def reporter(model):
        return model.cleaned_cells[index]

    return reporter


class RoombaModel(mesa.Model):
    """Modelo para varios agentes de limpieza que se coordinan con una máquina de estados."""

    def __init__(
        self,
        width=12,
        height=12,
        dirt_count=25,
        obstacle_count=15,
        max_steps=300,
        seed=42,
        num_agents=2,
    ):
        # Semilla None da un RNG nuevo; reiniciar debería reordenar los inicios incluso con los mismos parámetros
        super().__init__(seed=seed)
        self.reset_randomizer()
        self.width = width
        self.height = height
        self.max_steps = max_steps
        self.num_agents = num_agents
        self.moves = {i: 0 for i in range(self.num_agents)}
        self.cleaned_cells = {i: 0 for i in range(self.num_agents)}
        self.time_to_clean = None
        self.elapsed_steps = 0

        # Malla con capacidad >1 para permitir roombas + suciedad + estaciones en la misma celda
        self.grid = OrthogonalMooreGrid(
            (self.width, self.height), torus=False, capacity=4, random=self.random
        )
        self.cells = {cell.coordinate: cell for cell in self.grid}
        self._target_reservations = {}

        # Aleatorizar la distribución
        self._place_obstacles(obstacle_count)
        self._place_dirt(dirt_count)
        self.initial_dirty = self.remaining_dirty()

        # Crear agentes con sus propias estaciones base en celdas libres aleatorias
        self.roombas = []
        self.station_positions = []
        start_cells = self._pick_random_start_cells(self.num_agents)
        for idx, cell in enumerate(start_cells):
            ChargingStation(self, cell)
            self.station_positions.append(cell.coordinate)
            agent = RoombaAgent(self, cell, cell.coordinate, agent_id=idx)
            self.roombas.append(agent)

        # Recolectar estadísticas globales y por agente
        model_reporters = {
            "suciedad_restante": report_remaining_dirty,
            "porcentaje_limpio": report_clean_percentage,
        }
        for idx, agent in enumerate(self.roombas):
            model_reporters[f"bateria_{idx}"] = make_battery_reporter(idx)
            model_reporters[f"movimientos_{idx}"] = make_moves_reporter(idx)
            model_reporters[f"limpio_por_{idx}"] = make_cleaned_reporter(idx)

        self.datacollector = mesa.DataCollector(model_reporters)

        self.running = True
        if self.initial_dirty == 0:
            self.time_to_clean = 0
            self.running = False

    def _place_obstacles(self, count):
        """Colocar obstáculos aleatorios."""
        available_cells = list(self.cells.values())
        self.random.shuffle(available_cells)
        for cell in available_cells[: min(count, len(available_cells))]:
            Obstacle(self, cell)

    def _place_dirt(self, count):
        """Colocar manchas de suciedad aleatorias, sin obstáculos ni estación."""
        candidate_cells = []
        for coord, cell in self.cells.items():
            if any(isinstance(agent, Obstacle) for agent in cell.agents):
                continue
            candidate_cells.append(cell)

        self.random.shuffle(candidate_cells)
        for cell in candidate_cells[: min(count, len(candidate_cells))]:
            DirtPatch(self, cell)

    def _pick_random_start_cells(self, count):
        """Elegir celdas aleatorias sin obstáculos para iniciar estaciones o agentes."""
        free_cells = [
            cell
            for cell in self.grid
            if all(not isinstance(a, Obstacle) for a in cell.agents)
            and all(not isinstance(a, DirtPatch) for a in cell.agents)
        ]
        if len(free_cells) < count:
            raise ValueError("No hay celdas suficientes para iniciar los agentes.")
        self.random.shuffle(free_cells)
        return free_cells[:count]

    def remaining_dirty(self):
        """Número de celdas sucias que siguen presentes."""
        total = 0
        for agent in self.agents:
            if isinstance(agent, DirtPatch) and agent.dirty:
                total += 1
        return total

    def closest_dirty(self, origin):
        """Coordenadas de la mancha sucia más cercana al origen."""
        closest_position = None
        closest_distance = None

        for agent in self.agents:
            if isinstance(agent, DirtPatch) and agent.dirty:
                position = agent.cell.coordinate
                distance = abs(position[0] - origin[0]) + abs(position[1] - origin[1])
                if closest_distance is None or distance < closest_distance:
                    closest_distance = distance
                    closest_position = position

        return closest_position

    @property
    def clean_percentage(self):
        if self.initial_dirty == 0:
            return 100.0
        total_cleaned = sum(self.cleaned_cells.values())
        return (total_cleaned / self.initial_dirty) * 100

    def step(self):
        if not self.running:
            return

        self.elapsed_steps += 1
        # Cada roomba actúa de forma independiente
        for agent in self.roombas:
            agent.step()
        self.datacollector.collect(self)

        # Detener cuando todo esté limpio
        if self.remaining_dirty() == 0 and self.time_to_clean is None:
            self.time_to_clean = self.elapsed_steps
            self.running = False

        # Detener al llegar al tiempo máximo
        if self.max_steps is not None and self.elapsed_steps >= self.max_steps:
            self.running = False

        # Detener si el agente se queda sin energía
        if all(roomba.battery <= 0 for roomba in self.roombas):
            self.running = False

    def reserve_target(self, agent, coordinate):
        """Evitar que varios agentes seleccionen el mismo objetivo."""
        if coordinate in self._target_reservations.values():
            return False
        self._target_reservations[agent] = coordinate
        return True

    def release_target(self, agent):
        """Liberar la reserva de un agente."""
        self._target_reservations.pop(agent, None)
