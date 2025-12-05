// This script will replicate the logic from your gui.py file.

const CHUNK_SIZE = 200;
const MAX_SEARCH_ENTRIES = 20000; // Corresponds to _should_stop_fetching limit

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
    let stopFlag = false; // Flag to stop ongoing fetches/searches

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
        // Disable buttons until leagues are loaded
        fetchButton.disabled = true;
        searchButton.disabled = true;
        try {
            const response = await fetch('/leagues');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const responseData = await response.json(); // This is the Flask jsonify output
            const leagues = responseData.result; // The actual list of leagues is inside the 'result' key

            if (!leagues) throw new Error("API response did not contain a 'result' array.");
            
            allLeaguesData = leagues;
            leagueMenu.innerHTML = ''; // Clear "fetching..."
            // Sort leagues alphabetically by their display text
            // This sort is now robust and handles malformed entries from the API.
            leagues.sort((a, b) => {
                const textA = a?.text || ''; // Safely access 'text' or default to empty string
                const textB = b?.text || ''; // Safely access 'text' or default to empty string
                return textA.localeCompare(textB);
            });

            leagues.forEach(league => {
                const option = document.createElement('option');
                // The API gives us 'id' and 'text'. We'll use 'text' for the user-facing display.
                option.value = league.text;
                option.textContent = league.text;
                leagueMenu.appendChild(option);
            });
            // Re-enable buttons now that leagues are loaded
            fetchButton.disabled = false;
            searchButton.disabled = false;
        } catch (error) {
            console.error("Error fetching leagues:", error);
            leagueMenu.innerHTML = '<option>Error fetching leagues</option>';
            // Keep buttons disabled if there's an error
        }
    }

    // --- Event Listeners ---

    privateLeagueCheck.addEventListener('change', () => {
        leagueMenu.disabled = privateLeagueCheck.checked;
        privateLeagueEntry.disabled = !privateLeagueCheck.checked;
        if (privateLeagueCheck.checked) {
            // If private league is checked, deep search is not possible
            deepSearchCheck.checked = false; // Deep search is for public leagues
        }
    });

    deepSearchCheck.addEventListener('change', () => {
        if (deepSearchCheck.checked) {
            privateLeagueCheck.checked = false;
            // If deep search is checked, private league entry is disabled
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
        // Show More button is enabled only if not fetching and not "All" ascendancies
        showMoreButton.disabled = isFetching || (ascendancyMenu.value === "All");
    }

    function updateStatusBar(message, isError = false) {
        statusBar.textContent = message;
        statusBar.style.color = isError ? 'red' : '#6c757d';
        if (isError) console.error(message);
        else console.log(message);
    }

    function resetButtonStates() {
        setButtonsState(false);
    }

    function formatResults(results, leagueName) {
        const width = 90;
        const header = `✅ ASCENDANCY STANDINGS ✅`.padStart(width / 2 + 15); // Adjust for emoji
        const leagueLine = `League: ${leagueName}`.padStart(width / 2 + leagueName.length / 2);
        const separator = "-".repeat(width);
        let output = `${separator}\n${header.padStart(45 + header.length/2)}\n${leagueLine.padStart(45 + leagueLine.length/2)}\n${separator}\n`;
        output += `ASCENDANCY\tLEVEL\tCHARACTER NAME\tRANK (Asc/Global)\n`;
        output += `${separator}\n`;

        let lastAscendancy = null;
        for (const char of results) {
            if (lastAscendancy && char.ascendancy !== lastAscendancy) {
                output += `\n`; // Just a newline for separation between ascendancies
            }
            const rankStr = `${char.asc_rank} / ${char.global_rank}`;
            output += `${char.ascendancy.padEnd(15)}\t${String(char.level).padEnd(5)}\t${char.name.padEnd(25)}\t${rankStr}\n`;
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
                const errorData = await response.json();
                updateStatusBar(`API Error: ${response.status} - ${errorData.error || response.statusText}`, true);
                return null;
            }
            return await response.json();
        } catch (error) {
            updateStatusBar(`Network error fetching ladder: ${error.message}`, true);
            return null; // Return null on network errors
        }
    }

    // --- Core Logic Functions ---

    function startFetch() {
        allFetchedEntries = [];
        currentOffset = 0; // Reset offset for new fetch
        currentLimit = 20;
        fetchAndDisplayData();
    }

    function showMore() {
        currentLimit += 50;
        fetchAndDisplayData(true); // Indicate that this is a "show more" action
    }

    async function fetchAndDisplayData(isShowMore = false) {
        setButtonsState(true);
        stopFlag = false; // Clear stop flag for new operation
        updateStatusBar("Fetching data...");
        resultsTextbox.textContent = "";

        const leagueName = getSelectedLeagueName();
        const leagueId = getSelectedLeagueId();
        const ascendancy = ascendancyMenu.value === "All" ? null : ascendancyMenu.value;

        // This is a simplified version of the Python fetching loop.
        while (!stopFlag && currentOffset < MAX_SEARCH_ENTRIES) {
            updateStatusBar(`Fetching characters ${currentOffset} to ${currentOffset + CHUNK_SIZE}...`);
            const data = await apiFetchLadder(leagueId, currentOffset, deepSearchCheck.checked);
            if (stopFlag) break; // Check stopFlag again after API call

            if (stopFlag) break;
            if (!data || !data.entries || data.entries.length === 0) {
                break; // No more data or an error occurred
            }

            allFetchedEntries.push(...data.entries);
            currentOffset += CHUNK_SIZE;
            
            // Sort by rank to maintain order (important for accurate ascendancy ranks)
            allFetchedEntries.sort((a, b) => a.rank - b.rank);

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
        updateStatusBar(`Done. Showing top ${currentLimit} for ${ascendancy || 'all ascendancies'}.`);
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
        const ascendanciesToProcess = selectedAscendancy ? [selectedAscendancy] : ALL_ASCENDANCY_NAMES;
        const ascendancyGroups = {};
        ascendanciesToProcess.forEach(asc => ascendancyGroups[asc] = []);

        // 1. Core Grouping Logic
        // We need to re-calculate ascendancy ranks based on the full, sorted list of entries.
        const tempAscendancyCounts = {};
        ALL_ASCENDANCY_NAMES.forEach(asc => tempAscendancyCounts[asc] = 0);

        for (const entry of entries) {
            const charData = entry.character;
            const ascendancy = charData.class;

            if (ascendancy in tempAscendancyCounts) {
                tempAscendancyCounts[ascendancy]++;
                const ascRank = tempAscendancyCounts[ascendancy];

                const characterInfo = {
                    ascendancy: ascendancy,
                    level: charData.level,
                    xp: charData.experience,
                    name: charData.name,
                    global_rank: entry.rank,
                    asc_rank: ascRank
                };

                if (ascendancyGroups[ascendancy] && ascendancyGroups[ascendancy].length < limit) {
                    ascendancyGroups[ascendancy].push(characterInfo);
                }
            }
        }

        // 2. Final Consolidation and Sorting
        let finalLadderList = [];
        for (const ascList of Object.values(ascendancyGroups)) {
            finalLadderList.push(...ascList);
        }

        // Sort by ascendancy name, then by ascendancy rank
        finalLadderList.sort((a, b) => {
            if (a.ascendancy < b.ascendancy) return -1;
            if (a.ascendancy > b.ascendancy) return 1;
            return a.asc_rank - b.asc_rank;
        });

        return finalLadderList;
    }

    // --- Main Execution ---
    populateAscendancies();
    loadLeagues();

});