let allFetchedEntries = [];
let foundCharacterEntry = null;
let raceInterval = null;
let isSearching = false;
let stopSearchFlag = false;
let currentLimit = 10;
let currentOffset = 0;

const CHUNK_SIZE = 200;

const ASCENDANCIES = [
    "Guardian", "Hierophant", "Inquisitor", "Assassin", "Saboteur", "Trickster", 
    "Berserker", "Chieftain", "Juggernaut", "Champion", "Gladiator", "Slayer", 
    "Necromancer", "Occultist", "Elementalist", "Deadeye", "Pathfinder", "Raider", "Ascendant"
];

document.addEventListener('DOMContentLoaded', () => {
    fetchLeagues();
    populateAscendancies();
});

async function fetchLeagues() {
    try {
        const response = await fetch('/leagues');
        const leagues = await response.json();
        const select = document.getElementById('leagueSelect');
        select.innerHTML = '';
        
        if (Array.isArray(leagues)) {
            leagues.sort((a, b) => {
                const textA = (a.text || a.id).toLowerCase();
                const textB = (b.text || b.id).toLowerCase();
                return textA.localeCompare(textB);
            });
            leagues.forEach(league => {
                const option = document.createElement('option');
                option.value = league.id;
                option.textContent = league.text || league.id;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option>Error fetching leagues</option>';
        }
    } catch (error) {
        console.error(error);
        document.getElementById('leagueSelect').innerHTML = '<option>Connection Error</option>';
    }
}

function populateAscendancies() {
    const select = document.getElementById('ascendancySelect');
    ASCENDANCIES.sort();
    ASCENDANCIES.forEach(asc => {
        const option = document.createElement('option');
        option.value = asc;
        option.textContent = asc;
        select.appendChild(option);
    });
}

function updateStatus(msg) {
    document.getElementById('status').textContent = msg;
}

function logResult(msg) {
    const box = document.getElementById('resultsBox');
    // The fetch result is a table with its own padding.
    // Other results (search, status) are plain text and need padding.
    if (msg.trim().startsWith('<table')) {
        box.innerHTML = msg;
    } else {
        // Wrap plain text to add padding and preserve formatting.
        box.innerHTML = `<pre style="padding: 10px; margin: 0; font-family: 'Consolas', monospace; color: #ccc; white-space: pre-wrap; word-wrap: break-word;">${msg}</pre>`;
    }
}

function stopSearch() {
    stopSearchFlag = true;
}

function togglePrivateLeague() {
    const isChecked = document.getElementById('privateLeagueCheck').checked;
    const leagueSelect = document.getElementById('leagueSelect');
    const privateInput = document.getElementById('privateLeagueInput');

    if (isChecked) {
        leagueSelect.disabled = true;
        privateInput.disabled = false;
    } else {
        leagueSelect.disabled = false;
        privateInput.disabled = true;
    }
}

function getSelectedLeagueId() {
    const isPrivate = document.getElementById('privateLeagueCheck').checked;
    return isPrivate ? document.getElementById('privateLeagueInput').value.trim() : document.getElementById('leagueSelect').value;
}

async function fetchCharacters() {
    currentLimit = 10;
    currentOffset = 0;
    allFetchedEntries = [];
    await fetchAndDisplayData();
}

async function showMoreCharacters() {
    currentLimit += 50;
    await fetchAndDisplayData();
}

async function fetchAndDisplayData() {
    const leagueId = getSelectedLeagueId();
    const ascendancy = document.getElementById('ascendancySelect').value;
    const selectedAsc = ascendancy === "All" ? null : ascendancy;

    document.getElementById('fetchBtn').disabled = true;
    document.getElementById('showMoreBtn').disabled = true;
    document.getElementById('searchBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('raceBtn').disabled = true;
    
    stopSearchFlag = false;
    logResult(""); // Clear previous results

    while (true) {
        if (stopSearchFlag) break;
        if (shouldStopFetching(selectedAsc)) break;

        updateStatus(`Fetching characters ${currentOffset} to ${currentOffset + CHUNK_SIZE}...`);
        
        try {
            const response = await fetch(`/public-ladder/${encodeURIComponent(leagueId)}?limit=${CHUNK_SIZE}&offset=${currentOffset}`);
            const data = await response.json();

            if (data.error) {
                updateStatus(`Error: ${data.message}`);
                break;
            }

            const entries = data.entries || [];
            if (entries.length === 0) break;

            allFetchedEntries.push(...entries);
            currentOffset += CHUNK_SIZE;

            // Live update for "All"
            if (!selectedAsc) {
                const results = processLadderData(allFetchedEntries, selectedAsc, currentLimit);
                logResult(formatResults(results, leagueId));
            }

            await new Promise(r => setTimeout(r, 500));

        } catch (e) {
            updateStatus(`Network error: ${e.message}`);
            break;
        }
    }

    // Final update
    const results = processLadderData(allFetchedEntries, selectedAsc, currentLimit);
    logResult(formatResults(results, leagueId));
    
    updateStatus(`Done. Showing top ${currentLimit} for ${selectedAsc || 'all ascendancies'}.`);
    
    document.getElementById('fetchBtn').disabled = false;
    document.getElementById('searchBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    
    if (ascendancy !== "All") {
        document.getElementById('showMoreBtn').disabled = false;
    }
}

function shouldStopFetching(ascendancy) {
    if (currentOffset >= 15000) return true;
    
    if (ascendancy) {
        const count = allFetchedEntries.filter(e => e.character.class === ascendancy).length;
        return count >= currentLimit;
    }
    
    // For "All", check if we have enough for every ascendancy
    const counts = {};
    ASCENDANCIES.forEach(a => counts[a] = 0);
    allFetchedEntries.forEach(e => {
        if (counts[e.character.class] !== undefined) counts[e.character.class]++;
    });
    
    return ASCENDANCIES.every(a => counts[a] >= currentLimit);
}

async function searchCharacter() {
    const charName = document.getElementById('charNameInput').value.trim();
    const leagueId = getSelectedLeagueId();
    
    if (!charName) {
        logResult("Please enter a character name.");
        return;
    }

    // Reset state
    isSearching = true;
    stopSearchFlag = false;
    allFetchedEntries = []; // Clear cache for fallback
    foundCharacterEntry = null;
    
    document.getElementById('searchBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('raceBtn').disabled = true;
    document.getElementById('raceModeContainer').classList.add('hidden');
    
    let offset = 0;
    let found = false;

    updateStatus(`Searching for ${charName}...`);
    logResult("Starting search...");

    while (!stopSearchFlag && !found && offset < 15000) {
        updateStatus(`Scanning offset ${offset}...`);
        
        try {
            const response = await fetch(`/public-ladder/${encodeURIComponent(leagueId)}?limit=${CHUNK_SIZE}&offset=${offset}`);
            const data = await response.json();
            
            if (data.error) {
                logResult(`Error: ${data.message}`);
                break;
            }

            const entries = data.entries || [];
            if (entries.length === 0) break;

            // Cache entries for Race Mode fallback
            allFetchedEntries.push(...entries);

            for (const entry of entries) {
                if (entry.character.name.toLowerCase() === charName.toLowerCase()) {
                    foundCharacterEntry = entry;
                    found = true;
                    break;
                }
            }

            if (found) break;
            
            offset += CHUNK_SIZE;
            // Small delay to be nice to the proxy/API
            await new Promise(r => setTimeout(r, 200));

        } catch (e) {
            logResult(`Network error: ${e.message}`);
            break;
        }
    }

    document.getElementById('searchBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;

    if (found) {
        updateStatus(`Found ${foundCharacterEntry.character.name}!`);
        logResult(`Character Found:\nName: ${foundCharacterEntry.character.name}\nLevel: ${foundCharacterEntry.character.level}\nClass: ${foundCharacterEntry.character.class}\nRank: ${foundCharacterEntry.rank}`);
        document.getElementById('raceBtn').disabled = false;
    } else if (stopSearchFlag) {
        updateStatus("Search stopped.");
        logResult("Search cancelled by user.");
    } else {
        updateStatus("Character not found.");
        logResult(`Character '${charName}' not found in top ${offset} entries.`);
    }
}

function popoutRaceMode() {
    if (!foundCharacterEntry) return;

    // Store data for the popout window to access
    localStorage.setItem('raceModeCharacter', JSON.stringify(foundCharacterEntry));
    localStorage.setItem('raceModeLeagueId', getSelectedLeagueId());
    localStorage.setItem('allFetchedEntries', JSON.stringify(allFetchedEntries));

    // Open the new window
    const popoutWidth = 570;
    const popoutHeight = 360;
    window.open('/popout.html', 'PoeRaceMode', `width=${popoutWidth},height=${popoutHeight},resizable=yes,scrollbars=no`);
}

function toggleRaceView() {
    const mode = document.getElementById('viewModeSelect').value;
    const ascSection = document.getElementById('ascSection');
    const globalSection = document.getElementById('globalSection');

    if (mode === 'both') {
        ascSection.classList.remove('hidden');
        globalSection.classList.remove('hidden');
    } else if (mode === 'ascendancy') {
        ascSection.classList.remove('hidden');
        globalSection.classList.add('hidden');
    } else if (mode === 'global') {
        ascSection.classList.add('hidden');
        globalSection.classList.remove('hidden');
    }
}

function startRaceMode() {
    if (!foundCharacterEntry) return;
    
    document.getElementById('raceModeContainer').classList.remove('hidden');
    document.getElementById('trackingHeader').textContent = `Tracking: ${foundCharacterEntry.character.name}`;
    
    // Initial load
    updateRaceData();
    
    // Setup auto-refresh
    toggleAutoRefresh();
    
    // Scroll down to race mode
    document.getElementById('raceModeContainer').scrollIntoView({ behavior: 'smooth' });
}

function toggleAutoRefresh() {
    const isChecked = document.getElementById('autoRefreshCheck').checked;
    if (raceInterval) clearInterval(raceInterval);
    
    if (isChecked) {
        raceInterval = setInterval(updateRaceData, 60000); // 60s
    }
}

async function updateRaceData() {
    const btn = document.getElementById('refreshRaceBtn');
    btn.disabled = true;
    btn.textContent = "Refreshing...";

    const leagueId = document.getElementById('leagueSelect').value;
    const targetRank = foundCharacterEntry.rank;
    
    // Fetch window of 200 centered on rank
    const limit = 200;
    const offset = Math.max(0, targetRank - (limit / 2));

    try {
        const response = await fetch(`/public-ladder/${encodeURIComponent(leagueId)}?limit=${limit}&offset=${offset}`);
        const data = await response.json();

        if (data.entries) {
            processRaceData(data.entries);
        } else {
            console.error("Failed to refresh race data");
        }
    } catch (e) {
        console.error(e);
    }

    btn.disabled = false;
    btn.textContent = "Refresh";
}

function processRaceData(surroundingEntries) {
    const myName = foundCharacterEntry.character.name;
    
    // 1. Find self in new data
    const myNewEntry = surroundingEntries.find(e => e.character.name === myName);
    
    if (!myNewEntry) {
        // Character fell out of the fetch window or API error
        return; 
    }

    // Update local state
    foundCharacterEntry = myNewEntry;
    const myXp = myNewEntry.character.experience;
    const myClass = myNewEntry.character.class;

    const getNeighbor = (list, selfEntry, direction, cache) => {
        const idx = list.findIndex(e => e.character.name === selfEntry.character.name);
        if (idx === -1) { // Not found in live slice, rely entirely on cache
            const cacheIdx = cache.findIndex(e => e.character.name === selfEntry.character.name);
            if (cacheIdx === -1) return null;
            if (direction === 'ahead') return cache[cacheIdx - 1] || null;
            return cache[cacheIdx + 1] || null;
        }
        
        if (direction === 'ahead') {
            if (idx > 0) return list[idx - 1];
            // Fallback to cache if at the edge of the live slice
            const cacheIdx = allFetchedEntries.findIndex(e => e.character.name === selfEntry.character.name);
            if (cacheIdx > 0) return allFetchedEntries[cacheIdx - 1];
        } else { // 'behind'
            if (idx < list.length - 1) return list[idx + 1];
            // Fallback to cache
            const cacheIdx = allFetchedEntries.findIndex(e => e.character.name === selfEntry.character.name);
            if (cacheIdx !== -1 && cacheIdx < allFetchedEntries.length - 1) return allFetchedEntries[cacheIdx + 1];
        }
        return null;
    };

    const ascEntries = surroundingEntries.filter(e => e.character.class === myClass);
    const cachedAscEntries = allFetchedEntries.filter(e => e.character.class === myClass);

    const globalAhead = getNeighbor(surroundingEntries, myNewEntry, 'ahead', allFetchedEntries);
    const globalBehind = getNeighbor(surroundingEntries, myNewEntry, 'behind', allFetchedEntries);
    renderLadderTable('globalTable', globalAhead, globalBehind, myXp);

    const ascAhead = getNeighbor(ascEntries, myNewEntry, 'ahead', cachedAscEntries);
    const ascBehind = getNeighbor(ascEntries, myNewEntry, 'behind', cachedAscEntries);
    renderLadderTable('ascTable', ascAhead, ascBehind, myXp);
}

function renderLadderTable(elementId, ahead, behind, myXp) {
    const container = document.getElementById(elementId);
    container.innerHTML = '';
    
    const createRow = (title, entry, cssClass) => {
        const xpDiff = entry ? entry.character.experience - myXp : 0;
        const xpClass = xpDiff > 0 ? 'xp-plus' : (xpDiff < 0 ? 'xp-minus' : 'xp-neutral');
        const xpText = entry ? `XP: ${xpDiff > 0 ? '+' : ''}${xpDiff.toLocaleString()}` : '';
        
        return `
            <div class="race-row ${cssClass}">
                <div class="col-title">${title}</div>
                <div class="col-name">${entry ? `${entry.character.name} (Lvl ${entry.character.level})` : 'N/A'}</div>
                <div class="col-xp ${xpClass}">${xpText}</div>
                <div class="col-rank">${entry ? '#' + entry.rank : ''}</div>
            </div>
        `;
    };

    container.innerHTML += createRow("Ahead:", ahead, "row-ahead");
    container.innerHTML += createRow("Behind:", behind, "row-behind");
}

function processLadderData(entries, selectedAscendancy, limit) {
    const results = [];
    const ascCounts = {};

    // Calculate ranks
    for (const entry of entries) {
        const asc = entry.character.class;
        if (!ascCounts[asc]) ascCounts[asc] = 0;
        ascCounts[asc]++;
        
        const item = {
            name: entry.character.name,
            level: entry.character.level,
            ascendancy: asc,
            global_rank: entry.rank,
            asc_rank: ascCounts[asc]
        };

        if (selectedAscendancy) {
            if (asc === selectedAscendancy && item.asc_rank <= limit) {
                results.push(item);
            }
        } else {
            if (item.asc_rank <= limit) {
                results.push(item);
            }
        }
    }
    
    // Sort
    results.sort((a, b) => {
        if (a.ascendancy < b.ascendancy) return -1;
        if (a.ascendancy > b.ascendancy) return 1;
        return a.asc_rank - b.asc_rank;
    });
    
    return results;
}

function formatResults(results, league) {
    let output = `<table class="results-table">
        <thead>
            <tr>
                <th>Ascendancy</th>
                <th>Level</th>
                <th>Character Name</th>
                <th style="text-align: right;">Rank (Asc/Global)</th>
            </tr>
        </thead>
        <tbody>`;
    
    let lastAsc = null;
    results.forEach(char => {
        if (lastAsc && char.ascendancy !== lastAsc) {
            output += `<tr><td colspan="4" style="background-color: #4da6ff; height: 2px; padding: 0; border: none;"></td></tr>`;
        }
        output += `<tr>
            <td>${char.ascendancy}</td>
            <td>${char.level}</td>
            <td>${char.name}</td>
            <td style="text-align: right;">${char.asc_rank} / ${char.global_rank}</td>
        </tr>`;
        lastAsc = char.ascendancy;
    });
    output += `</tbody></table>`;
    return output;
}