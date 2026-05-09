from dataclasses import dataclass

import pygame

from tasks import (
    adjacency_list_to_adjacency_matrix,
    adjacency_matrix_to_adjacency_list,
    connected_components,
    depth_first_search,
    edges_list_to_adjacency_matrix,
)


WIDTH = 1100
HEIGHT = 720
TOOLBAR_HEIGHT = 76
LEFT_WIDTH = 720
PANEL_PADDING = 18
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
PANEL_BG = (241, 244, 249)
OUTPUT_BG = (255, 255, 255)
ERROR = (185, 62, 62)
DFS_ACTIVE = (255, 199, 85)
DFS_DONE = (91, 170, 113)
COMPONENT_COLORS = [
    (91, 170, 113),
    (255, 199, 85),
    (91, 141, 239),
    (224, 103, 117),
    (166, 113, 216),
    (65, 180, 176),
]


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: str


class GraphApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Редактор графов")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 18)
        self.small_font = pygame.font.SysFont("arial", 14)
        self.vertex_font = pygame.font.SysFont("arial", 22, bold=True)

        self.vertices: list[pygame.Vector2] = []
        self.edges: list[tuple[int, int]] = []
        self.directed = False
        self.mode = "edit"
        self.selected_vertex: int | None = None
        self.dragging_vertex: int | None = None
        self.drag_moved = False
        self.mouse_pos = pygame.Vector2(0, 0)
        self.selected_task = "edges_to_matrix"
        self.task_error = ""
        self.preview_edges: list[tuple[int, int]] = []
        self.preview_mode = "graph"
        self.dfs_start_vertex = 0
        self.dfs_order: list[int] = []
        self.dfs_animation_running = False
        self.dfs_visible_count = 0
        self.components: list[list[int]] = []
        self.animation_started_at = pygame.time.get_ticks()

        self.buttons = self.create_buttons()
        self.task_buttons = self.create_task_buttons()
        self.dfs_buttons = self.create_dfs_buttons()

    def create_buttons(self) -> list[Button]:
        specs = [
            ("Правка", "edit"),
            ("Удалить", "remove"),
            ("Ориент.: нет", "toggle_directed"),
            ("Очистить", "clear"),
        ]
        buttons: list[Button] = []
        x = 12
        for label, action in specs:
            width = 82
            if action == "toggle_directed":
                width = 116
            buttons.append(Button(pygame.Rect(x, 18, width, 40), label, action))
            x += width + 8
        return buttons

    def create_task_buttons(self) -> list[Button]:
        x = LEFT_WIDTH + PANEL_PADDING
        y = 82
        width = WIDTH - LEFT_WIDTH - PANEL_PADDING * 2
        labels = [
            ("Список ребер -> матрица смежности", "edges_to_matrix"),
            ("Матрица смежности -> список смежности", "matrix_to_adjacency"),
            ("Список смежности -> матрица смежности", "adjacency_to_matrix"),
            ("Поиск в глубину", "dfs"),
            ("Компоненты связности", "components"),
        ]
        return [
            Button(pygame.Rect(x, y + index * 48, width, 38), label, action)
            for index, (label, action) in enumerate(labels)
        ]

    def create_dfs_buttons(self) -> list[Button]:
        y = 322
        return [
            Button(
                pygame.Rect(WIDTH - PANEL_PADDING - 98, y, 98, 32),
                "Старт",
                "dfs_toggle",
            )
        ]

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
                    self.handle_mouse_up()
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key_down(event.key)

            self.update_preview()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

    def handle_key_down(self, key: int) -> None:
        if key == pygame.K_a:
            self.set_mode("edit")
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

        clicked_task = self.task_button_at(pos)
        if clicked_task is not None:
            if self.selected_task != clicked_task.action:
                self.animation_started_at = pygame.time.get_ticks()
                self.dfs_animation_running = False
                self.dfs_visible_count = 0
            self.selected_task = clicked_task.action
            self.selected_vertex = None
            self.dragging_vertex = None
            return

        clicked_dfs_button = self.dfs_button_at(pos)
        if clicked_dfs_button is not None:
            self.handle_dfs_button(clicked_dfs_button)
            return

        preview_vertex = self.preview_vertex_at(pos)
        if preview_vertex is not None:
            self.dfs_start_vertex = preview_vertex
            self.dfs_animation_running = False
            self.dfs_visible_count = 0
            return

        if not self.in_canvas(pos):
            return

        vertex_index = self.vertex_at(pos)
        if self.mode == "edit":
            if vertex_index is None:
                self.selected_vertex = None
                self.vertices.append(pygame.Vector2(pos))
            else:
                self.dragging_vertex = vertex_index
                self.drag_moved = False
        elif self.mode == "remove":
            if vertex_index is not None:
                self.remove_vertex(vertex_index)
            else:
                edge_index = self.edge_at(pos)
                if edge_index is not None:
                    del self.edges[edge_index]

    def handle_mouse_motion(self, pos: tuple[int, int]) -> None:
        if self.dragging_vertex is None:
            return

        x = min(max(pos[0], VERTEX_RADIUS), LEFT_WIDTH - VERTEX_RADIUS)
        y = min(max(pos[1], TOOLBAR_HEIGHT + VERTEX_RADIUS), HEIGHT - VERTEX_RADIUS)
        if self.vertices[self.dragging_vertex].distance_to((x, y)) > 2:
            self.drag_moved = True
        self.vertices[self.dragging_vertex] = pygame.Vector2(x, y)

    def handle_mouse_up(self) -> None:
        if self.mode == "edit" and self.dragging_vertex is not None:
            if not self.drag_moved:
                self.handle_edge_click(self.dragging_vertex)

        self.dragging_vertex = None
        self.drag_moved = False

    def handle_button(self, button: Button) -> None:
        if button.action in {"edit", "remove"}:
            self.set_mode(button.action)
        elif button.action == "toggle_directed":
            self.toggle_directed()
        elif button.action == "clear":
            self.vertices.clear()
            self.edges.clear()
            self.selected_vertex = None
            self.dragging_vertex = None

    def handle_dfs_button(self, button: Button) -> None:
        if not self.vertices:
            self.dfs_start_vertex = 0
            self.dfs_animation_running = False
            self.dfs_visible_count = 0
            return

        if button.action == "dfs_toggle":
            if self.dfs_animation_running:
                self.dfs_animation_running = False
                self.dfs_visible_count = 0
            else:
                self.dfs_visible_count = 0
                self.animation_started_at = pygame.time.get_ticks()
                self.dfs_animation_running = True

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.selected_vertex = None
        self.dragging_vertex = None
        self.drag_moved = False

    def toggle_directed(self) -> None:
        self.directed = not self.directed
        self.buttons[2].label = f"Ориент.: {'да' if self.directed else 'нет'}"
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
        self.draw_right_panel()
        self.draw_status()
        pygame.display.flip()

    def draw_toolbar(self) -> None:
        pygame.draw.rect(self.screen, BG, (0, 0, WIDTH, TOOLBAR_HEIGHT))
        pygame.draw.rect(self.screen, PANEL_BG, (LEFT_WIDTH, 0, WIDTH - LEFT_WIDTH, HEIGHT))
        for button in self.buttons:
            is_active = button.action == self.mode
            is_hovered = button.rect.collidepoint(self.mouse_pos)
            color = BUTTON_ACTIVE if is_active else BUTTON_HOVER if is_hovered else BUTTON
            pygame.draw.rect(self.screen, color, button.rect, border_radius=8)
            pygame.draw.rect(self.screen, CANVAS_BORDER, button.rect, 1, border_radius=8)
            label = self.font.render(button.label, True, TEXT)
            self.screen.blit(label, label.get_rect(center=button.rect.center))

    def draw_canvas(self) -> None:
        canvas_rect = pygame.Rect(0, TOOLBAR_HEIGHT, LEFT_WIDTH, HEIGHT - TOOLBAR_HEIGHT)
        pygame.draw.rect(self.screen, CANVAS, canvas_rect)
        pygame.draw.line(
            self.screen,
            CANVAS_BORDER,
            (0, TOOLBAR_HEIGHT),
            (LEFT_WIDTH, TOOLBAR_HEIGHT),
            1,
        )
        pygame.draw.line(
            self.screen, CANVAS_BORDER, (LEFT_WIDTH, 0), (LEFT_WIDTH, HEIGHT), 1
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

            text = self.vertex_font.render(str(index), True, TEXT)
            self.screen.blit(text, text.get_rect(center=position))

    def draw_status(self) -> None:
        hints = {
            "edit": "Клик по вершине выбирает ее для ребра; пустое место добавляет вершину.",
            "remove": "Щелкните по вершине или ребру, чтобы удалить выбранный элемент.",
        }
        orientation = "ориентированный" if self.directed else "неориентированный"
        mode_names = {
            "edit": "правка",
            "remove": "удаление",
        }
        text = (
            f"Режим: {mode_names[self.mode]} | Граф: {orientation} | "
            f"Вершин: {len(self.vertices)} | Ребер: {len(self.edges)}"
        )
        status = self.small_font.render(text, True, MUTED)
        hint = self.small_font.render(hints[self.mode], True, MUTED)
        self.screen.blit(status, (18, HEIGHT - 46))
        self.screen.blit(hint, (18, HEIGHT - 24))

    def draw_right_panel(self) -> None:
        title = self.font.render("Задания для студентов", True, TEXT)
        self.screen.blit(title, (LEFT_WIDTH + PANEL_PADDING, 24))

        subtitle = self.small_font.render(
            "Выберите задание для графа слева.", True, MUTED
        )
        self.screen.blit(subtitle, (LEFT_WIDTH + PANEL_PADDING, 50))

        for button in self.task_buttons:
            is_active = button.action == self.selected_task
            is_hovered = button.rect.collidepoint(self.mouse_pos)
            color = BUTTON_ACTIVE if is_active else BUTTON_HOVER if is_hovered else BUTTON
            pygame.draw.rect(self.screen, color, button.rect, border_radius=8)
            pygame.draw.rect(self.screen, CANVAS_BORDER, button.rect, 1, border_radius=8)
            label = self.small_font.render(button.label, True, TEXT)
            self.screen.blit(label, label.get_rect(center=button.rect.center))

        if self.selected_task == "dfs":
            label = self.small_font.render(
                f"Стартовая вершина: {self.dfs_start_vertex}", True, TEXT
            )
            self.screen.blit(label, (LEFT_WIDTH + PANEL_PADDING, 330))
            for button in self.dfs_buttons:
                is_hovered = button.rect.collidepoint(self.mouse_pos)
                color = BUTTON_HOVER if is_hovered else BUTTON
                pygame.draw.rect(self.screen, color, button.rect, border_radius=8)
                pygame.draw.rect(self.screen, CANVAS_BORDER, button.rect, 1, border_radius=8)
                label = "Стоп" if button.action == "dfs_toggle" and self.dfs_animation_running else button.label
                text = self.font.render(label, True, TEXT)
                self.screen.blit(text, text.get_rect(center=button.rect.center))

        output_rect = self.preview_rect()
        pygame.draw.rect(self.screen, OUTPUT_BG, output_rect, border_radius=8)
        pygame.draw.rect(self.screen, CANVAS_BORDER, output_rect, 1, border_radius=8)

        if self.task_error:
            self.draw_wrapped_text(self.task_error, output_rect.inflate(-28, -28), ERROR)
        else:
            self.draw_preview_graph(output_rect)

        footer = self.small_font.render(
            "Реализуйте функции заданий в файле tasks.py.", True, MUTED
        )
        self.screen.blit(footer, (LEFT_WIDTH + PANEL_PADDING, HEIGHT - 44))

    def button_at(self, pos: tuple[int, int]) -> Button | None:
        for button in self.buttons:
            if button.rect.collidepoint(pos):
                return button
        return None

    def task_button_at(self, pos: tuple[int, int]) -> Button | None:
        for button in self.task_buttons:
            if button.rect.collidepoint(pos):
                return button
        return None

    def dfs_button_at(self, pos: tuple[int, int]) -> Button | None:
        if self.selected_task != "dfs":
            return None
        for button in self.dfs_buttons:
            if button.rect.collidepoint(pos):
                return button
        return None

    def preview_vertex_at(self, pos: tuple[int, int]) -> int | None:
        if self.selected_task != "dfs" or self.task_error:
            return None
        positions = self.preview_positions(self.preview_rect())
        point = pygame.Vector2(pos)
        for index in range(len(positions) - 1, -1, -1):
            if point.distance_to(positions[index]) <= VERTEX_RADIUS:
                return index
        return None

    @staticmethod
    def preview_rect() -> pygame.Rect:
        return pygame.Rect(
            LEFT_WIDTH + PANEL_PADDING,
            374,
            WIDTH - LEFT_WIDTH - PANEL_PADDING * 2,
            HEIGHT - 444,
        )

    def vertex_at(self, pos: tuple[int, int]) -> int | None:
        point = pygame.Vector2(pos)
        for index in range(len(self.vertices) - 1, -1, -1):
            if point.distance_to(self.vertices[index]) <= VERTEX_RADIUS:
                return index
        return None

    def edge_at(self, pos: tuple[int, int]) -> int | None:
        point = pygame.Vector2(pos)
        best_index = None
        best_distance = 12.0

        for index, (start, end) in enumerate(self.edges):
            if start >= len(self.vertices) or end >= len(self.vertices):
                continue

            distance = self.distance_to_segment(
                point, self.vertices[start], self.vertices[end]
            )
            if distance < best_distance:
                best_distance = distance
                best_index = index

        return best_index

    @staticmethod
    def distance_to_segment(
        point: pygame.Vector2, start: pygame.Vector2, end: pygame.Vector2
    ) -> float:
        segment = end - start
        if segment.length_squared() == 0:
            return point.distance_to(start)

        projection = (point - start).dot(segment) / segment.length_squared()
        projection = max(0.0, min(1.0, projection))
        closest = start + segment * projection
        return point.distance_to(closest)

    @staticmethod
    def in_canvas(pos: tuple[int, int]) -> bool:
        return 0 <= pos[0] < LEFT_WIDTH and TOOLBAR_HEIGHT <= pos[1] <= HEIGHT

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

    def update_preview(self) -> None:
        try:
            if self.vertices:
                self.dfs_start_vertex = min(self.dfs_start_vertex, len(self.vertices) - 1)
            else:
                self.dfs_start_vertex = 0
                self.dfs_animation_running = False
                self.dfs_visible_count = 0
            self.preview_mode = "graph"
            self.dfs_order = []
            self.components = []
            self.preview_edges = self.run_selected_task()
            if self.preview_mode == "dfs" and self.dfs_animation_running:
                visible_count = self.current_dfs_visible_count()
                if visible_count >= len(self.dfs_order):
                    self.dfs_visible_count = len(self.dfs_order)
                    self.dfs_animation_running = False
            self.task_error = ""
        except NotImplementedError as error:
            self.preview_edges = []
            self.dfs_order = []
            self.dfs_animation_running = False
            self.dfs_visible_count = 0
            self.components = []
            self.task_error = str(error)
        except (TypeError, ValueError, IndexError) as error:
            self.preview_edges = []
            self.dfs_order = []
            self.dfs_animation_running = False
            self.dfs_visible_count = 0
            self.components = []
            self.task_error = f"Выбранная функция вернула некорректные данные: {error}"

    def run_selected_task(self) -> list[tuple[int, int]]:
        vertex_count = len(self.vertices)
        edges = self.zero_based_edges()

        if self.selected_task == "edges_to_matrix":
            matrix = edges_list_to_adjacency_matrix(vertex_count, edges, self.directed)
            return self.zero_based_edges_from_adjacency_matrix(matrix, self.directed)

        if self.selected_task == "matrix_to_adjacency":
            matrix = self.build_adjacency_matrix(vertex_count, edges, self.directed)
            adjacency_list = adjacency_matrix_to_adjacency_list(matrix, self.directed)
            return self.zero_based_edges_from_adjacency_list(adjacency_list, self.directed)

        if self.selected_task == "dfs":
            adjacency_list = self.build_adjacency_list(vertex_count, edges, self.directed)
            self.dfs_order = depth_first_search(adjacency_list, self.dfs_start_vertex)
            self.validate_vertex_list(self.dfs_order, vertex_count)
            self.preview_mode = "dfs"
            return list(self.edges)

        if self.selected_task == "components":
            adjacency_list = self.build_adjacency_list(vertex_count, edges, False)
            self.components = connected_components(adjacency_list)
            self.validate_components(self.components, vertex_count)
            self.preview_mode = "components"
            return list(self.edges)

        adjacency_list = self.build_adjacency_list(vertex_count, edges, self.directed)
        matrix = adjacency_list_to_adjacency_matrix(adjacency_list, self.directed)
        return self.zero_based_edges_from_adjacency_matrix(matrix, self.directed)

    def zero_based_edges(self) -> list[tuple[int, int]]:
        return list(self.edges)

    @staticmethod
    def build_adjacency_matrix(
        vertex_count: int, edges: list[tuple[int, int]], directed: bool
    ) -> list[list[int]]:
        matrix = [[0 for _ in range(vertex_count)] for _ in range(vertex_count)]
        for start, end in edges:
            matrix[start][end] = 1
            if not directed:
                matrix[end][start] = 1
        return matrix

    @staticmethod
    def build_adjacency_list(
        vertex_count: int, edges: list[tuple[int, int]], directed: bool
    ) -> list[list[int]]:
        adjacency_list = [[] for _ in range(vertex_count)]
        for start, end in edges:
            adjacency_list[start].append(end)
            if not directed:
                adjacency_list[end].append(start)
        return adjacency_list

    def zero_based_edges_from_adjacency_list(
        self, adjacency_list: list[list[int]], directed: bool
    ) -> list[tuple[int, int]]:
        edges: list[tuple[int, int]] = []
        for start, neighbors in enumerate(adjacency_list):
            for end in neighbors:
                if not isinstance(end, int):
                    raise TypeError("значения в списке смежности должны быть целыми числами")
                edge = (start, end)
                if edge[1] < 0 or edge[1] >= len(adjacency_list):
                    raise ValueError("список смежности содержит вершину вне графа")
                edges.append(edge if directed else self.normalized_edge(*edge))
        return edges if directed else self.deduplicate_undirected_edges(edges)

    def zero_based_edges_from_adjacency_matrix(
        self, matrix: list[list[int]], directed: bool
    ) -> list[tuple[int, int]]:
        if not matrix:
            return []

        vertex_count = len(matrix)
        if any(len(row) != vertex_count for row in matrix):
            raise ValueError("матрица смежности должна быть квадратной")

        edges: list[tuple[int, int]] = []
        for start, row in enumerate(matrix):
            for end, value in enumerate(row):
                if value != 1:
                    continue
                if directed:
                    edges.append((start, end))
                elif start < end:
                    if matrix[end][start] != 1:
                        raise ValueError(
                            "матрица смежности неориентированного графа должна быть симметричной"
                        )
                    edges.append((start, end))
        return edges if directed else self.deduplicate_undirected_edges(edges)

    @staticmethod
    def validate_vertex_list(vertices: list[int], vertex_count: int) -> None:
        for vertex in vertices:
            if not isinstance(vertex, int):
                raise TypeError("номера вершин должны быть целыми числами")
            if vertex < 0 or vertex >= vertex_count:
                raise ValueError("список содержит вершину вне графа")

    def validate_components(
        self, components: list[list[int]], vertex_count: int
    ) -> None:
        seen: set[int] = set()
        for component in components:
            self.validate_vertex_list(component, vertex_count)
            for vertex in component:
                if vertex in seen:
                    raise ValueError("вершина встречается в нескольких компонентах")
                seen.add(vertex)

    def draw_preview_graph(self, rect: pygame.Rect) -> None:
        positions = self.preview_positions(rect)
        for start, end in self.preview_edges:
            if start < len(positions) and end < len(positions):
                self.draw_edge_between(positions[start], positions[end], self.directed)

        vertex_fills = self.preview_vertex_fills(len(positions))
        for index, position in enumerate(positions):
            pygame.draw.circle(self.screen, vertex_fills[index], position, VERTEX_RADIUS)
            pygame.draw.circle(self.screen, GREEN, position, VERTEX_RADIUS, 3)
            text = self.vertex_font.render(str(index), True, TEXT)
            self.screen.blit(text, text.get_rect(center=position))

        self.draw_preview_caption(rect)

    def preview_vertex_fills(self, vertex_count: int) -> list[tuple[int, int, int]]:
        fills = [VERTEX for _ in range(vertex_count)]

        if self.preview_mode == "dfs":
            visible_count = self.current_dfs_visible_count()
            visible_vertices = self.dfs_order[:visible_count]
            for vertex in visible_vertices[:-1]:
                if 0 <= vertex < vertex_count:
                    fills[vertex] = DFS_DONE
            if visible_vertices:
                active_vertex = visible_vertices[-1]
                if 0 <= active_vertex < vertex_count:
                    fills[active_vertex] = DFS_ACTIVE

        elif self.preview_mode == "components":
            for component_index, component in enumerate(self.components):
                color = COMPONENT_COLORS[component_index % len(COMPONENT_COLORS)]
                for vertex in component:
                    if 0 <= vertex < vertex_count:
                        fills[vertex] = color

        return fills

    def current_dfs_visible_count(self) -> int:
        if not self.dfs_animation_running:
            return min(self.dfs_visible_count, len(self.dfs_order))

        elapsed = pygame.time.get_ticks() - self.animation_started_at
        return min(len(self.dfs_order), elapsed // 700 + 1)

    def draw_preview_caption(self, rect: pygame.Rect) -> None:
        if self.preview_mode == "dfs":
            state = "идет" if self.dfs_animation_running else "остановлена"
            text = f"DFS ({state}): {self.dfs_order}"
        elif self.preview_mode == "components":
            text = f"Компоненты: {self.components}"
        else:
            return

        caption_rect = pygame.Rect(rect.x + 12, rect.bottom - 28, rect.width - 24, 20)
        self.draw_wrapped_text(text, caption_rect, MUTED)

    def preview_positions(self, rect: pygame.Rect) -> list[pygame.Vector2]:
        if not self.vertices:
            return []

        content_rect = rect.inflate(-VERTEX_RADIUS * 3, -VERTEX_RADIUS * 3)
        min_x = min(vertex.x for vertex in self.vertices)
        max_x = max(vertex.x for vertex in self.vertices)
        min_y = min(vertex.y for vertex in self.vertices)
        max_y = max(vertex.y for vertex in self.vertices)

        graph_width = max_x - min_x
        graph_height = max_y - min_y

        if graph_width == 0 and graph_height == 0:
            return [pygame.Vector2(content_rect.center)]

        scale_x = content_rect.width / graph_width if graph_width else float("inf")
        scale_y = content_rect.height / graph_height if graph_height else float("inf")
        scale = min(scale_x, scale_y, 1.0)

        scaled_width = graph_width * scale
        scaled_height = graph_height * scale
        offset = pygame.Vector2(
            content_rect.centerx - scaled_width / 2 - min_x * scale,
            content_rect.centery - scaled_height / 2 - min_y * scale,
        )

        return [vertex * scale + offset for vertex in self.vertices]

    def draw_edge_between(
        self, start: pygame.Vector2, end: pygame.Vector2, directed: bool
    ) -> None:
        direction = end - start
        if direction.length_squared() == 0:
            return

        unit = direction.normalize()
        line_start = start + unit * VERTEX_RADIUS
        line_end = end - unit * VERTEX_RADIUS
        pygame.draw.line(self.screen, EDGE, line_start, line_end, EDGE_WIDTH)

        if directed:
            self.draw_arrow_head(line_end, unit)

    def draw_wrapped_text(self, text: str, rect: pygame.Rect, color: tuple[int, int, int]) -> None:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if self.small_font.size(candidate)[0] <= rect.width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        y = rect.y
        for line in lines:
            surface = self.small_font.render(line, True, color)
            self.screen.blit(surface, (rect.x, y))
            y += 20


if __name__ == "__main__":
    GraphApp().run()
