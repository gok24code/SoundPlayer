from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, ListItem, ListView, Static


class SoundPlayer(App):
    CSS = """
        Screen {
            layout: horizontal;
        }

        #sidebar {
            width: 20;
            background: $panel;
            border-right: tall green;
        }

        #main-content {
            width: 1fr;
        }

        #playback-bar {
            dock: bottom;
            height: 3;
            background: black;
            color: white;
            content-align: center middle;
            margin-bottom:2;
        }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("space", "toggle_play", "Play/Pause"),
        ("n", "next_track", "Next"),
        ("p", "prev_track", "Previous"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Play Lists", id="play_lists")
                yield ListView(id="playlist-list")
            with Vertical(id="main-content"):
                yield DataTable()
        yield Static("Nothing playing...", id="playback-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Song", "Artist", "Album")
        table.add_row("Sample Song", "Sample Artist", "Sample Album")


if __name__ == "__main__":
    app = SoundPlayer()
    app.run()
