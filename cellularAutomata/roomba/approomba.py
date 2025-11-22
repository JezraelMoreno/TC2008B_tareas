from roomba import ChargingStation, DirtPatch, Obstacle, RoombaAgent, RoombaModel

from mesa.visualization import (
    CommandConsole,
    Slider,
    SolaraViz,
    make_plot_component,
    make_space_component,
)
from mesa.visualization.components import AgentPortrayalStyle


def roomba_portrayal(agent):
    if agent is None:
        return

    portrayal = AgentPortrayalStyle(size=80, marker="o", zorder=2)

    if isinstance(agent, RoombaAgent):
        portrayal.color = "deepskyblue"
        portrayal.size = 90
    elif isinstance(agent, Obstacle):
        portrayal.marker = "s"
        portrayal.color = "gray"
        portrayal.size = 120
        portrayal.zorder = 1
    elif isinstance(agent, DirtPatch):
        portrayal.marker = "s"
        portrayal.color = "saddlebrown"
        portrayal.size = 120
        portrayal.zorder = 0
    elif isinstance(agent, ChargingStation):
        portrayal.marker = "s"
        portrayal.color = "gold"
        portrayal.size = 100
        portrayal.zorder = 0
    return portrayal


def post_process(ax):
    ax.set_aspect("equal")


def post_process_lines(ax):
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.9))


model_params = {
    "seed": {"type": "InputText", "value": 42, "label": "Semilla"},
    "width": Slider("Ancho del cuarto", 12, 6, 30),
    "height": Slider("Alto del cuarto", 12, 6, 30),
    "dirt_count": Slider("Celdas sucias", 25, 1, 200, 1),
    "obstacle_count": Slider("Obstáculos", 12, 0, 150, 1),
    "max_steps": Slider("Pasos máximos", 300, 50, 800, 10),
}


model = RoombaModel(
    width=model_params["width"].value,
    height=model_params["height"].value,
    dirt_count=model_params["dirt_count"].value,
    obstacle_count=model_params["obstacle_count"].value,
    max_steps=model_params["max_steps"].value,
    seed=model_params["seed"]["value"],
)

space_component = make_space_component(
    roomba_portrayal,
    draw_grid=False,
    post_process=post_process,
)

lineplot_component = make_plot_component(
    {
        "bateria": "tab:orange",
        "suciedad_restante": "tab:red",
        "porcentaje_limpio": "tab:green",
        "movimientos": "tab:blue",
    },
    post_process=post_process_lines,
)

page = SolaraViz(
    model,
    components=[space_component, lineplot_component, CommandConsole],
    model_params=model_params,
    name="Roomba",
)
