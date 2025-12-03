// This script will replicate the logic from your gui.py file.

const CHUNK_SIZE = 200;

document.addEventListener('DOMContentLoaded', () => {
    // --- Element References ---
    const leagueMenu = document.getElementById('league-menu');
    const ascendancyMenu = document.getElementById('ascendancy-menu');
    const privateLeagueCheck = document.getElementById('private-league-check');
    const privateLeagueEntry = document.getElementById('private-league-entry');
    const deepSearchCheck = document.getElementById('deep-search-check');
    const fetchButton = document.getElementById('fetch-button');
    const charNameEntry = document.getElementById('char-name-entry');
    const searchButton = document.getElementById('search-button');
    const stopButton = document.getElementById('stop-button');
    const resultsTextbox = document.getElementById('results-textbox');
    const showMoreButton = document.getElementById('show-more-button');
    const statusBar = document.getElementById('status-bar');

    // --- State Variables ---
    let allLeaguesData = [];
    let allFetchedEntries = [];
    let currentLimit = 20;
    let currentOffset = 0;
    let stopFlag = false;

    const ALL_ASCENDANCY_NAMES = [
        "Ascendant", "Assassin", "Berserker", "Champion", "Chieftain",
        "Deadeye", "Elementalist", "Gladiator", "Guardian", "Hierophant",
        "Inquisitor", "Juggernaut", "Necromancer", "Occultist", "Pathfinder",
        "Saboteur", "Slayer", "Trickster", "Warden"
    ];

    // --- Initialization ---

    function populateAscendancies() {
        ascendancyMenu.innerHTML = '<option>All</option>';
        ALL_ASCENDANCY_NAMES.forEach(asc => {
            const option = document.createElement('option');
            option.value = asc;
            option.textContent = asc;
            ascendancyMenu.appendChild(option);
        });
    }

    async function loadLeagues() {
        try {
            const response = await fetch('/leagues');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const leagues = await response.json();

            allLeaguesData = leagues;
            leagueMenu.innerHTML = ''; // Clear "fetching..."
            leagues.forEach(league => {
                const option = document.createElement('option');
                // The API gives us 'id' and 'text'. We'll use 'text' for display.
                option.value = league.text;
                option.textContent = league.text;
                leagueMenu.appendChild(option);
            });
        } catch (error) {
            console.error("Error fetching leagues:", error);
            leagueMenu.innerHTML = '<option>Error fetching leagues</option>';
        }
    }

    // --- Event Listeners ---

    privateLeagueCheck.addEventListener('change', () => {
        leagueMenu.disabled = privateLeagueCheck.checked;
        privateLeagueEntry.disabled = !privateLeagueCheck.checked;
        if (privateLeagueCheck.checked) {
            deepSearchCheck.checked = false; // Deep search is for public leagues
        }
    });

    deepSearchCheck.addEventListener('change', () => {
        if (deepSearchCheck.checked) {
            privateLeagueCheck.checked = false;
            leagueMenu.disabled = false;
            privateLeagueEntry.disabled = true;
        }
    });

    fetchButton.addEventListener('click', startFetch);
    searchButton.addEventListener('click', startSearch);
    showMoreButton.addEventListener('click', showMore);

    stopButton.addEventListener('click', () => {
        stopFlag = true;
        console.log("Search stopped by user.");
        statusBar.textContent = "Search stopped.";
        resetButtonStates();
    });

    // --- Helper Functions ---

    function getSelectedLeagueName() {
        if (privateLeagueCheck.checked) {
            return privateLeagueEntry.value;
        }
        return leagueMenu.value;
    }

    function getSelectedLeagueId() {
        const selectedName = getSelectedLeagueName();
        const league = allLeaguesData.find(l => l.text === selectedName);
        // The authenticated API needs the 'id', the public one can use the name.
        // We'll always try to return the ID if we can find it.
        return league ? league.id : selectedName; 
    }

    function setButtonsState(isFetching) {
        fetchButton.disabled = isFetching;
        searchButton.disabled = isFetching;
        stopButton.disabled = !isFetching;
        showMoreButton.disabled = isFetching || ascendancyMenu.value === "All";
    }

    function resetButtonStates() {
        setButtonsState(false);
    }

    function formatResults(results, leagueName) {
        const header = `✅ ASCENDANCY STANDINGS ✅`;
        const leagueLine = `League: ${leagueName}`;
        const separator = "-".repeat(90);

        let output = `${separator}\n${header.padStart(45 + header.length/2)}\n${leagueLine.padStart(45 + leagueLine.length/2)}\n${separator}\n`;
        output += `ASCENDANCY\tLEVEL\tCHARACTER NAME\tRANK (Asc/Global)\n`;
        output += `${separator}\n`;

        let lastAscendancy = null;
        for (const char of results) {
            if (lastAscendancy && char.ascendancy !== lastAscendancy) {
                output += `${separator}\n`;
            }
            const rankStr = `${char.asc_rank} / ${char.global_rank}`;
            output += `${char.ascendancy}\t${char.level}\t${char.name}\t${rankStr}\n`;
            lastAscendancy = char.ascendancy;
        }
        output += `${separator}\n`;
        return output;
    }

    async function apiFetchLadder(leagueId, offset, deepSearch) {
        const endpoint = deepSearch ? 'ladder' : 'public-ladder';
        const url = `/${endpoint}/${encodeURIComponent(leagueId)}?limit=${CHUNK_SIZE}&offset=${offset}`;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                console.error(`API Error: ${response.statusText}`);
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error("Network error fetching ladder:", error);
            return null;
        }
    }

    // --- Core Logic Functions ---

    function startFetch() {
        allFetchedEntries = [];
        currentOffset = 0;
        currentLimit = 20;
        fetchAndDisplayData();
    }

    function showMore() {
        currentLimit += 50;
        fetchAndDisplayData();
    }

    async function fetchAndDisplayData() {
        setButtonsState(true);
        stopFlag = false;
        statusBar.textContent = "Fetching data...";
        resultsTextbox.textContent = "";

        const leagueName = getSelectedLeagueName();
        const leagueId = getSelectedLeagueId();
        const ascendancy = ascendancyMenu.value === "All" ? null : ascendancyMenu.value;

        // This is a simplified version of the Python fetching loop.
        // A full implementation would check _should_stop_fetching inside the loop.
        while (!stopFlag && currentOffset < 20000) {
            statusBar.textContent = `Fetching characters ${currentOffset} to ${currentOffset + CHUNK_SIZE}...`;
            const data = await apiFetchLadder(leagueId, currentOffset, deepSearchCheck.checked);

            if (stopFlag) break;
            if (!data || !data.entries || data.entries.length === 0) {
                break; // No more data or an error occurred
            }

            allFetchedEntries.push(...data.entries);
            currentOffset += CHUNK_SIZE;

            // Live update for "All" ascendancies
            if (!ascendancy) {
                const processed = processLadderData(allFetchedEntries, null, currentLimit);
                resultsTextbox.textContent = formatResults(processed, leagueName);
            }

            await new Promise(resolve => setTimeout(resolve, 250)); // Respect rate limits
        }

        // Final update
        const processed = processLadderData(allFetchedEntries, ascendancy, currentLimit);
        resultsTextbox.textContent = formatResults(processed, leagueName);
        statusBar.textContent = `Done. Showing top ${currentLimit} for ${ascendancy || 'all ascendancies'}.`;
        resetButtonStates();
    }

    async function startSearch() {
        const charName = charNameEntry.value.trim();
        if (!charName) {
            resultsTextbox.textContent = "Please enter a character name to search.";
            return;
        }

        setButtonsState(true);
        stopFlag = false;
        statusBar.textContent = `Searching for ${charName}...`;
        resultsTextbox.textContent = "";

        // Simplified search logic for the web version
        // A full implementation would mirror the Python version's local search first.
        let offset = 0;
        let found = false;
        const leagueId = getSelectedLeagueId();

        while (!stopFlag && offset < 20000 && !found) {
            statusBar.textContent = `Searching... Scanned ${offset} characters.`;
            const data = await apiFetchLadder(leagueId, offset, deepSearchCheck.checked);

            if (stopFlag) break;
            if (!data || !data.entries || data.entries.length === 0) {
                break; // End of ladder
            }

            for (const entry of data.entries) {
                if (entry.character.name === charName) {
                    resultsTextbox.textContent = `Character Found!\n\n` + JSON.stringify(entry, null, 2);
                    statusBar.textContent = `Found ${charName} at rank ${entry.rank}.`;
                    found = true;
                    break;
                }
            }
            offset += CHUNK_SIZE;
            await new Promise(resolve => setTimeout(resolve, 250));
        }

        if (!found && !stopFlag) {
            resultsTextbox.textContent = `Character '${charName}' not found after scanning ${offset} entries.`;
            statusBar.textContent = "Search complete. Character not found.";
        }
        resetButtonStates();
    }

    // This is a simplified JS version of your data_processor.py
    function processLadderData(entries, selectedAscendancy, limit) {
        // This is a placeholder. A full implementation would replicate the Python logic.
        const filtered = selectedAscendancy ? entries.filter(e => e.character.class === selectedName) : entries;
        return filtered.slice(0, limit).map(e => ({
            ascendancy: e.character.class,
            level: e.character.level,
            name: e.character.name,
            global_rank: e.rank,
            asc_rank: 'N/A' // Ascendancy rank calculation is complex for the frontend
        }));
    }

    // --- Main Execution ---
    populateAscendancies();
    loadLeagues();

});