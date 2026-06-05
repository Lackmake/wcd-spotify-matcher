import os
import sys
import re
import urllib.request
import urllib.parse
import json
import webbrowser
import unicodedata
from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. Configuration & Utilities
PORT = 8888
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"

def load_env(filepath):
    env = {}
    if not os.path.exists(filepath):
        return env
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
    return env

def normalize(s):
    # Strip invisible control/formatting characters
    s = "".join(c for c in s if unicodedata.category(c) not in ('Cf', 'Cn', 'Co', 'Cs'))
    # Accent decomposition
    nfkd = unicodedata.normalize('NFKD', s)
    # Keep letters and numbers, lowercase
    only_alphanum = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    # Strip other non-alphanumeric punctuation
    only_alphanum = re.sub(r'[^a-z0-9\s]', '', only_alphanum)
    # Collapse multiple spaces
    return " ".join(only_alphanum.split())

def lev_distance(s1, s2):
    if len(s1) < len(s2):
        return lev_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def is_match(artist1_norm, artist2_norm):
    if not artist1_norm or not artist2_norm:
        return False
    # Exact match
    if artist1_norm == artist2_norm:
        return True
    # Substring match (whole words, length >= 3)
    words1 = artist1_norm.split()
    words2 = artist2_norm.split()
    if len(words1) >= 2 and artist1_norm in artist2_norm:
        return True
    if len(words2) >= 2 and artist2_norm in artist1_norm:
        return True
    # Levenshtein distance check for close spelling
    dist = lev_distance(artist1_norm, artist2_norm)
    min_len = min(len(artist1_norm), len(artist2_norm))
    if min_len > 4 and dist <= 1:
        return True
    if min_len > 8 and dist <= 2:
        return True
    return False

# 2. Local OAuth Server
auth_code = None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if parsed_path.path == "/callback":
            if "code" in query_params:
                auth_code = query_params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"""
                <html>
                <head>
                    <title>Auth Successful</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #121212; color: #ffffff; text-align: center; padding: 50px; }
                        h1 { color: #1DB954; }
                        .container { max-width: 500px; margin: 0 auto; background: #1e1e1e; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Authentication Successful!</h1>
                        <p>Spotify has successfully authorized your request.</p>
                        <p>You can close this tab and return to the console script.</p>
                    </div>
                </body>
                </html>
                """)
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization failed: no code returned.")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress server logging to keep terminal clean
        return

def run_local_server():
    server = HTTPServer(("127.0.0.1", PORT), OAuthHandler)
    # Stop server after receiving one request
    while auth_code is None:
        server.handle_request()

# 3. HTTP Request Helpers
def post_url(url, data_dict, headers=None):
    if headers is None:
        headers = {}
    data = urllib.parse.urlencode(data_dict).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        sys.exit(1)

def get_url(url, headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        sys.exit(1)

# 4. Main Execution
def main():
    # Load credentials
    env = load_env(".env")
    client_id = env.get("SPOTIFY_CLIENT_ID")
    client_secret = env.get("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret or "your_" in client_id or "your_" in client_secret:
        print("ERROR: Please fill in your Spotify client ID and client secret in the .env file.")
        print("See the implementation plan for instructions.")
        sys.exit(1)
        
    print("Spotify Matcher started.")
    print("Opening browser for Spotify authentication...")
    
    # Authorize URL
    scope = "user-library-read user-top-read user-read-recently-played"
    auth_params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": scope
    }
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(auth_params)
    
    webbrowser.open(auth_url)
    print("Waiting for callback on http://127.0.0.1:8888...")
    
    run_local_server()
    
    if not auth_code:
        print("Authentication failed.")
        sys.exit(1)
        
    print("Authentication successful! Trading code for access token...")
    
    # Token exchange
    token_response = post_url(
        "https://accounts.spotify.com/api/token",
        {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret
        }
    )
    
    access_token = token_response.get("access_token")
    if not access_token:
        print("Failed to acquire access token.")
        sys.exit(1)
        
    print("Successfully authenticated with Spotify.")
    
    # 5. Fetch Spotify Profile Data (Liked Songs + Top Artists + Top Tracks)
    spotify_data = {} # normalized_name -> details dict
    headers = {"Authorization": f"Bearer {access_token}"}
    
    def add_artist_info(artist_name, liked_song=None, top_artist_term=None, top_track_song=None, recent_song=None):
        norm = normalize(artist_name)
        if norm not in spotify_data:
            spotify_data[norm] = {
                "original_artist": artist_name,
                "liked_songs": [],
                "top_artist_terms": [],
                "top_track_songs": [],
                "recently_played_songs": []
            }
        
        # Keep the most standard/readable case spelling
        current_orig = spotify_data[norm]["original_artist"]
        if artist_name != current_orig and sum(1 for c in artist_name if c.isupper()) < sum(1 for c in current_orig if c.isupper()):
            # Keep mixed/clean case rather than all caps if possible
            if not artist_name.isupper():
                spotify_data[norm]["original_artist"] = artist_name

        if liked_song and liked_song not in spotify_data[norm]["liked_songs"]:
            spotify_data[norm]["liked_songs"].append(liked_song)
        if top_artist_term and top_artist_term not in spotify_data[norm]["top_artist_terms"]:
            spotify_data[norm]["top_artist_terms"].append(top_artist_term)
        if top_track_song and top_track_song not in spotify_data[norm]["top_track_songs"]:
            spotify_data[norm]["top_track_songs"].append(top_track_song)
        if recent_song and recent_song not in spotify_data[norm]["recently_played_songs"]:
            spotify_data[norm]["recently_played_songs"].append(recent_song)

    # 5.1 Fetch Liked Songs
    liked_url = "https://api.spotify.com/v1/me/tracks?limit=50"
    print("\nFetching your Spotify Liked Songs...")
    track_count = 0
    while liked_url:
        res = get_url(liked_url, headers)
        items = res.get("items", [])
        if not items:
            break
            
        for item in items:
            track = item.get("track")
            if not track:
                continue
            track_name = track.get("name")
            track_count += 1
            for artist in track.get("artists", []):
                artist_name = artist.get("name")
                if artist_name:
                    add_artist_info(artist_name, liked_song=track_name)
        
        print(f"Processed {track_count} liked tracks...")
        liked_url = res.get("next")
        
    print(f"Completed fetching. Total liked songs: {track_count}")
    
    # 5.2 Fetch Top Artists & Top Tracks
    time_ranges = ["short_term", "medium_term", "long_term"]
    range_names = {
        "short_term": "recent (4 weeks)",
        "medium_term": "medium (6 months)",
        "long_term": "all-time (long-term)"
    }
    
    print("\nFetching your Spotify Top Artists...")
    for tr in time_ranges:
        print(f"Fetching top artists for {range_names[tr]}...")
        top_url = f"https://api.spotify.com/v1/me/top/artists?limit=50&time_range={tr}"
        res = get_url(top_url, headers)
        for idx, artist in enumerate(res.get("items", [])):
            artist_name = artist.get("name")
            if artist_name:
                add_artist_info(artist_name, top_artist_term=range_names[tr])
                
    print("\nFetching your Spotify Top Tracks...")
    for tr in time_ranges:
        print(f"Fetching top tracks for {range_names[tr]}...")
        top_url = f"https://api.spotify.com/v1/me/top/tracks?limit=50&time_range={tr}"
        res = get_url(top_url, headers)
        for item in res.get("items", []):
            track_name = item.get("name")
            for artist in item.get("artists", []):
                artist_name = artist.get("name")
                if artist_name:
                    add_artist_info(artist_name, top_track_song=f"'{track_name}' ({range_names[tr]})")

    print("\nFetching your Spotify Recently Played Tracks...")
    recent_url = "https://api.spotify.com/v1/me/player/recently-played?limit=50"
    res = get_url(recent_url, headers)
    recent_count = 0
    for item in res.get("items", []):
        track = item.get("track")
        if track:
            track_name = track.get("name")
            recent_count += 1
            for artist in track.get("artists", []):
                artist_name = artist.get("name")
                if artist_name:
                    add_artist_info(artist_name, recent_song=track_name)
    print(f"Completed fetching. Total recently played songs: {recent_count}")

    print(f"\nCompleted fetching Spotify profile.")
    print(f"Unique artist names found in your music profile: {len(spotify_data)}")
    
    # 6. Parse Lineup Artists
    lineup_file = "artists.txt"
    if not os.path.exists(lineup_file):
        print(f"Error: lineup file {lineup_file} not found.")
        sys.exit(1)
        
    lineup_by_day = {}
    current_day = None
    
    with open(lineup_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("=== ") and " artists)" in line:
                match = re.match(r"=== (\w+) \(", line)
                if match:
                    current_day = match.group(1)
                    lineup_by_day[current_day] = []
                continue
            
            if current_day:
                original_lineup_entry = line
                parts = re.split(r'\s+[Bb]2[Bb]\s+', original_lineup_entry)
                for part in parts:
                    part_clean = part.strip()
                    if part_clean:
                        lineup_by_day[current_day].append({
                            "original_entry": original_lineup_entry,
                            "artist_name": part_clean,
                            "normalized_name": normalize(part_clean)
                        })
                        
    # 7. Perform Matching
    print("\nMatching lineup against listening profile...")
    matches_by_day = {day: [] for day in lineup_by_day.keys()}
    
    for day, lineup_entries in lineup_by_day.items():
        for entry in lineup_entries:
            lineup_norm = entry["normalized_name"]
            for spotify_norm, info in spotify_data.items():
                if is_match(lineup_norm, spotify_norm):
                    # Check if already matched in this day
                    already_matched = [m["lineup_artist"] for m in matches_by_day[day]]
                    if entry["artist_name"] not in already_matched:
                        matches_by_day[day].append({
                            "lineup_artist": entry["artist_name"],
                            "original_entry": entry["original_entry"],
                            "matched_spotify_artist": info["original_artist"],
                            "liked_songs": info["liked_songs"],
                            "top_artist_terms": info["top_artist_terms"],
                            "top_track_songs": info["top_track_songs"],
                            "recently_played_songs": info["recently_played_songs"]
                        })
                        
    # 8. Output Results
    print("\n=== MATCH RESULTS ===\n")
    report_file = "match_report.txt"
    with open(report_file, "w", encoding="utf-8") as out:
        out.write("=== World Club Dome 2026 Artist Matching Report ===\n\n")
        
        total_matches = 0
        for day in ["Friday", "Saturday", "Sunday"]:
            day_matches = matches_by_day.get(day, [])
            total_matches += len(day_matches)
            header = f"--- {day} ({len(day_matches)} Matches) ---"
            print(header)
            out.write(header + "\n")
            
            if not day_matches:
                print("  No matches found.")
                out.write("  No matches found.\n")
            else:
                day_matches_sorted = sorted(day_matches, key=lambda x: x["lineup_artist"].lower())
                for match in day_matches_sorted:
                    lineup_str = match["lineup_artist"]
                    if lineup_str != match["original_entry"]:
                        lineup_str += f" (part of '{match['original_entry']}')"
                    
                    match_str = f"  * {lineup_str} -> Matched Spotify artist: '{match['matched_spotify_artist']}'"
                    print(match_str)
                    out.write(match_str + "\n")
                    
                    # Print listener context indicators
                    indicators = []
                    if match["top_artist_terms"]:
                        terms_str = ", ".join(match["top_artist_terms"])
                        indicators.append(f"Top Artist ({terms_str})")
                    if match["top_track_songs"]:
                        indicators.append(f"In your Top Tracks")
                    if match["liked_songs"]:
                        indicators.append(f"In your Liked Songs")
                    if match.get("recently_played_songs"):
                        indicators.append(f"Recently Played")
                        
                    context_str = f"    Listener Status: {'; '.join(indicators)}"
                    print(context_str)
                    out.write(context_str + "\n")
                    
                    # Print liked songs details if any
                    if match["liked_songs"]:
                        liked_list = ", ".join([f"'{t}'" for t in match["liked_songs"]])
                        songs_str = f"    Liked songs: {liked_list}"
                        print(songs_str)
                        out.write(songs_str + "\n")
                        
                    # Print recently played songs if any
                    if match.get("recently_played_songs"):
                        recent_list = ", ".join([f"'{t}'" for t in match["recently_played_songs"]])
                        songs_str = f"    Recently played: {recent_list}"
                        print(songs_str)
                        out.write(songs_str + "\n")
                        
                    # Print top track details if no liked/recent songs but top tracks exist
                    elif match["top_track_songs"]:
                        tracks_list = ", ".join(match["top_track_songs"])
                        songs_str = f"    Top tracks: {tracks_list}"
                        print(songs_str)
                        out.write(songs_str + "\n")
                        
            print()
            out.write("\n")
            
        summary = f"Total matched artists across all days: {total_matches}"
        print(summary)
        out.write(summary + "\n")
        
    print(f"\nDetailed report written to '{report_file}'")

if __name__ == "__main__":
    main()
