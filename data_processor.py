STANDARD_ASCENDANCIES = [
    "Ascendant", "Assassin", "Berserker", "Champion", "Chieftain", 
    "Deadeye", "Elementalist", "Gladiator", "Guardian", "Hierophant", 
    "Inquisitor", "Juggernaut", "Necromancer", "Occultist", "Pathfinder", 
    "Saboteur", "Slayer", "Trickster", "Warden"
]

TEMPORARY_ASCENDANCIES = [
    "Ancestral Commander", "Antiquarian", "Architect of Chaos", "Aristocrat", 
    "Behemoth", "Blind Prophet", "Bog Shaman", "Daughter of Oshabi", 
    "Gambler", "Harbinger", "Herald", "Paladin", "Polytheist", 
    "Puppeteer", "Scavenger", "Servant of Arakaali", "Surfcaster", 
    "Whisperer", "Wildspeaker"
]

ALL_ASCENDANCY_NAMES = STANDARD_ASCENDANCIES + TEMPORARY_ASCENDANCIES

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
    for index, entry in enumerate(all_fetched_entries):
        char_data = entry['character']
        ascendancy = char_data['class']
        
        if ascendancy not in ascendancy_groups:
             continue 
        
        asc_rank = len(ascendancy_groups[ascendancy]) + 1

        character_info = {
            'ascendancy': ascendancy,
            'level': char_data['level'],
            'xp': char_data['experience'],
            'name': char_data['name'],
            'global_rank': entry['rank'],
            'asc_rank': asc_rank,
            'dead': entry.get('dead', False),
            'retired': entry.get('retired', False)
        }

        if len(ascendancy_groups[ascendancy]) < limit:
            ascendancy_groups[ascendancy].append(character_info)

    # 2. Final Consolidation and Sorting
    final_ladder_list = []
    for asc_list in ascendancy_groups.values():
        final_ladder_list.extend(asc_list)
        
    final_ladder_list.sort(key=lambda x: (x['ascendancy'], -x['level']))
    
    return final_ladder_list