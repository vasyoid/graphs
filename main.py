from dataclasses import dataclass

import pygame


WIDTH = 1100
HEIGHT = 720
TOOLBAR_HEIGHT = 76
FPS = 60

VERTEX_RADIUS = 24
EDGE_WIDTH = 3
ARROW_SIZE = 14

BG = (246, 248, 251)
CANVAS = (255, 255, 255)
CANVAS_BORDER = (213, 220, 230)
TEXT = (34, 40, 49)
MUTED = (92, 103, 115)
BLUE = (54, 109, 232)
BLUE_DARK = (30, 80, 190)
RED = (219, 73, 73)
GREEN = (61, 150, 97)
EDGE = (45, 52, 62)
VERTEX = (255, 255, 255)
VERTEX_BORDER = (45, 98, 210)
SELECTED = (255, 204, 92)
BUTTON = (233, 238, 246)
BUTTON_HOVER = (222, 229, 241)
BUTTON_ACTIVE = (205, 219, 248)


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: str


class GraphApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Graph Canvas")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 18)
        self.small_font = pygame.font.SysFont("arial", 14)
        self.vertex_font = pygame.font.SysFont("arial", 22, bold=True)

        self.vertices: list[pygame.Vector2] = []
        self.edges: list[tuple[int, int]] = []
        self.directed = False
        self.mode = "add"
        self.selected_vertex: int | None = None
        self.dragging_vertex: int | None = None
        self.mouse_pos = pygame.Vector2(0, 0)

        self.buttons = self.create_buttons()

    def create_buttons(self) -> list[Button]:
        specs = [
            ("Add vertex", "add"),
            ("Move", "move"),
            ("Add edge", "edge"),
            ("Remove", "remove"),
            ("Directed: off", "toggle_directed"),
            ("Clear", "clear"),
        ]
        buttons: list[Button] = []
        x = 18
        for label, action in specs:
            width = 132 if action != "toggle_directed" else 154
            buttons.append(Button(pygame.Rect(x, 18, width, 40), label, action))
            x += width + 10
        return buttons

    def run(self) -> None:
        running = True
        while running:
            self.mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_mouse_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging_vertex = None
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key_down(event.key)

            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

    def handle_key_down(self, key: int) -> None:
        if key == pygame.K_a:
            self.set_mode("add")
        elif key == pygame.K_m:
            self.set_mode("move")
        elif key == pygame.K_e:
            self.set_mode("edge")
        elif key in (pygame.K_DELETE, pygame.K_BACKSPACE, pygame.K_r):
            self.set_mode("remove")
        elif key == pygame.K_d:
            self.toggle_directed()
        elif key == pygame.K_ESCAPE:
            self.selected_vertex = None
            self.dragging_vertex = None

    def handle_mouse_down(self, pos: tuple[int, int]) -> None:
        clicked_button = self.button_at(pos)
        if clicked_button is not None:
            self.handle_button(clicked_button)
            return

        if not self.in_canvas(pos):
            return

        vertex_index = self.vertex_at(pos)
        if self.mode == "add":
            if vertex_index is None:
                self.vertices.append(pygame.Vector2(pos))
        elif self.mode == "move":
            if vertex_index is not None:
                self.dragging_vertex = vertex_index
        elif self.mode == "remove":
            if vertex_index is not None:
                self.remove_vertex(vertex_index)
        elif self.mode == "edge":
            if vertex_index is not None:
                self.handle_edge_click(vertex_index)

    def handle_mouse_motion(self, pos: tuple[int, int]) -> None:
        if self.dragging_vertex is None:
            return

        x = min(max(pos[0], VERTEX_RADIUS), WIDTH - VERTEX_RADIUS)
        y = min(max(pos[1], TOOLBAR_HEIGHT + VERTEX_RADIUS), HEIGHT - VERTEX_RADIUS)
        self.vertices[self.dragging_vertex] = pygame.Vector2(x, y)

    def handle_button(self, button: Button) -> None:
        if button.action in {"add", "move", "edge", "remove"}:
            self.set_mode(button.action)
        elif button.action == "toggle_directed":
            self.toggle_directed()
        elif button.action == "clear":
            self.vertices.clear()
            self.edges.clear()
            self.selected_vertex = None
            self.dragging_vertex = None

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.selected_vertex = None
        self.dragging_vertex = None

    def toggle_directed(self) -> None:
        self.directed = not self.directed
        self.buttons[4].label = f"Directed: {'on' if self.directed else 'off'}"
        if not self.directed:
            self.edges = self.deduplicate_undirected_edges(self.edges)
        self.selected_vertex = None

    def handle_edge_click(self, vertex_index: int) -> None:
        if self.selected_vertex is None:
            self.selected_vertex = vertex_index
            return

        start = self.selected_vertex
        end = vertex_index
        self.selected_vertex = None

        if start == end:
            return

        edge = (start, end) if self.directed else self.normalized_edge(start, end)
        if edge not in self.edges:
            self.edges.append(edge)

    def remove_vertex(self, vertex_index: int) -> None:
        del self.vertices[vertex_index]

        next_edges: list[tuple[int, int]] = []
        for start, end in self.edges:
            if start == vertex_index or end == vertex_index:
                continue
            new_start = start - 1 if start > vertex_index else start
            new_end = end - 1 if end > vertex_index else end
            next_edges.append((new_start, new_end))

        self.edges = (
            next_edges if self.directed else self.deduplicate_undirected_edges(next_edges)
        )
        self.selected_vertex = None
        self.dragging_vertex = None

    def draw(self) -> None:
        self.screen.fill(BG)
        self.draw_toolbar()
        self.draw_canvas()
        self.draw_edges()
        self.draw_vertices()
        self.draw_status()
        pygame.display.flip()

    def draw_toolbar(self) -> None:
        pygame.draw.rect(self.screen, BG, (0, 0, WIDTH, TOOLBAR_HEIGHT))
        for button in self.buttons:
            is_active = button.action == self.mode
            is_hovered = button.rect.collidepoint(self.mouse_pos)
            color = BUTTON_ACTIVE if is_active else BUTTON_HOVER if is_hovered else BUTTON
            pygame.draw.rect(self.screen, color, button.rect, border_radius=8)
            pygame.draw.rect(self.screen, CANVAS_BORDER, button.rect, 1, border_radius=8)
            label = self.font.render(button.label, True, TEXT)
            self.screen.blit(label, label.get_rect(center=button.rect.center))

    def draw_canvas(self) -> None:
        canvas_rect = pygame.Rect(0, TOOLBAR_HEIGHT, WIDTH, HEIGHT - TOOLBAR_HEIGHT)
        pygame.draw.rect(self.screen, CANVAS, canvas_rect)
        pygame.draw.line(
            self.screen, CANVAS_BORDER, (0, TOOLBAR_HEIGHT), (WIDTH, TOOLBAR_HEIGHT), 1
        )

    def draw_edges(self) -> None:
        for start, end in self.edges:
            if start >= len(self.vertices) or end >= len(self.vertices):
                continue
            self.draw_edge(self.vertices[start], self.vertices[end])

    def draw_edge(self, start: pygame.Vector2, end: pygame.Vector2) -> None:
        direction = end - start
        if direction.length_squared() == 0:
            return

        unit = direction.normalize()
        line_start = start + unit * VERTEX_RADIUS
        line_end = end - unit * VERTEX_RADIUS
        pygame.draw.line(self.screen, EDGE, line_start, line_end, EDGE_WIDTH)

        if self.directed:
            self.draw_arrow_head(line_end, unit)

    def draw_arrow_head(self, tip: pygame.Vector2, unit: pygame.Vector2) -> None:
        left = unit.rotate(150) * ARROW_SIZE
        right = unit.rotate(-150) * ARROW_SIZE
        points = [tip, tip + left, tip + right]
        pygame.draw.polygon(self.screen, EDGE, points)

    def draw_vertices(self) -> None:
        for index, position in enumerate(self.vertices):
            fill = SELECTED if index == self.selected_vertex else VERTEX
            border = BLUE_DARK if index == self.selected_vertex else VERTEX_BORDER
            pygame.draw.circle(self.screen, fill, position, VERTEX_RADIUS)
            pygame.draw.circle(self.screen, border, position, VERTEX_RADIUS, 3)

            text = self.vertex_font.render(str(index + 1), True, TEXT)
            self.screen.blit(text, text.get_rect(center=position))

    def draw_status(self) -> None:
        hints = {
            "add": "Click empty canvas space to add a numbered vertex.",
            "move": "Drag a vertex to move it.",
            "edge": "Click two vertices to add an edge.",
            "remove": "Click a vertex to remove it; remaining vertices renumber automatically.",
        }
        orientation = "directed" if self.directed else "undirected"
        text = (
            f"Mode: {self.mode} | Graph: {orientation} | "
            f"Vertices: {len(self.vertices)} | Edges: {len(self.edges)}"
        )
        status = self.small_font.render(text, True, MUTED)
        hint = self.small_font.render(hints[self.mode], True, MUTED)
        self.screen.blit(status, (18, HEIGHT - 46))
        self.screen.blit(hint, (18, HEIGHT - 24))

    def button_at(self, pos: tuple[int, int]) -> Button | None:
        for button in self.buttons:
            if button.rect.collidepoint(pos):
                return button
        return None

    def vertex_at(self, pos: tuple[int, int]) -> int | None:
        point = pygame.Vector2(pos)
        for index in range(len(self.vertices) - 1, -1, -1):
            if point.distance_to(self.vertices[index]) <= VERTEX_RADIUS:
                return index
        return None

    @staticmethod
    def in_canvas(pos: tuple[int, int]) -> bool:
        return TOOLBAR_HEIGHT <= pos[1] <= HEIGHT

    @staticmethod
    def normalized_edge(start: int, end: int) -> tuple[int, int]:
        return (start, end) if start < end else (end, start)

    def deduplicate_undirected_edges(
        self, edges: list[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        seen: set[tuple[int, int]] = set()
        result: list[tuple[int, int]] = []
        for start, end in edges:
            edge = self.normalized_edge(start, end)
            if edge not in seen:
                seen.add(edge)
                result.append(edge)
        return result


if __name__ == "__main__":
    GraphApp().run()
