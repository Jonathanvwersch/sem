class CodeLocation:
    def __init__(self, file_path: str, start_line: int, end_line: int, score: float):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.score = score
