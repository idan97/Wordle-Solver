import itertools
import json
import os
from typing import List, Dict, Tuple
import math
from tqdm import tqdm
from multiprocessing import Pool, cpu_count

# Constants for letter transformations
REGULAR_TO_FINAL = {'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פ': 'ף', 'צ': 'ץ'}
FINAL_TO_REGULAR = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}

def load_json(filepath):
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)

# Function to get the absolute path of a file
def get_absolute_path(relative_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)

def convert_to_final_form(word: str) -> str:
    if word[-1] in REGULAR_TO_FINAL:
        word = word[:-1] + REGULAR_TO_FINAL[word[-1]]
    return word

def save_entropy_scores_to_file(entropy_scores: Dict[str, float], filepath: str):
    sorted_entropy_scores = dict(sorted(entropy_scores.items(), key=lambda x: x[1], reverse=True)[:5])
    readable_entropy_scores = {convert_to_final_form(word): score for word, score in sorted_entropy_scores.items()}
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(readable_entropy_scores, f, ensure_ascii=False, indent=4)

def load_entropy_scores_from_file(filepath: str) -> Dict[str, float]:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def update_entropy_scores(guesses: List[str], solutions: List[str]) -> Dict[str, float]:
    with Pool(cpu_count()) as pool:
        results = list(tqdm(pool.imap(calculate_entropy, [(guess, solutions) for guess in guesses]), total=len(guesses), desc="Calculating entropy scores"))
    entropy_scores = dict(zip(guesses, results))
    return entropy_scores

def calculate_entropy(args) -> float:
    guess, solutions = args
    entropy_score = 0
    total_solutions = len(solutions)
    patterns = {''.join(i): 0 for i in itertools.product("012", repeat=5)}
    patterns = dict.fromkeys(patterns, 0)

    for solution in solutions:
        pattern = ''.join(map(str, get_pattern(guess, solution)))  # Convert pattern list to string
        patterns[pattern] += 1
    
    for pattern in patterns:
        probability = patterns[pattern] / total_solutions
        if probability > 0:
            entropy_score += probability * math.log2(1 / probability)
    
    return entropy_score

def filter_solutions(solutions: List[str], guess: str, pattern: str) -> List[str]:
    filtered_solutions = solutions.copy()
    pattern_counts = {'0': {}, '1': {}, '2': {}}

    # Count the occurrences of each pattern for each letter
    for i in range(len(guess)):
        if guess[i] not in pattern_counts[pattern[i]]:
            pattern_counts[pattern[i]][guess[i]] = 0
        pattern_counts[pattern[i]][guess[i]] += 1

    # Filter solutions
    for i in range(len(guess)):
        curr_char = guess[i]
        if pattern[i] == '2':
            filtered_solutions = [solution for solution in filtered_solutions if solution[i] == curr_char]
        elif pattern[i] == '1':
            filtered_solutions = [solution for solution in filtered_solutions if solution[i] != curr_char and solution.count(curr_char) >= pattern_counts['1'][curr_char]]
        elif pattern[i] == '0':
            filtered_solutions = [
                solution for solution in filtered_solutions
                if curr_char not in solution or
                (solution.count(curr_char) == pattern_counts['2'].get(curr_char, 0) + pattern_counts['1'].get(curr_char, 0))
            ]

    return filtered_solutions

def get_pattern(guess: str, solution: str) -> List[int]:
    pattern = [0] * len(guess)
    letter_counts = {}

    for letter in solution:
        if letter in letter_counts:
            letter_counts[letter] += 1
        else:
            letter_counts[letter] = 1

    for i in range(len(guess)):
        if guess[i] == solution[i]:
            pattern[i] = 2
            letter_counts[guess[i]] -= 1

    for i in range(len(guess)):
        if guess[i] in letter_counts and letter_counts[guess[i]] > 0 and pattern[i] != 2:
            pattern[i] = 1
            letter_counts[guess[i]] -= 1

    return pattern

def calculate_best_three_words(guesses: List[str], solutions: List[str]) -> List[Tuple[Tuple[str, str, str], float]]:
    first_word_scores = update_entropy_scores(guesses, solutions)
    top_first_words = sorted(first_word_scores.items(), key=lambda x: x[1], reverse=True)[:1000]
    
    best_three_words = []
    
    for first_word, first_score in tqdm(top_first_words, desc="Evaluating top first words"):
        for first_pattern in itertools.product("012", repeat=5):
            first_pattern_str = ''.join(first_pattern)
            remaining_solutions = filter_solutions(solutions, first_word, first_pattern_str)
            if not remaining_solutions:
                continue

            second_word_scores = update_entropy_scores(guesses, remaining_solutions)
            top_second_words = sorted(second_word_scores.items(), key=lambda x: x[1], reverse=True)[:20]
            
            for second_word, second_score in top_second_words:
                for second_pattern in itertools.product("012", repeat=5):
                    second_pattern_str = ''.join(second_pattern)
                    remaining_solutions = filter_solutions(remaining_solutions, second_word, second_pattern_str)
                    if not remaining_solutions:
                        continue

                    third_word_scores = update_entropy_scores(guesses, remaining_solutions)
                    top_third_words = sorted(third_word_scores.items(), key=lambda x: x[1], reverse=True)[:5]

                    for third_word, third_score in top_third_words:
                        combined_entropy = first_score + second_score + third_score
                        best_three_words.append(((first_word, second_word, third_word), combined_entropy))

    best_three_words = sorted(best_three_words, key=lambda x: x[1], reverse=True)[:10]
    return best_three_words

# Load data from files using absolute paths
hebrew_guesses = (load_json(get_absolute_path("data/hebrew_guesses.json"))['words'])
hebrew_solutions_meduyeket = (load_json(get_absolute_path("data/hebrew_solutions_meduyeket.json"))['words'])

def find_best_starting_words():
    best_three_words = calculate_best_three_words(hebrew_guesses, hebrew_solutions_meduyeket)
    
    print("\nBest sequence of three starting words based on entropy scores:")
    for word, score in best_three_words:
        print(f"{convert_to_final_form(word)}: {score:.2f}")

if __name__ == '__main__':
    find_best_starting_words()
