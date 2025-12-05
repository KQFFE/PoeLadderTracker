import customtkinter
import threading
import time
# Use the new singleton API client
from api import GGGAPIClient
from data_processor import process_ladder_data, ALL_ASCENDANCY_NAMES

CHUNK_SIZE = 200

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("PoE Ladder Tracker")
        self.geometry("700x1000")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.stop_search_event = threading.Event()
        self.current_limit = 10
        self.all_fetched_entries = []
        self.current_offset = 0
        self.all_leagues_data = [] # To store full league objects for ID lookup

        # --- Font ---
        self.textbox_font = customtkinter.CTkFont(family="Consolas", size=12)

        # --- Options Frame ---
        self.options_frame = customtkinter.CTkFrame(self)
        self.options_frame.grid(row=0, column=0, padx=20, pady=(20,10), sticky="ew")
        self.options_frame.grid_columnconfigure(0, weight=1)
        self.options_frame.grid_columnconfigure(1, weight=1)

        self.league_label = customtkinter.CTkLabel(self.options_frame, text="Ladder")
        self.league_label.grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")
        self.league_menu = customtkinter.CTkOptionMenu(self.options_frame, values=["Fetching leagues..."])
        self.league_menu.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")

        self.ascendancy_label = customtkinter.CTkLabel(self.options_frame, text="Ascendancy")
        self.ascendancy_label.grid(row=0, column=1, padx=10, pady=(10,0), sticky="w")
        self.ascendancy_menu = customtkinter.CTkOptionMenu(self.options_frame, values=["All"] + ALL_ASCENDANCY_NAMES, command=self.on_ascendancy_change)
        self.ascendancy_menu.grid(row=1, column=1, padx=10, pady=(0,10), sticky="ew")

        self.private_league_check = customtkinter.CTkCheckBox(self.options_frame, text="Use Private League", command=self.toggle_private_league)
        self.private_league_check.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        self.private_league_entry = customtkinter.CTkEntry(self.options_frame, placeholder_text="Name of Private League (PLxxxxx)")
        self.private_league_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.private_league_entry.configure(state="disabled") # Disabled by default

        self.deep_search_check = customtkinter.CTkCheckBox(self.options_frame, text="Deep Search (Public Leagues Only)")
        self.deep_search_check.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.deep_search_check.bind("<Button-1>", self.on_deep_search_toggle)

        self.fetch_button = customtkinter.CTkButton(self.options_frame, text="Fetch Characters", command=self.start_fetch_thread)
        self.fetch_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Search Frame ---
        self.search_frame = customtkinter.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.char_name_label = customtkinter.CTkLabel(self.search_frame, text="Character Name")
        self.char_name_label.grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")
        self.char_name_entry = customtkinter.CTkEntry(self.search_frame)
        self.char_name_entry.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")

        self.search_button = customtkinter.CTkButton(self.search_frame, text="Search Character", command=self.start_search_thread)
        self.search_button.grid(row=1, column=1, padx=(10,5), pady=(0,10))
        
        self.stop_search_button = customtkinter.CTkButton(self.search_frame, text="Stop", command=self.stop_search, state="disabled")
        self.stop_search_button.grid(row=1, column=2, padx=(0,10), pady=(0,10))

        # --- Results Textbox ---
        self.textbox = customtkinter.CTkTextbox(self, width=600, font=self.textbox_font)
        self.textbox.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        
        # --- Configure Tab Stops for Perfect Column Alignment ---
        # We will set the tabs dynamically once the widget is drawn.
        # This ensures the right-aligned column is always correct.
        self.after(100, self.configure_tabs)

        # --- Show More Button ---
        self.show_more_button = customtkinter.CTkButton(self, text="Show More", command=self.start_show_more_thread, state="disabled")
        self.show_more_button.grid(row=3, column=0, padx=20, pady=(0,10), sticky="ew")

        # --- Status Bar ---
        self.status_label = customtkinter.CTkLabel(self, text="Ready.", text_color="gray")
        self.status_label.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

        # --- Disclaimer Label ---
        self.disclaimer_label = customtkinter.CTkLabel(self, text="This product isn't affiliated with or endorsed by Grinding Gear Games in any way.", text_color="gray")
        self.disclaimer_label.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="s")

        self.load_leagues()

    def configure_tabs(self):
        """
        Dynamically configures tab stops for the results textbox.
        This ensures the right-most column is always perfectly aligned.
        """
        # Get the actual width of the textbox after it has been rendered.
        widget_width = self.textbox.winfo_width()
        # Define tab stops: Asc(0), Lvl(140), Name(200), Rank(far right, right-aligned)
        tab_stops = (180, 300, widget_width - 35, "right")
        self.textbox.configure(tabs=tab_stops)

    def get_selected_league(self):
        try:
            if self.private_league_check.get() == 1:
                return self.private_league_entry.get()
            else:
                return self.league_menu.get()
        except Exception:
            # This can happen if the menu is not yet populated
            return None

    def _get_league_id_from_name(self, league_name_or_id):
        """
        Finds the GGG API 'id' for a league name from cached data.
        The proxy needs the 'id' for authenticated requests.
        """
        for league in self.all_leagues_data:
            if league.get('id') == league_name_or_id or league.get('text') == league_name_or_id:
                return league['id']
        return league_name_or_id # Fallback for private leagues

    def toggle_private_league(self):
        if self.private_league_check.get() == 1: # Checked
            self.league_menu.configure(state="disabled")
            self.deep_search_check.deselect()
            self.private_league_entry.configure(state="normal")
        else: # Unchecked
            # Re-enable only if leagues were successfully loaded
            self.league_menu.configure(state="normal")
            self.deep_search_check.configure(state="normal")
            self.private_league_entry.configure(state="disabled")

    def on_ascendancy_change(self, choice):
        if choice == "All":
            self.show_more_button.configure(state="disabled")
        else:
            self.show_more_button.configure(state="normal")

    def on_deep_search_toggle(self, event=None):
        if self.private_league_check.get() == 1:
            self.deep_search_check.deselect()
            return "break"

    def load_leagues(self):
        def update_ui(leagues_data):
            # The proxy returns a JSON object with a 'result' key containing the leagues.
            leagues = leagues_data.get('result') if isinstance(leagues_data, dict) else None

            if leagues and isinstance(leagues, list):
                # The proxy filters to PC leagues; we just need to display them.
                self.all_leagues_data = leagues # Store full data for ID lookup
                league_display_names = [league.get('text', league['id']) for league in leagues]
                self.league_menu.configure(values=league_display_names)

                if league_display_names:
                    self.league_menu.set(league_display_names[0])
            else:
                print("Error: Could not parse leagues from API response.")
                self.league_menu.configure(values=["Error fetching leagues"])
                self.league_menu.set("Error fetching leagues")
                # Disable buttons if leagues fail to load
                self.fetch_button.configure(state="disabled")
                self.search_button.configure(state="disabled")
                self.all_leagues_data = [] # Clear data on error

        def task():
            self.status_label.configure(text="Fetching leagues...")
            leagues = GGGAPIClient.fetch_leagues()
            self.after(0, update_ui, leagues)
        thread = threading.Thread(target=task, daemon=True)
        thread.start()

    def start_fetch_thread(self):
        self.current_limit = 10
        self.all_fetched_entries = []
        self.current_offset = 0
        self.fetch_and_display_data_thread()

    def start_show_more_thread(self):
        self.current_limit += 50
        self.fetch_and_display_data_thread()

    def fetch_and_display_data_thread(self):
        self.fetch_button.configure(state="disabled")
        self.search_button.configure(state="disabled")
        self.stop_search_button.configure(state="disabled")
        self.show_more_button.configure(state="disabled")
        self.status_label.configure(text="Fetching data...")
        self.textbox.delete("1.0", "end")
        
        thread = threading.Thread(target=self.fetch_and_display_data, daemon=True)
        thread.start()

    def _should_stop_fetching(self, ascendancy):
        """Helper to determine if the data fetching loop should stop."""
        # Stop if we hit the GGG API limit for a single search
        if self.current_offset >= 15000:
            return True

        # Stop condition for a single ascendancy when enough have been found
        if ascendancy:
            count = sum(1 for entry in self.all_fetched_entries if entry['character']['class'] == ascendancy)
            return count >= self.current_limit
        
        # Stop condition for "All" ascendancies when all have enough entries
        ascendancy_counts = {asc: 0 for asc in ALL_ASCENDANCY_NAMES}
        for entry in self.all_fetched_entries:
            char_class = entry['character']['class']
            if char_class in ascendancy_counts:
                ascendancy_counts[char_class] += 1
        return all(count >= self.current_limit for count in ascendancy_counts.values())

    def update_textbox(self, output):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", output)

    def update_textbox_and_scroll(self, output):
        """Updates the textbox and scrolls to the end."""
        self.update_textbox(output)
        self.textbox.see("end")

    def fetch_and_display_data(self):
        selected_league_input = self.get_selected_league()
        deep_search = self.deep_search_check.get() == 1

        # For deep search, we must resolve the name to the GGG ID for the proxy.
        league_id = self._get_league_id_from_name(selected_league_input) if deep_search else selected_league_input

        if not league_id:
            self.status_label.configure(text=f"Error: League '{selected_league_input}' not found.")
            return

        ascendancy = self.ascendancy_menu.get()
        if ascendancy == "All":
            ascendancy = None

        while True:
            if self._should_stop_fetching(ascendancy): break
            self.status_label.configure(text=f"Fetching characters {self.current_offset} to {self.current_offset + CHUNK_SIZE}...")
            data = GGGAPIClient.fetch_ladder(league_id, limit=CHUNK_SIZE, offset=self.current_offset, deep_search=deep_search)
            
            if data is None:
                self.status_label.configure(text="Error: Failed to fetch ladder data from API.")
                break
            
            entries = data.get('entries', [])
            if not entries: break # No more entries to fetch
            
            self.all_fetched_entries.extend(entries)
            self.current_offset += CHUNK_SIZE

            # Live update for "All" ascendancies
            if not ascendancy:
                final_results = process_ladder_data(self.all_fetched_entries, selected_ascendancy=ascendancy, limit=self.current_limit)
                output = self.format_results(final_results, selected_league_input)
                self.after(0, self.update_textbox, output)

            # Add a small delay to respect API rate limits
            time.sleep(0.5)
        
        # Final update for single ascendancy
        if ascendancy:
            final_results = process_ladder_data(self.all_fetched_entries, selected_ascendancy=ascendancy, limit=self.current_limit)
            output = self.format_results(final_results, selected_league_input)
            # If the limit is greater than the initial fetch, it means "Show More" was used.
            if self.current_limit > 10:
                self.after(0, self.update_textbox_and_scroll, output)
            else:
                self.after(0, self.update_textbox, output)

        self.status_label.configure(text=f"Done. Showing top {self.current_limit} for {ascendancy if ascendancy else 'all ascendancies'}.")
        self.fetch_button.configure(state="normal")
        self.search_button.configure(state="normal")
        if self.ascendancy_menu.get() != "All":
            self.show_more_button.configure(state="normal")

    def format_results(self, final_results, league):
        width = 90
        header = f"✅ ASCENDANCY STANDINGS ✅".center(width)
        league_line = f"League: {league}".center(width)
        separator = "-" * width

        output = [f"{separator}\n", f"{header}\n", f"{league_line}\n", f"{separator}\n"]

        # Use tabs (\t) to align columns instead of manual padding
        table_header = f"ASCENDANCY\tLEVEL\tCHARACTER NAME\tRANK (Asc/Global)"
        output.append(f"{table_header}\n")
        output.append(f"{separator}\n")

        last_ascendancy = None
        for char in final_results:
            if last_ascendancy and char['ascendancy'] != last_ascendancy:
                output.append(f"{separator}\n")
            
            rank_str = f"{char['asc_rank']} / {char['global_rank']}"
            line = f"{char['ascendancy']}\t{char['level']}\t{char['name']}\t{rank_str}"
            output.append(f"{line}\n")
            last_ascendancy = char['ascendancy']

        output.append(f"{separator}\n")
        return "".join(output)

    def start_search_thread(self):
        char_name = self.char_name_entry.get()
        if not char_name:
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", "Please enter a character name to search.")
            return

        self.fetch_button.configure(state="disabled")
        self.search_button.configure(state="disabled")
        self.stop_search_button.configure(state="normal")
        self.status_label.configure(text=f"Searching for {char_name}...")
        self.textbox.delete("1.0", "end")

        self.stop_search_event.clear()
        thread = threading.Thread(target=self.search_character, daemon=True)
        thread.start()

    def stop_search(self):
        self.stop_search_event.set()

    def search_character(self):
        selected_league_input = self.get_selected_league()
        deep_search = self.deep_search_check.get() == 1

        # Resolve name to ID for deep search
        league_id = self._get_league_id_from_name(selected_league_input) if deep_search else selected_league_input

        if not league_id:
            self.status_label.configure(text=f"Error: League '{selected_league_input}' not found.")
            return

        char_name_to_find = self.char_name_entry.get()
        # --- 1. Search already fetched data first for an instant result ---
        # Check if the character exists in the data we've already downloaded.
        if self.all_fetched_entries:
            self.status_label.configure(text=f"Searching {len(self.all_fetched_entries)} pre-fetched entries...")
            # We need to calculate the ascendancy rank within the local data
            local_ascendancy_counts = {asc: 0 for asc in ALL_ASCENDANCY_NAMES}
            for entry in self.all_fetched_entries:
                char_data = entry['character']
                ascendancy = char_data['class']
                if ascendancy in local_ascendancy_counts:
                    local_ascendancy_counts[ascendancy] += 1
                
                if char_data['name'] == char_name_to_find:
                    # Character found in the locally cached data!
                    asc_rank = local_ascendancy_counts[ascendancy]
                    result = f"Character Found (in pre-fetched data):\n"
                    result += f"  Name: {char_data['name']}\n"
                    result += f"  Level: {char_data['level']}\n"
                    result += f"  Class: {ascendancy}\n"
                    result += f"  ---\n"
                    result += f"  Global Rank: {entry['rank']}\n"
                    result += f"  Ascendancy Rank (in fetched list): {asc_rank}"
                    self.after(0, self.update_textbox, result)
                    self.after(0, self.status_label.configure, {"text": f"Search complete. Found {char_name_to_find} locally."})
                    self.after(0, self.reset_button_states)
                    return # Exit the function since we found the character

        # --- 2. If not found locally, start a full remote search ---
        # Reset state for a new search. This is crucial.
        current_offset = 0
        found_char = None
        ascendancy_counts = {asc: 0 for asc in ALL_ASCENDANCY_NAMES}

        while True: 
            # For character search, we still fetch sequentially to find the character ASAP.
            # The logic here remains the same. The user's request was about the "Fetch Characters" button.
            # If you want to speed this up too, we can apply a similar concurrent pattern.

            if self.stop_search_event.is_set():
                break # Manual stop

            self.after(0, self.status_label.configure, {"text": f"Searching... Scanned {current_offset} characters so far."})
            data = GGGAPIClient.fetch_ladder(league_id, limit=CHUNK_SIZE, offset=current_offset, deep_search=deep_search)

            is_first_fetch = current_offset == 0
            is_private_league = self.private_league_check.get() == 1
            
            # Check for invalid private league name on the first fetch.
            if is_first_fetch and (data is None or not data.get('entries')):
                error_message = f"❌ Error: League '{selected_league_input}' not found or is empty.\nPlease check the name and try again."
                self.after(0, self.update_textbox, error_message)
                break # Stop searching

            if data is None: 
                self.after(0, self.update_textbox, "Error fetching ladder data.")
                break # API error
            entries = data.get('entries', [])
            if not entries: 
                # Reached the end of the ladder
                found_char = None # Ensure found_char is None
                break 
            for entry in entries:
                if self.stop_search_event.is_set():
                    break
                char_data = entry['character']
                ascendancy = char_data['class']
                
                if ascendancy in ascendancy_counts:
                    ascendancy_counts[ascendancy] += 1

                if char_data['name'] == char_name_to_find:
                    found_char = char_data
                    found_char['global_rank'] = entry['rank']
                    found_char['ascendancy_rank'] = ascendancy_counts.get(ascendancy)
                    break
            
            if found_char:
                break

            current_offset += CHUNK_SIZE
            if current_offset >= 15000 and not deep_search:
                break # Stop public search at 15k
            
            # Add a small delay to respect API rate limits
            time.sleep(0.5)

        if self.stop_search_event.is_set():
            self.after(0, self.status_label.configure, {"text": "Search stopped."})
            self.after(0, self.update_textbox, "Search was cancelled.")
        elif found_char:
            result = f"Character Found:\n"
            result += f"  Name: {found_char['name']}\n"
            result += f"  Level: {found_char['level']}\n"
            result += f"  Class: {found_char['class']}\n\n"
            result += f"  ---\n"
            result += f"  Global Rank: {found_char['global_rank']}\n"
            result += f"  Ascendancy Rank: {found_char['ascendancy_rank']}"
            self.after(0, self.update_textbox, result)
            self.after(0, self.status_label.configure, {"text": f"Search complete. Found {char_name_to_find}."})
        elif found_char is None: # Only show "not found" if the search completed without finding the char
            message = f"Character '{char_name_to_find}' not found after scanning {current_offset} entries."
            self.after(0, self.update_textbox, message)
            self.after(0, self.status_label.configure, {"text": "Search complete. Character not found."})

        self.after(0, self.reset_button_states)

    def reset_button_states(self):
        """Helper function to re-enable buttons after an operation."""
        # Schedule the final UI state updates on the main thread
        self.fetch_button.configure(state="normal")
        self.search_button.configure(state="normal")
        self.stop_search_button.configure(state="disabled")