import tkinter as tk
from collections import deque

class TemperatureGraph(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg='#202020', highlightthickness=0)
        self.temperatures = deque(maxlen=20) # 20 points * 3s interval = 60 seconds
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

        max_temp = max(self.temperatures) if self.temperatures else 100
        min_temp = min(self.temperatures) if self.temperatures else 0

        # Add some padding
        max_temp += 5
        min_temp = max(0, min_temp - 5)

        temp_range = max_temp - min_temp
        if temp_range == 0:
            temp_range = 1

        points = []
        for i, temp in enumerate(self.temperatures):
            x = (i / (len(self.temperatures) -1 if len(self.temperatures) > 1 else 1)) * width
            y = height - ((temp - min_temp) / temp_range) * height
            points.append((x, y))

        if len(points) > 1:
            self.create_line(points, fill="#00ff00", width=2)
