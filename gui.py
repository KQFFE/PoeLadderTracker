import customtkinter
import threading
import unicodedata
# Use the new singleton API client
from api import GGGAPIClient
from data_processor import process_ladder_data, ALL_ASCENDANCY_NAMES

CHUNK_SIZE = 200 # Define chunk size, as it was previously in api_client

def get_display_width(s):
    width = 0
    for char in s:
        if unicodedata.east_asian_width(char) in ('F', 'W'):
            width += 2
        else:
            width += 1
    return width

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

        self.fetch_button = customtkinter.CTkButton(self.options_frame, text="Fetch Characters", command=self.start_fetch_thread)
        self.fetch_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

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

    def get_selected_league(self):
        try:
            if self.private_league_check.get() == 1:
                return self.private_league_entry.get()
            else:
                return self.league_menu.get()
        except Exception:
            # This can happen if the menu is not yet populated
            return None

    def toggle_private_league(self):
        if self.private_league_check.get() == 1: # Checked
            self.league_menu.configure(state="disabled")
            self.private_league_entry.configure(state="normal")
        else: # Unchecked
            # Re-enable only if leagues were successfully loaded
            self.league_menu.configure(state="normal")
            self.private_league_entry.configure(state="disabled")

    def on_ascendancy_change(self, choice):
        if choice == "All":
            self.show_more_button.configure(state="disabled")
        else:
            self.show_more_button.configure(state="normal")

    def load_leagues(self):
        def update_ui(leagues_data):
            if leagues_data:
                league_ids = [league['id'] for league in leagues_data]
                self.league_menu.configure(values=league_ids)
                if league_ids:
                    self.league_menu.set(league_ids[0])
            else:
                self.league_menu.configure(values=["Error fetching leagues"])
                self.league_menu.set("Error fetching leagues")

        def task():
            leagues = GGGAPIClient.fetch_leagues()
            self.after(0, update_ui, leagues)
        
        thread = threading.Thread(target=task)
        thread.start()

    def start_fetch_thread(self):
        self.current_limit = 10
        self.all_fetched_entries = []
        self.current_offset = 0
        self.fetch_and_display_data_thread()

    def start_show_more_thread(self):
        self.current_limit += 20
        self.fetch_and_display_data_thread()

    def fetch_and_display_data_thread(self):
        self.fetch_button.configure(state="disabled")
        self.search_button.configure(state="disabled")
        self.stop_search_button.configure(state="disabled")
        self.show_more_button.configure(state="disabled")
        self.status_label.configure(text="Fetching data...")
        self.textbox.delete("1.0", "end")
        
        thread = threading.Thread(target=self.fetch_and_display_data)
        thread.start()

    def update_textbox(self, output):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", output)

    def fetch_and_display_data(self):
        league = self.get_selected_league()
        ascendancy = self.ascendancy_menu.get()
        if ascendancy == "All":
            ascendancy = None

        # Smart fetching loop
        while True:
            if self.stop_search_event.is_set(): break

            # Stop condition for single ascendancy fetch
            if ascendancy and self.current_offset >= 20000:
                break

            # Stop condition for "All" ascendancies
            if not ascendancy:
                ascendancy_counts = {asc: 0 for asc in ALL_ASCENDANCY_NAMES}
                for entry in self.all_fetched_entries:
                    char_class = entry['character']['class']
                    if char_class in ascendancy_counts:
                        ascendancy_counts[char_class] += 1
                if all(count >= self.current_limit for count in ascendancy_counts.values()) or self.current_offset >= 20000:
                    break

            self.status_label.configure(text=f"Fetching characters {self.current_offset} to {self.current_offset + CHUNK_SIZE}...")
            # Use the new API client to fetch a chunk of data
            data = GGGAPIClient.fetch_ladder(league, limit=CHUNK_SIZE, offset=self.current_offset)
            
            is_private_league = self.private_league_check.get() == 1
            is_first_fetch = self.current_offset == 0

            # Check for invalid private league name on the first fetch
            if is_first_fetch and is_private_league and (data is None or not data.get('entries')):
                error_message = f"❌ Error: Private league '{league}' not found or is empty.\nPlease check the name and try again."
                self.after(0, self.update_textbox, error_message)
                self.status_label.configure(text="Error: Private league not found.")
                break # Stop fetching

            if data is None: break # Generic error occurred
            
            entries = data.get('entries', [])
            if not entries: break # No more entries to fetch
            
            self.all_fetched_entries.extend(entries)
            self.current_offset += CHUNK_SIZE

            # Live update for "All" ascendancies
            if not ascendancy:
                final_results = process_ladder_data(self.all_fetched_entries, selected_ascendancy=ascendancy, limit=self.current_limit)
                output = self.format_results(final_results, league)
                self.after(0, self.update_textbox, output)

            # Stop condition for single ascendancy
            if ascendancy:
                count = sum(1 for entry in self.all_fetched_entries if entry['character']['class'] == ascendancy)
                if count >= self.current_limit:
                    break
        
        # Final update for single ascendancy
        if ascendancy:
            final_results = process_ladder_data(self.all_fetched_entries, selected_ascendancy=ascendancy, limit=self.current_limit)
            output = self.format_results(final_results, league)
            self.after(0, self.update_textbox, output)

        self.status_label.configure(text=f"Done. Showing top {self.current_limit} for {ascendancy if ascendancy else 'all ascendancies'}.")
        self.fetch_button.configure(state="normal")
        self.search_button.configure(state="normal")
        if self.ascendancy_menu.get() != "All":
            self.show_more_button.configure(state="normal")

    def format_results(self, final_results, league):
        width = 80
        header = f"✅ ASCENDANCY STANDINGS ✅".center(width)
        league_line = f"League: {league}".center(width)
        separator = "-" * width

        output = [f"{separator}\n", f"{header}\n", f"{league_line}\n", f"{separator}\n"]

        table_header = f"| {'ASCENDANCY':<15} | {'LEVEL':^7} | {'CHARACTER NAME':^35} "
        output.append(f"{table_header}\n")
        output.append(f"{separator}\n")

        last_ascendancy = None
        for char in final_results:
            if last_ascendancy and char['ascendancy'] != last_ascendancy:
                output.append(f"{separator}\n")
            
            asc_name = char['ascendancy']
            level = char['level']
            char_name = char['name']

            char_name_width = 35
            display_width = get_display_width(char_name)
            padding = char_name_width - display_width
            left_padding = padding // 2
            right_padding = padding - left_padding
            centered_char_name = f"{ ' ' * left_padding}{char_name}{ ' ' * right_padding}"

            line = f"| {asc_name:<15} | {level:^7} | {centered_char_name} "
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
        thread = threading.Thread(target=self.search_character)
        thread.start()

    def stop_search(self):
        self.stop_search_event.set()

    def search_character(self):
        league = self.get_selected_league()
        char_name_to_find = self.char_name_entry.get()
        
        current_offset = 0
        global_rank = 0
        ascendancy_rank = 0
        found_char = None
        ascendancy_counts = {asc: 0 for asc in ALL_ASCENDANCY_NAMES}

        while True: 
            if self.stop_search_event.is_set():
                break

            self.status_label.configure(text=f"Searching... Scanned {global_rank} characters so far.")
            # Use the new API client to fetch a chunk of data
            data = GGGAPIClient.fetch_ladder(league, limit=CHUNK_SIZE, offset=current_offset)

            if data is None: 
                self.textbox.insert("1.0", "Error fetching ladder data.")
                break
            
            entries = data.get('entries', [])
            if not entries: 
                self.textbox.insert("1.0", f"Character '{char_name_to_find}' not found in this ladder.")
                break

            for entry in entries:
                if self.stop_search_event.is_set():
                    break
                global_rank += 1
                char_data = entry['character']
                ascendancy = char_data['class']
                
                if ascendancy in ascendancy_counts:
                    ascendancy_counts[ascendancy] += 1

                if char_data['name'] == char_name_to_find:
                    found_char = char_data
                    ascendancy_rank = ascendancy_counts[ascendancy]
                    break
            
            if found_char:
                break

            current_offset += CHUNK_SIZE

        if self.stop_search_event.is_set():
            self.status_label.configure(text="Search stopped.")
            self.textbox.insert("1.0", "Search was cancelled.")
        elif found_char:
            result = f"Character Found:\n"
            result += f"  Name: {found_char['name']}\n"
            result += f"  Level: {found_char['level']}\n"
            result += f"  Class: {found_char['class']}\n"
            result += f"  ---\n"
            result += f"  Global Rank: {global_rank}\n"
            result += f"  Ascendancy Rank: {ascendancy_rank}"
            self.textbox.insert("1.0", result)
            self.status_label.configure(text=f"Search complete. Found {char_name_to_find}.")
        else:
            self.textbox.insert("1.0", f"Character '{char_name_to_find}' not found after scanning {global_rank} entries.")
            self.status_label.configure(text="Search complete. Character not found.")

        self.fetch_button.configure(state="normal")
        self.search_button.configure(state="normal")
        self.stop_search_button.configure(state="disabled")