import glob
import inquirer  # type: ignore[import-untyped]

<TO DO> make as Class 
dir_path = glob.glob('maps/**/*.txt')
question = [
    inquirer.List(
        'Choose a file',
        message='which file would like to try?',
        choices=dir_path,
    )
]
answers = inquirer.prompt(question)

print(answers)
if answers:
    selected_file = str(answers['Choose a file'])
print(f"Choosen file path is: {selected_file}")

# • The first line defines the number of drones using nb_drones:
# <number>.
# • Zone definition on each line using type prefixes:
# ◦ start_hub:
# ◦ end_hub:
# ◦ hub:
# <name> <x> <y> [metadata] marks the starting zone.
# <name> <x> <y> [metadata] marks the end zone.
# <name> <x> <y> [metadata] defines a regular zone.
# ◦ The connection syntax forbids dashes in zone names (see below).
# • All metadata is optional and enclosed in brackets [...] with default values:
# ◦ zone=<type> (default: normal)
# ◦ color=<value> (default: none)
# ◦ max_drones=<number> (default: 1) - Maximum drones that can occupy this
# zone simultaneously
# ◦ Tags inside brackets can appear in any order.
# • Zone types:
# 9Fly-in
# Drones are interesting.
# ◦ normal – Standard zone with 1 turn movement cost (default)
# ◦ blocked – Inaccessible zone. Drones must not enter or pass through this zone.
# Any path using it is invalid.
# ◦ restricted – A sensitive or dangerous zone. Movement to this zone costs 2
# turns.
# ◦ priority – A preferred zone. Movement to this zone costs 1 turn but should
# be prioritized in pathfinding.
# • Colors:
# ◦ Colors are optional and can be used for visual representation (terminal output
# or graphical display).
# ◦ Accepted values for color are any valid single-word strings (e.g., red, blue,
# gray). There is no fixed list of allowed colors.
# ◦ When colors are specified, the implementation should provide visual feedback
# through colored terminal output or graphical representation.
# • Connections are defined using connection:
# <name1>-<name2> [metadata]:
# ◦ Define a bidirectional connection (edge) between two zones.
# ◦ The connection syntax forbids dashes in zone names.
# ◦ Optional metadata can be specified in brackets [...]:
# ∗ max_link_capacity=<number> (default: 1) - Maximum drones that can
# traverse this connection simultaneously
# • Comments start with ’#’ and are ignored.