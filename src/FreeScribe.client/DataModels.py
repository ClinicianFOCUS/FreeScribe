class WhisperModelEnum:
    def __init__(self, name, ram, vram, display):
        self.name = name
        self.ram = ram
        self.vram = vram
        self.display = display

    def __repr__(self):
        return f"WhisperModelEnum(name='{self.name}', ram={self.ram}, vram={self.vram}, display='{self.display}')"