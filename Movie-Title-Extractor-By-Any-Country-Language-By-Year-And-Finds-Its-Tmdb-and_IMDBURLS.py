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
import re
import base64
from urllib.parse import quote

# ===============================================
# CONFIGURATION
# ===============================================
TMDB_API_KEY = '6fad3f86b8452ee232deb7977d7dcf58'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
WIKI_BASE = "https://en.wikipedia.org/wiki/List_of_{}_films_of_{}"

logging.getLogger("imdbpy").setLevel(logging.ERROR)
ia = IMDb()

# ===============================================
# Sound Functions
# ===============================================
def play_extended_completion_sound():
    """Play a 6-second completion sound with multiple effects"""
    extended_sound_js = """
    <script>
    function playExtendedCompletionSound() {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Main success melody (plays for 6 seconds)
        const mainOscillator = audioContext.createOscillator();
        const mainGain = audioContext.createGain();
        
        mainOscillator.connect(mainGain);
        mainGain.connect(audioContext.destination);
        
        mainOscillator.type = 'sine';
        mainGain.gain.value = 0.1;
        
        // Play a victory melody sequence
        const melody = [
            {freq: 523.25, time: 0},   // C
            {freq: 659.25, time: 0.5}, // E
            {freq: 783.99, time: 1.0}, // G
            {freq: 1046.50, time: 1.5}, // C (high)
            {freq: 880.00, time: 2.0}, // A
            {freq: 783.99, time: 2.5}, // G
            {freq: 659.25, time: 3.0}, // E
            {freq: 523.25, time: 3.5}, // C
            {freq: 659.25, time: 4.0}, // E
            {freq: 783.99, time: 4.5}, // G
            {freq: 1046.50, time: 5.0}, // C (high)
            {freq: 1046.50, time: 5.5}  // C (high sustained)
        ];
        
        mainOscillator.start();
        
        melody.forEach(note => {
            mainOscillator.frequency.setValueAtTime(note.freq, audioContext.currentTime + note.time);
        });
        
        // Fade out
        mainGain.gain.setValueAtTime(0.1, audioContext.currentTime + 5.8);
        mainGain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 6.0);
        mainOscillator.stop(audioContext.currentTime + 6.0);
        
        // Add some background harmony
        const harmonyOscillator = audioContext.createOscillator();
        const harmonyGain = audioContext.createGain();
        
        harmonyOscillator.connect(harmonyGain);
        harmonyGain.connect(audioContext.destination);
        
        harmonyOscillator.type = 'triangle';
        harmonyGain.gain.value = 0.05;
        
        const harmonyNotes = [
            {freq: 392.00, time: 0},    // G
            {freq: 493.88, time: 1.5},  // B
            {freq: 392.00, time: 3.0},  // G
            {freq: 329.63, time: 4.5}   // E
        ];
        
        harmonyOscillator.start();
        
        harmonyNotes.forEach(note => {
            harmonyOscillator.frequency.setValueAtTime(note.freq, audioContext.currentTime + note.time);
        });
        
        harmonyGain.gain.setValueAtTime(0.05, audioContext.currentTime + 5.8);
        harmonyGain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 6.0);
        harmonyOscillator.stop(audioContext.currentTime + 6.0);
    }
    playExtendedCompletionSound();
    </script>
    """
    st.components.v1.html(extended_sound_js, height=0)

def play_success_sound():
    """Play success sound - default selection"""
    play_extended_completion_sound()

# ===============================================
# Enhanced TMDb & IMDb Functions
# ===============================================
def clean_movie_title(title):
    """Clean movie title by removing brackets and extra content"""
    if not title or pd.isna(title):
        return ""
    title = str(title)
    # Remove content in brackets
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'\(.*?\)', '', title)
    # Remove extra spaces and strip
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def get_tmdb_id_advanced(title, year):
    """Enhanced TMDb search with better matching"""
    try:
        clean_title = clean_movie_title(title)
        url = f"{TMDB_BASE_URL}/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": clean_title, "year": year, "include_adult": "false"}
        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()
        
        if data.get("results"):
            # Try exact match first
            for movie in data["results"]:
                if (movie.get("title", "").lower() == clean_title.lower() or 
                    movie.get("original_title", "").lower() == clean_title.lower()):
                    return process_tmdb_movie(movie["id"])
            
            # Fallback to first result
            return process_tmdb_movie(data["results"][0]["id"])
        
        return "N/A", "N/A", "N/A", "N/A"
    except Exception as e:
        return "N/A", "N/A", "N/A", "N/A"

def process_tmdb_movie(tmdb_id):
    """Get detailed movie info from TMDb"""
    try:
        details_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
        params = {"api_key": TMDB_API_KEY, "append_to_response": "credits"}
        det_res = requests.get(details_url, params=params, timeout=15)
        
        if det_res.status_code == 200:
            movie_data = det_res.json()
            imdb_id = movie_data.get("imdb_id", "N/A")
            
            # Get director from credits
            director = "N/A"
            if "credits" in movie_data and "crew" in movie_data["credits"]:
                for person in movie_data["credits"]["crew"]:
                    if person.get("job") == "Director":
                        director = person.get("name", "N/A")
                        break
            
            # Get poster path
            poster_path = movie_data.get("poster_path", "")
            poster_url = f"https://image.tmdb.org/t/p/w200{poster_path}" if poster_path else "N/A"
            
            return tmdb_id, imdb_id, director, poster_url
        
        return tmdb_id, "N/A", "N/A", "N/A"
    except Exception:
        return tmdb_id, "N/A", "N/A", "N/A"

def get_imdb_rating(imdb_id):
    """Get IMDb rating for a movie"""
    try:
        if imdb_id and imdb_id != "N/A":
            movie = ia.get_movie(imdb_id.replace("tt", ""))
            if movie and 'rating' in movie:
                return f"{movie['rating']}/10"
        return "N/A"
    except Exception:
        return "N/A"

# ===============================================
# Enhanced Wikipedia Scraper with Detailed Progress Tracking
# ===============================================
def extract_movies_generic(url, category, year, progress_bar, status_text, year_text, total_movies_text):
    """Enhanced movie extraction with detailed progress tracking"""
    try:
        status_text.text(f"🔍 Connecting to Wikipedia for {category} {year}...")
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            st.warning(f"❌ Wikipedia page not found for {category} {year} (HTTP {res.status_code})")
            return pd.DataFrame()
        
        status_text.text(f"📊 Parsing Wikipedia tables for {category} {year}...")
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Remove unwanted elements
        for element in soup.find_all(["sup", "span"]):
            element.decompose()
        
        tables = soup.find_all("table", {"class": "wikitable"})
        if not tables:
            st.warning(f"⚠️ No movie tables found for {category} {year}")
            return pd.DataFrame()

        all_movies = []
        
        # Calculate total rows for progress tracking
        total_rows = 0
        for table in tables:
            try:
                df_temp = pd.read_html(StringIO(str(table)))[0]
                total_rows += len(df_temp)
            except:
                continue

        if total_rows == 0:
            st.warning(f"⚠️ No valid movie data found for {category} {year}")
            return pd.DataFrame()

        processed_rows = 0
        valid_movies_count = 0

        for table_idx, table in enumerate(tables):
            try:
                df = pd.read_html(StringIO(str(table)))[0]
                df.columns = [str(c).split('\n')[0].strip() for c in df.columns]

                # Enhanced column detection
                name_col = next((c for c in df.columns if any(word in c.lower() for word in 
                            ["title", "film", "movie", "name"])), df.columns[0])
                director_col = next((c for c in df.columns if "director" in c.lower()), None)

                for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
                    movie = clean_movie_title(row.get(name_col, ""))
                    if not movie or movie.lower() in ["title", "film", "movie", "name", "nan"]:
                        processed_rows += 1
                        progress_percentage = (processed_rows / total_rows) * 100
                        progress_bar.progress(progress_percentage / 100)
                        status_text.text(f"⏳ Processing: {processed_rows}/{total_rows} rows")
                        total_movies_text.text(f"🎬 Valid movies found: {valid_movies_count}")
                        continue

                    # Update progress with movie-specific info
                    current_progress = processed_rows + 1
                    progress_percentage = (current_progress / total_rows) * 100
                    
                    status_text.text(f"🎬 Processing: {movie}")
                    total_movies_text.text(f"📊 Progress: {processed_rows + 1}/{total_rows} ({progress_percentage:.1f}%)")
                    progress_bar.progress(progress_percentage / 100)

                    # Get director from Wikipedia first
                    wiki_director = "N/A"
                    if director_col and director_col in row:
                        wiki_director = str(row[director_col]).split('[')[0].strip()
                        if wiki_director.lower() in ["", "nan", "tbd"]:
                            wiki_director = "N/A"

                    # Get TMDb data
                    tmdb_id, imdb_id, tmdb_director, poster_url = get_tmdb_id_advanced(movie, year)
                    
                    # Use TMDb director if available, otherwise Wikipedia director
                    final_director = tmdb_director if tmdb_director != "N/A" else wiki_director
                    
                    # Get IMDb rating
                    imdb_rating = get_imdb_rating(imdb_id) if imdb_id != "N/A" else "N/A"

                    # Create URLs
                    tmdb_url = f"https://www.themoviedb.org/movie/{tmdb_id}" if tmdb_id != "N/A" else "N/A"
                    imdb_url = f"https://www.imdb.com/title/{imdb_id}" if imdb_id != "N/A" else "N/A"

                    # Determine issues
                    reason = []
                    if tmdb_id == "N/A":
                        reason.append("TMDb ID not found")
                    if imdb_id == "N/A":
                        reason.append("IMDb ID not found")
                    if final_director == "N/A":
                        reason.append("Director not found")

                    all_movies.append({
                        "Movie": movie,
                        "Director": final_director,
                        "Release Year": year,
                        "TMDb ID": tmdb_id,
                        "IMDb ID": imdb_id,
                        "IMDb Rating": imdb_rating,
                        "Poster URL": poster_url,
                        "TMDb Link": tmdb_url,
                        "IMDb Link": imdb_url,
                        "Issue": " | ".join(reason) if reason else "None"
                    })

                    valid_movies_count += 1
                    processed_rows += 1

                    time.sleep(0.2)  # Rate limiting

            except Exception as e:
                st.warning(f"⚠️ Error processing table {table_idx + 1}: {e}")
                continue

        # Final update for this year
        progress_bar.progress(1.0)
        status_text.text(f"✅ Completed {category} {year}")
        total_movies_text.text(f"🎉 Extraction complete: {valid_movies_count} movies found")
        
        st.success(f"✅ Extracted {valid_movies_count} movies for {category} {year}")
        return pd.DataFrame(all_movies)
        
    except Exception as e:
        st.error(f"❌ Error extracting {category} movies for {year}: {e}")
        return pd.DataFrame()

# ===============================================
# Enhanced HTML Generator
# ===============================================
def generate_beautiful_html(df, category, start_year, end_year, total_movies):
    """Generate a beautiful HTML report with advanced styling"""
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{category} Movies {start_year}-{end_year}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                min-height: 100vh;
            }}
            .header {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                margin-bottom: 2rem;
            }}
            .movie-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                margin-bottom: 1.5rem;
                overflow: hidden;
            }}
            .movie-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
            }}
            .movie-poster {{
                height: 200px;
                background: linear-gradient(45deg, #f0f0f0, #e0e0e0);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #666;
                font-size: 14px;
            }}
            .movie-poster img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
            }}
            .movie-info {{
                padding: 1.5rem;
            }}
            .movie-title {{
                font-weight: 700;
                color: #2c3e50;
                margin-bottom: 0.5rem;
                font-size: 1.1rem;
                line-height: 1.3;
            }}
            .movie-meta {{
                color: #7f8c8d;
                font-size: 0.9rem;
                margin-bottom: 0.5rem;
            }}
            .badge-custom {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border-radius: 20px;
                padding: 0.4rem 0.8rem;
                font-size: 0.8rem;
            }}
            .stats-card {{
                background: rgba(255, 255, 255, 0.95);
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 2rem;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            }}
            .btn-custom {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                border: none;
                border-radius: 25px;
                padding: 0.5rem 1.5rem;
                color: white;
                text-decoration: none;
                display: inline-block;
                transition: transform 0.3s ease;
            }}
            .btn-custom:hover {{
                transform: translateY(-2px);
                color: white;
            }}
            .issue-badge {{
                background: #e74c3c;
                color: white;
                padding: 0.3rem 0.6rem;
                border-radius: 15px;
                font-size: 0.8rem;
            }}
            .rating {{
                color: #f39c12;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container py-5">
            <!-- Header -->
            <div class="header text-center p-5 mb-4">
                <h1 class="display-4 fw-bold text-gradient mb-3">
                    <i class="fas fa-film me-3"></i>{category} Movies Collection
                </h1>
                <p class="lead mb-2">{start_year} - {end_year} • {total_movies} Movies</p>
                <p class="text-muted">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>

            <!-- Statistics -->
            <div class="stats-card">
                <div class="row text-center">
                    <div class="col-md-3">
                        <h3 class="fw-bold text-primary">{total_movies}</h3>
                        <p class="text-muted">Total Movies</p>
                    </div>
                    <div class="col-md-3">
                        <h3 class="fw-bold text-success">{len(df[df['TMDb ID'] != 'N/A'])}</h3>
                        <p class="text-muted">TMDb Found</p>
                    </div>
                    <div class="col-md-3">
                        <h3 class="fw-bold text-info">{len(df[df['IMDb ID'] != 'N/A'])}</h3>
                        <p class="text-muted">IMDb Found</p>
                    </div>
                    <div class="col-md-3">
                        <h3 class="fw-bold text-warning">{len(df[df['Issue'] == 'None'])}</h3>
                        <p class="text-muted">Complete Records</p>
                    </div>
                </div>
            </div>

            <!-- Movies Grid -->
            <div class="row" id="moviesGrid">
    """

    # Add movie cards
    for idx, movie in df.iterrows():
        poster_html = f'<img src="{movie["Poster URL"]}" alt="{movie["Movie"]}" loading="lazy">' if movie["Poster URL"] != "N/A" else '<div class="d-flex align-items-center justify-content-center h-100"><i class="fas fa-film fa-3x text-muted"></i></div>'
        
        tmdb_button = f'<a href="{movie["TMDb Link"]}" class="btn btn-sm btn-outline-primary me-2" target="_blank"><i class="fas fa-database"></i> TMDb</a>' if movie["TMDb Link"] != "N/A" else '<button class="btn btn-sm btn-outline-secondary me-2" disabled><i class="fas fa-database"></i> TMDb</button>'
        
        imdb_button = f'<a href="{movie["IMDb Link"]}" class="btn btn-sm btn-warning me-2" target="_blank"><i class="fab fa-imdb"></i> IMDb</a>' if movie["IMDb Link"] != "N/A" else '<button class="btn btn-sm btn-outline-secondary me-2" disabled><i class="fab fa-imdb"></i> IMDb</button>'
        
        rating_html = f'<span class="rating"><i class="fas fa-star"></i> {movie["IMDb Rating"]}</span>' if movie["IMDb Rating"] != "N/A" else '<span class="text-muted">No Rating</span>'
        
        issue_badge = f'<span class="issue-badge">{movie["Issue"]}</span>' if movie["Issue"] != "None" else '<span class="badge bg-success">Complete</span>'

        html_template += f"""
                <div class="col-lg-4 col-md-6">
                    <div class="movie-card">
                        <div class="movie-poster">
                            {poster_html}
                        </div>
                        <div class="movie-info">
                            <div class="movie-title">{movie["Movie"]}</div>
                            <div class="movie-meta">
                                <i class="fas fa-calendar-alt me-1"></i>{movie["Release Year"]} 
                                <span class="mx-2">•</span>
                                {rating_html}
                            </div>
                            <div class="movie-meta">
                                <i class="fas fa-user-tie me-1"></i>{movie["Director"]}
                            </div>
                            <div class="d-flex justify-content-between align-items-center mt-3">
                                <div class="btn-group">
                                    {tmdb_button}
                                    {imdb_button}
                                </div>
                                {issue_badge}
                            </div>
                        </div>
                    </div>
                </div>
        """

    html_template += """
            </div>
            
            <!-- Footer -->
            <div class="text-center mt-5 text-white">
                <p>Generated with ❤️ using Movie Data Extractor</p>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    return html_template

# ===============================================
# Streamlit App with Enhanced Progress Tracking & Sound
# ===============================================
def main():
    st.set_page_config(
        page_title="🎬 Advanced Movie Data Extractor",
        page_icon="🎭",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(45deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(45deg, #667eea, #764ba2);
    }
    .progress-container {
        margin: 1rem 0;
        padding: 1rem;
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
    }
    .completion-animation {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(45deg, #00b09b, #96c93d);
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .progress-info {
        font-family: 'Courier New', monospace;
        font-size: 1.1rem;
        font-weight: bold;
        color: #333;
        background: rgba(255,255,255,0.9);
        padding: 0.5rem 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-header">🎬 Advanced Movie Data Extractor</h1>', unsafe_allow_html=True)
    
    # Sidebar with sound options
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.markdown("---")
        
        category_input = st.text_input(
            "**Movie Category**", 
            value="Hindi",
            help="Enter movie category (e.g., Hindi, Tamil, Bengali, Hollywood, Bollywood)"
        )
        category = category_input.replace(" ", "_")
        if category:
            category = category[0].upper() + category[1:]
        
        col1, col2 = st.columns(2)
        with col1:
            start_year = st.number_input(
                "**Start Year**", 
                min_value=1900, 
                max_value=datetime.now().year, 
                value=2020
            )
        with col2:
            end_year = st.number_input(
                "**End Year**", 
                min_value=1900, 
                max_value=datetime.now().year, 
                value=2023
            )
        
        st.markdown("---")
        st.header("🔊 Sound Settings")
        # Default selection is Success Sound
        sound_option = st.selectbox(
            "Completion Sound",
            ["Success Sound", "Simple Beep", "None"],
            index=0,  # Default to Success Sound
            help="Choose the sound to play when extraction completes"
        )
        
        st.markdown("---")
        st.info("""
        **Instructions:**
        1. Enter movie category
        2. Select year range
        3. Click 'Fetch Movies'
        4. Download results
        
        **Progress Display:**
        - Shows current/total rows
        - Percentage completion
        - Real-time updates
        - 6-second completion sound
        """)
    
    # Main content
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Fetch Movies", use_container_width=True):
            if start_year > end_year:
                st.error("❌ Start year cannot be greater than end year!")
                return
                
            all_data = []
            
            # Overall progress tracking
            st.subheader("📊 Overall Progress")
            overall_progress_bar = st.progress(0)
            overall_status = st.empty()
            overall_count = st.empty()
            
            total_years = end_year - start_year + 1
            years_processed = 0
            
            for idx, year in enumerate(range(start_year, end_year + 1), start=1):
                # Year-specific progress tracking
                st.markdown(f"---")
                st.subheader(f"🎯 Processing {category} {year}")
                
                # Create progress elements for this year
                year_progress_bar = st.progress(0)
                year_status = st.empty()
                year_count = st.empty()
                
                # Update overall progress
                overall_progress = years_processed / total_years
                overall_progress_bar.progress(overall_progress)
                overall_status.text(f"📅 Processing year {year} of {end_year}")
                overall_count.markdown(f'<div class="progress-info">Overall: {years_processed}/{total_years} years ({(overall_progress * 100):.1f}%)</div>', unsafe_allow_html=True)
                
                url = WIKI_BASE.format(category, year)
                df = extract_movies_generic(url, category, year, year_progress_bar, year_status, year_count, st.empty())
                
                if not df.empty:
                    all_data.append(df)
                
                years_processed += 1
                
                # Clear year-specific progress elements
                year_progress_bar.empty()
                year_status.empty()
                year_count.empty()
            
            # Final overall progress
            overall_progress_bar.progress(1.0)
            overall_status.text("✅ All years processed successfully!")
            overall_count.markdown(f'<div class="progress-info">🎉 Complete: {total_years}/{total_years} years (100%)</div>', unsafe_allow_html=True)
            
            if not all_data:
                st.warning("⚠️ No data found for the given category/years.")
            else:
                final_df = pd.concat(all_data, ignore_index=True)
                total_movies = len(final_df)
                final_df.insert(0, "S.No", range(1, total_movies + 1))
                
                # Display completion animation and play sound
                st.markdown("""
                <div class="completion-animation">
                    <h2>🎉 Extraction Complete!</h2>
                    <p>Your movie data has been successfully processed</p>
                    <p><i class="fas fa-music"></i> Playing completion sound...</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Play completion sound based on user selection
                if sound_option == "Success Sound":
                    play_success_sound()
                elif sound_option == "Simple Beep":
                    play_extended_completion_sound()  # Still use extended sound for consistency
                
                # Add a small delay to ensure sound plays
                time.sleep(0.5)
                
                # Display results
                st.success(f"✅ Extraction completed! Total movies: {total_movies}")
                
                # Show statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Movies", total_movies)
                with col2:
                    st.metric("TMDb Found", len(final_df[final_df['TMDb ID'] != 'N/A']))
                with col3:
                    st.metric("IMDb Found", len(final_df[final_df['IMDb ID'] != 'N/A']))
                with col4:
                    st.metric("Complete Records", len(final_df[final_df['Issue'] == 'None']))
                
                # Show dataframe with expander
                with st.expander("📊 View Data Table", expanded=True):
                    st.dataframe(final_df, use_container_width=True)
                
                # Date-time formatting for filename
                now = datetime.now()
                hour = now.strftime("%I").lstrip("0")
                minute = now.strftime("%M")
                am_pm = now.strftime("%p").lower()
                date_str = now.strftime(f"{hour}{am_pm}{minute}minutes_%d_%B_%Y")
                
                base_name = f"Wikipedia_{start_year}_{end_year}_{category}_{total_movies}_Movies"
                
                # Download buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    csv = final_df.to_csv(index=False, encoding="utf-8-sig")
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        file_name=f"{base_name}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    beautiful_html = generate_beautiful_html(final_df, category, start_year, end_year, total_movies)
                    st.download_button(
                        "🎨 Download Beautiful HTML",
                        beautiful_html,
                        file_name=f"{base_name}.html",
                        mime="text/html",
                        use_container_width=True
                    )

if __name__ == "__main__":
    main()
