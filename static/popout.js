let foundCharacterEntry = null;
let leagueId = null;
let allFetchedEntries = [];
let raceInterval = null;
let xpHistory = {};

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
    // Retrieve data from main window's localStorage
    foundCharacterEntry = JSON.parse(localStorage.getItem('raceModeCharacter'));
    leagueId = localStorage.getItem('raceModeLeagueId');
    allFetchedEntries = JSON.parse(localStorage.getItem('allFetchedEntries')) || [];
    
    const storedHistory = localStorage.getItem('raceModeXpHistory');
    if (storedHistory) {
        xpHistory = JSON.parse(storedHistory);
    }

    if (foundCharacterEntry && leagueId) {
        document.title = `Race: ${foundCharacterEntry.character.name}`;
        document.getElementById('classHeader').textContent = foundCharacterEntry.character.class;
        updateHeaderInfo();
        
        updateRaceData();
        toggleAutoRefresh();
    } else {
        document.body.innerHTML = '<div style="padding: 20px;"><h1>No character data found.</h1><p>Please search for a character in the main window first and click "Popout".</p></div>';
    }
});

function updateHeaderInfo() {
    if (!foundCharacterEntry) return;
    const name = foundCharacterEntry.character.name;
    // Try to find rank in cached entries if available, otherwise use what we have
    let rank = foundCharacterEntry.asc_rank || '?';
    if (rank === '?' && allFetchedEntries.length > 0) {
        const myClass = foundCharacterEntry.character.class;
        const ascEntries = allFetchedEntries.filter(e => e.character.class === myClass);
        const idx = ascEntries.findIndex(e => e.character.name === name);
        if (idx !== -1) rank = idx + 1;
    }
    document.getElementById('trackingHeader').textContent = `Tracking: ${name} | Asc: #${rank}`;
}

function toggleRaceView() {
    const mode = document.getElementById('viewModeSelect').value;
    const ascSection = document.getElementById('ascSection');
    const globalSection = document.getElementById('globalSection');
    const globalHeader = document.getElementById('globalHeader');

    if (mode === 'both') {
        ascSection.classList.remove('hidden');
        globalSection.classList.remove('hidden');
        globalHeader.classList.remove('hidden');
    } else if (mode === 'ascendancy') {
        ascSection.classList.remove('hidden');
        globalSection.classList.add('hidden');
    } else if (mode === 'global') {
        ascSection.classList.add('hidden');
        globalSection.classList.remove('hidden');
        globalHeader.classList.add('hidden');
    }
}

function toggleAutoRefresh() {
    const isChecked = document.getElementById('autoRefreshCheck').checked;
    const btn = document.getElementById('refreshRaceBtn');
    
    if (raceInterval) clearInterval(raceInterval);
    
    if (isChecked) {
        raceInterval = setInterval(updateRaceData, 60000); // 60s
        if (btn && btn.style.display !== 'none') {
            const isInitial = btn.style.display === '';
            const container = btn.parentElement;
            const oldHeight = container.offsetHeight;
            btn.style.display = 'none';
            if (!isInitial) {
                const newHeight = container.offsetHeight;
                window.resizeBy(0, newHeight - oldHeight);
            }
        }
    } else {
        if (btn && btn.style.display === 'none') {
            const container = btn.parentElement;
            const oldHeight = container.offsetHeight;
            btn.style.display = 'block';
            const newHeight = container.offsetHeight;
            window.resizeBy(0, newHeight - oldHeight);
        }
    }
}

async function updateRaceData() {
    if (!foundCharacterEntry || !leagueId) return;

    const btn = document.getElementById('refreshRaceBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Refreshing...";
    }

    const charName = foundCharacterEntry.character.name.toLowerCase();
    let currentOffset = 0;
    let found = false;
    let ascCounts = {};
    let surroundingEntries = [];
    let prevChunk = [];

    // Scan from 0 to get accurate Ascendancy Ranks
    while (currentOffset < 15000) {
        try {
            const response = await fetch(`/public-ladder/${encodeURIComponent(leagueId)}?limit=${CHUNK_SIZE}&offset=${currentOffset}`);
            const data = await response.json();
            
            if (!data.entries || data.entries.length === 0) break;
            
            const entries = data.entries;
            
            for (let i = 0; i < entries.length; i++) {
                const entry = entries[i];
                const asc = entry.character.class;
                if (!ascCounts[asc]) ascCounts[asc] = 0;
                ascCounts[asc]++;
                
                // Stamp ranks
                entry.ascendancy_rank = ascCounts[asc];
                entry.rank = currentOffset + i + 1;
                
                if (entry.character.name.toLowerCase() === charName) {
                    found = true;
                    // Build context: prev chunk (last 10) + current chunk
                    surroundingEntries = [...(prevChunk.slice(-10)), ...entries];
                    
                    // If near end of chunk, fetch one more small chunk for "Behind" neighbor
                    if (i >= entries.length - 2) {
                         const nextRes = await fetch(`/public-ladder/${encodeURIComponent(leagueId)}?limit=10&offset=${currentOffset + CHUNK_SIZE}`);
                         const nextData = await nextRes.json();
                         if (nextData.entries) {
                             nextData.entries.forEach((ne, ni) => {
                                 const nasc = ne.character.class;
                                 if (!ascCounts[nasc]) ascCounts[nasc] = 0;
                                 ascCounts[nasc]++;
                                 ne.ascendancy_rank = ascCounts[nasc];
                                 ne.rank = currentOffset + CHUNK_SIZE + ni + 1;
                             });
                             surroundingEntries.push(...nextData.entries);
                         }
                    }
                    break;
                }
            }
            
            if (found) break;
            
            prevChunk = entries;
            currentOffset += CHUNK_SIZE;
            
            // Small delay to prevent UI lockup
            await new Promise(r => setTimeout(r, 50));
            
        } catch (e) {
            console.error(e);
            break;
        }
    }

    if (found) {
        processRaceData(surroundingEntries);
    }

    if (btn) {
        btn.disabled = false;
        btn.textContent = "Refresh";
    }
}

function processRaceData(surroundingEntries) {
    const myName = foundCharacterEntry.character.name;
    const myNewEntry = surroundingEntries.find(e => e.character.name === myName);
    
    if (!myNewEntry) return; 

    foundCharacterEntry = myNewEntry;
    updateHeaderInfo();
    const myXp = myNewEntry.character.experience;
    const myClass = myNewEntry.character.class;

    // Calculate rates and update history
    const now = Date.now();
    const rates = {};
    surroundingEntries.forEach(entry => {
        const name = entry.character.name;
        if (xpHistory[name]) {
            const prev = xpHistory[name];
            const timeDiff = (now - prev.time) / 1000;
            const xpDiff = entry.character.experience - prev.xp;
            
            if (xpDiff > 0 && timeDiff > 0) {
                // XP Changed: Calculate new rate
                const currentRate = (xpDiff / timeDiff) * 3600;
                rates[name] = currentRate;
                xpHistory[name] = {
                    xp: entry.character.experience,
                    time: now,
                    lastRate: currentRate,
                    lastUpdate: now
                };
            } else {
                // XP Unchanged: Check for idle timeout (5 mins)
                const lastUpdate = prev.lastUpdate || prev.time;
                const timeSinceUpdate = (now - lastUpdate) / 1000;
                
                if (timeSinceUpdate > 300) {
                    rates[name] = 0;
                } else {
                    rates[name] = prev.lastRate || 0;
                }
                
                // Update timestamp but preserve lastRate and lastUpdate
                xpHistory[name] = {
                    xp: entry.character.experience,
                    time: now,
                    lastRate: rates[name],
                    lastUpdate: lastUpdate
                };
            }
        } else {
            rates[name] = 0;
            xpHistory[name] = {
                xp: entry.character.experience,
                time: now,
                lastRate: 0,
                lastUpdate: now
            };
        }
    });

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
    renderLadderTable('globalTable', globalAhead, myNewEntry, globalBehind, myXp, 'rank', rates);

    const ascAhead = getNeighbor(ascEntries, myNewEntry, 'ahead', cachedAscEntries);
    const ascBehind = getNeighbor(ascEntries, myNewEntry, 'behind', cachedAscEntries);
    renderLadderTable('ascTable', ascAhead, myNewEntry, ascBehind, myXp, 'ascendancy_rank', rates);
}

function renderLadderTable(elementId, ahead, current, behind, myXp, rankField, rates) {
    const container = document.getElementById(elementId);
    container.innerHTML = '';
    
    const createRow = (title, entry, cssClass) => {
        let xpDisplay = '';
        let xpColor = '#eeeeee';
        let rankDisplay = '';
        
        if (entry) {
            if (cssClass === 'row-track') {
                const rate = rates && rates[entry.character.name] ? rates[entry.character.name] : 0;
                if (rate >= 1000000) {
                    xpDisplay = `XP/h: ${(rate / 1000000).toFixed(2).replace('.', ',')}m`;
                } else {
                    xpDisplay = `XP/h: ${Math.floor(rate).toLocaleString()}`;
                }
                xpColor = '#ffffff';
            } else {
                if (entry.dead) {
                    xpDisplay = '💀';
                    xpColor = '#FF5252';
                } else if (entry.retired) {
                    xpDisplay = '♿';
                    xpColor = '#AAAAAA';
                } else {
                    const rate = rates && rates[entry.character.name] ? rates[entry.character.name] : 0;
                    if (rate >= 1000000) {
                        xpDisplay = `${(rate / 1000000).toFixed(2).replace('.', ',')} m/h`;
                    } else {
                        xpDisplay = `${Math.floor(rate).toLocaleString()}/h`;
                    }
                    if (rate > 0) xpColor = '#2CC985';
                    else xpColor = '#888888';
                }
            }
            rankDisplay = '#' + (entry[rankField] || entry.rank || '?');
        }

        const progress = entry ? calculateProgress(entry.character.level, entry.character.experience) : 0;
        let progressContent;

        if (entry && entry.dead) {
            progressContent = `<div class="col-progress" style="width: 100px; margin: 0 10px; text-align: center;"><span style="color: #FF5252; font-size: 16px; line-height: 1;">💀</span></div>`;
        } else if (entry && entry.retired) {
            progressContent = `<div class="col-progress" style="width: 100px; margin: 0 10px; text-align: center;"><span style="color: #AAAAAA; font-size: 16px; line-height: 1;">♿</span></div>`;
        } else {
            progressContent = `<div class="col-progress" style="width: 100px; margin: 0 10px; background-color: #ffffff; height: 8px;">
                    <div style="background-color: #2CC985; height: 100%; width: ${progress}%;"></div>
                </div>`;
        }
        
        // Colors matching desktop app
        const bgColors = {
            'row-ahead': '#242424', // gray14
            'row-track': '#404040', // gray25
            'row-behind': '#2b2b2b' // gray17
        };
        
        return `
            <div class="race-row ${cssClass}" style="display: flex; align-items: center; padding: 5px 0; background-color: ${bgColors[cssClass] || 'transparent'}; margin-bottom: 1px; font-family: 'Segoe UI', sans-serif; font-size: 13px; color: #eeeeee;">
                <div class="col-title" style="width: 60px; font-weight: bold; padding-left: 10px;">${title}</div>
                <div class="col-name" style="flex: 1; padding: 0 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${entry ? `${entry.character.name} (Lvl ${entry.character.level})` : 'N/A'}</div>
                ${progressContent}
                <div class="col-xp" style="width: 130px; text-align: right; padding: 0 5px; color: ${xpColor}; font-variant-numeric: tabular-nums;">${xpDisplay}</div>
                <div class="col-rank" style="width: 60px; text-align: right; padding-right: 10px; color: #ffffff;">${rankDisplay}</div>
            </div>
        `;
    };

    container.innerHTML += createRow("Ahead:", ahead, "row-ahead");
    container.innerHTML += createRow("You:", current, "row-track");
    container.innerHTML += createRow("Behind:", behind, "row-behind");
}