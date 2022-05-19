"""A simple application using examples/boilerplate.py as a basis."""

from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace

import pytermgui as ptg

import command
import webaas_api


PALETTE_LIGHT = "#FCBA03"
PALETTE_MID = "#8C6701"
PALETTE_DARK = "#4D4940"
PALETTE_DARKER = "#242321"

def _process_arguments(argv: list[str] | None = None) -> Namespace:
    """Processes command line arguments.
    Note that you don't _have to_ use the bultin argparse module for this; it
    is just what the module uses.
    Args:
        argv: A list of command line arguments, not including the binary path
            (sys.argv[0]).
    """

    parser = ArgumentParser(description="My first PTG application.")

    return parser.parse_args(argv)


def _create_aliases() -> None:
    """Creates all the TIM aliases used by the application.
    Aliases should generally follow the following format:
        namespace.item
    For example, the title color of an app named "myapp" could be something like:
        myapp.title
    """

    ptg.tim.alias("app.text", "#cfc7b0")

    ptg.tim.alias("app.header", f"bold @{PALETTE_MID} #d9d2bd")
    ptg.tim.alias("app.header.fill", f"@{PALETTE_LIGHT}")

    ptg.tim.alias("app.title", f"bold {PALETTE_LIGHT}")
    ptg.tim.alias("app.button.label", f"bold @{PALETTE_DARK} app.text")
    ptg.tim.alias("app.button.highlight", "inverse app.button.label")

    ptg.tim.alias("app.footer", f"@{PALETTE_DARKER}")


def _configure_widgets() -> None:
    """Defines all the global widget configurations.
    Some example lines you could use here:
        ptg.boxes.DOUBLE.set_chars_of(ptg.Window)
        ptg.Splitter.set_char("separator", " ")
        ptg.Button.styles.label = "myapp.button.label"
        ptg.Container.styles.border__corner = "myapp.border"
    """

    ptg.boxes.DOUBLE.set_chars_of(ptg.Window)
    ptg.boxes.ROUNDED.set_chars_of(ptg.Container)

    ptg.Button.styles.label = "app.button.label"
    ptg.Button.styles.highlight = "app.button.highlight"

    ptg.Slider.styles.filled__cursor = PALETTE_MID
    ptg.Slider.styles.filled_selected = PALETTE_LIGHT

    ptg.Label.styles.value = "app.text"

    ptg.Window.styles.border__corner = "#C2B280"
    ptg.Container.styles.border__corner = PALETTE_DARK

    ptg.Splitter.set_char("separator", "")


def _define_layout() -> ptg.Layout:
    """Defines the application layout.
    Layouts work based on "slots" within them. Each slot can be given dimensions for
    both width and height. Integer values are interpreted to mean a static width, float
    values will be used to "scale" the relevant terminal dimension, and giving nothing
    will allow PTG to calculate the corrent dimension.
    """

    layout = ptg.Layout()

    # A header slot with a height of 1
    layout.add_slot("Header", height=1)
    layout.add_break()

    # A body slot that will fill the entire width, and the height is remaining
    layout.add_slot("Body")

    # A slot in the same row as body, using the full non-occupied height and
    # 20% of the terminal's height.
    layout.add_slot("Body right", width=0.2)

    layout.add_break()
    layout.add_slot("Body bottom", height=3)

    layout.add_break()

    # A footer with a static height of 1
    layout.add_slot("Footer", height=1)

    return layout


def _confirm_quit(manager: ptg.WindowManager) -> None:
    """Creates an "Are you sure you want to quit" modal window"""

    modal = ptg.Window(
        "[app.title]Are you sure you want to quit?",
        "",
        ptg.Container(
            ptg.Splitter(
                ptg.Button("Yes", lambda *_: manager.stop()),
                ptg.Button("No", lambda *_: modal.close()),
            ),
        ),
    ).center()

    modal.select(1)
    manager.add(modal)

input_field = ptg.InputField()
container_window = ptg.Container(box="EMPTY")
people_container_window = ptg.Container(box="EMPTY")
body_window = ptg.Window(
                "[app.title]ChatRoom XXX",
                "",
                container_window,
                vertical_align=ptg.VerticalAlignment.TOP,
                overflow=ptg.Overflow.SCROLL,
            )
people_window = ptg.Window(
                "People List",
                people_container_window,
                vertical_align=ptg.VerticalAlignment.TOP,
                overflow=ptg.Overflow.SCROLL,
            )

def show_message(message_str_list):
    label_list = []
    for message in message_str_list:
        message_label = ptg.Label(message, 
                                  parent_align=ptg.HorizontalAlignment.LEFT,
                                  size_policy=ptg.SizePolicy.RELATIVE)
        message_label.relative_width = 1.0
        label_list.append(message_label)
    container_window.set_widgets(label_list)

def show_person(person_str_list):
    label_list = []
    for message in person_str_list:
        message_label = ptg.Label(message, 
                                  parent_align=ptg.HorizontalAlignment.LEFT,
                                  size_policy=ptg.SizePolicy.RELATIVE)
        message_label.relative_width = 1.0
        label_list.append(message_label)
    people_container_window.set_widgets(label_list)

def updatePrintField(inputField, key):
    input_str = str.strip(inputField.value)
    if len(input_str) == 0:
        return

    if input_str[0] == '/':
        # Process Command
        chatroom_app.process_command(input_str)
    else:
        # Process Message
        chatroom_app.process_message(input_str)
    inputField.value = ""

def main(argv: list[str] | None = None) -> None:
    """Runs the application."""

    _create_aliases()
    _configure_widgets()

    args = _process_arguments(argv)

    with ptg.WindowManager() as manager:
        manager.layout = _define_layout()

        header = ptg.Window(
            "[app.header] Welcome to Chat TUI ",
            box="EMPTY",
            is_persistant=True,
        )

        header.styles.fill = "app.header.fill"

        # Since header is the first defined slot, this will assign to the correct place
        manager.add(header)

        footer = ptg.Window(
            ptg.Button("Quit", lambda *_: _confirm_quit(manager)),
            box="EMPTY",
        )
        footer.styles.fill = "app.footer"

        # Since the second slot, body was not assigned to, we need to manually assign
        # to "footer"
        manager.add(footer, assign="footer")

        manager.add(
            people_window,
            assign="body_right",
        )

        manager.add(
            body_window,
            assign="body",
        )

        manager.add(
            ptg.Window(
                input_field,
                vertical_align=ptg.VerticalAlignment.BOTTOM,
                overflow=ptg.Overflow.SCROLL,
            ),
            assign="body_bottom",
        )
        input_field.bind(ptg.keys.ENTER, updatePrintField)

    ptg.tim.print(f"[{PALETTE_LIGHT}]Goodbye!")

if __name__ == "__main__":
    # webaas_api.initWeBaas()
    chatroom_app = command.ChatRoomApp(show_person, show_message)
    main(sys.argv[1:])
