import glob
import inquirer  # type: ignore[import-untyped]
from dataclasses import dataclass


@dataclass
class Parser:
    x_max: int
    y_max: int
    start: tuple[int, int]
    end: tuple[int, int]
    number_of_drone: int
    outpu_file: str

    @classmethod
    def select_file(self) -> str:
        dir_path = glob.glob("maps/**/*.txt")
        question = [
            inquirer.List(
                "Choose a file",
                message="which file would like to try?",
                choices=dir_path,
            )
        ]
        answers = inquirer.prompt(question)
        if answers:
            selected = answers["Choose a file"]

        print(f"The file  {selected} is selected")
        return selected


# def read_txt(self, selected) -> None:
#     try:
#         with open(self.selected, "r") as f:


if __name__ == "__main__":
    Parser.select_file()
