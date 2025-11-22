import mesa
from mesa.discrete_space import OrthogonalMooreGrid

from .agent import ChargingStation, DirtPatch, Obstacle, RoombaAgent


def report_battery(model):
    return model.roomba.battery


def report_remaining_dirty(model):
    return model.remaining_dirty()


def report_clean_percentage(model):
    return model.clean_percentage


def report_moves(model):
    return model.moves


class RoombaModel(mesa.Model):
    """Modelo para agentes de limpieza que usan máquina de estados."""

    def __init__(
        self,
        width=12,
        height=12,
        dirt_count=25,
        obstacle_count=15,
        max_steps=300,
        seed=42,
        roomba_count=1,
    ):
        super().__init__(seed=seed)
        self.width = width
        self.height = height
        self.max_steps = max_steps
        self.moves = 0
        self.cleaned_cells = 0
        self.time_to_clean = None
        self.elapsed_steps = 0

        # Grid con capacidad >1 para permitir roomba + suciedad + estación en la misma celda
        self.grid = OrthogonalMooreGrid(
            (self.width, self.height), torus=False, capacity=3, random=self.random
        )
        self.cells = {cell.coordinate: cell for cell in self.grid}
        self._target_reservations = {}

        self.station_pos = (1, 1)
        if self.station_pos not in self.cells:
            raise ValueError("La estación de carga debe caber dentro del grid")

        # Aleatorizar la distribución
        self._place_obstacles(obstacle_count)
        self._place_dirt(dirt_count)
        self.initial_dirty = self.remaining_dirty()

        station_cell = self.cells[self.station_pos]
        ChargingStation(self, station_cell)

        self.roombas = [
            RoombaAgent(self, station_cell, self.station_pos) for _ in range(max(1, roomba_count))
        ]
        self.roomba = self.roombas[0]

        self.datacollector = mesa.DataCollector(
            {
                "bateria": report_battery,
                "suciedad_restante": report_remaining_dirty,
                "porcentaje_limpio": report_clean_percentage,
                "movimientos": report_moves,
            }
        )

        self.running = True
        if self.initial_dirty == 0:
            self.time_to_clean = 0
            self.running = False

    def _place_obstacles(self, count):
        """Colocar obstáculos aleatorios, evitando la celda de la estación."""
        available_cells = [
            cell for coord, cell in self.cells.items() if coord != self.station_pos
        ]
        self.random.shuffle(available_cells)
        for cell in available_cells[: min(count, len(available_cells))]:
            Obstacle(self, cell)

    def _place_dirt(self, count):
        """Colocar manchas de suciedad aleatorias, sin obstáculos ni estación."""
        candidate_cells = []
        for coord, cell in self.cells.items():
            if coord == self.station_pos:
                continue
            if any(isinstance(agent, Obstacle) for agent in cell.agents):
                continue
            candidate_cells.append(cell)

        self.random.shuffle(candidate_cells)
        for cell in candidate_cells[: min(count, len(candidate_cells))]:
            DirtPatch(self, cell)

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
        return (self.cleaned_cells / self.initial_dirty) * 100

    def step(self):
        if not self.running:
            return

        self.elapsed_steps += 1
        for roomba in self.roombas:
            roomba.step()
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
