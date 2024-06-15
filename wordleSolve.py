import itertools
import json
import os
from typing import List, Dict
import math
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import tkinter as tk
from tkinter import messagebox, StringVar, OptionMenu

# Constants for letter transformations
REGULAR_TO_FINAL = {'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פ': 'ף', 'צ': 'ץ'}
FINAL_TO_REGULAR = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}

# Color mapping
COLOR_TO_NUMBER = {'Grey': '0', 'Yellow': '1', 'Green': '2'}

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

def convert_to_regular_form(word: str) -> str:
    return "".join(FINAL_TO_REGULAR.get(char, char) for char in word)

def preprocess_words(words: List[str]) -> List[str]:
    return [convert_to_final_form(word) for word in words]

# Load data from files using absolute paths
hebrew_guesses = (load_json(get_absolute_path("data/hebrew_guesses.json"))['words'])
hebrew_guesses_long = (load_json(get_absolute_path("data/hebrew_guesses_long.json"))['words'])
hebrew_solutions_meduyeket = (load_json(get_absolute_path("data/hebrew_solutions_meduyeket.json"))['words'])

current_solutions = hebrew_guesses.copy()

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
    guess = convert_to_regular_form(guess[::-1])  # Reverse the guess and convert to regular form
    filtered_solutions = solutions.copy()

    for i in range(len(guess)):
        curr_char = guess[i]
        if pattern[i] == '2':
            filtered_solutions = [solution for solution in filtered_solutions if solution[i] == curr_char]
        elif pattern[i] == '1':
            filtered_solutions = [solution for solution in filtered_solutions if solution[i] != guess[i] and guess[i] in solution]
        elif pattern[i] == '0':
            filtered_solutions = [solution for solution in filtered_solutions if guess[i] not in solution]

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

class WordleSolverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Wordle Solver")
        
        # Center the window on the screen
        self.center_window()

        self.current_solutions = hebrew_solutions_meduyeket.copy()

        # Guess entry
        self.guess_vars = [StringVar() for _ in range(5)]
        self.guess_entries = [tk.Entry(root, textvariable=self.guess_vars[i], width=3, font=('Helvetica', 24), justify='right') for i in range(5)]
        for i, entry in enumerate(reversed(self.guess_entries)):  # Place entries right to left
            entry.grid(row=0, column=i, padx=10, pady=5)

        # Color selection
        self.color_vars = [StringVar(value='Grey') for _ in range(5)]
        self.color_buttons = [tk.OptionMenu(root, self.color_vars[i], 'Grey', 'Yellow', 'Green') for i in range(5)]
        for i, button in enumerate(reversed(self.color_buttons)):  # Place buttons right to left
            button.config(width=8)
            button.grid(row=1, column=i, padx=10, pady=5)

        # Submit button
        self.submit_button = tk.Button(root, text="Submit", command=self.submit_guess, font=('Helvetica', 14), width=20, height=2)
        self.submit_button.grid(row=2, columnspan=5, pady=10)

        # Results display
        self.possible_solutions_label = tk.Label(root, text="Possible Solutions: 0", font=('Helvetica', 14))
        self.possible_solutions_label.grid(row=3, columnspan=5, pady=5)

        self.top_guesses_label = tk.Label(root, text="Top 5 Guesses:\n", font=('Helvetica', 14))
        self.top_guesses_label.grid(row=4, columnspan=5, pady=5)

        # Initial display of top 5 guesses
        self.display_top_guesses()

    def center_window(self):
        window_width = 700
        window_height = 400
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        self.root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    def submit_guess(self):
        guess = "".join(var.get() for var in self.guess_vars[::-1])  # Read entries right to left
        pattern = "".join(COLOR_TO_NUMBER[var.get()] for var in self.color_vars[::-1])  # Read entries right to left

        if len(guess) != 5 or not all(c in "אבגדהוזחטיכלמנסעפצקרשתךםןףץ" for c in guess):
            messagebox.showerror("Error", "Invalid guess.")
            return

        new_solutions = filter_solutions(self.current_solutions, guess, pattern[::-1])  # Reverse pattern to match right-to-left order
        self.possible_solutions_label.config(text=f"Possible Solutions: {len(new_solutions)}")

        if len(new_solutions) == 0:
            messagebox.showinfo("Info", "No possible solutions found with the given pattern.")
            return

        self.current_solutions = new_solutions

        if len(self.current_solutions) <= 5:
            remaining_solutions = "\n".join([convert_to_final_form(word) for word in self.current_solutions])
            self.top_guesses_label.config(text=f"Remaining Solutions:\n{remaining_solutions}")
            if len(self.current_solutions) == 1:
                messagebox.showinfo("Solution Found", f"Solution found! The word is: {convert_to_final_form(self.current_solutions[0])}")
            self.reset_gui()
            return
        
        self.display_top_guesses()
        self.reset_gui()

    def reset_gui(self):
        for var in self.guess_vars:
            var.set('')
        for var in self.color_vars:
            var.set('Grey')
        for entry in self.guess_entries:
            entry.config(state='normal')

    def display_top_guesses(self):
        entropy_scores = update_entropy_scores(hebrew_guesses, self.current_solutions)
        sorted_entropy_scores = sorted(entropy_scores.items(), key=lambda x: x[1], reverse=True)
        top_words = "\n".join([f"{convert_to_final_form(word)}: {score:.2f}" for word, score in sorted_entropy_scores[:5]])  # Convert to final form before displaying
        self.top_guesses_label.config(text=f"Top 5 Guesses:\n{top_words}")

def run_gui():
    root = tk.Tk()
    app = WordleSolverGUI(root)
    root.mainloop()

if __name__ == '__main__':
    run_gui()