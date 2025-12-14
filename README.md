# Word Flashcards

A simple, clean desktop flashcard application built with Python and Tkinter.

This app allows users to create word sets, review them as flashcards, edit existing sets, and store data locally for future use.

---

## ✨ Features

- Create custom word sets (one word per line)
- Automatically remove duplicate words (case-insensitive)
- Review words as flashcards with:
  - Next / Previous navigation
  - Keyboard shortcuts (← → Space)
  - Shuffle / reshuffle
- Edit existing word sets safely
- Persistent local storage using JSON
- Clean UI with dark theme

---

## 🖥️ Screens & Interaction

- **Create a Set**: add a new word list
- **Flashcards**: review words one by one
- **Edit Mode**: modify an existing set without creating duplicates
- UI state is managed carefully to avoid accidental overwrites

---

## 🛠️ Requirements

- Python 3.9+
- No external dependencies (uses only standard library)

---

## 🚀 How to Run

```bash
python flashcards.py
