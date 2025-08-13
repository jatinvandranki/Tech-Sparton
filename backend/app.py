from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import time
import hashlib
import subprocess
import os # Make sure os is imported
from collections import Counter
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

app = Flask(__name__)
CORS(app)

# --- AI Model Loading ---
print("Loading model and tokenizer...")
model = load_model('password_generator.h5')
with open('../rockyou.txt', 'r', encoding='latin-1') as f:
    passwords = f.read().splitlines()
tokenizer = Tokenizer(char_level=True)
tokenizer.fit_on_texts(passwords[:50000])
max_sequence_len = 31
print("Model and tokenizer loaded.")

# --- Helper Functions ---
def scrape_with_selenium(url):
    print(f"--- Scraping: {url} ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(executable_path='./chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        time.sleep(3)
        text = driver.find_element(By.TAG_NAME, 'body').text.lower()
        words = re.findall(r'\b\w{4,10}\b', text)
        return [word for word, count in Counter(words).most_common(5)] if words else []
    finally:
        driver.quit()

def mutate_password(password):
    base_words = {password.lower(), password.capitalize(), password.upper()}
    final_mutations = set(base_words)
    for base in base_words:
        for suffix in ['1', '123', '!', '2024', '2025']:
            final_mutations.add(base + suffix)
    leetspeak = password.lower().replace('e', '3').replace('a', '@').replace('o', '0')
    final_mutations.add(leetspeak)
    final_mutations.add(leetspeak + '!')
    final_mutations.add(leetspeak + '123')
    return list(final_mutations)

def generate_ai_passwords(keywords):
    ai_passwords = set()
    for seed in keywords:
        current_seed = seed
        for _ in range(3):
            token_list = tokenizer.texts_to_sequences([current_seed])[0]
            padded_sequence = pad_sequences([token_list], maxlen=max_sequence_len-1, padding='pre')
            predicted_probs = model.predict(padded_sequence, verbose=0)[0]
            current_seed += tokenizer.index_word.get(np.argmax(predicted_probs), '')
            ai_passwords.add(current_seed)
    return list(ai_passwords)

def crack_with_hashcat(wordlist_or_file, target_hash, hash_mode='0'):
    is_file = isinstance(wordlist_or_file, str)
    wordlist_filename = wordlist_or_file if is_file else "temp_wordlist.txt"
    hash_filename = "temp_hash.txt"
    
    # --- THIS IS THE FIX ---
    # Use the absolute path if it's a file (like rockyou.txt)
    if is_file:
        wordlist_filename = os.path.abspath(wordlist_filename)

    if not is_file:
        with open(wordlist_filename, "w", encoding='utf-8') as f:
            for password in wordlist_or_file:
                f.write(password + "\n")
    
    with open(hash_filename, "w") as f:
        f.write(target_hash)
    
    # Make sure this path is correct for your system
    hashcat_path = r"C:\Users\jatin\OneDrive\Desktop\tech-spartans\backend\hashcat.exe" 
    command = [hashcat_path, "-m", str(hash_mode), "-a", "0", hash_filename, wordlist_filename, "--show"]
    
    try:
        start_time = time.time()
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        time_taken = round((time.time() - start_time) * 1000, 2)
        output = result.stdout.strip()
        cracked = output.split(":")[-1] if ":" in output else None
        return cracked, time_taken
    except subprocess.CalledProcessError as e:
        print(f"Hashcat exited with an error: {e.stderr}")
        return None, None
    finally:
        if not is_file and os.path.exists(wordlist_filename):
            os.remove(wordlist_filename)
        if os.path.exists(hash_filename):
            os.remove(hash_filename)

@app.route('/analyze', methods=['POST'])
def analyze_target():
    data = request.get_json()
    url, target_hash = data.get('url'), data.get('target_hash', '').lower()
    if not url or not target_hash:
        return jsonify({"error": "URL and Hash are required for analysis."}), 400

    keywords = scrape_with_selenium(url)
    if not keywords:
        return jsonify({"error": "Could not extract keywords from URL."})

    ai_only_wordlist = generate_ai_passwords(keywords)
    hybrid_wordlist = list(set(p for pwd in ai_only_wordlist for p in mutate_password(pwd)))
    dictionary_file = "../rockyou.txt"

    results = {}
    cracked_password_length = 8

    print("Running Dictionary Attack...")
    cracked, time_taken = crack_with_hashcat(dictionary_file, target_hash)
    results['dictionary'] = {"cracked": bool(cracked), "time": time_taken, "wordlist_size": len(passwords)}
    if cracked: cracked_password_length = len(cracked)

    print("Running AI-Only Attack...")
    cracked, time_taken = crack_with_hashcat(ai_only_wordlist, target_hash)
    results['ai_only'] = {"cracked": bool(cracked), "time": time_taken, "wordlist_size": len(ai_only_wordlist)}
    if cracked: cracked_password_length = len(cracked)

    print("Running Hybrid Attack...")
    cracked, time_taken = crack_with_hashcat(hybrid_wordlist, target_hash)
    results['hybrid'] = {"cracked": bool(cracked), "time": time_taken, "wordlist_size": len(hybrid_wordlist)}
    if cracked: cracked_password_length = len(cracked)

    print("Calculating Brute-Force Estimate...")
    charset_size = 95
    combinations = charset_size ** cracked_password_length
    guesses_per_second = 100_000_000_000
    seconds_to_crack = combinations / guesses_per_second
    if seconds_to_crack > 3.154e+7 * 1000:
        brute_force_time = "1,000+ years"
    else:
        brute_force_time = f"{seconds_to_crack / (365 * 24 * 3600):,.0f} years"
    results['brute_force'] = {"cracked": None, "time": brute_force_time, "wordlist_size": combinations}

    return jsonify({"results": results})

if __name__ == '__main__':
    app.run(debug=False, port=5000)