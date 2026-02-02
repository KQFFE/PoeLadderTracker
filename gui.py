import customtkinter
import threading
import time
import bisect
# Use the new singleton API client
from api import GGGAPIClient
from data_processor import process_ladder_data, ALL_ASCENDANCY_NAMES, STANDARD_ASCENDANCIES, TEMPORARY_ASCENDANCIES

CHUNK_SIZE = 200

# Cumulative XP required to reach each level (Index 0 = Level 1, Index 99 = Level 100)
XP_THRESHOLDS = [
    0, 525, 1760, 3785, 7105, 11555, 17490, 24440, 33270, 43480, 
    55260, 68735, 84025, 101275, 120635, 142245, 166260, 192845, 222180, 254455, 
    289865, 328635, 371005, 417210, 467495, 522125, 581370, 645520, 714890, 789800, 
    870610, 957670, 1051380, 1152180, 1260490, 1376770, 1501510, 1635220, 1778470, 1931840, 
    2095950, 2271400, 2458880, 2659110, 2872840, 3100850, 3344000, 3603180, 3879300, 4173340, 
    4486300, 4819200, 5173240, 5549440, 5949080, 6373380, 6823740, 7301590, 7808410, 8345790, 
    9014110, 9642440, 10300330, 10989400, 11711210, 12467530, 13260310, 14091650, 14963630, 15878350,
    16837910, 17844430, 18900030, 20006830, 21167050, 22383000, 23657000, 24991400, 26389590, 27854000,
    29387690, 30994240, 32676590, 34438830, 36284680, 38217650, 40241980, 42361570, 44580960, 46904320,
    49336530, 51882550, 54547440, 57336320, 60254390, 63307990, 66503570, 69847620, 73346730, 77007690,
    80837590, 84844800, 89037020, 93422240, 98008750, 102805050, 107820020, 113063810, 118546860, 124279830,
    130273670, 136539690, 143089510, 149935150, 157088920, 164563460, 172371710, 180527890, 189046650, 197943090,
    207232750, 216932680, 227059440, 237630000, 248661850, 260172950, 272181750, 284707200, 297770640, 311394640,
    325603050, 340419960, 355870690, 371976740, 388765800, 406268850, 424510040, 443527560, 463351800, 484015380,
    505552380, 528000000, 551398610, 575781650, 601196630, 627685280, 655293510, 684069220, 714062300, 745323700,
    777906360, 811865920, 847259890, 884147560, 922590960, 962656590, 1004415360, 1047942660, 1093318250, 1140625140,
    1189940290, 1241353650, 1294957250, 1350844010, 1409118080, 1469884060, 1533247040, 1599312500, 1668186440, 1740005340,
    1814886150, 1892956380, 1974354000, 2059217440, 2147686550, 2239902660, 2336008570, 2436158510, 2540508200, 2649215860,
    2762441200, 2880355400, 3003131150, 3130942660, 3263966290, 3402380750, 3546368010, 3696112040, 3851799730, 4013611040,
    4181728120, 4250334444
]

class RaceModeWindow(customtkinter.CTkToplevel):
    def __init__(self, master, target_character_entry):
        super().__init__(master)
        self.master_app = master
        self.target_entry = target_character_entry
        self.auto_refresh_job = None
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.title("Race Mode")
        self.geometry("560x460")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Main Content

        # --- Widgets ---
        # Save original colors for transparency toggle
        self.orig_window_bg = self._fg_color

        # --- Header Frame (Row 0) ---
        self.header_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(0, weight=1)

        # --- Main Frame (Row 1) ---
        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.orig_frame_bg = self.main_frame._fg_color
        self.header_frame.configure(fg_color=self.orig_frame_bg)

        # Left: Tracking + Asc Rank
        self.tracking_label = customtkinter.CTkLabel(self.header_frame, text="", font=customtkinter.CTkFont(weight="bold"))
        self.tracking_label.grid(row=0, column=0, sticky="w", padx=5)

        # Right: Ladder Name (Class) - No "Ladder" suffix
        self.ladder_label = customtkinter.CTkLabel(self.header_frame, text=self.target_entry['character']['class'], font=customtkinter.CTkFont(weight="bold", size=14))
        self.ladder_label.grid(row=0, column=1, sticky="e", padx=5)

        # --- Define Colors ---
        BEHIND_COLOR = ("gray75", "gray17") # Slightly darker than frame
        AHEAD_COLOR = ("gray70", "gray14")  # Even darker
        TRACK_COLOR = ("gray65", "gray25")  # Highlight for tracked char

        # --- Display Labels ---
        # Ascendancy Frame (Row 1)
        self.asc_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.asc_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.asc_frame.grid_columnconfigure(0, weight=0)
        self.asc_frame.grid_columnconfigure(1, weight=1)
        self.asc_frame.grid_columnconfigure(2, weight=0)
        self.asc_frame.grid_columnconfigure(3, weight=0)

        # Ascendancy Ladder
        self.asc_ahead_labels = self.create_info_row(self.asc_frame, "Ahead:", 0, fg_color=AHEAD_COLOR)
        self.asc_track_labels = self.create_info_row(self.asc_frame, "You:", 1, fg_color=TRACK_COLOR)
        self.asc_behind_labels = self.create_info_row(self.asc_frame, "Behind:", 2, fg_color=BEHIND_COLOR)

        # Global Frame (Row 2)
        self.global_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.global_frame.grid(row=2, column=0, sticky="ew", pady=5)
        self.global_frame.grid_columnconfigure(0, weight=0)
        self.global_frame.grid_columnconfigure(1, weight=1)
        self.global_frame.grid_columnconfigure(2, weight=0)
        self.global_frame.grid_columnconfigure(3, weight=0)

        # Global Ladder
        self.global_header = self.create_header_label(self.global_frame, "Global Ladder", 0)
        self.global_ahead_labels = self.create_info_row(self.global_frame, "Ahead:", 1, fg_color=AHEAD_COLOR)
        self.global_track_labels = self.create_info_row(self.global_frame, "You:", 2, fg_color=TRACK_COLOR)
        self.global_behind_labels = self.create_info_row(self.global_frame, "Behind:", 3, fg_color=BEHIND_COLOR)
        
        # --- Footer Frame (Row 3) ---
        self.footer_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.footer_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=10)
        self.footer_frame.grid_columnconfigure(3, weight=1) # Spacer

        # Always on Top checkbox (Left)
        self.always_on_top_var = customtkinter.StringVar(value="on")
        self.always_on_top_check = customtkinter.CTkCheckBox(self.footer_frame, text="Always on Top", command=self.toggle_always_on_top, variable=self.always_on_top_var, onvalue="on", offvalue="off")
        self.always_on_top_check.grid(row=0, column=0, sticky="w", padx=(5, 5))
        self.toggle_always_on_top() # Set initial state

        # Transparent Background checkbox
        self.transparent_var = customtkinter.StringVar(value="off")
        self.transparent_check = customtkinter.CTkCheckBox(self.footer_frame, text="Transparent", command=self.toggle_transparency, variable=self.transparent_var, onvalue="on", offvalue="off")
        self.transparent_check.grid(row=0, column=1, sticky="w", padx=(5, 5))

        # Auto Refresh checkbox
        self.auto_refresh_var = customtkinter.StringVar(value="on")
        self.auto_refresh_check = customtkinter.CTkCheckBox(self.footer_frame, text="Auto Refresh", variable=self.auto_refresh_var, onvalue="on", offvalue="off", command=self.toggle_auto_refresh)
        self.auto_refresh_check.grid(row=0, column=2, sticky="w", padx=(5, 5))

        # View Mode Menu (Rightmost)
        self.view_mode_menu = customtkinter.CTkOptionMenu(self.footer_frame, values=["Ladders", "Ascendancy", "Global"], command=self.toggle_view_mode, width=110)
        self.view_mode_menu.grid(row=0, column=4, sticky="e", padx=5)

        # Refresh button (Row 4)
        self.refresh_button = customtkinter.CTkButton(self.main_frame, text="Refresh", command=self.refresh_data_thread)
        self.refresh_button.grid(row=4, column=0, pady=(5, 5), sticky="ew", padx=10)

        self.update_header_info()
        self.toggle_auto_refresh() # Set initial button state
        self.refresh_data_thread() # Initial data load

    def toggle_view_mode(self, choice):
        if choice == "Ladders":
            self.asc_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
            self.global_frame.grid(row=2, column=0, sticky="ew", pady=5)
        elif choice == "Ascendancy":
            self.asc_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
            self.global_frame.grid_forget()
        elif choice == "Global":
            self.asc_frame.grid_forget()
            self.global_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))

    def create_header_label(self, parent, text, row):
        label = customtkinter.CTkLabel(parent, text=text, font=customtkinter.CTkFont(weight="bold", underline=True))
        label.grid(row=row, column=0, columnspan=4, pady=(10, 2), sticky="w", padx=5)
        return label

    def create_info_row(self, parent, title, row, fg_color=None):
        # Create a frame to hold the row content and provide the background color
        row_frame = customtkinter.CTkFrame(parent, fg_color=fg_color, corner_radius=0)
        row_frame.grid(row=row, column=0, columnspan=4, sticky="nsew", pady=1)
        
        # Configure columns within the frame to match the desired layout
        row_frame.grid_columnconfigure(0, weight=0) # Title
        row_frame.grid_columnconfigure(1, weight=1) # Name
        row_frame.grid_columnconfigure(2, weight=0) # Progress Bar
        row_frame.grid_columnconfigure(3, weight=0) # XP
        row_frame.grid_columnconfigure(4, weight=0) # Rank

        # Title (Col 0)
        title_label = customtkinter.CTkLabel(row_frame, text=title, width=60, anchor="w", fg_color=fg_color)
        title_label.grid(row=0, column=0, sticky="ew", ipady=3, padx=(5,0))
        
        # Name (Lvl) (Col 1)
        name_label = customtkinter.CTkLabel(row_frame, text="--", anchor="w", fg_color=fg_color)
        name_label.grid(row=0, column=1, sticky="ew", ipady=3, padx=5)
        
        # Progress Bar (Col 2)
        progress_bar = customtkinter.CTkProgressBar(row_frame, height=10, width=100, corner_radius=0, progress_color="#2CC985", fg_color="white")
        progress_bar.grid(row=0, column=2, sticky="ew", padx=5)
        progress_bar.set(0)

        # XP (Col 3)
        xp_label = customtkinter.CTkLabel(row_frame, text="--", width=130, anchor="e", fg_color=fg_color)
        xp_label.grid(row=0, column=3, sticky="ew", ipady=3, padx=5)
        
        # Rank (Col 4)
        rank_label = customtkinter.CTkLabel(row_frame, text="#--", width=60, anchor="e", fg_color=fg_color)
        rank_label.grid(row=0, column=4, sticky="ew", ipady=3, padx=(0,5))
        
        return name_label, xp_label, rank_label, progress_bar

    def toggle_always_on_top(self):
        is_on_top = self.always_on_top_var.get() == "on"
        self.attributes("-topmost", is_on_top)

    def toggle_transparency(self):
        if self.transparent_var.get() == "on":
            # Use a specific color as the transparent key to make background invisible
            # but keep text and widgets opaque.
            TRANS_COLOR = "#000001"
            self.configure(fg_color=TRANS_COLOR)
            self.main_frame.configure(fg_color=TRANS_COLOR)
            self.attributes("-transparentcolor", TRANS_COLOR)
            self.attributes("-alpha", 1.0)
        else:
            self.configure(fg_color=self.orig_window_bg)
            self.main_frame.configure(fg_color=self.orig_frame_bg)
            self.attributes("-transparentcolor", "")
            self.attributes("-alpha", 1.0)

    def toggle_auto_refresh(self):
        if self.auto_refresh_var.get() == "off":
            if self.auto_refresh_job:
                self.after_cancel(self.auto_refresh_job)
                self.auto_refresh_job = None
            self.refresh_button.grid(row=4, column=0, pady=(5, 5), sticky="ew", padx=10)
        else:
            # If turned on, schedule a refresh if one isn't already running/scheduled
            if not self.auto_refresh_job:
                self.auto_refresh_job = self.after(60000, self.refresh_data_thread)
            self.refresh_button.grid_forget()

    def on_close(self):
        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)
        self.destroy()

    def refresh_data_thread(self):
        if self.auto_refresh_job:
            self.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None
        self.refresh_button.configure(state="disabled", text="Refreshing...")
        thread = threading.Thread(target=self.refresh_data, daemon=True)
        thread.start()

    def refresh_data(self):
        selected_league_input = self.master_app.get_selected_league()
        deep_search = self.master_app.deep_search_check.get() == 1
        league_id = self.master_app._get_league_id_from_name(selected_league_input)
        target_name = self.target_entry['character']['name'].lower()

        # Scan from the top to ensure accurate Ascendancy Rank
        current_offset = 0
        ascendancy_counts = {asc: 0 for asc in ALL_ASCENDANCY_NAMES}
        found_entry = None
        surrounding_entries = []
        prev_chunk = []

        while True:
            if not self.winfo_exists(): return

            data = GGGAPIClient.fetch_ladder(league_id, limit=CHUNK_SIZE, offset=current_offset, deep_search=deep_search)
            
            if not data or 'entries' not in data:
                break

            entries = data['entries']
            if not entries:
                break

            for i, entry in enumerate(entries):
                char_data = entry['character']
                asc = char_data['class']
                
                if asc in ascendancy_counts:
                    ascendancy_counts[asc] += 1
                
                # Stamp ranks on every entry so neighbors have data
                entry['ascendancy_rank'] = ascendancy_counts.get(asc)
                entry['rank'] = current_offset + i + 1
                
                if char_data['name'].lower() == target_name:
                    found_entry = entry
                    
                    # Construct context for neighbors
                    context = []
                    if prev_chunk:
                        context.extend(prev_chunk[-10:])
                    context.extend(entries)
                    
                    # If near end, try to fetch next chunk for "Behind" neighbor
                    if i >= len(entries) - 2:
                         next_data = GGGAPIClient.fetch_ladder(league_id, limit=10, offset=current_offset + CHUNK_SIZE, deep_search=deep_search)
                         if next_data and 'entries' in next_data:
                             # Process ranks for next chunk context
                             for n_i, n_entry in enumerate(next_data['entries']):
                                 n_asc = n_entry['character']['class']
                                 if n_asc in ascendancy_counts:
                                     ascendancy_counts[n_asc] += 1
                                 n_entry['ascendancy_rank'] = ascendancy_counts.get(n_asc)
                                 n_entry['rank'] = current_offset + CHUNK_SIZE + n_i + 1
                             context.extend(next_data['entries'])

                    surrounding_entries = context
            
            if found_entry:
                break

            prev_chunk = entries
            current_offset += CHUNK_SIZE
            
            time.sleep(0.1) # Prevent UI freeze during deep scans
            if current_offset >= 15000 and not deep_search:
                break
            if current_offset > 20000: # Safety cap
                break

        if found_entry:
            self.after(0, self.process_and_display_data, surrounding_entries, found_entry)
        else:
            error_message = "Character not found in ladder."
            self.after(0, self.global_ahead_labels[0].configure, {"text": error_message})
        self.after(0, self.on_refresh_complete)

    def on_refresh_complete(self):
        self.refresh_button.configure(state="normal", text="Refresh")
        # Schedule next refresh if auto-refresh is enabled
        if self.auto_refresh_var.get() == "on":
            self.auto_refresh_job = self.after(60000, self.refresh_data_thread)

    def process_and_display_data(self, surrounding_entries, updated_entry=None):
        my_original_name = self.target_entry['character']['name']
        
        # Find the updated entry for the target character
        if updated_entry:
            my_new_entry = updated_entry
        else:
            my_new_entry = next((e for e in surrounding_entries if e['character']['name'] == my_original_name), None)
        
        if not my_new_entry:
            # Handle case where character is not found in the refreshed data
            self.asc_ahead_labels[0].configure(text="Character not found in this data slice.")
            self.asc_behind_labels[0].configure(text="")
            self.global_ahead_labels[0].configure(text="")
            self.global_behind_labels[0].configure(text="")
            return

        # Update the window's state for the next refresh
        self.target_entry = my_new_entry
        
        # Update Header
        self.update_header_info()

        my_new_xp = int(my_new_entry['character']['experience'])
        my_ascendancy = my_new_entry['character']['class']

        def update_row_data(labels, neighbor_entry, target_xp, rank_field='rank'):
            name_label, xp_label, rank_label, progress_bar = labels
            if neighbor_entry:
                neighbor_xp = int(neighbor_entry['character']['experience'])
                xp_diff = neighbor_xp - target_xp
                name_label.configure(text=f"{neighbor_entry['character']['name']} (Lvl {neighbor_entry['character']['level']})")
                
                # Check if this is the tracked character
                if neighbor_entry['character']['name'] == self.target_entry['character']['name']:
                     xp_label.configure(text=f"XP: {neighbor_xp:,}")
                     xp_label.configure(text_color=("black", "white"))
                else:
                    xp_label.configure(text=f"XP: {xp_diff:+,}")
                    if xp_diff > 0:
                        xp_label.configure(text_color="#2CC985") # Green
                    elif xp_diff < 0:
                        xp_label.configure(text_color="#FF5252") # Red
                    else:
                        xp_label.configure(text_color=("black", "white"))

                rank_val = neighbor_entry.get(rank_field, '?')
                rank_label.configure(text=f"#{rank_val}")
                
                # Calculate Level Progress
                lvl = neighbor_entry['character']['level']
                curr_xp = neighbor_xp
                
                if lvl >= 100:
                    progress = 1.0
                elif curr_xp > 0:
                    # Dynamically find the XP bracket to ensure valid progress calculation
                    # regardless of the XP_THRESHOLDS list structure
                    idx = bisect.bisect_right(XP_THRESHOLDS, curr_xp) - 1
                    if idx >= 0 and idx < len(XP_THRESHOLDS) - 1:
                        start_xp = XP_THRESHOLDS[idx]
                        end_xp = XP_THRESHOLDS[idx + 1]
                        progress = (curr_xp - start_xp) / (end_xp - start_xp) if end_xp > start_xp else 0
                    else:
                        progress = 1.0 if idx >= len(XP_THRESHOLDS) - 1 else 0
                else:
                    progress = 0
                progress_bar.set(progress)
            else:
                name_label.configure(text="N/A")
                xp_label.configure(text="")
                xp_label.configure(text_color=("black", "white"))
                rank_label.configure(text="")
                progress_bar.set(0)

        # Helper to find neighbors in cached data if live data fails
        def get_fallback_neighbor(target_list, target_name, direction="ahead"):
            try:
                # Find index of self in the cached list
                idx = next(i for i, e in enumerate(target_list) if e['character']['name'] == target_name)
                if direction == "ahead":
                    return target_list[idx - 1] if idx > 0 else None
                else:
                    return target_list[idx + 1] if idx < len(target_list) - 1 else None
            except (StopIteration, ValueError):
                return None

        cached_entries = self.master_app.all_fetched_entries
        cached_asc_entries = [e for e in cached_entries if e['character']['class'] == my_ascendancy]

        # --- Process Global Ladder ---
        try:
            global_idx = surrounding_entries.index(my_new_entry)
            global_ahead = surrounding_entries[global_idx - 1] if global_idx > 0 else None
            if not global_ahead: global_ahead = get_fallback_neighbor(cached_entries, my_original_name, "ahead")
            
            global_behind = surrounding_entries[global_idx + 1] if global_idx < len(surrounding_entries) - 1 else None
            if not global_behind: global_behind = get_fallback_neighbor(cached_entries, my_original_name, "behind")

            update_row_data(self.global_ahead_labels, global_ahead, my_new_xp)
            update_row_data(self.global_behind_labels, global_behind, my_new_xp)
            update_row_data(self.global_track_labels, my_new_entry, my_new_xp)
        except ValueError:
            self.global_ahead_labels[0].configure(text="Error processing global rank.")
            self.global_behind_labels[0].configure(text="")

        # --- Process Ascendancy Ladder ---
        asc_entries = [e for e in surrounding_entries if e['character']['class'] == my_ascendancy]
        try:
            asc_idx = asc_entries.index(my_new_entry)
            asc_ahead = asc_entries[asc_idx - 1] if asc_idx > 0 else None
            if not asc_ahead: asc_ahead = get_fallback_neighbor(cached_asc_entries, my_original_name, "ahead")
            
            asc_behind = asc_entries[asc_idx + 1] if asc_idx < len(asc_entries) - 1 else None
            if not asc_behind: asc_behind = get_fallback_neighbor(cached_asc_entries, my_original_name, "behind")
            
            update_row_data(self.asc_ahead_labels, asc_ahead, my_new_xp, 'ascendancy_rank')
            update_row_data(self.asc_behind_labels, asc_behind, my_new_xp, 'ascendancy_rank')
            update_row_data(self.asc_track_labels, my_new_entry, my_new_xp, 'ascendancy_rank')
        except ValueError:
            self.asc_ahead_labels[0].configure(text="Error processing ascendancy rank.")
            self.asc_behind_labels[0].configure(text="")

    def update_header_info(self):
        asc_rank = self.target_entry.get('ascendancy_rank', '?')
        name = self.target_entry['character']['name']
        text = f"Tracking: {name}  |  Asc: #{asc_rank}"
        self.tracking_label.configure(text=text)

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
        self.found_character_for_race_mode = None
        self.race_mode_window = None

        # --- Font ---
        self.textbox_font = customtkinter.CTkFont(family="Consolas", size=12)

        # --- Options Frame ---
        self.options_frame = customtkinter.CTkFrame(self)
        self.options_frame.grid(row=0, column=0, padx=20, pady=(20,10), sticky="ew")
        self.options_frame.grid_columnconfigure(0, weight=1)
        self.options_frame.grid_columnconfigure(1, weight=1)

        self.league_label = customtkinter.CTkLabel(self.options_frame, text="Ladder")
        self.league_label.grid(row=0, column=0, padx=10, pady=(10,0), sticky="w")
        self.league_menu = customtkinter.CTkOptionMenu(self.options_frame, values=["Fetching leagues..."], command=self.on_league_change)
        self.league_menu.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")

        self.ascendancy_label = customtkinter.CTkLabel(self.options_frame, text="Ascendancy")
        self.ascendancy_label.grid(row=0, column=1, padx=10, pady=(10,0), sticky="w")
        self.ascendancy_menu = customtkinter.CTkOptionMenu(self.options_frame, values=["All"] + STANDARD_ASCENDANCIES, command=self.on_ascendancy_change)
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
        self.char_name_entry.bind("<Return>", self.start_search_thread)

        self.search_button = customtkinter.CTkButton(self.search_frame, text="Search Character", command=self.start_search_thread)
        self.search_button.grid(row=1, column=1, padx=(10,5), pady=(0,10))
        
        self.stop_search_button = customtkinter.CTkButton(self.search_frame, text="Stop", command=self.stop_search, state="disabled")
        self.stop_search_button.grid(row=1, column=2, padx=(0,5), pady=(0,10))

        self.race_mode_button = customtkinter.CTkButton(self.search_frame, text="Race Mode", command=self.launch_race_mode_thread, state="disabled")
        self.race_mode_button.grid(row=1, column=3, padx=(0,10), pady=(0,10))
        
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

    def on_league_change(self, choice):
        # Filter ascendancies based on league type
        if "Phrecia" in choice:
            new_values = ["All"] + TEMPORARY_ASCENDANCIES
        else:
            new_values = ["All"] + STANDARD_ASCENDANCIES
        
        self.ascendancy_menu.configure(values=new_values)
        self.ascendancy_menu.set("All")
        self.show_more_button.configure(state="disabled")

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
            # The proxy returns a direct JSON list of leagues.
            # We assign it directly and check if it's a valid list.
            leagues = leagues_data

            if isinstance(leagues, list):
                # The proxy filters to PC leagues; we just need to display them.
                self.all_leagues_data = leagues # Store full data for ID lookup
                league_display_names = [league.get('text', league['id']) for league in leagues]
                league_display_names.sort()
                self.league_menu.configure(values=league_display_names)

                if league_display_names:
                    self.league_menu.set(league_display_names[0])
                    self.on_league_change(league_display_names[0])
                self.status_label.configure(text="Ready.")
            elif isinstance(leagues, dict) and 'error' in leagues:
                error_message = leagues.get('message', 'An unknown API error occurred.')
                self.status_label.configure(text=f"Error: {error_message}")
                self.league_menu.configure(values=["Error: Check Status"])
                self.league_menu.set("Error: Check Status")
                self.fetch_button.configure(state="disabled")
                self.search_button.configure(state="disabled")
                self.all_leagues_data = [] # Clear data on error
            else:
                print("Error: Could not parse leagues from API response.")
                self.league_menu.configure(values=["Error fetching leagues"])
                self.league_menu.set("Error fetching leagues")
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
        self.race_mode_button.configure(state="disabled")
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
        
        # Only wait for the ascendancies relevant to the current league type
        selected_league = self.get_selected_league() or ""
        if "Phrecia" in selected_league:
            return all(ascendancy_counts[asc] >= self.current_limit for asc in TEMPORARY_ASCENDANCIES)
        else:
            return all(ascendancy_counts[asc] >= self.current_limit for asc in STANDARD_ASCENDANCIES)

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

        # Always resolve the league name to its proper ID for the API.
        league_id = self._get_league_id_from_name(selected_league_input)

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
        self.after(0, self.reset_button_states)

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

    def start_search_thread(self, event=None):
        char_name = self.char_name_entry.get()
        if not char_name:
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", "Please enter a character name to search.")
            return

        self.fetch_button.configure(state="disabled")
        self.search_button.configure(state="disabled")
        self.stop_search_button.configure(state="normal")
        self.race_mode_button.configure(state="disabled")
        self.status_label.configure(text=f"Searching for {char_name}...")
        self.textbox.delete("1.0", "end")

        self.stop_search_event.clear()
        thread = threading.Thread(target=self.search_character, daemon=True)
        thread.start()

    def stop_search(self):
        self.stop_search_event.set()

    def launch_race_mode_thread(self):
        if self.race_mode_window is not None and self.race_mode_window.winfo_exists():
            self.race_mode_window.focus()
            return

        if not self.found_character_for_race_mode:
            return
        
        self.race_mode_window = RaceModeWindow(
            master=self, 
            target_character_entry=self.found_character_for_race_mode
        )
        self.race_mode_window.focus()

    def search_character(self):
        selected_league_input = self.get_selected_league()
        deep_search = self.deep_search_check.get() == 1
        league_id = self._get_league_id_from_name(selected_league_input)

        if not league_id:
            self.status_label.configure(text=f"Error: League '{selected_league_input}' not found.")
            return

        char_name_to_find = self.char_name_entry.get().strip()

        current_offset = 0
        self.all_fetched_entries = [] # Clear cache for new search
        found_entry = None
        ascendancy_counts = {asc: 0 for asc in ALL_ASCENDANCY_NAMES}

        while True:
            if self.stop_search_event.is_set():
                break

            self.after(0, self.status_label.configure, {"text": f"Searching... Scanned {current_offset} characters so far."})
            data = GGGAPIClient.fetch_ladder(league_id, limit=CHUNK_SIZE, offset=current_offset, deep_search=deep_search)

            if data and isinstance(data, dict) and data.get('error'):
                self.after(0, self.update_textbox, f"Error: {data.get('message', 'Unknown API error')}")
                break

            entries = data.get('entries', [])
            if not entries:
                break
            
            self.all_fetched_entries.extend(entries) # Store for Race Mode fallback
            self.current_offset = current_offset + CHUNK_SIZE # Sync state so "Show More" works correctly

            for i, entry in enumerate(data['entries']):
                if self.stop_search_event.is_set():
                    break
                char_data = entry['character']
                ascendancy = char_data['class']
                
                if ascendancy in ascendancy_counts:
                    ascendancy_counts[ascendancy] += 1

                entry['ascendancy_rank'] = ascendancy_counts.get(ascendancy)
                entry['rank'] = current_offset + i + 1

                if entry['character']['name'].lower() == char_name_to_find.lower():
                    found_entry = entry
            
            if found_entry:
                break

            current_offset += CHUNK_SIZE
            if current_offset >= 15000 and not deep_search:
                break
            
            time.sleep(0.1) # Reduced sleep for faster searching

        if self.stop_search_event.is_set():
            self.after(0, self.status_label.configure, {"text": "Search stopped."})
            self.after(0, self.update_textbox, "Search was cancelled.")
        elif found_entry:
            self.found_character_for_race_mode = found_entry
            char_data = found_entry['character']
            result = f"Character Found:\n"
            result += f"  Name: {char_data['name']}\n"
            result += f"  Level: {char_data['level']}\n"
            result += f"  Class: {char_data['class']}\n\n"
            result += f"  ---\n"
            result += f"  Global Rank: {found_entry['rank']}\n"
            result += f"  Ascendancy Rank: {found_entry['ascendancy_rank']}"
            self.after(0, self.update_textbox, result)
            self.after(0, self.status_label.configure, {"text": f"Search complete. Found {char_name_to_find}."})
            self.after(0, self.race_mode_button.configure, {"state": "normal"})
        else:
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
        
        if self.found_character_for_race_mode:
            self.race_mode_button.configure(state="normal")
        else:
            self.race_mode_button.configure(state="disabled")
            
        if self.ascendancy_menu.get() != "All":
            self.show_more_button.configure(state="normal")
        else:
            self.show_more_button.configure(state="disabled")