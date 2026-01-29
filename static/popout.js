let foundCharacterEntry = null;
let leagueId = null;
let allFetchedEntries = [];
let raceInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    // Retrieve data from main window's localStorage
    foundCharacterEntry = JSON.parse(localStorage.getItem('raceModeCharacter'));
    leagueId = localStorage.getItem('raceModeLeagueId');
    allFetchedEntries = JSON.parse(localStorage.getItem('allFetchedEntries')) || [];

    if (foundCharacterEntry && leagueId) {
        document.title = `Race: ${foundCharacterEntry.character.name}`;
        document.getElementById('trackingHeader').textContent = `Tracking: ${foundCharacterEntry.character.name}`;
        document.getElementById('ascHeader').textContent = `${foundCharacterEntry.character.class} Ladder`;
        
        updateRaceData();
        toggleAutoRefresh();
    } else {
        document.body.innerHTML = '<div style="padding: 20px;"><h1>No character data found.</h1><p>Please search for a character in the main window first and click "Popout".</p></div>';
    }
});

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

function toggleAutoRefresh() {
    const isChecked = document.getElementById('autoRefreshCheck').checked;
    if (raceInterval) clearInterval(raceInterval);
    
    if (isChecked) {
        raceInterval = setInterval(updateRaceData, 60000); // 60s
    }
}

async function updateRaceData() {
    if (!foundCharacterEntry || !leagueId) return;

    const btn = document.getElementById('refreshRaceBtn');
    btn.disabled = true;
    btn.textContent = "Refreshing...";

    const targetRank = foundCharacterEntry.rank;
    
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
    const myNewEntry = surroundingEntries.find(e => e.character.name === myName);
    
    if (!myNewEntry) return; 

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
            const cacheIdx = cache.findIndex(e => e.character.name === selfEntry.character.name);
            if (cacheIdx > 0) return cache[cacheIdx - 1];
        } else { // 'behind'
            if (idx < list.length - 1) return list[idx + 1];
            // Fallback to cache
            const cacheIdx = cache.findIndex(e => e.character.name === selfEntry.character.name);
            if (cacheIdx !== -1 && cacheIdx < cache.length - 1) return cache[cacheIdx + 1];
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