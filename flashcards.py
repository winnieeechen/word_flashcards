import json
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "flashcard_data.json")


# ----------------------------
# Data persistence
# ----------------------------
def load_data():
    """
    Load word set data from the local JSON file.

    Returns:
        dict: {group_name: [word1, word2, ...]}
    """
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, list):
                    cleaned[k] = [str(x) for x in v if str(x).strip()]
            return cleaned
        return {}
    except Exception:
        return {}


def save_data(data: dict):
    """
    Save word set data to the local JSON file.
    """
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_words(text: str):
    """
    Normalize raw text input into a clean list of words.

    - Trims whitespace
    - Removes empty lines
    - De-duplicates words (case-insensitive) while preserving order
    """
    lines = [ln.strip() for ln in text.splitlines()]
    words = [w for w in lines if w]
    seen = set()
    uniq = []
    for w in words:
        key = w.lower()
        if key not in seen:
            uniq.append(w)
            seen.add(key)
    return uniq


# ----------------------------
# Main application
# ----------------------------
class FlashcardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Word Flashcards")
        self.geometry("980x620")
        self.minsize(900, 560)
        
        # Application state
        self.data = load_data()              # {group_name: [words]}
        self.current_group_name = None       # currently selected set
        self.session_words = []              # shuffled words for review
        self.index = 0                       # current card index
        self.editing_group = None            # active edit target (None if not editing)

        self._build_style()
        self._build_layout()
        self._refresh_group_list()

 

    # ---------- UI styling ----------
    def _build_style(self):
        """
        Configure global UI styles and theme.
        """
        self.configure(bg="#0b1220")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background="#0b1220")
        style.configure("TLabel", background="#0b1220", foreground="#e8eefc")
        style.configure("Title.TLabel", font=("Helvetica", 20, "bold"), foreground="#e8eefc")
        style.configure("Sub.TLabel", font=("Helvetica", 11), foreground="#b9c6ea")

        style.configure("TButton", font=("Helvetica", 11))

        style.configure(
            "PrimaryBlack.TButton",
            foreground="#000000",
            padding=(14, 8)
        )
        style.map(
            "PrimaryBlack.TButton",
            foreground=[("disabled", "#555555")]
        )

        style.configure(
            "SecondaryBlack.TButton",
            foreground="#000000",
            padding=(14, 8)
        )
        style.map(
            "SecondaryBlack.TButton",
            foreground=[("disabled", "#555555")]
        )

    # ---------- Layout ----------
    def _build_layout(self):
        """
        Build the overall window layout:
        left panel (sets) + right panel (tabs).
        """
        # Top header
        header = ttk.Frame(self, padding=(18, 14))
        header.pack(side="top", fill="x")

        ttk.Label(header, text="Word Flashcards", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Create word sets → shuffle → flip cards (Prev / Next) → saved locally for review.",
            style="Sub.TLabel"
        ).pack(anchor="w", pady=(6, 0))

        # Main content area
        main = ttk.Frame(self, padding=(18, 14))
        main.pack(side="top", fill="both", expand=True)

        main.columnconfigure(0, weight=1, minsize=260)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        # Left panel: word set list
        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Your Word Sets", font=("Helvetica", 13, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        # Listbox + scrollbar
        list_frame = ttk.Frame(left)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.group_list = tk.Listbox(
            list_frame,
            bg="#0f1a33",
            fg="#e8eefc",
            highlightthickness=0,
            selectbackground="#2b5cff",
            selectforeground="#ffffff",
            activestyle="none",
            font=("Helvetica", 12),
            relief="flat"
        )
        self.group_list.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.group_list.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.group_list.config(yscrollcommand=sb.set)

        self.group_list.bind("<<ListboxSelect>>", self._on_group_select)

        # Actions below list
        actions = ttk.Frame(left)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)

        self.btn_start = ttk.Button(actions, text="Review", style="Primary.TButton",
                                    command=self.start_session_from_selected)
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_delete = ttk.Button(actions, text="Delete", style="Danger.TButton",
                                     command=self.delete_selected_group)
        self.btn_delete.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Right panel: tabs
        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(right)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Tabs
        self.tab_create = ttk.Frame(self.notebook, padding=(16, 16))
        self.notebook.add(self.tab_create, text="Create a Set")

        self.tab_cards = ttk.Frame(self.notebook, padding=(16, 16))
        self.notebook.add(self.tab_cards, text="Flashcards")

        self._build_create_tab()
        self._build_cards_tab()

        # Default tab
        self.notebook.select(self.tab_create)

        # Reset Create tab when leaving edit mode
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)


    # ---------- Create tab ----------
    def _build_create_tab(self):
        """
        Build UI elements for creating or editing a word set.
        """
        self.tab_create.columnconfigure(0, weight=1)

        ttk.Label(self.tab_create, text="1) Name your set", font=("Helvetica", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        name_frame = ttk.Frame(self.tab_create)
        name_frame.grid(row=1, column=0, sticky="ew", pady=(8, 16))
        name_frame.columnconfigure(0, weight=1)

        self.entry_set_name = tk.Entry(
            name_frame,
            bg="#0f1a33",
            fg="#e8eefc",
            insertbackground="#e8eefc",
            relief="flat",
            font=("Helvetica", 12),
            highlightthickness=1,
            highlightbackground="#20315c",
            highlightcolor="#2b5cff"
        )
        self.entry_set_name.grid(row=0, column=0, sticky="ew", ipady=8)

        ttk.Label(self.tab_create, text="2) Enter words (one per line)", font=("Helvetica", 13, "bold")).grid(
            row=2, column=0, sticky="w"
        )

        text_frame = ttk.Frame(self.tab_create)
        text_frame.grid(row=3, column=0, sticky="nsew", pady=(8, 12))
        self.tab_create.rowconfigure(3, weight=1)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.text_words = tk.Text(
            text_frame,
            bg="#0f1a33",
            fg="#e8eefc",
            insertbackground="#e8eefc",
            relief="flat",
            font=("Helvetica", 12),
            wrap="word",
            highlightthickness=1,
            highlightbackground="#20315c",
            highlightcolor="#2b5cff"
        )
        self.text_words.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_words.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.text_words.config(yscrollcommand=sb.set)

        # Save / Update button
        btns = ttk.Frame(self.tab_create)
        btns.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        btns.columnconfigure(0, weight=1)

        self.btn_save_set = ttk.Button(btns, text="Save Set", style="Primary.TButton", command=self.save_new_set)
        self.btn_save_set.grid(row=0, column=0, sticky="ew")

        hint = "Tip: You can paste many lines at once. Words are auto de-duplicated (case-insensitive)."
        ttk.Label(self.tab_create, text=hint, style="Sub.TLabel").grid(row=5, column=0, sticky="w", pady=(10, 0))

    def reset_create_form(self):
        """
        Reset the Create tab to a clean 'new set' state.
        """
        self.entry_set_name.configure(state="normal")
        self.entry_set_name.delete(0, "end")
        self.text_words.delete("1.0", "end")
        self.btn_save_set.configure(text="Save Set")
        self.notebook.tab(self.tab_create, text="Create a Set")

    def save_new_set(self):
        """
        Save a new word set or update an existing one (edit mode).
        """
        text = self.text_words.get("1.0", "end").strip()
        words = normalize_words(text)

        if self.editing_group:
            name = self.editing_group
        else:
            name = self.entry_set_name.get().strip()

        if not name:
            messagebox.showwarning("Missing name", "Please name your word set.")
            return
        if not words:
            messagebox.showwarning("No words", "Please enter at least 1 word (one per line).")
            return

        if self.editing_group:
            self.data[name] = words
            save_data(self.data)
            self._refresh_group_list(select=name)
            messagebox.showinfo("Updated", f"Updated '{name}' with {len(words)} words.")

            self.editing_group = None
            self.reset_create_form()
            self.start_session(name)
            return

        if name in self.data:
            ok = messagebox.askyesno(
                "Overwrite?",
                f"A set named '{name}' already exists.\nDo you want to overwrite it?"
            )
            if not ok:
                return

        self.data[name] = words
        save_data(self.data)
        self._refresh_group_list(select=name)
        messagebox.showinfo("Saved", f"Saved '{name}' with {len(words)} words.")


    # ---------- Group list ----------
    def _refresh_group_list(self, select=None):
        """
        Refresh the word set list in the left panel.
        """
        self.group_list.delete(0, "end")
        for group_name in sorted(self.data.keys(), key=lambda s: s.lower()):
            self.group_list.insert("end", group_name)

        if select:
            items = self.group_list.get(0, "end")
            for i, g in enumerate(items):
                if g == select:
                    self.group_list.selection_clear(0, "end")
                    self.group_list.selection_set(i)
                    self.group_list.see(i)
                    self.current_group_name = select
                    break

    def _selected_group_name(self):
        """
        Return the currently selected group name from the list.
        """
        sel = self.group_list.curselection()
        if not sel:
            return None
        return self.group_list.get(sel[0])

    def _on_group_select(self, event=None):
        """
        Handle selection changes in the group list.
        """
        g = self._selected_group_name()
        self.current_group_name = g

    def delete_selected_group(self):
        """
        Delete the selected word set after confirmation.
        """
        g = self._selected_group_name()
        if not g:
            messagebox.showinfo("Select a set", "Please select a word set first.")
            return
        ok = messagebox.askyesno("Delete?", f"Delete '{g}'? This cannot be undone.")
        if not ok:
            return
        self.data.pop(g, None)
        save_data(self.data)
        self.current_group_name = None
        self._refresh_group_list()
        messagebox.showinfo("Deleted", f"Deleted '{g}'.")

        if g == self.current_group_name:
            self.session_words = []
            self.index = 0
            self.lbl_group.configure(text="No set selected")
            self.lbl_progress.configure(text="")
            self._set_cards_enabled(False)
            self._render_card()

    def start_session_from_selected(self):
        """
        Start a flashcard session from the selected set.
        """
        g = self._selected_group_name()
        if not g:
            messagebox.showinfo("Select a set", "Please select a word set first.")
            return
        self.start_session(g)

    # ---------- Flashcards tab ----------
    def _build_cards_tab(self):
        """
        Build UI elements for flashcard review.
        """
        self.tab_cards.columnconfigure(0, weight=1)
        self.tab_cards.rowconfigure(2, weight=1)

        top = ttk.Frame(self.tab_cards)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        self.lbl_group = ttk.Label(top, text="No set selected", font=("Helvetica", 13, "bold"))
        self.lbl_group.grid(row=0, column=0, sticky="w")

        self.lbl_progress = ttk.Label(top, text="", font=("Helvetica", 11), foreground="#b9c6ea")
        self.lbl_progress.grid(row=0, column=1, sticky="e")

        # Card display area
        card_outer = ttk.Frame(self.tab_cards)
        card_outer.grid(row=2, column=0, sticky="nsew", pady=(16, 12))
        card_outer.rowconfigure(0, weight=1)
        card_outer.columnconfigure(0, weight=1)

        self.card_canvas = tk.Canvas(
            card_outer,
            bg="#0b1220",
            highlightthickness=0
        )
        self.card_canvas.grid(row=0, column=0, sticky="nsew")

        self.card_rect = None
        self.card_text_id = None

        # Navigation controls
        controls = ttk.Frame(self.tab_cards)
        controls.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=1)
        controls.columnconfigure(3, weight=1)

        self.btn_prev = ttk.Button(controls, text="← Previous", style="Secondary.TButton", command=self.prev_card)
        self.btn_prev.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_next = ttk.Button(controls, text="Next → ", style="Primary.TButton", command=self.next_card)
        self.btn_next.grid(row=0, column=1, sticky="ew", padx=6)

        self.btn_shuffle = ttk.Button(controls, text="Reshuffle", style="Secondary.TButton", command=self.reshuffle)
        self.btn_shuffle.grid(row=0, column=2, sticky="ew", padx=6)

        self.btn_edit = ttk.Button(controls, text="✎ Edit Set", style="Secondary.TButton",
                                   command=self.edit_current_set)
        self.btn_edit.grid(row=0, column=3, sticky="ew", padx=(6, 0))

        # Keyboard shortcuts
        self.bind("<Left>", lambda e: self.prev_card())
        self.bind("<Right>", lambda e: self.next_card())
        self.bind("<space>", lambda e: self.next_card())

        self.card_canvas.bind("<Configure>", lambda e: self._render_card())

        self._set_cards_enabled(False)

        hint = "Shortcuts: ← Previous | → Next | Space Next"
        ttk.Label(self.tab_cards, text=hint, style="Sub.TLabel").grid(row=4, column=0, sticky="w", pady=(10, 0))

    def _set_cards_enabled(self, enabled: bool):
        """
        Enable or disable flashcard navigation buttons.
        """
        state = "normal" if enabled else "disabled"
        for b in [self.btn_prev, self.btn_next, self.btn_shuffle]:
            b.configure(state=state)

    def start_session(self, group_name: str):
        """
        Initialize and start a flashcard review session.
        """
        if group_name not in self.data or not self.data[group_name]:
            messagebox.showwarning("Empty set", "This set has no words.")
            return

        self.current_group_name = group_name
        self.session_words = list(self.data[group_name])
        random.shuffle(self.session_words)
        self.index = 0

        self.lbl_group.configure(text=f"Set: {group_name}")
        self._update_progress()
        self._set_cards_enabled(True)

        self.notebook.select(self.tab_cards)
        self._render_card()

    def edit_current_set(self):
        """
        Enter edit mode for the currently active word set.
        """
        g = self.current_group_name
        if not g or g not in self.data:
            messagebox.showinfo("No set", "Please start/review a set first, then click Edit.")
            return

        self.editing_group = g

        self.notebook.select(self.tab_create)
        self.notebook.tab(self.tab_create, text=f"Edit: {g}")

        self.entry_set_name.delete(0, "end")
        self.entry_set_name.insert(0, g)

        self.text_words.delete("1.0", "end")
        self.text_words.insert("1.0", "\n".join(self.data[g]))

        self.entry_set_name.configure(state="disabled")
        self.btn_save_set.configure(text="Update Set")

        self.text_words.focus_set()

    def _on_tab_changed(self, event):
        """
        Reset Create tab when leaving edit mode.
        """
        tab = event.widget.nametowidget(event.widget.select())
        if tab == self.tab_create and self.editing_group is None:
            self.reset_create_form()

    def reshuffle(self):
        """
        Reshuffle words and restart from the first card.
        """
        if not self.session_words:
            return
        random.shuffle(self.session_words)
        self.index = 0
        self._update_progress()
        self._render_card()

    def prev_card(self):
        """
        Move to the previous flashcard.
        """
        if not self.session_words:
            return
        if self.index > 0:
            self.index -= 1
            self._update_progress()
            self._render_card()

    def next_card(self):
        """
        Move to the next flashcard.
        """
        if not self.session_words:
            return
        if self.index < len(self.session_words) - 1:
            self.index += 1
            self._update_progress()
            self._render_card()
        else:
            messagebox.showinfo("Done!", "You reached the last card.\nYou can reshuffle to review again.")

    def _update_progress(self):
        """
        Update progress label (current / total).
        """
        if not self.session_words:
            self.lbl_progress.configure(text="")
            return
        self.lbl_progress.configure(text=f"{self.index + 1} / {len(self.session_words)}")

    def _render_card(self):
        """
        Render the current flashcard on the canvas.
        """
        self.card_canvas.delete("all")

        w = self.card_canvas.winfo_width()
        h = self.card_canvas.winfo_height()
        if w <= 10 or h <= 10:
            return

        card_w = int(w * 0.86)
        card_h = int(h * 0.72)
        x0 = (w - card_w) // 2
        y0 = (h - card_h) // 2
        x1 = x0 + card_w
        y1 = y0 + card_h

        self.card_canvas.create_rectangle(
            x0 + 10, y0 + 10, x1 + 10, y1 + 10,
            fill="#060a12", outline=""
        )

        self.card_canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#0f1a33",
            outline="#20315c",
            width=2
        )

        if not self.session_words:
            word = "Select a set and start."
            sub = "Go to the left list → choose a set → Review."
        else:
            word = self.session_words[self.index]
            sub = "Use buttons or ← / → / Space"

        base = max(26, min(52, card_w // 14))
        if len(word) > 12:
            base = max(22, base - (len(word) - 12) // 2)

        self.card_canvas.create_text(
            (w // 2), (h // 2) - 10,
            text=word,
            fill="#e8eefc",
            font=("Helvetica", base, "bold"),
            width=card_w - 90,
            justify="center"
        )

        self.card_canvas.create_text(
            (w // 2), (y1 - 34),
            text=sub,
            fill="#b9c6ea",
            font=("Helvetica", 11),
            justify="center"
        )


if __name__ == "__main__":
    app = FlashcardApp()
    app.mainloop()
