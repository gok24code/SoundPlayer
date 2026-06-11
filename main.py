import os
import logging
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, ListItem, ListView, Static

# Spotify API isteklerini loglamak için
from textual.logging import TextualHandler

logging.basicConfig(
    level="INFO",
    handlers=[TextualHandler()]
)
logger = logging.getLogger("spotipy")
logger.setLevel(logging.INFO)

SCOPE = "user-library-read playlist-read-private user-modify-playback-state"

load_dotenv()

class SPlayer(App):
    CSS = """
        Screen {
            layout: horizontal;
        }
        #sidebar {
            width: 25;
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sp = None

    def get_spotify_client(self):
        client_id = os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8080/")

        if not client_id or not client_secret:
            return None

        try:
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=SCOPE,
                open_browser=True,
                cache_path=".cache",
            )
            token_info = auth_manager.get_access_token(as_dict=False)
            if token_info:
                return spotipy.Spotify(auth=token_info)
        except Exception as e:
            self.log(f"Auth Error: {e}")
            return None
        return None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Play Lists", id="play_lists")
                yield ListView(id="playlist-list")
            with Vertical(id="main-content"):
                yield DataTable(cursor_type="row")
        yield Static("Initializing Spotify...", id="playback-bar")
        yield Footer()

    async def on_mount(self) -> None:
        self.sp = self.get_spotify_client()
        if not self.sp:
            self.handle_connection_error()
            return

        self.query_one("#playback-bar").update("Spotify Connected")
        table = self.query_one(DataTable)
        table.add_columns("Song", "Artist", "Album")
        self.run_worker(self.load_playlists, thread=True)

    def load_playlists(self) -> None:
        try:
            results = self.sp.current_user_playlists()
            self.call_from_thread(self.populate_playlists, results)
        except Exception as e:
            self.call_from_thread(self.handle_connection_error, e)

    def populate_playlists(self, results) -> None:
        playlist_list = self.query_one("#playlist-list")
        for item in results["items"]:
            list_item = ListItem(Label(item["name"]))
            list_item.playlist_id = item["id"]
            playlist_list.append(list_item)

    def handle_connection_error(self, error: Exception = None) -> None:
        self.query_one("#sidebar").display = False
        self.query_one(DataTable).display = False
        message = "Hesap bağlanamadı veya yetki hatası"
        if error:
            self.log(f"Connection Error: {error}")
        self.query_one("#main-content").mount(Label(message, id="error-message"))

    @on(ListView.Selected)
    def on_playlist_selected(self, event: ListView.Selected) -> None:
        playlist_id = getattr(event.item, "playlist_id", None)
        if playlist_id:
            self.log(f"Selected playlist: {playlist_id}")
            table = self.query_one(DataTable)
            table.clear()
            try:
                results = self.sp.playlist_items(playlist_id)
                for item in results.get("items", []):
                    track = item.get("track") or item.get("item")
                    if track and isinstance(track, dict) and "name" in track:
                        artists = track.get("artists", [])
                        artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
                        album = track.get("album", {})
                        album_name = album.get("name", "Unknown") if album else "Unknown"
                        table.add_row(track["name"], artist_name, album_name, key=track.get("uri"))
            except Exception as e:
                self.log(f"Error loading playlist: {e}")

    @on(DataTable.RowSelected)
    def on_track_selected(self, event: DataTable.RowSelected) -> None:
        track_uri = event.row_key.value
        if track_uri:
            try:
                self.sp.start_playback(uris=[track_uri])
                row_data = self.query_one(DataTable).get_row(event.row_key)
                self.query_one("#playback-bar").update(f"Playing: {row_data[0]} - {row_data[1]}")
            except Exception as e:
                self.log(f"Error playing track: {e}")

    def action_toggle_play(self) -> None:
        try:
            playback = self.sp.current_playback()
            if playback and playback["is_playing"]:
                self.sp.pause_playback()
            else:
                self.sp.start_playback()
        except Exception as e:
            self.log(f"Toggle play error: {e}")

    def action_next_track(self) -> None:
        try:
            self.sp.next_track()
        except Exception as e:
            self.log(f"Next track error: {e}")

    def action_prev_track(self) -> None:
        try:
            self.sp.previous_track()
        except Exception as e:
            self.log(f"Prev track error: {e}")

app = SPlayer()

if __name__ == "__main__":
    app.run()
