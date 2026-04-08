STANDARD_ASCENDANCIES = [
    "Ascendant", "Assassin", "Berserker", "Champion", "Chieftain", "Deadeye",
    "Elementalist", "Gladiator", "Guardian", "Hierophant", "Inquisitor",
    "Juggernaut", "Necromancer", "Occultist", "Pathfinder", "Reliquarian",
    "Saboteur", "Slayer", "Trickster", "Warden"
]

TEMPORARY_ASCENDANCIES = [
    "Ancestral Commander", "Antiquarian", "Architect of Chaos", "Aristocrat", 
    "Behemoth", "Blind Prophet", "Bog Shaman", "Daughter of Oshabi", 
    "Gambler", "Harbinger", "Herald", "Paladin", "Polytheist", 
    "Puppeteer", "Scavenger", "Servant of Arakaali", "Surfcaster", 
    "Whisperer", "Wildspeaker"
]
 
BASE_CLASSES = [
    "Duelist", "Marauder", "Ranger", "Scion", "Shadow", "Templar", "Witch"
]
 
ALL_ASCENDANCY_NAMES = STANDARD_ASCENDANCIES + TEMPORARY_ASCENDANCIES + BASE_CLASSES

# Mapping of every subclass to its parent base class for aggregate ranking
CLASS_TO_BASE = {
    "Assassin": "Shadow", "Saboteur": "Shadow", "Trickster": "Shadow", "Shadow": "Shadow",
    "Slayer": "Duelist", "Gladiator": "Duelist", "Champion": "Duelist", "Duelist": "Duelist",
    "Juggernaut": "Marauder", "Berserker": "Marauder", "Chieftain": "Marauder", "Marauder": "Marauder",
    "Deadeye": "Ranger", "Pathfinder": "Ranger", "Warden": "Ranger", "Ranger": "Ranger",
    "Guardian": "Templar", "Hierophant": "Templar", "Inquisitor": "Templar", "Templar": "Templar",
    "Necromancer": "Witch", "Occultist": "Witch", "Elementalist": "Witch", "Witch": "Witch",
    "Ascendant": "Scion", "Scion": "Scion",
    # Event specific mappings (best effort)
    "Reliquarian": "Scion", "Antiquarian": "Duelist", "Aristocrat": "Scion", "Behemoth": "Marauder", 
    "Blind Prophet": "Templar", "Wildspeaker": "Ranger", "Whisperer": "Witch", 
    "Architect of Chaos": "Shadow"
}
 
def process_ladder_data(all_fetched_entries, selected_ascendancy=None, limit=5):
    """
    Filters the top characters for each Ascendancy from the raw ladder data,
    then sorts them as requested.
    If a selected_ascendancy is provided, it only returns data for that one.
    The number of characters per ascendancy is controlled by the limit parameter.
    """
    
    # Determine if we are filtering by a base class (Class Ranking) or a specific ascendancy
    is_base_filter = selected_ascendancy in BASE_CLASSES
    
    if is_base_filter:
        # Aggregate all matching subclasses into one group named after the base class
        ascendancy_groups = {selected_ascendancy: []}
    else:
        # Standard behavior: separate groups for every individual class/ascendancy
        ascendancies_to_process = [selected_ascendancy] if selected_ascendancy else ALL_ASCENDANCY_NAMES
        ascendancy_groups = {asc: [] for asc in ascendancies_to_process}
    
    # 1. Core Grouping Logic
    for index, entry in enumerate(all_fetched_entries):
        char_data = entry['character']
        actual_class = char_data['class']
        
        if is_base_filter:
            # Check if this character's parent matches the selected base class
            if CLASS_TO_BASE.get(actual_class) == selected_ascendancy:
                target_group = selected_ascendancy
            else:
                continue
        else:
            if actual_class not in ascendancy_groups:
                continue
            target_group = actual_class
        
        character_info = {
            'ascendancy': actual_class, # Keep the specific name for display
            'group': target_group,
            'level': char_data['level'],
            'xp': char_data['experience'],
            'name': char_data['name'],
            'global_rank': entry['rank'],
            'asc_rank': 0, # Temporarily set to 0, will be re-assigned after sorting
            'dead': entry.get('dead', False),
            'retired': entry.get('retired', False)
        }
        ascendancy_groups[target_group].append(character_info)

    # 2. Final Consolidation and Sorting
    final_ladder_list = []
    for asc_list in ascendancy_groups.values():
        final_ladder_list.extend(asc_list)
        
    # If base class ranking, sort by global rank. Otherwise, group by ascendancy name then level.
    if is_base_filter: # For base classes, sort by global rank
        final_ladder_list.sort(key=lambda x: x['global_rank'])
    else:
        final_ladder_list.sort(key=lambda x: (x['ascendancy'], -x['level']))

    # Re-assign asc_rank after final sort and before applying the limit.
    # This ensures asc_rank reflects the rank within the *final, sorted* list
    # for the specific group (either individual ascendancy or aggregated base class).
    if is_base_filter:
        for i, char_info in enumerate(final_ladder_list):
            char_info['asc_rank'] = i + 1
    else: # For individual ascendancies, re-rank within their sorted groups
        current_asc = None
        rank_in_group = 0
        for i, char_info in enumerate(final_ladder_list):
            if char_info['ascendancy'] != current_asc:
                current_asc = char_info['ascendancy']
                rank_in_group = 1
            else:
                rank_in_group += 1
            char_info['asc_rank'] = rank_in_group

    # Return the top 'limit' characters for each individual group/ascendancy
    return [c for c in final_ladder_list if c['asc_rank'] <= limit]