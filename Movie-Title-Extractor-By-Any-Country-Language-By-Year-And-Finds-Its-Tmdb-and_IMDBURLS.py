import os
import time
import requests
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from datetime import datetime
from imdb import IMDb
import logging
import streamlit as st

# ===============================================
# CONFIGURATION
# ===============================================
TMDB_API_KEY = '6fad3f86b8452ee232deb7977d7dcf58'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
WIKI_BASE = "https://en.wikipedia.org/wiki/List_of_{}_films_of_{}"

logging.getLogger("imdbpy").setLevel(logging.ERROR)
ia = IMDb()

# ===============================================
# TMDb & IMDb Functions
# ===============================================
def get_tmdb_id(title, year):
    try:
        url = f"{TMDB_BASE_URL}/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": title, "year": year}
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        if data.get("results"):
            movie = data["results"][0]
            tmdb_id = movie["id"]
            details_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
            det_res = requests.get(details_url, params={"api_key": TMDB_API_KEY}, timeout=10)
            if det_res.status_code == 200:
                imdb_id = det_res.json().get("imdb_id", "N/A")
            else:
                imdb_id = "N/A"
            return tmdb_id, imdb_id
        return "N/A", "N/A"
    except Exception:
        return "N/A", "N/A"

def get_imdb_id(title, year):
    try:
        results = ia.search_movie(title)
        for result in results:
            if result.get('year') and abs(result['year'] - int(year)) <= 1:
                ia.update(result)
                return f"tt{result.movieID}"
        return "N/A"
    except Exception:
        _, imdb_id = get_tmdb_id(title, year)
        return imdb_id

# ===============================================
# Wikipedia Scraper
# ===============================================
def extract_movies_generic(url, category, year, progress_callback=None):
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code != 200:
            st.warning(f"Wikipedia page not found for {category} {year} (HTTP {res.status_code})")
            return pd.DataFrame()
        
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table", {"class": "wikitable"})
        if not tables:
            st.warning(f"No movie tables found for {category} {year}")
            return pd.DataFrame()

        all_movies = []
        for table in tables:
            df = pd.read_html(StringIO(str(table)))[0]
            df.columns = [str(c).strip() for c in df.columns]

            name_col = next((c for c in df.columns if "title" in c.lower() or "film" in c.lower()), df.columns[0])
            director_col = next((c for c in df.columns if "director" in c.lower()), None)

            for i, (_, row) in enumerate(df.iterrows(), start=1):
                movie = str(row.get(name_col, "")).strip()
                if not movie or movie.lower() in ["title", "film"]:
                    continue
                director = str(row.get(director_col, "")).strip() if director_col else "N/A"

                tmdb_id, tmdb_imdb = get_tmdb_id(movie, year)
                imdb_id = get_imdb_id(movie, year) if tmdb_imdb == "N/A" else tmdb_imdb

                tmdb_url = f"https://www.themoviedb.org/movie/{tmdb_id}" if tmdb_id != "N/A" else "N/A"
                imdb_url = f"https://www.imdb.com/title/{imdb_id}" if imdb_id != "N/A" else "N/A"

                reason = []
                if tmdb_id == "N/A":
                    reason.append("TMDb ID not found")
                if imdb_id == "N/A":
                    reason.append("IMDb ID not found")

                all_movies.append({
                    "Movie": movie,
                    "Director": director,
                    "Release Year": year,
                    "TMDb": tmdb_url,
                    "IMDb": imdb_url,
                    "Issue": ", ".join(reason) if reason else "None"
                })

                time.sleep(0.1)
                if progress_callback:
                    progress_callback(i/len(df))

        st.success(f"Extracted {len(all_movies)} movies for {category} {year}")
        return pd.DataFrame(all_movies)
    except Exception as e:
        st.error(f"Error extracting {category} movies for {year}: {e}")
        return pd.DataFrame()

# ===============================================
# Streamlit App
# ===============================================
st.title("🎬 Movie Data Extractor from Wikipedia")

category_input = st.text_input("Enter movie category (e.g., Hindi, Tamil, Bengali, Hollywood, Bollywood, Bangladeshi):", "Hindi")
category = category_input.replace(" ", "_")
if category:
    category = category[0].upper() + category[1:]

start_year = st.number_input("Start Year", min_value=1900, max_value=datetime.now().year, value=2020, step=1)
end_year = st.number_input("End Year", min_value=1900, max_value=datetime.now().year, value=2023, step=1)

if st.button("Fetch Movies"):
    all_data = []
    overall_progress = st.progress(0)
    total_years = end_year - start_year + 1

    for idx, year in enumerate(range(start_year, end_year + 1), start=1):
        st.info(f"Fetching {category} movies for {year}...")
        year_progress_bar = st.progress(0)

        def progress_callback(p):
            year_progress_bar.progress(min(int(p*100), 100))

        url = WIKI_BASE.format(category, year)
        df = extract_movies_generic(url, category, year, progress_callback)
        if not df.empty:
            all_data.append(df)

        overall_progress.progress(int(idx/total_years*100))

    if not all_data:
        st.warning("No data found for the given category/years.")
    else:
        final_df = pd.concat(all_data, ignore_index=True)
        total_movies = len(final_df)
        final_df.insert(0, "S.No", range(1, total_movies + 1))

        # Date-time formatting
        now = datetime.now()
        hour = now.strftime("%I").lstrip("0")
        minute = now.strftime("%M")
        am_pm = now.strftime("%p").lower()
        date_str = now.strftime(f"{hour}{am_pm} {minute} minutes %d %B %Y")

        base_name = f"({date_str}) Wikipedia {start_year}-{end_year} {category} total {total_movies} Movie List with IMDb and TMDb ID"

        st.success(f"✅ Extraction completed! Total movies: {total_movies}")

        # Show dataframe
        st.dataframe(final_df)

        # Provide download links
        csv = final_df.to_csv(index=False, encoding="utf-8-sig").encode('utf-8')
        html = final_df.to_html(index=False, escape=False).encode('utf-8')

        st.download_button("Download CSV", csv, file_name=f"{base_name}.csv")
        st.download_button("Download HTML", html, file_name=f"{base_name}.html")

