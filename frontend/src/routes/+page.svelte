<script lang="ts">
    import { onMount } from 'svelte';

    // Types
    interface Haiku {
        text: string[];
    }

    type Location = string;
    type SearchResult = LocationResult;

    // Weather state with default values
    let weather = {
        temperature: 72,
        condition: 'Sunny',
        location: 'New York',
        humidity: 45
    };

    interface HaikuData {
        text: string[];
        conditions: any;  // You can type this more specifically if needed
        forecast: any;    // You can type this more specifically if needed
    }

    interface WeatherData {
        today: HaikuData;
        tomorrow: HaikuData;
    }

    // Update haiku state to store both days
    let weatherData: WeatherData = {
        today: {
            text: ["Loading your haiku...", "Nature's words will soon appear", "Please wait a moment"],
            conditions: {},
            forecast: {}
        },
        tomorrow: {
            text: ["Loading your haiku...", "Nature's words will soon appear", "Please wait a moment"],
            conditions: {},
            forecast: {}
        }
    };

    // Update currentHaiku to be derived from weatherData and showingTomorrow
    $: currentHaiku = showingTomorrow ? weatherData.tomorrow : weatherData.today;

    // Load saved city from LocalStorage on mount
    onMount(async () => {
        const savedCity = localStorage.getItem('selectedCity');
        if (savedCity) {
            weather.location = savedCity;
        }

        const savedHistory = localStorage.getItem('recentLocations');
        if (savedHistory) {
            recentLocations = JSON.parse(savedHistory);
        }

        await fetchHaikus();
    });

    // Location search state with history
    let showDialog = false;
    let newLocation = '';
    let searchResults: SearchResult[] = [];
    let isSearching = false;
    let selectedIndex = -1;
    let recentLocations: LocationHistory[] = [];
    const MAX_RECENT_LOCATIONS = 10;

    let isRateLimited = false;
    let rateLimitMessage = "Please wait a moment before searching again...";

    async function fetchHaikus() {
        try {
            console.log('Fetching haikus for:', weather.location);
            
            const response = await fetch(
                `http://localhost:8000/api/haikus?location=${encodeURIComponent(weather.location)}`
            );
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                console.error('Response not OK:', response.statusText);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received haiku data:', data);
            
            if (!data.today?.text || !data.tomorrow?.text) {
                console.error('Invalid haiku data received:', data);
                throw new Error('Invalid haiku data');
            }
            
            weatherData = data;
        } catch (error) {
            console.error('Error fetching haikus:', error);
            const errorHaiku = {
                text: ["Error occurred here", "Could not fetch new haiku", "Please try again soon"],
                conditions: {},
                forecast: {}
            };
            weatherData = {
                today: errorHaiku,
                tomorrow: errorHaiku
            };
        }
    }

    // Update handleLocationSelect to use new fetchHaikus
    function handleLocationSelect(result: LocationResult) {
        const location = result.display_name;
        weather.location = location.split(',')[0];
        localStorage.setItem('selectedCity', weather.location);
        
        // Update history
        const now = Date.now();
        const newHistoryEntry: LocationHistory = {
            display_name: location,
            lat: result.lat,
            lon: result.lon,
            timestamp: now
        };

        // Remove any existing entry for this location
        recentLocations = recentLocations.filter(loc => 
            loc.display_name !== location
        );

        // Add new location to start of array
        recentLocations = [newHistoryEntry, ...recentLocations]
            .slice(0, MAX_RECENT_LOCATIONS);  // Keep only most recent

        // Save to localStorage
        localStorage.setItem('recentLocations', JSON.stringify(recentLocations));

        newLocation = '';
        searchResults = [];
        showDialog = false;
        fetchHaikus();  // Replace fetchHaiku() with fetchHaikus()
    }

    // Update toggleDay to just switch the state (no fetch needed)
    function toggleDay() {
        showingTomorrow = !showingTomorrow;
    }

    // Add interface for location search results
    interface LocationResult {
        display_name: string;
        lat: number;
        lon: number;
    }

    interface LocationHistory {
        display_name: string;
        lat: number;
        lon: number;
        timestamp: number;
    }

    async function searchLocations(query: string) {
        if (!query.trim()) {
            // Show recent locations when search is empty
            searchResults = recentLocations.map(loc => ({
                display_name: loc.display_name,
                lat: loc.lat,
                lon: loc.lon
            }));
            return;
        }

        isSearching = true;
        const queryLower = query.toLowerCase();
        
        try {
            // Get history matches first - immediate results
            const historyMatches = recentLocations
                .filter(loc => 
                    loc.display_name.toLowerCase().includes(queryLower)
                )
                .map(loc => ({
                    display_name: loc.display_name,
                    lat: loc.lat,
                    lon: loc.lon
                }));

            // Show history results immediately
            searchResults = historyMatches;

            // Then fetch API results
            const response = await fetch(
                `http://localhost:8000/api/locations/search?query=${encodeURIComponent(query)}`
            );
            
            if (response.status === 429) {
                isRateLimited = true;
                setTimeout(() => { isRateLimited = false; }, 5000); // Reset after 5 seconds
                return; // Keep showing history results
            }
            
            if (!response.ok) {
                throw new Error('Search failed');
            }
            
            isRateLimited = false;
            const apiResults: LocationResult[] = await response.json();
            
            // Combine results, removing duplicates and prioritizing history
            const seenLocations = new Set(historyMatches.map(loc => loc.display_name));
            const combinedResults = [
                ...historyMatches,
                ...apiResults.filter(result => !seenLocations.has(result.display_name))
            ];
            
            searchResults = combinedResults;
            
        } catch (error) {
            console.error('Error searching locations:', error);
            if (searchResults.length === 0) {  // Keep history results if API fails
                searchResults = [];
            }
        } finally {
            isSearching = false;
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (!searchResults.length) return;

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, searchResults.length - 1);
                break;
            case 'ArrowUp':
                event.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                break;
            case 'Enter':
                event.preventDefault();
                if (selectedIndex >= 0) {
                    handleLocationSelect(searchResults[selectedIndex]);
                }
                break;
            case 'Escape':
                event.preventDefault();
                searchResults = [];
                selectedIndex = -1;
                break;
        }
    }

    // Debounce the search function
    let searchTimeout: ReturnType<typeof setTimeout>;
    function handleLocationInput(event: Event) {
        const target = event.target as HTMLInputElement;
        newLocation = target.value;
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchLocations(newLocation);
        }, 500);
    }

    // Day toggle state and handlers
    let showingTomorrow = false;

    $: dayOfWeek = new Date(Date.now() + (showingTomorrow ? 86400000 : 0))
        .toLocaleDateString('en-US', { weekday: 'long' });

    $: historyCount = searchResults.filter(result => 
        recentLocations.some(loc => loc.display_name === result.display_name)
    ).length;
</script>

<svelte:head>
    <link href="https://fonts.googleapis.com/css2?family=Cormorant:ital,wght@1,600&display=swap" rel="stylesheet">
</svelte:head>

<main class="container">    
    <div class="weather-card" role="region" aria-label="Weather information">
        <h2 class="location">
            <button 
                class="location-button" 
                on:click={() => showDialog = true}
                aria-label="Change location from {weather.location}"
            >
                {weather.location}
            </button>
            <span class="separator" aria-hidden="true">&nbsp;-&nbsp;</span>
            <button 
                class="day-button" 
                on:click={toggleDay}
                aria-label="Switch to {showingTomorrow ? 'today' : 'tomorrow'}"
            >
                {dayOfWeek}
            </button>
        </h2>
        <div class="haiku" aria-label="Weather haiku">
            {#each currentHaiku.text as line}
                <p>{line}</p>
            {/each}
        </div>
    </div>

    <footer class="page-footer">
        <div class="bottom-links">
            <div class="credits-row">
                <p class="credit">
                    <a href="https://justin-steele.me" 
                       class="subtle-link" 
                       target="_blank" 
                       rel="noopener noreferrer">site by Justin Steele</a>
                </p>
                <span class="bullet" aria-hidden="true">&bull;</span>
                <p class="coffee">
                    <a href="https://ko-fi.com/justinsteele1499" 
                       class="subtle-link" 
                       target="_blank" 
                       rel="noopener noreferrer">support the developer</a>
                </p>
            </div>
            <div class="credits-row powered-by">
                <p class="credit">powered by</p>
                <a href="https://open-meteo.com/" 
                   class="subtle-link" 
                   target="_blank" 
                   rel="noopener noreferrer">Open-Meteo</a>
                <span class="bullet" aria-hidden="true">&bull;</span>
                <a href="https://www.openstreetmap.org/" 
                   class="subtle-link" 
                   target="_blank" 
                   rel="noopener noreferrer">OpenStreetMap</a>
                <span class="bullet" aria-hidden="true">&bull;</span>
                <a href="https://cursor.sh/" 
                   class="subtle-link" 
                   target="_blank" 
                   rel="noopener noreferrer">Cursor</a>
                <span class="bullet" aria-hidden="true">&bull;</span>
                <a href="https://vercel.com/" 
                   class="subtle-link" 
                   target="_blank" 
                   rel="noopener noreferrer">Vercel</a>
                <span class="bullet" aria-hidden="true">&bull;</span>
                <a href="https://svelte.dev/" 
                   class="subtle-link" 
                   target="_blank" 
                   rel="noopener noreferrer">Svelte</a>
            </div>
        </div>
    </footer>
</main>

{#if showDialog}
    <dialog 
        class="location-dialog" 
        open
        aria-labelledby="dialog-title"
    >
        <div class="search-container">
            <h3 id="dialog-title" class="visually-hidden">Change Location</h3>
            <input
                type="text"
                value={newLocation}
                on:input={handleLocationInput}
                on:keydown={handleKeydown}
                placeholder="Enter city name"
                autocomplete="off"
                aria-label="New location name"
                aria-expanded={searchResults.length > 0}
                aria-autocomplete="list"
                aria-controls="location-results"
            />
            {#if isRateLimited}
                <div class="rate-limit-warning" role="alert">
                    {rateLimitMessage}
                </div>
            {/if}
            {#if searchResults.length > 0}
                <ul 
                    id="location-results"
                    class="search-results"
                    role="listbox"
                >
                    {#each searchResults as result, i}
                        <li 
                            role="option"
                            aria-selected={i === selectedIndex}
                            class="result-item"
                            class:selected={i === selectedIndex}
                            class:history={i < historyCount}
                            on:click={() => handleLocationSelect(result)}
                        >
                            {result.display_name}
                            {#if i < historyCount}
                                <span class="history-indicator">recent</span>
                            {/if}
                        </li>
                    {/each}
                </ul>
            {/if}
            {#if isSearching && !isRateLimited}
                <div class="loading-indicator">Searching...</div>
            {/if}
            <div class="dialog-buttons">
                <button 
                    type="button" 
                    on:click={() => {
                        showDialog = false;
                        searchResults = [];
                    }}
                >
                    Cancel
                </button>
            </div>
        </div>
    </dialog>
{/if}

<style>
    .container {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
    }

    .weather-card {
        text-align: center;
        transform: translateY(-10vh);
    }

    .switch-day {
        font-size: 0.8rem;
        margin: 0;
        position: absolute;
        top: 2rem;
        color: #666;
    }

    .bottom-links {
        position: absolute;
        bottom: 3.5rem;
        left: 0;
        right: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.3rem;
        text-align: center;
        width: 100%;
    }

    .left-credits {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.3rem;
    }

    .credit, .coffee {
        font-size: 0.8rem;
        margin: 0;
        color: #666;
    }

    .subtle-link {
        color: inherit;
        text-decoration: none;
    }

    .subtle-link:hover {
        text-decoration: underline;
    }

    .location {
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
    }

    .weather-info {
        margin-top: 1rem;
    }

    .temperature, .condition, .humidity {
        font-family: 'Cormorant', serif;
        font-style: italic;
        font-weight: 400;
    }

    .temperature {
        font-size: 2.5rem;
        margin: 0;
    }

    .condition {
        font-size: 1.2rem;
        color: #666;
        margin: 0.5rem 0;
    }

    .humidity {
        margin: 0;
    }

    .location-button {
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        color: inherit;
        cursor: pointer;
    }

    .location-button:hover {
        text-decoration: underline;
    }

    .location-dialog {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        padding: 2rem;
        border: none;
        border-radius: 8px;
        background: white;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }

    .location-dialog::backdrop {
        background: rgba(0, 0, 0, 0.3);
    }

    .location-dialog input {
        width: 100%;
        padding: 0.5rem;
        font-size: 1rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        margin-bottom: 1rem;
    }

    .dialog-buttons {
        display: flex;
        gap: 1rem;
        justify-content: flex-end;
    }

    .dialog-buttons button {
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }

    .dialog-buttons button[type="button"] {
        background: #eee;
    }

    .dialog-buttons button[type="submit"] {
        background: #666;
        color: white;
    }

    .dialog-buttons button:hover {
        opacity: 0.9;
    }

    .separator, .day-text {
        cursor: default;
    }

    .day-button {
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        color: inherit;
        cursor: pointer;
    }

    .day-button:hover {
        text-decoration: underline;
    }

    .haiku {
        font-family: 'Cormorant', serif;
        font-style: italic;
        font-weight: 600;
        color: black;
        margin: 3rem 0;
        line-height: 1.8;
    }

    .haiku p {
        margin: 0;
        font-size: 2rem;
    }

    /* Add visually-hidden utility class */
    .visually-hidden {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        border: 0;
    }

    /* Remove unused classes */
    .switch-day,
    .weather-info,
    .temperature,
    .condition,
    .humidity {
        display: none;
    }

    /* Update footer positioning */
    .page-footer {
        position: absolute;
        bottom: 1.5rem;
        left: 0;
        right: 0;
        text-align: center;
    }

    .credits-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
    }

    .bullet {
        color: #666;
    }

    .search-container {
        position: relative;
        min-width: 300px;
    }

    .search-results {
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        max-height: 200px;
        overflow-y: auto;
        margin: 0;
        padding: 0;
        list-style: none;
        background: white;
        border: 1px solid #ccc;
        border-top: none;
        border-radius: 0 0 4px 4px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .result-item {
        padding: 0.5rem 1rem;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .result-item:hover,
    .result-item.selected {
        background-color: #f5f5f5;
    }

    .loading-indicator {
        position: absolute;
        right: 1rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.8rem;
        color: #666;
    }

    /* Update dialog styles */
    .location-dialog {
        min-width: 320px;
    }

    .location-dialog input {
        width: 100%;
        padding: 0.5rem;
        font-size: 1rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        margin-bottom: 1rem;
    }

    .powered-by {
        font-size: 0.7rem;
        margin-top: 0.5rem;
        color: #888;
        gap: 0.5rem;
    }

    .powered-by .credit {
        font-size: inherit;
        color: inherit;
    }

    .powered-by .bullet {
        color: #888;
    }

    .powered-by a {
        color: inherit;
    }

    .history-indicator {
        font-size: 0.7em;
        color: #666;
        margin-left: 0.5rem;
        padding: 0.1rem 0.3rem;
        border-radius: 3px;
        background: #f0f0f0;
    }

    .result-item.history {
        background-color: #fafafa;
    }

    .result-item.history:hover,
    .result-item.history.selected {
        background-color: #f0f0f0;
    }

    .rate-limit-warning {
        position: absolute;
        right: 1rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.8rem;
        color: #e67e22;  /* Orange warning color */
        animation: fadeInOut 2s ease-in-out infinite;
    }

    @keyframes fadeInOut {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
</style>
