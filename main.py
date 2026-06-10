import os
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, ListItem, ListView, Static

SCOPE = "user-library-read playlist-read-private user-modify-playback-state"

load_dotenv()

def get_spotify_client():
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8080")

    if not client_id or not client_secret:
        return None

    try:
        return spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=SCOPE,
                open_browser=True,
            )
        )
    except Exception:
        return None


sp = get_spotify_client()


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

        #error-message {
            width: 100%;
            height: 100%;
            content-align: center middle;
            color: $error;
            text-style: bold;
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

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Song", "Artist", "Album")

        try:
            if not sp:
                raise Exception("Spotify client not initialized")

            # Run the blocking Spotify call in a worker to prevent UI freeze
            self.run_worker(self.load_playlists, thread=True)

        except Exception:
            self.handle_connection_error()

    def load_playlists(self) -> None:
        try:
            results = sp.current_user_playlists()
            self.call_from_thread(self.populate_playlists, results)
        except Exception:
            self.call_from_thread(self.handle_connection_error)

    def populate_playlists(self, results) -> None:
        playlist_list = self.query_one("#playlist-list")
        for item in results["items"]:
            list_item = ListItem(Label(item["name"]))
            list_item.playlist_id = item["id"]
            playlist_list.append(list_item)

    def handle_connection_error(self) -> None:
        self.query_one("#sidebar").display = False
        self.query_one(DataTable).display = False
        self.query_one("#main-content").mount(
            Label("Hesap bağlanamadı", id="error-message")
        )

    @on(ListView.Selected)
    def on_playlist_selected(self, event: ListView.Selected) -> None:
        playlist_id = getattr(event.item, "playlist_id", None)
        if playlist_id:
            table = self.query_one(DataTable)
            table.clear()
            results = sp.playlist_items(playlist_id)
            for item in results["items"]:
                track = item["track"]
                if track:  # Bazı podcast veya boş öğeler track içermeyebilir
                    table.add_row(
                        track["name"],
                        track["artists"][0]["name"],
                        track["album"]["name"],
                    )

    def action_toggle_play(self) -> None:
        try:
            playback = sp.current_playback()
            if playback and playback["is_playing"]:
                sp.pause_playback()
            else:
                sp.start_playback()
        except Exception:
            pass

    def action_next_track(self) -> None:
        try:
            sp.next_track()
        except Exception:
            pass

    def action_prev_track(self) -> None:
        try:
            sp.previous_track()
        except Exception:
            pass


if __name__ == "__main__":
    app = SoundPlayer()
    app.run()
