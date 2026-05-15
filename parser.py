import glob
import inquirer  # type: ignore[import-untyped]


dir_path = glob.glob('maps/**/*.txt')
question = [
    inquirer.List(
        'Choose a file',
        message='which file would like to try?',
        choices=dir_path,
    )
]
answer = inquirer.prompt(question)

print(answer)

