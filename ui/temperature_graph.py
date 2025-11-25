import tkinter as tk
from collections import deque

class TemperatureGraph(tk.Canvas):
    def __init__(self, parent, theme_colors, **kwargs):
        super().__init__(parent, **kwargs)
        self.colors = theme_colors
        self.configure(bg=self.colors['background'], highlightthickness=0)
        self.temperatures = deque(maxlen=20)  # 20 points * 3s interval = 60 seconds
        self.bind("<Configure>", self.draw_graph)

    def add_temperature(self, temp):
        self.temperatures.append(temp)
        self.draw_graph()

    def draw_graph(self, event=None):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()

        if not self.temperatures:
            return

        padding_left = 30  # Space for labels
        graph_width = width - padding_left

        max_temp = max(self.temperatures) if self.temperatures else 100
        min_temp = min(self.temperatures) if self.temperatures else 0

        # Add some padding
        max_temp_display = max_temp + 5
        min_temp_display = max(0, min_temp - 5)

        temp_range = max_temp_display - min_temp_display
        if temp_range == 0: temp_range = 1

        # Draw labels
        self.create_text(padding_left - 5, 5, text=f"{max_temp_display}°C", anchor="ne", fill=self.colors['foreground'])
        self.create_text(padding_left - 5, height - 5, text=f"{min_temp_display}°C", anchor="se", fill=self.colors['foreground'])

        # Current temperature display
        current_temp = self.temperatures[-1]
        self.create_text(width - 5, 5, text=f"Now: {current_temp}°C", anchor="ne", fill=self.colors['foreground'])

        points = []
        for i, temp in enumerate(self.temperatures):
            x = padding_left + (i / (len(self.temperatures) - 1 if len(self.temperatures) > 1 else 1)) * graph_width
            y = height - ((temp - min_temp_display) / temp_range) * height
            points.append((x, y))

        if len(points) > 1:
            self.create_line(points, fill=self.colors['line'], width=2)
