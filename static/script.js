// --- Configuration ---
// By setting the base URL to an empty string, the browser will automatically
// use the current origin (e.g., "http://127.0.0.1:5000" locally, or
// "https://poeladdertracker.xyz" in production) for API requests.
const PROXY_BASE_URL = "";
const ALL_ASCENDANCY_NAMES = [
    "Slayer", "Gladiator", "Champion", "Assassin", "Saboteur", "Trickster", "Juggernaut", "Berserker", "Chieftain",
    "Necromancer", "Occultist", "Elementalist", "Deadeye", "Raider", "Pathfinder", "Inquisitor", "Hierophant",
    "Guardian", "Ascendant"
];
// Sort the array alphabetically for display in the dropdown menu.
ALL_ASCENDANCY_NAMES.sort();
const CHUNK_SIZE = 200;

// --- State ---
const state = {
    allFetchedEntries: [],
    currentOffset: 0,
    currentLimit: 10,
    allLeaguesData: [],
    stopSearchController: null,
};

let leagueMenu, ascendancyMenu, privateLeagueCheck, privateLeagueEntry,
    deepSearchCheck, fetchButton, searchButton, stopButton, charNameEntry,
    resultsBox, showMoreButton, statusLabel;

// --- API Client ---
async function makeApiRequest(endpoint, signal) {
    try {
        const response = await fetch(`${PROXY_BASE_URL}/${endpoint}`, { signal });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }
        return await response.json();
    } catch (e) {
        console.error(`Error fetching from ${endpoint}:`, e);
        statusLabel.textContent = `Error: Failed to fetch data from server.`;
        return null;
    }
}

function fetchLeagues() {
    return makeApiRequest("leagues");
}

function fetchLadder(leagueId, limit, offset, isDeep, signal) {
    const endpoint = isDeep
        ? `ladder/${leagueId}?limit=${limit}&offset=${offset}`
        : `public-ladder/${leagueId}?limit=${limit}&offset=${offset}`;
    return makeApiRequest(endpoint, signal);
}

// --- UI Logic ---
function setControlsState(isFetching) {
    fetchButton.disabled = isFetching;
    searchButton.disabled = isFetching;
    stopButton.disabled = !isFetching;
    leagueMenu.disabled = isFetching || privateLeagueCheck.checked;
    ascendancyMenu.disabled = isFetching;
    privateLeagueCheck.disabled = isFetching;
    deepSearchCheck.disabled = isFetching || privateLeagueCheck.checked;
    privateLeagueEntry.disabled = isFetching || !privateLeagueCheck.checked;
    charNameEntry.disabled = isFetching;
}

function formatResults(finalResults, league) {
    let tableRows = '';
    let lastAscendancy = null;

    for (const char of finalResults) {
        const isNewAscendancy = lastAscendancy && char.ascendancy !== lastAscendancy;
        const separatorClass = isNewAscendancy ? ' class="ascendancy-separator"' : '';

        tableRows += `
            <tr${separatorClass}>
                <td>${char.ascendancy}</td>
                <td>${char.level}</td>
                <td>${char.name}</td>
                <td>${char.asc_rank} / ${char.global_rank}</td>
            </tr>`;
        lastAscendancy = char.ascendancy;
    }

    return `
        <table>
            <thead><tr><th>Ascendancy</th><th>Level</th><th>Character Name</th><th>Rank (Asc/Global)</th></tr></thead>
            <tbody>${tableRows}</tbody>
        </table>`;
}

// --- Data Fetching ---
async function loadLeagues() {
    setControlsState(true); // Disable controls while loading
    updateStatus("Fetching leagues from proxy...");
    const data = await fetchLeagues();
    
    const leaguesArray = Array.isArray(data) ? data : (data && Array.isArray(data.result) ? data.result : null);

    if (leaguesArray && leaguesArray.length > 0) {
        state.allLeaguesData = leaguesArray;
        state.allLeaguesData.sort((a, b) => a.id.localeCompare(b.id));

        leagueMenu.innerHTML = leaguesArray
            .map(lg => `<option value="${lg.id}">${lg.id}</option>`)
            .join('');
        
        const defaultLeague = state.allLeaguesData.find(lg => lg.id === "Standard") || state.allLeaguesData[0];
        if (defaultLeague) {
            leagueMenu.value = defaultLeague.id;
        }

        updateStatus("Ready.");
        setControlsState(false);
    } else {
        leagueMenu.innerHTML = `<option value="">Error fetching leagues</option>`;
        // The error is already logged by makeApiRequest. Just update the status.
        updateStatus("Error: Could not load leagues. See console for details.");
        setControlsState(false); // Allow user to try again if it was a temp issue.
    }
}

function getSelectedLeagueId() {
    if (privateLeagueCheck.checked) {
        const privateId = privateLeagueEntry.value.trim();
        if (!privateId) {
            updateStatus("Error: Private league name cannot be empty.");
            return null;
        }
        return privateId;
    }

    if (!leagueMenu.value) {
        updateStatus("Error: Please select a league.");
        return null;
    }
    return leagueMenu.value;
}

async function fetchAndDisplayData() {
    setControlsState(true);
    updateStatus("Fetching data...");
    resultsBox.textContent = "";
    showMoreButton.style.display = 'none';

    const leagueId = getSelectedLeagueId();
    if (!leagueId) {
        setControlsState(false);
        return;
    }

    const selectedAscendancy = ascendancyMenu.value === "All" ? null : ascendancyMenu.value;
    const isDeep = deepSearchCheck.checked;

    while (true) {
        const shouldStop = () => {
            if (state.currentOffset >= 15000 && !isDeep) return true;
            if (selectedAscendancy) {
                const count = state.allFetchedEntries.filter(e => e.character.class === selectedAscendancy).length;
                return count >= state.currentLimit;
            }
            return false;
        };

        if (shouldStop()) break;

        updateStatus(`Fetching characters ${state.currentOffset} to ${state.currentOffset + CHUNK_SIZE}...`);
        const data = await fetchLadder(leagueId, CHUNK_SIZE, state.currentOffset, isDeep, state.stopSearchController ? state.stopSearchController.signal : null);

        if (!data || !data.entries || data.entries.length === 0) break;

        state.allFetchedEntries.push(...data.entries);
        state.currentOffset += CHUNK_SIZE;

        if (!selectedAscendancy) {
            const processed = processLadderData(state.allFetchedEntries, null, state.currentLimit);
            resultsBox.innerHTML = formatResults(processed, leagueId);
        }
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    const processed = processLadderData(state.allFetchedEntries, selectedAscendancy, state.currentLimit);
    resultsBox.innerHTML = formatResults(processed, leagueId);
    resultsBox.scrollTop = 0; // Scroll to top to see results

    updateStatus(`Done. Showing top ${state.currentLimit} for ${selectedAscendancy || 'all ascendancies'}.`);
    setControlsState(false);
    if (selectedAscendancy) {
        showMoreButton.style.display = 'block';
    }
}

async function searchCharacter() {
    const charName = charNameEntry.value.trim();
    if (!charName) {
        resultsBox.textContent = "Please enter a character name to search.";
        return;
    }

    state.stopSearchController = new AbortController();
    setControlsState(true);
    resultsBox.textContent = `Searching for '${charName}'...`;

    const leagueId = getSelectedLeagueId();
    if (!leagueId) {
        setControlsState(false);
        return;
    }
    const isDeep = deepSearchCheck.checked;
    let currentSearchOffset = 0;
    let foundEntry = null;
    const allScannedEntries = [];

    try {
        while (true) {
            if (state.stopSearchController.signal.aborted) throw new Error("Search stopped by user.");
            // Stop searching public ladders after 15k entries, deep search continues
            if (currentSearchOffset >= 15000 && !isDeep) break;

            updateStatus(`Searching... Scanned ${currentSearchOffset} characters.`);
            const data = await fetchLadder(leagueId, CHUNK_SIZE, currentSearchOffset, isDeep, state.stopSearchController.signal);

            if (!data || !data.entries || data.entries.length === 0) break;

            allScannedEntries.push(...data.entries);

            foundEntry = data.entries.find(e => e.character.name.toLowerCase() === charName.toLowerCase());
            if (foundEntry) break;

            currentSearchOffset += CHUNK_SIZE;
            await new Promise(resolve => setTimeout(resolve, 500)); // Rate limit between chunks
        }

        if (foundEntry) {
            // Calculate ascendancy rank from all scanned entries
            const ascendancyCounts = {};
            allScannedEntries.sort((a, b) => a.rank - b.rank);
            for (const entry of allScannedEntries) {
                ascendancyCounts[entry.character.class] = (ascendancyCounts[entry.character.class] || 0) + 1;
                if (entry.character.name === foundEntry.character.name) break;
            }
            const ascRank = ascendancyCounts[foundEntry.character.class];

            const resultHTML = `
                <table>
                    <thead><tr><th colspan="2">Character Found</th></tr></thead>
                    <tbody>
                        <tr><td>Name</td><td>${foundEntry.character.name}</td></tr>
                        <tr><td>Level</td><td>${foundEntry.character.level}</td></tr>
                        <tr><td>Class</td><td>${foundEntry.character.class}</td></tr>
                        <tr><td>Rank</td><td>${ascRank} (Asc) / ${foundEntry.rank} (Global)</td></tr>
                    </tbody>
                </table>`;
            resultsBox.innerHTML = resultHTML;
            updateStatus(`Search complete. Found '${charName}'.`);
        } else {
            resultsBox.innerHTML = `
                <div style="padding: 20px; text-align: center;">
                    Character '${charName}' not found after scanning ${currentSearchOffset} entries.
                </div>`;
            updateStatus("Search complete. Character not found.");
        }
    } catch (error) {
        updateStatus(error.name === 'AbortError' ? "Search stopped." : `Search failed: ${error.message}`);
    } finally {
        setControlsState(false);
        state.stopSearchController = null;
    }
}

function updateStatus(message) {
    statusLabel.textContent = message;
}

// --- Event Listeners ---
function initializeApp() {
    // --- DOM Element Lookups ---
    // This is done inside initializeApp to ensure the DOM is fully loaded.
    leagueMenu = document.getElementById('league-menu');
    ascendancyMenu = document.getElementById('ascendancy-menu');
    privateLeagueCheck = document.getElementById('private-league-check');
    privateLeagueEntry = document.getElementById('private-league-entry');
    deepSearchCheck = document.getElementById('deep-search-check');
    fetchButton = document.getElementById('fetch-button');
    searchButton = document.getElementById('search-button');
    stopButton = document.getElementById('stop-button');
    charNameEntry = document.getElementById('char-name-entry');
    resultsBox = document.getElementById('results-box');
    showMoreButton = document.getElementById('show-more-button');
    statusLabel = document.getElementById('status-label');

    ascendancyMenu.innerHTML = ["All", ...ALL_ASCENDANCY_NAMES]
        .map(asc => `<option value="${asc}">${asc}</option>`)
        .join('');

    loadLeagues();

    privateLeagueCheck.addEventListener('change', () => {
        const isChecked = privateLeagueCheck.checked;
        privateLeagueEntry.disabled = !isChecked;
        leagueMenu.disabled = isChecked;
        deepSearchCheck.disabled = isChecked;
        if (isChecked) deepSearchCheck.checked = false;
    });

    ascendancyMenu.addEventListener('change', () => {
        showMoreButton.style.display = ascendancyMenu.value === "All" ? 'none' : 'block';
    });

    fetchButton.addEventListener('click', () => {
        state.allFetchedEntries = [];
        state.currentOffset = 0;
        state.currentLimit = 10;
        fetchAndDisplayData();
    });

    showMoreButton.addEventListener('click', () => {
        state.currentLimit += 20;
        fetchAndDisplayData(); // Re-run fetch to get more data if needed
    });

    searchButton.addEventListener('click', searchCharacter);
    stopButton.addEventListener('click', () => {
        if (state.stopSearchController) state.stopSearchController.abort();
    });
}

// --- Data Processor ---
function processLadderData(entries, selectedAscendancy, limit) {
    const ascendancyCounts = {};
    const filteredEntries = [];

    // Sort all entries by global rank first to ensure correct ascendancy ranking
    entries.sort((a, b) => a.rank - b.rank);

    for (const entry of entries) {
        const charClass = entry.character.class;
        ascendancyCounts[charClass] = (ascendancyCounts[charClass] || 0) + 1;

        if (!selectedAscendancy || charClass === selectedAscendancy) {
            filteredEntries.push({
                ascendancy: charClass,
                level: entry.character.level,
                name: entry.character.name,
                global_rank: entry.rank,
                asc_rank: ascendancyCounts[charClass]
            });
        }
    }

    if (selectedAscendancy) {
        return filteredEntries.slice(0, limit);
    }

    const finalResults = [];
    const processedCounts = {};
    ALL_ASCENDANCY_NAMES.forEach(asc => processedCounts[asc] = 0);

    for (const entry of filteredEntries) {
        if (processedCounts[entry.ascendancy] < limit) {
            finalResults.push(entry);
            processedCounts[entry.ascendancy]++;
        }
    }
    return finalResults.sort((a, b) => a.ascendancy.localeCompare(b.ascendancy) || a.asc_rank - b.asc_rank);
}

// Polyfill for String.center
String.prototype.center = function (width, char = ' ') {
    const length = this.length;
    if (length >= width) return this.toString();
    const left = Math.floor((width - length) / 2);
    const right = width - length - left;
return char.repeat(left) + this + char.repeat(right);
};

// --- App Start ---
document.addEventListener('DOMContentLoaded', initializeApp);