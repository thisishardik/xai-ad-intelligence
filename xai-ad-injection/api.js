// api.js
// Client for fetching ads from ad_server.py

const AD_SERVER_URL = "http://127.0.0.1:8001";

/**
 * Get the current Twitter/X username from the page
 * @returns {Promise<string|null>} Username or null if not found
 */
export async function getCurrentUsername() {
    try {
        // Method 1: Check URL pathname (most reliable)
        const pathname = window.location.pathname;
        const urlMatch = pathname.match(/^\/([^\/\?]+)/);
        if (urlMatch && urlMatch[1]) {
            const potentialUsername = urlMatch[1];
            // Exclude known routes
            const excludedRoutes = ['home', 'explore', 'notifications', 'messages', 'i', 'compose', 'settings', 'search', 'compose', 'bookmarks', 'lists', 'communities'];
            if (!excludedRoutes.includes(potentialUsername.toLowerCase()) && potentialUsername.length > 0) {
                console.log(`[API] Found username from URL: ${potentialUsername}`);
                return potentialUsername;
            }
        }

        // Method 2: Check profile link in navigation
        const profileLink = document.querySelector('a[data-testid="AppTabBar_Profile_Link"], a[href*="/"][href*="profile"]');
        if (profileLink) {
            const href = profileLink.getAttribute('href');
            if (href) {
                const match = href.match(/^\/([^\/\?]+)/);
                if (match && match[1]) {
                    const username = match[1];
                    if (username && !['home', 'explore', 'notifications'].includes(username.toLowerCase())) {
                        console.log(`[API] Found username from profile link: ${username}`);
                        return username;
                    }
                }
            }
        }

        // Method 3: Check sidebar account switcher
        const accountSwitcher = document.querySelector('[data-testid="SideNav_AccountSwitcher_Button"]');
        if (accountSwitcher) {
            const link = accountSwitcher.querySelector('a[href^="/"]');
            if (link) {
                const href = link.getAttribute('href');
                const match = href.match(/^\/([^\/\?]+)/);
                if (match && match[1]) {
                    const username = match[1];
                    if (username && username.length > 0) {
                        console.log(`[API] Found username from account switcher: ${username}`);
                        return username;
                    }
                }
            }
        }

        // Method 4: Try to extract from page metadata or title
        // Twitter sometimes includes username in page title or meta tags
        
        // Fallback: Use a default test user or return null
        console.warn("[API] Could not determine username, will use fallback ads");
        return null;
    } catch (err) {
        console.warn("[API] Error getting username:", err);
        return null;
    }
}

/**
 * Fetch the best ad for a user from ad_server.py
 * @param {string} userId - Twitter username/user ID
 * @param {number} variant - Optional variant index
 * @returns {Promise<Object|null>} Ad data or null if error
 */
export async function fetchAd(userId, variant = null) {
    try {
        let url = `${AD_SERVER_URL}/api/ad/${encodeURIComponent(userId)}`;
        if (variant !== null) {
            url += `?variant=${variant}`;
        }

        console.log(`[API] Fetching ad for user: ${userId}`, { url });

        const response = await fetch(url, {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                console.warn(`[API] No ads found for user: ${userId}`);
                return null;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const adData = await response.json();
        console.log(`[API] Fetched ad:`, adData);
        return adData;

    } catch (err) {
        console.error(`[API] Error fetching ad for ${userId}:`, err);
        return null;
    }
}

/**
 * Fetch all ad variants for a user
 * @param {string} userId - Twitter username/user ID
 * @returns {Promise<Object|null>} All ads data or null if error
 */
export async function fetchAllAds(userId) {
    try {
        const url = `${AD_SERVER_URL}/api/ads/${encodeURIComponent(userId)}`;

        console.log(`[API] Fetching all ads for user: ${userId}`);

        const response = await fetch(url, {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            if (response.status === 404) {
                console.warn(`[API] No ads found for user: ${userId}`);
                return null;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`[API] Fetched ${data.total_ads} ads for user`);
        return data;

    } catch (err) {
        console.error(`[API] Error fetching all ads for ${userId}:`, err);
        return null;
    }
}

/**
 * Check if ad server is available
 * @returns {Promise<boolean>} True if server is reachable
 */
export async function checkServerHealth() {
    try {
        const response = await fetch(`${AD_SERVER_URL}/health`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        });
        return response.ok;
    } catch (err) {
        return false;
    }
}
