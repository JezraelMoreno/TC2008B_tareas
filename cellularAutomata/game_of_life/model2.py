from mesa import Model
from mesa.discrete_space import OrthogonalMooreGrid
from .agent import Cell


class ConwaysGameOfLife(Model):
    """
    2D cellular automaton updated top-down using the three cells above
    each position (Rule 90 mapping). The top row is initialized randomly
    and remains the seed for computing the rows below in sequence.
    """
    def __init__(self, width=50, height=50, initial_fraction_alive=0.2, seed=None):
        """Create a new playing area of (width, height) cells.
        - Only the top row (y==height-1) is initialized randomly using
          `initial_fraction_alive`.
        - Remaining rows start DEAD.
        - Grid does not wrap (torus=False); out-of-bounds neighbors are DEAD.
        """
        super().__init__(seed=seed)

        """Grid where cells are connected to their 8 neighbors.

        Example for two dimensions:
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            ( 0, -1),          ( 0, 1),
            ( 1, -1), ( 1, 0), ( 1, 1),
        ]
        """
        self.width = width
        self.height = height
        # Non-wrapping grid; we only look at cells above, so edges are DEAD
        self.grid = OrthogonalMooreGrid((width, height), capacity=1, torus=False)

        # Coordinate -> agent lookup for fast access
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
        Create one new row per tick using the three cells above it (visual top → bottom).
        The top row (y==height-1) is the initial seed and never changes. Edges are DEAD (0).
        """
    
        def get_above_states(x, y_minus_1):
            left = self.agent_at.get((x - 1, y_minus_1))
            mid = self.agent_at.get((x, y_minus_1))
            right = self.agent_at.get((x + 1, y_minus_1))
            sl = left.state if left is not None else Cell.DEAD
            sm = mid.state if mid is not None else Cell.DEAD
            sr = right.state if right is not None else Cell.DEAD
            return sl, sm, sr
        # Rule mapping for the three above cells to new state
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
