# World Club Dome Spotify Matcher

A utility to scrape the World Club Dome lineup and match the performing artists against your Spotify listening profile (Liked Songs, Top Artists, and Top Tracks) to find out which festival acts you already know and love!

## Features

- **Lineup Scraper**: Extracts lineup artist names for all three days (Friday, Saturday, Sunday) from the official World Club Dome site.
- **Robust Matching Engine**:
  - **B2B Splitting**: Separates back-to-back entries (e.g. `Artist A b2b Artist B`) to match them individually.
  - **Multi-Artist Tracks**: Extracts and evaluates every artist on your liked songs.
  - **Normalization**: Handles punctuation, accents/diacritics (e.g. `Möbius` -> `mobius`, `ÉTIENNE` -> `etienne`), and case differences.
  - **Fuzzy Spell Check**: Matches close spelling variations using normalized string similarity (Levenshtein distance).
- **Multi-Indicator Reporting**: Flags why you know an artist (e.g. if they are in your Liked Songs, Top Tracks, or a Top Artist over short, medium, or long-term periods).

---

## Setup & Usage

### 1. Prerequisites & Spotify Application
To access your Spotify profile data, you need to create a free Spotify Developer Application:
1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and log in.
2. Click **Create app** and configure:
   - **App name**: `WCD Artist Matcher`
   - **Redirect URI**: `http://127.0.0.1:8888/callback` *(This loopback IP address is strictly required by Spotify; `localhost` is not allowed).*
3. Save your application settings.
4. Copy your **Client ID** and **Client Secret**.

### 2. Installation & Credentials
1. Clone this repository to your local machine.
2. Create a `.env` file in the root directory (this is automatically ignored by Git):
   ```ini
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   ```
3. Make sure Python 3 is installed.

### 3. Run the Matching Script
Run the script from your terminal:
```bash
python spotify_match.py
```

1. The script will automatically open your default browser to Spotify's authorization page.
2. Log in and click **Agree** to authorize the script (uses `user-library-read` and `user-top-read` scopes).
3. Once authorized, return to your terminal. The script will fetch your data and compile the match report.

---

## Files

- `artists.txt`: The extracted list of WCD artists grouped by day.
- `match_report.txt`: The final generated matching report showing performing artists you listen to, categorized by day with liked songs details.
- `spotify_match.py`: The Python execution script.
