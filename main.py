"""Sign in with Google using only the Python standard library."""

import base64
import hashlib
import json
import queue
import secrets
import threading
import time
import tkinter as tk
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tkinter import ttk
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


CREDENTIALS = Path(__file__).with_name("credentials.json")
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SIGN_IN_TIMEOUT = 180


class SignInError(Exception):
    """A sign-in problem that can be shown in the portal."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_credentials(credentials=CREDENTIALS):
    try:
        data = json.loads(credentials.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SignInError(f"Place {credentials.name} beside main.py. See README.md for setup.") from None
    except (ValueError, OSError):
        raise SignInError(f"Could not read {credentials.name}. Download a fresh copy from Google Cloud.") from None

    client = data.get("installed") if isinstance(data, dict) else None
    client_id = client.get("client_id") if isinstance(client, dict) else None
    if not isinstance(client_id, str) or not client_id.endswith(".apps.googleusercontent.com"):
        raise SignInError("Use the credentials JSON for a Google OAuth client of type Desktop app.")
    return client


def google_json(request, action):
    try:
        # Keep codes and bearer tokens on the intended HTTPS endpoint.
        with build_opener(NoRedirects()).open(request, timeout=10) as response:
            return json.load(response)
    except HTTPError as error:
        error.close()
        raise SignInError(f"Google could not {action} (HTTP {error.code}). Check your OAuth setup and try again.") from None
    except OSError:
        raise SignInError(f"Could not reach Google to {action}. Check your internet connection.") from None
    except ValueError:
        raise SignInError(f"Google returned an unreadable response while trying to {action}.") from None


def receive_code(client_id, verifier, cancelled, portal_name="Enterprise Employee Portal"):
    state = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(1)
            super().setup()

        def log_message(self, *args):
            pass  # The callback URL contains a one-time authorization code.

        def do_GET(self):
            try:
                location = urlsplit(self.path)
            except ValueError:
                self.send_error(400)
                return
            if location.path != "/":
                self.send_error(404)
                return
            values = parse_qs(location.query)
            returned_state = values.get("state", [])
            if (len(returned_state) != 1 or not secrets.compare_digest(
                    returned_state[0].encode("utf-8"), state.encode("ascii"))):
                self.send_error(400, "This request does not match the current sign-in.")
                return

            codes = values.get("code", [])
            if "error" in values or len(codes) != 1:
                result["error"] = values.get("error", ["invalid_response"])[0]
            else:
                result["code"] = codes[0]

            message = f"Return to the {portal_name} to see your sign-in status.".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(message)

    try:
        with HTTPServer(("127.0.0.1", 0), Callback) as server:
            redirect_uri = f"http://127.0.0.1:{server.server_port}/"
            parameters = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "prompt": "select_account",
            }
            if not webbrowser.open(f"{AUTH_URL}?{urlencode(parameters)}"):
                raise SignInError("Could not open your default browser.")
            server.timeout = 0.25
            deadline = time.monotonic() + SIGN_IN_TIMEOUT
            while not result and not cancelled.is_set() and time.monotonic() < deadline:
                server.handle_request()
    except OSError:
        raise SignInError("Could not start the local sign-in callback. Try signing in again.") from None

    if cancelled.is_set() or result.get("error") == "access_denied":
        raise SignInError("Sign-in was cancelled.")
    if "error" in result:
        raise SignInError("Google declined the sign-in. Check your OAuth client and audience settings.")
    if "code" not in result:
        raise SignInError("Sign-in timed out. Try again and finish signing in within three minutes.")
    return result["code"], redirect_uri


def fetch_picture(url):
    # Only fetch Google-hosted pictures, without sending the access token.
    if not isinstance(url, str):
        return None
    try:
        location = urlsplit(url)
        if location.scheme != "https" or not (location.hostname or "").endswith(".googleusercontent.com"):
            return None
        limit = 512 * 1024
        with build_opener(NoRedirects()).open(url, timeout=3) as response:
            image = response.read(limit + 1)
        if len(image) <= limit:
            return image
    except HTTPError as error:
        error.close()
    except (OSError, ValueError):
        pass
    return None


def sign_in(cancelled, credentials=CREDENTIALS, portal_name="Enterprise Employee Portal"):
    client = load_credentials(credentials)
    verifier = secrets.token_urlsafe(48)
    code, redirect_uri = receive_code(client["client_id"], verifier, cancelled, portal_name)
    if cancelled.is_set():
        raise SignInError("Sign-in was cancelled.")
    fields = {
        "client_id": client["client_id"],
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if client.get("client_secret"):
        fields["client_secret"] = client["client_secret"]
    token = google_json(Request(TOKEN_URL, data=urlencode(fields).encode("ascii")), "exchange the sign-in code")
    access_token = token.get("access_token") if isinstance(token, dict) else None
    if not isinstance(access_token, str) or not access_token:
        raise SignInError("Google did not return an access token.")
    if cancelled.is_set():
        raise SignInError("Sign-in was cancelled.")

    profile = google_json(
        Request(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}),
        "retrieve your profile",
    )
    if not isinstance(profile, dict) or not all(
        isinstance(profile.get(key), str) and profile[key] for key in ("sub", "email")
    ):
        raise SignInError("Google did not return an account ID and email address.")
    email = profile["email"]
    name = profile.get("name")
    if not isinstance(name, str) or not name.strip():
        name = email
    picture = None if cancelled.is_set() else fetch_picture(profile.get("picture"))
    return name, email, picture


class Portal:
    title = "Enterprise Employee Portal"

    def __init__(self, root, credentials=CREDENTIALS):
        self.root = root
        self.credentials = credentials
        self.cancelled = threading.Event()
        self.results = queue.Queue()
        self.picture = None
        root.title(self.title)
        root.geometry("500x375")
        root.minsize(430, 350)
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style(root)
        style.configure("Heading.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Avatar.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Portal.TButton", padding=(16, 8))
        self.card = ttk.Frame(root, padding=28)
        self.card.place(relx=0.5, rely=0.5, anchor="center", relwidth=1)
        self.login_screen()

    def clear(self):
        for widget in self.card.winfo_children():
            widget.destroy()
        self.picture = None

    def login_screen(self):
        self.clear()
        ttk.Label(self.card, text=self.title, style="Heading.TLabel").pack()
        ttk.Label(self.card, text="Use your Google account to access the portal.").pack(pady=(8, 24))
        self.button = ttk.Button(self.card, text="Sign in with Google", style="Portal.TButton", command=self.start)
        self.button.pack()
        self.cancel_button = ttk.Button(self.card, text="Cancel", command=self.cancelled.set)
        self.status = ttk.Label(self.card, wraplength=350, justify="center")
        self.status.pack(pady=(12, 0))

    def start(self):
        self.cancelled.clear()
        self.button.state(["disabled"])
        self.cancel_button.state(["!disabled"])
        self.cancel_button.pack(before=self.status, pady=(8, 0))
        self.status.config(text="Finish signing in in your browser.")
        threading.Thread(target=self.worker, daemon=True).start()
        self.root.after(100, self.check_result)

    def worker(self):
        try:
            self.results.put((sign_in(self.cancelled, self.credentials, self.title), None))
        except SignInError as error:
            self.results.put((None, str(error)))

    def check_result(self):
        try:
            account, error = self.results.get_nowait()
        except queue.Empty:
            if self.cancelled.is_set():
                self.cancel_button.state(["disabled"])
                self.status.config(text="Cancelling sign-in…")
            self.root.after(100, self.check_result)
            return

        if self.cancelled.is_set():
            error = "Sign-in was cancelled."
        if error:
            self.cancel_button.pack_forget()
            self.button.state(["!disabled"])
            self.status.config(text=error)
        else:
            self.dashboard(*account)

    def dashboard(self, name, email, picture):
        self.clear()
        if picture:
            try:
                self.picture = tk.PhotoImage(data=base64.b64encode(picture).decode("ascii"))
                scale = max(1, (max(self.picture.width(), self.picture.height()) + 79) // 80)
                self.picture = self.picture.subsample(scale)
            except tk.TclError:
                pass
        if self.picture:
            ttk.Label(self.card, image=self.picture).pack()
        else:
            initials = "".join(word[0].upper() for word in name.split()[:2])
            ttk.Label(self.card, text=initials, style="Avatar.TLabel").pack()
        ttk.Label(self.card, text=f"Welcome, {name}", style="Heading.TLabel",
                  wraplength=360, justify="center").pack(pady=(8, 4))
        ttk.Label(self.card, text=email, wraplength=360).pack()
        ttk.Button(self.card, text="Log out", style="Portal.TButton",
                   command=self.login_screen).pack(pady=(24, 0))

    def close(self):
        self.cancelled.set()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    Portal(root)
    root.mainloop()
