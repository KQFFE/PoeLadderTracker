let allFetchedEntries = [];
let foundCharacterEntry = null;
let raceInterval = null;
let isSearching = false;
let stopSearchFlag = false;
let currentLimit = 10;
let currentOffset = 0;

const CHUNK_SIZE = 200;

const XP_THRESHOLDS = [
    0, 525, 1760, 3781, 7184, 12186, 19324, 29377, 43181, 61693, 
    85990, 117506, 157384, 207736, 269997, 346462, 439268, 551295, 685171, 843709, 
    1030734, 1249629, 1504995, 1800847, 2142652, 2535122, 2984677, 3496798, 4080655, 4742836, 
    5490247, 6334393, 7283446, 8348398, 9541110, 10874351, 12361842, 14018289, 15859432, 17905634, 
    20171471, 22679999, 25456123, 28517857, 31897771, 35621447, 39721017, 44225461, 49176560, 54607467, 
    60565335, 67094245, 74247659, 82075627, 90631041, 99984974, 110197515, 121340161, 133497202, 146749362, 
    161191120, 176922628, 194049893, 212684946, 232956711, 255001620, 278952403, 304972236, 333233648, 363906163, 
    397194041, 433312945, 472476370, 514937180, 560961898, 610815862, 664824416, 723298169, 786612664, 855129128, 
    929261318, 1009443795, 1096169525, 1189918242, 1291270350, 1400795257, 1519130326, 1646943474, 1784977296, 1934009687, 
    2094900291, 2268549086, 2455921256, 2658074992, 2876116901, 3111280300, 3364828162, 3638186694, 3932818530, 4250334444
];

const STANDARD_ASCENDANCIES = [
    "Guardian", "Hierophant", "Inquisitor", "Assassin", "Saboteur", "Trickster", 
    "Berserker", "Chieftain", "Juggernaut", "Champion", "Gladiator", "Slayer", 
    "Necromancer", "Occultist", "Elementalist", "Deadeye", "Pathfinder", "Warden", "Ascendant"
];
const TEMPORARY_ASCENDANCIES = [
    "Ancestral Commander", "Antiquarian", "Architect of Chaos", "Aristocrat", 
    "Behemoth", "Blind Prophet", "Bog Shaman", "Daughter of Oshabi", 
    "Gambler", "Harbinger", "Herald", "Paladin", "Polytheist", 
    "Puppeteer", "Scavenger", "Servant of Arakaali", "Surfcaster", 
    "Whisperer", "Wildspeaker"
];
const ALL_ASCENDANCIES = [...STANDARD_ASCENDANCIES, ...TEMPORARY_ASCENDANCIES];

function calculateProgress(level, xp) {
    if (level >= 100) return 100;
    if (level < 1) return 0;
    const prevXp = XP_THRESHOLDS[level - 1];
    const nextXp = XP_THRESHOLDS[level];
    if (nextXp === undefined) return 100;
    const progress = (xp - prevXp) / (nextXp - prevXp);
    return Math.max(0, Math.min(100, progress * 100));
}

document.addEventListener('DOMContentLoaded', () => {
    fetchLeagues();
    document.getElementById('leagueSelect').addEventListener('change', populateAscendancies);
    document.getElementById('charNameInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchCharacter();
        }
    });
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
        populateAscendancies();
    } catch (error) {
        console.error(error);
        document.getElementById('leagueSelect').innerHTML = '<option>Connection Error</option>';
    }
}

function populateAscendancies() {
    const leagueSelect = document.getElementById('leagueSelect');
    const selectedLeague = leagueSelect.options[leagueSelect.selectedIndex]?.text || "";
    const select = document.getElementById('ascendancySelect');
    select.innerHTML = '';

    const allOption = document.createElement('option');
    allOption.value = "All";
    allOption.textContent = "All";
    select.appendChild(allOption);

    if (selectedLeague.includes("Phrecia")) {
        TEMPORARY_ASCENDANCIES.sort();
        TEMPORARY_ASCENDANCIES.forEach(asc => {
            const option = document.createElement('option');
            option.value = asc;
            option.textContent = asc;
            select.appendChild(option);
        });
    } else {
        STANDARD_ASCENDANCIES.sort();
        STANDARD_ASCENDANCIES.forEach(asc => {
            const option = document.createElement('option');
            option.value = asc;
            option.textContent = asc;
            select.appendChild(option);
        });
    }
}

function updateStatus(msg) {
    document.getElementById('status').textContent = msg;
}

function logResult(msg) {
    const box = document.getElementById('resultsBox');
    // The fetch result is a table with its own padding.
    // Other results (search, status) are plain text and need padding.
    if (msg.trim().startsWith('<')) {
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
    const leagueSelect = document.getElementById('leagueSelect');
    const selectedLeague = leagueSelect.options[leagueSelect.selectedIndex]?.text || "";
    const targetList = selectedLeague.includes("Phrecia") ? TEMPORARY_ASCENDANCIES : STANDARD_ASCENDANCIES;

    targetList.forEach(a => counts[a] = 0);
    allFetchedEntries.forEach(e => {
        if (counts[e.character.class] !== undefined) counts[e.character.class]++;
    });
    
    return targetList.every(a => counts[a] >= currentLimit);
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

            for (let i = 0; i < entries.length; i++) {
                const entry = entries[i];
                entry.rank = offset + i + 1;
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
        // Calculate Ascendancy Rank
        let ascRank = 0;
        const targetClass = foundCharacterEntry.character.class;
        for (const entry of allFetchedEntries) {
            if (entry.character.class === targetClass) ascRank++;
            if (entry.character.name === foundCharacterEntry.character.name) break;
        }
        foundCharacterEntry.ascendancy_rank = ascRank;

        updateStatus(`Found ${foundCharacterEntry.character.name}!`);
        
        const char = foundCharacterEntry.character;
        const html = `
            <div style="padding: 0 20px 20px 20px; font-family: 'Segoe UI', sans-serif; color: #E0E0E0; font-size: 18px; line-height: 1.5; white-space: normal;">
                <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 40px; color: #4da6ff;">Character Found:</div>
                <div style="margin-bottom: 0px;"><span style="color: #aaa; font-weight: bold; width: 100px; display: inline-block;">Name:</span> ${char.name}</div>
                <div style="margin-bottom: 0px;"><span style="color: #aaa; font-weight: bold; width: 100px; display: inline-block;">Level:</span> ${char.level}</div>
                <div style="margin-bottom: 20px;"><span style="color: #aaa; font-weight: bold; width: 100px; display: inline-block;">Class:</span> ${char.class}</div>
                <div style="margin-bottom: 0px;"><span style="color: #aaa; font-weight: bold; width: 150px; display: inline-block;">Global Rank:</span> ${foundCharacterEntry.rank}</div>
                <div><span style="color: #aaa; font-weight: bold; width: 150px; display: inline-block;">Ascendancy Rank:</span> ${foundCharacterEntry.ascendancy_rank}</div>
            </div>
        `;
        logResult(html);
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
    const popoutWidth = 800;
    const popoutHeight = 480;
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
    renderLadderTable('globalTable', globalAhead, myNewEntry, globalBehind, myXp);

    const ascAhead = getNeighbor(ascEntries, myNewEntry, 'ahead', cachedAscEntries);
    const ascBehind = getNeighbor(ascEntries, myNewEntry, 'behind', cachedAscEntries);
    renderLadderTable('ascTable', ascAhead, myNewEntry, ascBehind, myXp);
}

function renderLadderTable(elementId, ahead, current, behind, myXp) {
    const container = document.getElementById(elementId);
    container.innerHTML = '';
    
    const createRow = (title, entry, cssClass) => {
        let xpDisplay = '';
        let xpColor = '#eeeeee';
        
        if (entry) {
            if (cssClass === 'row-track') {
                xpDisplay = `XP: ${entry.character.experience.toLocaleString()}`;
                xpColor = '#ffffff';
            } else {
                const diff = entry.character.experience - myXp;
                const sign = diff > 0 ? '+' : '';
                xpDisplay = `XP: ${sign}${diff.toLocaleString()}`;
                if (diff > 0) xpColor = '#2CC985';
                else if (diff < 0) xpColor = '#FF5252';
            }
        }

        const progress = entry ? calculateProgress(entry.character.level, entry.character.experience) : 0;
        
        // Colors matching desktop app dark mode approximation
        const bgColors = {
            'row-ahead': '#242424',
            'row-track': '#404040',
            'row-behind': '#2b2b2b'
        };
        
        return `
            <div class="race-row ${cssClass}" style="display: flex; align-items: center; padding: 5px 0; background-color: ${bgColors[cssClass] || 'transparent'}; margin-bottom: 1px; font-family: 'Segoe UI', sans-serif; font-size: 13px; color: #eeeeee;">
                <div class="col-title" style="width: 60px; font-weight: bold; padding-left: 10px;">${title}</div>
                <div class="col-name" style="flex: 1; padding: 0 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${entry ? `${entry.character.name} (Lvl ${entry.character.level})` : 'N/A'}</div>
                <div class="col-progress" style="width: 100px; margin: 0 10px; background-color: #ffffff; height: 8px;">
                    <div style="background-color: #2CC985; height: 100%; width: ${progress}%;"></div>
                </div>
                <div class="col-xp" style="width: 130px; text-align: right; padding: 0 5px; color: ${xpColor}; font-variant-numeric: tabular-nums;">${xpDisplay}</div>
                <div class="col-rank" style="width: 60px; text-align: right; padding-right: 10px;">${entry ? '#' + entry.rank : ''}</div>
            </div>
        `;
    };

    container.innerHTML += createRow("Ahead:", ahead, "row-ahead");
    container.innerHTML += createRow("You:", current, "row-track");
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
            xp: entry.character.experience,
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
    // Colors matching desktop app
    const HEADER_TEXT_COLOR = "#4da6ff";
    const HEADER_SEP_COLOR = "#999999"; // gray60
    const ROW_SEP_COLOR = "#666666"; // gray40
    const ASC_SEP_COLOR = "#4da6ff";

    let output = `<table class="results-table" style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr>
                <th style="text-align: left; color: ${HEADER_TEXT_COLOR}; width: 140px;">Ascendancy</th>
                <th style="text-align: center; color: ${HEADER_TEXT_COLOR}; width: 60px;">Level</th>
                <th style="text-align: left; color: ${HEADER_TEXT_COLOR};">Character Name</th>
                <th style="text-align: center; color: ${HEADER_TEXT_COLOR}; width: 100px;">Progress</th>
                <th style="text-align: right; color: ${HEADER_TEXT_COLOR}; width: 120px;">Rank (Asc/Global)</th>
            </tr>
            <tr><td colspan="5" style="background-color: ${HEADER_SEP_COLOR}; height: 3px; padding: 0; border: none;"></td></tr>
        </thead>
        <tbody>`;
    
    let lastAsc = null;
    results.forEach(char => {
        if (lastAsc) {
            if (char.ascendancy !== lastAsc) {
                output += `<tr><td colspan="5" style="background-color: ${ASC_SEP_COLOR}; height: 2px; padding: 0; border: none;"></td></tr>`;
            } else {
                output += `<tr><td colspan="5" style="background-color: ${ROW_SEP_COLOR}; height: 2px; padding: 0; border: none;"></td></tr>`;
            }
        }
        const progress = calculateProgress(char.level, char.xp);
        output += `<tr>
            <td style="padding: 4px 10px;">${char.ascendancy}</td>
            <td style="text-align: center; padding: 4px 10px;">${char.level}</td>
            <td style="padding: 4px 10px;">${char.name}</td>
            <td style="padding: 4px 10px;"><div style="background-color: #eee; height: 8px; width: 100%;"><div style="background-color: #2CC985; height: 100%; width: ${progress}%;"></div></div></td>
            <td style="text-align: right; padding: 4px 10px;">${char.asc_rank} / ${char.global_rank}</td>
        </tr>`;
        lastAsc = char.ascendancy;
    });
    output += `</tbody></table>`;
    return output;
}