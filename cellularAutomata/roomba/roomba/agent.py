"""Definiciones de agentes y estados para la simulación de Roomba con máquina de estados."""

from mesa.discrete_space import CellAgent, FixedAgent


class Obstacle(FixedAgent):
    """Obstáculo simple para bloquear el movimiento."""

    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell

    def step(self):
        pass


class ChargingStation(FixedAgent):
    """Marca la ubicación de carga."""

    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell

    def step(self):
        pass


class DirtPatch(FixedAgent):
    """Mancha de suciedad que se debe limpiar."""

    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell
        self.dirty = True

    def clean(self):
        self.dirty = False
        self.remove()

    def step(self):
        pass


class TaskType:
    """Tipo de objetivo que puede seguir la Roomba."""

    # Constantes simples
    CLEANING = "cleaning"
    RETURNING = "returning"


class RoombaState:
    """Clase base para cada estado usado por la Roomba."""

    name = "base"

    def __init__(self, agent):
        self.agent = agent

    def on_enter(self):
        """Acción que se ejecuta al entrar a este estado."""

    def step(self):
        """Ejecuta el comportamiento asociado a este estado."""
        raise NotImplementedError


class ScanState(RoombaState):
    """Escanear toda la malla para decidir qué hacer."""

    name = "scan"

    def step(self):
        agent = self.agent

        if agent.battery <= 0:
            return

        # Escanear toda la malla antes de decidir el siguiente objetivo
        snapshot = agent.scan_environment()

        if agent.needs_recharge():
            if agent.set_target(agent.station_pos, TaskType.RETURNING):
                agent.change_state(NavigateState)
            else:
                agent.change_state(IdleState)
            return

        if snapshot["dirty_cells"]:
            if agent.select_dirty_target(snapshot["dirty_cells"]):
                agent.change_state(NavigateState)
                return

        # Cargar si ya no hay suciedad
        if agent.at_station:
            if agent.battery < agent.max_battery:
                agent.change_state(RechargeState)
            else:
                agent.change_state(IdleState)
            return

        if agent.set_target(agent.station_pos, TaskType.RETURNING):
            agent.change_state(NavigateState)
        else:
            agent.change_state(IdleState)


class NavigateState(RoombaState):
    """Moverse un paso hacia el objetivo asignado."""

    name = "navigate"

    def step(self):
        agent = self.agent

        if agent.target is None or agent.intent is None:
            agent.change_state(ScanState)
            return

        if agent.cell.coordinate == agent.target:
            if agent.intent == TaskType.CLEANING:
                agent.change_state(CleanState)
            elif agent.intent == TaskType.RETURNING:
                agent.change_state(RechargeState)
            else:
                agent.change_state(ScanState)
            return

        # Movimiento usando heurística Manhattan
        moved = agent._move_towards(agent.target)
        if not moved:
            # Reevaluar si está bloqueado
            agent.change_state(ScanState)


class CleanState(RoombaState):
    """Limpiar la suciedad en la celda actual."""

    name = "clean"

    def on_enter(self):
        # Liberar el objetivo reservado cuando empieza la limpieza
        self.agent.clear_target()

    def step(self):
        agent = self.agent
        agent.clean_current_cell()
        agent.change_state(ScanState)


class RechargeState(RoombaState):
    """Recargar en la estación hasta tener tarea o batería llena."""

    name = "recharge"

    def on_enter(self):
        self.agent.clear_target()

    def step(self):
        agent = self.agent

        if not agent.at_station:
            agent.change_state(ScanState)
            return

        # Recargar poco a poco mientras está en la estación
        agent.recharge()
        if agent.battery >= agent.max_battery:
            if agent.model.remaining_dirty() == 0:
                agent.change_state(IdleState)
            else:
                agent.change_state(ScanState)


class IdleState(RoombaState):
    """Sin tareas pendientes. Esperar en la estación."""

    name = "idle"

    def step(self):
        agent = self.agent
        if agent.model.remaining_dirty() > 0:
            agent.change_state(ScanState)
            return

        if agent.at_station and agent.battery < agent.max_battery:
            # Mantener la batería llena cuando no hay tareas
            agent.recharge()


class RoombaAgent(CellAgent):
    """Agente aspiradora implementado como máquina de estados."""

    max_battery = 100

    def __init__(self, model, cell, station_pos, return_threshold=20):
        super().__init__(model)
        self.cell = cell
        self.station_pos = station_pos
        self.return_threshold = return_threshold
        self.battery = self.max_battery

        # Variables de la máquina de estados
        self.intent = None
        self.target = None
        self.known_dirty = []

        # Reutilizar instancias de estado para no crearlas en cada paso
        self._cached_states = {}
        self.current_state = self._get_state(ScanState)
        self.current_state.on_enter()

    def _get_state(self, state_cls):
        if state_cls not in self._cached_states:
            self._cached_states[state_cls] = state_cls(self)
        return self._cached_states[state_cls]

    def change_state(self, state_cls):
        self.current_state = self._get_state(state_cls)
        self.current_state.on_enter()

    def _blocked(self, cell):
        """Revisa si una celda objetivo está bloqueada por obstáculos."""
        return any(isinstance(agent, Obstacle) for agent in cell.agents)

    def _valid_neighbors(self):
        """Vecinos a los que la Roomba puede moverse."""
        neighbors = []
        for neighbor in self.cell.neighborhood:
            if not self._blocked(neighbor):
                neighbors.append(neighbor)
        return neighbors

    @staticmethod
    def _manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _move_towards(self, target):
        """Mover un paso hacia una coordenada objetivo (Manhattan voraz)."""
        if target is None:
            return False

        candidates = self._valid_neighbors()
        if len(candidates) == 0:
            return False

        best_distance = None
        best_cells = []
        for cell in candidates:
            dist = self._manhattan(cell.coordinate, target)
            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_cells = [cell]
            elif dist == best_distance:
                best_cells.append(cell)

        if best_cells:
            chosen = self.random.choice(best_cells)
            self.cell = chosen
            self.model.moves += 1
            self._drain()
            return True
        return False

    def _drain(self):
        """Consumir una unidad de batería por acción."""
        if self.battery > 0:
            self.battery = max(self.battery - 1, 0)

    @property
    def at_station(self) -> bool:
        return self.cell.coordinate == self.station_pos

    def needs_recharge(self) -> bool:
        """Decide si el agente debe regresar a la estación."""
        # Si la batería está debajo del umbral, volver antes de seguir limpiando
        return (self.battery <= self.return_threshold and not self.at_station) or self.battery <= 0

    def clear_target(self):
        """Liberar la reserva del objetivo actual."""
        # Evitar que dos agentes reserven la misma celda
        self.model.release_target(self)
        self.target = None
        self.intent = None

    def set_target(self, coordinate, task):
        """Intentar reservar una coordenada objetivo para una tarea."""
        self.clear_target()
        if coordinate is None:
            return True

        if self.model.reserve_target(self, coordinate):
            self.target = coordinate
            self.intent = task
            return True

        return False

    def scan_environment(self):
        """Revisar cada celda y crear una foto del cuarto."""
        dirty_cells = []
        obstacles = []

        for coord, cell in self.model.cells.items():
            if any(isinstance(agent, Obstacle) for agent in cell.agents):
                obstacles.append(coord)
            if any(isinstance(agent, DirtPatch) and agent.dirty for agent in cell.agents):
                dirty_cells.append(coord)

        # Guardar el mapa de suciedad para analizarlo en el siguiente paso
        self.known_dirty = dirty_cells
        return {
            "dirty_cells": dirty_cells,
            "obstacles": obstacles,
        }

    def select_dirty_target(self, dirty_cells):
        """Reservar la celda sucia más cercana que esté libre."""
        ordered = list(dirty_cells)

        def distance_key(pos):
            return self._manhattan(self.cell.coordinate, pos)

        ordered.sort(key=distance_key)
        for coordinate in ordered:
            # Intentar reservar la celda sucia disponible más cercana
            if self.set_target(coordinate, TaskType.CLEANING):
                return coordinate
        return None

    def clean_current_cell(self) -> bool:
        """Limpiar la suciedad en la celda actual si existe."""
        dirt = [a for a in self.cell.agents if isinstance(a, DirtPatch) and a.dirty]
        if dirt:
            dirt[0].clean()
            self.model.cleaned_cells += 1
            self._drain()
            return True
        return False

    def recharge(self):
        """Recargar mientras está en la estación."""
        if self.at_station:
            self.battery = min(self.max_battery, self.battery + 5)

    def step(self):
        if self.battery <= 0:
            return

        self.current_state.step()
