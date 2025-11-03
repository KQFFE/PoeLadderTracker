ALL_ASCENDANCY_NAMES = [
    "Ascendant", "Assassin", "Berserker", "Champion", "Chieftain", 
    "Deadeye", "Elementalist", "Gladiator", "Guardian", "Hierophant", 
    "Inquisitor", "Juggernaut", "Necromancer", "Occultist", "Pathfinder", 
    "Saboteur", "Slayer", "Trickster", "Warden"
]

def process_ladder_data(all_fetched_entries, selected_ascendancy=None, limit=5):
    """
    Filters the top characters for each Ascendancy from the raw ladder data,
    then sorts them as requested.
    If a selected_ascendancy is provided, it only returns data for that one.
    The number of characters per ascendancy is controlled by the limit parameter.
    """
    
    ascendancies_to_process = [selected_ascendancy] if selected_ascendancy else ALL_ASCENDANCY_NAMES
    ascendancy_groups = {asc: [] for asc in ascendancies_to_process}
    
    # 1. Core Grouping Logic
    for entry in all_fetched_entries:
        char_data = entry['character']
        ascendancy = char_data['class']
        
        if ascendancy not in ascendancy_groups:
             continue 
        
        character_info = {
            'ascendancy': ascendancy,
            'level': char_data['level'],
            'xp': char_data['experience'],
            'name': char_data['name']
        }

        if len(ascendancy_groups[ascendancy]) < limit:
            ascendancy_groups[ascendancy].append(character_info)

    # 2. Final Consolidation and Sorting
    final_ladder_list = []
    for asc_list in ascendancy_groups.values():
        final_ladder_list.extend(asc_list)
        
    final_ladder_list.sort(key=lambda x: (x['ascendancy'], -x['level']))
    
    return final_ladder_list