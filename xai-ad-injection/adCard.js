// // // adCard.js

// // function createAdCard() {
// //     const card = document.createElement("article");

// //     card.className =
// //         "css-175oi2r r-18u37iz r-1udh08x r-1c4vpko r-1c7gwzm r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21";

// //     card.style.border = "1px solid rgba(255,255,255,0.1)";
// //     card.style.borderRadius = "16px";
// //     card.style.padding = "12px";
// //     card.style.background = "#0f1419";
// //     card.style.margin = "12px 0";

// //     card.innerHTML = `
// //         <div style="display:flex; gap:12px;">
// //             <img 
// //                 src="https://picsum.photos/40" 
// //                 style="width:40px;height:40px;border-radius:50%;" 
// //             />

// //             <div style="flex:1;">
// //                 <div style="font-weight:700;color:#e7e9ea;">Sponsored</div>
// //                 <div style="color:#71767b;font-size:13px;">This is a static ad placeholder</div>
// //             </div>
// //         </div>

// //         <div style="margin-top:10px;color:#e7e9ea;">
// //             🚀 Upgrade your workflow today!
// //         </div>

// //         <div style="margin-top:10px;">
// //             <img src="https://picsum.photos/500" 
// //                  style="width:100%;border-radius:12px;" />
// //         </div>
// //     `;

// //     return card;
// // }

// // window.createAdCard = createAdCard;

// // adCard.js

// import { fetchAd, getCurrentUsername, checkServerHealth } from "./api.js";

// // -----------------------------------------------------
// // 🔥 Utility: generate random dummy ads for testing (fallback)
// // -----------------------------------------------------
// function generateDummyAd() {
//     const titles = [
//         "Boost Your Productivity",
//         "Upgrade Your Workflow",
//         "Try Pro Tools Now",
//         "Level Up Your Career",
//         "AI Tools Sale!",
//         "New Feature Released!",
//     ];

//     const descriptions = [
//         "Save 20% today",
//         "Limited time offer",
//         "Best in class",
//         "Trusted by teams worldwide",
//         "Start your free trial",
//     ];

//     const images = [
//         "https://picsum.photos/500?1",
//         "https://picsum.photos/500?2",
//         "https://picsum.photos/500?3",
//         "https://picsum.photos/500?4",
//     ];

//     return {
//         title: titles[Math.floor(Math.random() * titles.length)],
//         description: descriptions[Math.floor(Math.random() * descriptions.length)],
//         image: images[Math.floor(Math.random() * images.length)],
//         brand: "AdBot",
//         avatar: "https://picsum.photos/40",
//     };
// }

// /**
//  * Format ad data from server to match expected format
//  */
// function formatServerAd(serverAd) {
//     if (!serverAd) return null;

//     return {
//         title: serverAd.title || "Sponsored Ad",
//         description: serverAd.description || "",
//         full_content: serverAd.full_content || "",
//         image: serverAd.image_uri || null,
//         brand: serverAd.brand || "AI Personalized",
//         avatar: serverAd.avatar || "https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
//         ctr_score: serverAd.ctr_score || 0,
//         confidence: serverAd.confidence || 0,
//         ad_index: serverAd.ad_index || 0,
//         total_variants: serverAd.total_variants || 1
//     };
// }

// /**
//  * Detect the current theme (dark/light) from Twitter/X page
//  * Uses multiple detection methods for reliability
//  * @returns {Object} Theme colors object
//  */
// function detectTheme() {
//     const htmlElement = document.documentElement;
//     const body = document.body;
//     let isDark = null;
    
//     // Method 1: Check data-theme attribute (Twitter/X primary method)
//     const dataTheme = htmlElement.getAttribute('data-theme');
//     if (dataTheme === 'dark') {
//         isDark = true;
//     } else if (dataTheme === 'light') {
//         isDark = false;
//     }
    
//     // Method 2: Check computed style of a tweet element (most reliable visual indicator)
//     if (isDark === null) {
//         const sampleTweet = document.querySelector('article[data-testid="tweet"]');
//         if (sampleTweet) {
//             const computedStyle = window.getComputedStyle(sampleTweet);
//             const bgColor = computedStyle.backgroundColor;
            
//             // Parse RGB values
//             const rgbMatch = bgColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
//             if (rgbMatch) {
//                 const r = parseInt(rgbMatch[1]);
//                 const g = parseInt(rgbMatch[2]);
//                 const b = parseInt(rgbMatch[3]);
//                 const brightness = r + g + b;
                
//                 // Twitter/X dark mode: typically rgb(0,0,0) or very dark colors
//                 // Light mode: typically rgb(255,255,255) or rgb(247,249,249)
//                 // Threshold: if brightness < 100, it's dark; if > 500, it's light
//                 if (brightness < 100) {
//                     isDark = true;
//                 } else if (brightness > 500) {
//                     isDark = false;
//                 }
//             }
//         }
//     }
    
//     // Method 3: Check body or main container background
//     if (isDark === null) {
//         const mainContainer = document.querySelector('[data-testid="primaryColumn"], main, [role="main"]');
//         const elementToCheck = mainContainer || body;
//         const bgColor = window.getComputedStyle(elementToCheck).backgroundColor;
        
//         const rgbMatch = bgColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
//         if (rgbMatch) {
//             const r = parseInt(rgbMatch[1]);
//             const g = parseInt(rgbMatch[2]);
//             const b = parseInt(rgbMatch[3]);
//             const brightness = r + g + b;
            
//             if (brightness < 50) {
//                 isDark = true;
//             } else if (brightness > 200) {
//                 isDark = false;
//             }
//         }
//     }
    
//     // Method 4: Check CSS custom properties (Twitter/X might use these)
//     if (isDark === null) {
//         const rootStyle = window.getComputedStyle(htmlElement);
//         // Try to get common CSS variables
//         const bgVar = rootStyle.getPropertyValue('--r-bg') || 
//                      rootStyle.getPropertyValue('--background-color') ||
//                      rootStyle.getPropertyValue('--bg-color');
        
//         if (bgVar) {
//             const rgbMatch = bgVar.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
//             if (rgbMatch) {
//                 const brightness = parseInt(rgbMatch[1]) + parseInt(rgbMatch[2]) + parseInt(rgbMatch[3]);
//                 isDark = brightness < 100;
//             }
//         }
//     }
    
//     // Method 5: Check for dark mode class names
//     if (isDark === null) {
//         const hasDarkClass = htmlElement.classList.contains('dark') || 
//                             body.classList.contains('dark') ||
//                             htmlElement.classList.contains('theme-dark');
//         const hasLightClass = htmlElement.classList.contains('light') || 
//                              body.classList.contains('light') ||
//                              htmlElement.classList.contains('theme-light');
        
//         if (hasDarkClass) {
//             isDark = true;
//         } else if (hasLightClass) {
//             isDark = false;
//         }
//     }
    
//     // Method 6: Fallback - check if prefers-color-scheme matches
//     if (isDark === null) {
//         const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
//         isDark = prefersDark;
//     }
    
//     // Default to dark mode if still uncertain (Twitter/X default)
//     if (isDark === null) {
//         isDark = true;
//     }
    
//     // Return theme colors matching Twitter/X design system
//     if (isDark) {
//         return {
//             isDark: true,
//             background: '#0f1419',
//             border: 'rgba(255,255,255,0.1)',
//             textPrimary: '#e7e9ea',
//             textSecondary: '#71767b',
//             cardBg: '#0f1419'
//         };
//     } else {
//         return {
//             isDark: false,
//             background: '#ffffff',
//             border: '#E7E9EC',
//             textPrimary: '#0f1419',
//             textSecondary: '#536471',
//             cardBg: '#ffffff'
//         };
//     }
// }

// // -----------------------------------------------------
// // ✅ Main function: returns a DOM element (not a string)
// // -----------------------------------------------------
// async function createAdCard() {
//     let adData = null;

//     // Try to fetch from ad_server.py
//     try {
//         const isServerAvailable = await checkServerHealth();
        
//         if (isServerAvailable) {
//             const username = await getCurrentUsername();
            
//             if (username) {
//                 console.log(`[AdCard] Fetching ad for user: ${username}`);
//                 const serverAd = await fetchAd(username);
                
//                 if (serverAd) {
//                     adData = formatServerAd(serverAd);
//                     console.log(`[AdCard] Using server ad:`, adData);
//                 } else {
//                     console.warn(`[AdCard] No ad found for ${username}, using fallback`);
//                 }
//             } else {
//                 console.warn(`[AdCard] Could not determine username, using fallback`);
//             }
//         } else {
//             console.warn(`[AdCard] Ad server not available, using fallback`);
//         }
//     } catch (err) {
//         console.error(`[AdCard] Error fetching ad:`, err);
//     }

//     // Fallback to dummy ad if server fetch failed
//     if (!adData) {
//         adData = generateDummyAd();
//         console.log(`[AdCard] Using dummy ad`);
//     }

//     // -------------------------------------------------
//     // ✅ Detect theme and build DOM element
//     // -------------------------------------------------
//     const theme = detectTheme();
    
//     // Try to copy styles from an actual tweet for perfect theme matching
//     const sampleTweet = document.querySelector('article[data-testid="tweet"]');
//     let tweetStyles = {
//         backgroundColor: null,
//         borderColor: null,
//         textPrimary: null,
//         textSecondary: null
//     };
    
//     if (sampleTweet) {
//         const computedStyle = window.getComputedStyle(sampleTweet);
//         tweetStyles.backgroundColor = computedStyle.backgroundColor;
//         tweetStyles.borderColor = computedStyle.borderColor || computedStyle.borderTopColor;
        
//         // Get primary text color from tweet text
//         const tweetText = sampleTweet.querySelector('[data-testid="tweetText"], span[dir="ltr"], div[dir="ltr"]');
//         if (tweetText) {
//             tweetStyles.textPrimary = window.getComputedStyle(tweetText).color;
//         } else {
//             tweetStyles.textPrimary = computedStyle.color;
//         }
        
//         // Get secondary text color from username/handle or timestamp
//         const secondaryText = sampleTweet.querySelector('span[data-testid="User-Name"], time, [data-testid="User-Names"] span:last-child');
//         if (secondaryText) {
//             tweetStyles.textSecondary = window.getComputedStyle(secondaryText).color;
//         }
//     }
    
//     const card = document.createElement("article");

//     card.className = "custom-ad-card";

//     // Use tweet's actual background if available, otherwise use theme colors
//     // Handle transparent or missing borders
//     let borderColor = theme.border;
//     if (tweetStyles.borderColor && 
//         tweetStyles.borderColor !== 'transparent' && 
//         tweetStyles.borderColor !== 'rgba(0, 0, 0, 0)' &&
//         !tweetStyles.borderColor.includes('rgba(0, 0, 0, 0)')) {
//         borderColor = tweetStyles.borderColor;
//     }
    
//     card.style.border = `1px solid ${borderColor}`;
//     card.style.borderRadius = "16px";
//     card.style.padding = "12px";
//     card.style.background = tweetStyles.backgroundColor || theme.cardBg;
//     card.style.margin = "12px 0";
//     card.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
    
//     // Debug logging (can be removed in production)
//     console.log('[AdCard] Theme detection:', {
//         isDark: theme.isDark,
//         tweetBg: tweetStyles.backgroundColor,
//         tweetTextColor: tweetStyles.textPrimary,
//         tweetSecondaryColor: tweetStyles.textSecondary,
//         cardBg: card.style.background,
//         dataTheme: document.documentElement.getAttribute('data-theme'),
//         borderColor: borderColor
//     });

//     // Build the ad card HTML
//     const imageHtml = adData.image 
//         ? `<div style="margin-top:10px;">
//             <img src="${adData.image}" 
//                  style="width:100%;border-radius:12px;object-fit:contain;display:block;" 
//                  onerror="this.style.display='none'" />
//         </div>`
//         : '';

//     // Use tweet colors if available, otherwise fall back to theme colors
//     const textPrimary = tweetStyles.textPrimary || theme.textPrimary;
//     const textSecondary = tweetStyles.textSecondary || theme.textSecondary;
    
//     const fullContentHtml = adData.full_content && adData.full_content !== adData.title
//         ? `<div style="margin-top:10px;color:${textPrimary};white-space:pre-wrap;line-height:1.5;">
//             ${adData.full_content.replace(/\n/g, '<br>')}
//         </div>`
//         : '';

//     card.innerHTML = `
//         <div>
//             <div style="font-weight:700;color:${textPrimary};">
//                 ${adData.brand} · Sponsored
//             </div>

//             ${adData.description ? `<div style="color:${textSecondary};font-size:13px;margin-top:4px;">
//                 ${adData.description}
//             </div>` : ''}
//         </div>

//         <div style="margin-top:10px;color:${textPrimary};font-weight:600;font-size:15px;">
//             ${adData.title}
//         </div>

//         ${fullContentHtml}
//         ${imageHtml}
//     `;

//     return card;
// }



// // -----------------------------------------------------
// // ✅ Export as ES module and also expose globally
// // -----------------------------------------------------
// export { createAdCard };
// window.createAdCard = createAdCard;


// // adCard.js
 
// function createAdCard() {
//     const card = document.createElement("article");
 
//     card.className =
//         "css-175oi2r r-18u37iz r-1udh08x r-1c4vpko r-1c7gwzm r-o7ynqc r-6416eg r-1ny4l3l r-1loqt21";
 
//     card.style.border = "1px solid rgba(255,255,255,0.1)";
//     card.style.borderRadius = "16px";
//     card.style.padding = "12px";
//     card.style.background = "#0f1419";
//     card.style.margin = "12px 0";
 
//     card.innerHTML = `
//         <div style="display:flex; gap:12px;">
//             <img 
//                 src="https://picsum.photos/40" 
//                 style="width:40px;height:40px;border-radius:50%;" 
//             />
 
//             <div style="flex:1;">
//                 <div style="font-weight:700;color:#e7e9ea;">Sponsored</div>
//                 <div style="color:#71767b;font-size:13px;">This is a static ad placeholder</div>
//             </div>
//         </div>
 
//         <div style="margin-top:10px;color:#e7e9ea;">
//             🚀 Upgrade your workflow today!
//         </div>
 
//         <div style="margin-top:10px;">
//             <img src="https://picsum.photos/500" 
//                  style="width:100%;border-radius:12px;" />
//         </div>
//     `;
 
//     return card;
// }
 
// window.createAdCard = createAdCard;
 
// adCard.js
 
import { fetchAd, getCurrentUsername, checkServerHealth } from "./api.js";
 
// -----------------------------------------------------
// 🔥 Utility: generate random dummy ads for testing (fallback)
// -----------------------------------------------------
function generateDummyAd() {
    const titles = [
        "Boost Your Productivity",
        "Upgrade Your Workflow",
        "Try Pro Tools Now",
        "Level Up Your Career",
        "AI Tools Sale!",
        "New Feature Released!",
    ];
 
    const descriptions = [
        "Save 20% today",
        "Limited time offer",
        "Best in class",
        "Trusted by teams worldwide",
        "Start your free trial",
    ];
 
    const images = [
        "https://picsum.photos/500?1",
        "https://picsum.photos/500?2",
        "https://picsum.photos/500?3",
        "https://picsum.photos/500?4",
    ];
 
    return {
        title: titles[Math.floor(Math.random() * titles.length)],
        description: descriptions[Math.floor(Math.random() * descriptions.length)],
        image: images[Math.floor(Math.random() * images.length)],
        brand: "AdBot",
        avatar: "https://picsum.photos/40",
    };
}
 
/**
 * Format ad data from server to match expected format
 */
function formatServerAd(serverAd) {
    if (!serverAd) return null;
 
    return {
        title: serverAd.title || "Sponsored Ad",
        description: serverAd.description || "",
        full_content: serverAd.full_content || "",
        image: serverAd.image_uri || null,
        brand: serverAd.brand || "AI Personalized",
        avatar: serverAd.avatar || "https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
        ctr_score: serverAd.ctr_score || 0,
        confidence: serverAd.confidence || 0,
        ad_index: serverAd.ad_index || 0,
        total_variants: serverAd.total_variants || 1
    };
}
 
/**
 * Detect the current theme (dark/light) from Twitter/X page
 * Uses multiple detection methods for reliability
 * @returns {Object} Theme colors object
 */
function detectTheme() {
    const htmlElement = document.documentElement;
    const body = document.body;
    let isDark = null;
 
    // Method 1: Check data-theme attribute (Twitter/X primary method)
    const dataTheme = htmlElement.getAttribute('data-theme');
    if (dataTheme === 'dark') {
        isDark = true;
    } else if (dataTheme === 'light') {
        isDark = false;
    }
 
    // Method 2: Check computed style of a tweet element (most reliable visual indicator)
    if (isDark === null) {
        const sampleTweet = document.querySelector('article[data-testid="tweet"]');
        if (sampleTweet) {
            const computedStyle = window.getComputedStyle(sampleTweet);
            const bgColor = computedStyle.backgroundColor;
 
            // Parse RGB values
            const rgbMatch = bgColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
            if (rgbMatch) {
                const r = parseInt(rgbMatch[1]);
                const g = parseInt(rgbMatch[2]);
                const b = parseInt(rgbMatch[3]);
                const brightness = r + g + b;
 
                // Twitter/X dark mode: typically rgb(0,0,0) or very dark colors
                // Light mode: typically rgb(255,255,255) or rgb(247,249,249)
                // Threshold: if brightness < 100, it's dark; if > 500, it's light
                if (brightness < 100) {
                    isDark = true;
                } else if (brightness > 500) {
                    isDark = false;
                }
            }
        }
    }
 
    // Method 3: Check body or main container background
    if (isDark === null) {
        const mainContainer = document.querySelector('[data-testid="primaryColumn"], main, [role="main"]');
        const elementToCheck = mainContainer || body;
        const bgColor = window.getComputedStyle(elementToCheck).backgroundColor;
 
        const rgbMatch = bgColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (rgbMatch) {
            const r = parseInt(rgbMatch[1]);
            const g = parseInt(rgbMatch[2]);
            const b = parseInt(rgbMatch[3]);
            const brightness = r + g + b;
 
            if (brightness < 50) {
                isDark = true;
            } else if (brightness > 200) {
                isDark = false;
            }
        }
    }
 
    // Method 4: Check CSS custom properties (Twitter/X might use these)
    if (isDark === null) {
        const rootStyle = window.getComputedStyle(htmlElement);
        // Try to get common CSS variables
        const bgVar = rootStyle.getPropertyValue('--r-bg') || 
                     rootStyle.getPropertyValue('--background-color') ||
                     rootStyle.getPropertyValue('--bg-color');
 
        if (bgVar) {
            const rgbMatch = bgVar.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
            if (rgbMatch) {
                const brightness = parseInt(rgbMatch[1]) + parseInt(rgbMatch[2]) + parseInt(rgbMatch[3]);
                isDark = brightness < 100;
            }
        }
    }
 
    // Method 5: Check for dark mode class names
    if (isDark === null) {
        const hasDarkClass = htmlElement.classList.contains('dark') || 
                            body.classList.contains('dark') ||
                            htmlElement.classList.contains('theme-dark');
        const hasLightClass = htmlElement.classList.contains('light') || 
                             body.classList.contains('light') ||
                             htmlElement.classList.contains('theme-light');
 
        if (hasDarkClass) {
            isDark = true;
        } else if (hasLightClass) {
            isDark = false;
        }
    }
 
    // Method 6: Fallback - check if prefers-color-scheme matches
    if (isDark === null) {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        isDark = prefersDark;
    }
 
    // Default to dark mode if still uncertain (Twitter/X default)
    if (isDark === null) {
        isDark = true;
    }
 
    // Return theme colors matching Twitter/X design system
    if (isDark) {
        return {
            isDark: true,
            background: '#0f1419',
            border: 'rgba(255,255,255,0.1)',
            textPrimary: '#e7e9ea',
            textSecondary: '#71767b',
            cardBg: '#0f1419'
        };
    } else {
        return {
            isDark: false,
            background: '#ffffff',
            border: '#E7E9EC',
            textPrimary: '#0f1419',
            textSecondary: '#536471',
            cardBg: '#ffffff'
        };
    }
}
 
// -----------------------------------------------------
// ✅ Main function: returns a DOM element (not a string)
// -----------------------------------------------------
async function createAdCard() {
    let adData = null;
 
    // Try to fetch from ad_server.py
    try {
        const isServerAvailable = await checkServerHealth();
 
        if (isServerAvailable) {
            const username = await getCurrentUsername();
 
            if (username) {
                console.log(`[AdCard] Fetching ad for user: ${username}`);
                const serverAd = await fetchAd(username);
 
                if (serverAd) {
                    adData = formatServerAd(serverAd);
                    console.log(`[AdCard] Using server ad:`, adData);
                } else {
                    console.warn(`[AdCard] No ad found for ${username}, using fallback`);
                }
            } else {
                console.warn(`[AdCard] Could not determine username, using fallback`);
            }
        } else {
            console.warn(`[AdCard] Ad server not available, using fallback`);
        }
    } catch (err) {
        console.error(`[AdCard] Error fetching ad:`, err);
    }
 
    // Fallback to dummy ad if server fetch failed
    if (!adData) {
        adData = generateDummyAd();
        console.log(`[AdCard] Using dummy ad`);
    }
 
    // -------------------------------------------------
    // ✅ Detect theme and build DOM element
    // -------------------------------------------------
    const theme = detectTheme();
 
    // Try to copy styles from an actual tweet for perfect theme matching
    const sampleTweet = document.querySelector('article[data-testid="tweet"]');
    let tweetStyles = {
        backgroundColor: null,
        borderColor: null,
        textPrimary: null,
        textSecondary: null
    };
 
    if (sampleTweet) {
        const computedStyle = window.getComputedStyle(sampleTweet);
        tweetStyles.backgroundColor = computedStyle.backgroundColor;
        tweetStyles.borderColor = computedStyle.borderColor || computedStyle.borderTopColor;
 
        // Get primary text color from tweet text
        const tweetText = sampleTweet.querySelector('[data-testid="tweetText"], span[dir="ltr"], div[dir="ltr"]');
        if (tweetText) {
            tweetStyles.textPrimary = window.getComputedStyle(tweetText).color;
        } else {
            tweetStyles.textPrimary = computedStyle.color;
        }
 
        // Get secondary text color from username/handle or timestamp
        const secondaryText = sampleTweet.querySelector('span[data-testid="User-Name"], time, [data-testid="User-Names"] span:last-child');
        if (secondaryText) {
            tweetStyles.textSecondary = window.getComputedStyle(secondaryText).color;
        }
    }
 
    const card = document.createElement("article");
 
    card.className = "custom-ad-card";
 
    // Always use theme border color (light gray for light theme, white for dark theme)
    card.style.border = `1px solid ${theme.border}`;
    card.style.borderRadius = "16px";
    card.style.padding = "12px";
    card.style.background = tweetStyles.backgroundColor || theme.cardBg;
    card.style.margin = "12px 0";
    card.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
 
    // Debug logging (can be removed in production)
    console.log('[AdCard] Theme detection:', {
        isDark: theme.isDark,
        tweetBg: tweetStyles.backgroundColor,
        tweetTextColor: tweetStyles.textPrimary,
        tweetSecondaryColor: tweetStyles.textSecondary,
        cardBg: card.style.background,
        dataTheme: document.documentElement.getAttribute('data-theme'),
        borderColor: theme.border
    });
 
    // Build the ad card HTML
    const imageHtml = adData.image 
        ? `<div style="margin-top:10px;">
            <img src="${adData.image}" 
                 style="width:100%;border-radius:12px;object-fit:contain;display:block;" 
                 onerror="this.style.display='none'" />
        </div>`
        : '';
 
    // Use tweet colors if available, otherwise fall back to theme colors
    const textPrimary = tweetStyles.textPrimary || theme.textPrimary;
    const textSecondary = tweetStyles.textSecondary || theme.textSecondary;
 
    const fullContentHtml = adData.full_content && adData.full_content !== adData.title
        ? `<div style="margin-top:10px;color:${textPrimary};white-space:pre-wrap;line-height:1.5;">
            ${adData.full_content.replace(/\n/g, '<br>')}
        </div>`
        : '';
 
    card.innerHTML = `
        <div>
            <div style="font-weight:700;color:${textPrimary};">
                ${adData.brand} · Sponsored
            </div>
 
            ${adData.description ? `<div style="color:${textSecondary};font-size:13px;margin-top:4px;">
                ${adData.description}
            </div>` : ''}
        </div>
 
        <div style="margin-top:10px;color:${textPrimary};font-weight:600;font-size:15px;">
            ${adData.title}
        </div>
 
        ${fullContentHtml}
        ${imageHtml}
    `;
 
    return card;
}
 
 
 
// -----------------------------------------------------
// ✅ Export as ES module and also expose globally
// -----------------------------------------------------
export { createAdCard };
window.createAdCard = createAdCard;