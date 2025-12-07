/ // adCard.js


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


   // Build the ad card HTML with beautified X-style design
   const imageHtml = adData.image
       ? `<div style="margin-top:12px; padding:12px; border-radius:16px; overflow:hidden; border:1px solid ${theme.border}; display:flex; align-items:center; justify-content:center; background:${theme.isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)'};">
           <img src="${adData.image}"
                alt="Ad creative"
                style="width:100%; display:block; object-fit:cover; max-height:400px; border-radius:8px;"
                onerror="this.parentElement.style.display='none'" />
       </div>`
       : '';


   // Use tweet colors if available, otherwise fall back to theme colors
   const textPrimary = tweetStyles.textPrimary || theme.textPrimary;
   const textSecondary = tweetStyles.textSecondary || theme.textSecondary;


   const fullContentHtml = adData.full_content && adData.full_content !== adData.title
       ? `<div style="margin-top:12px; color:${textPrimary}; font-size:15px; line-height:20px; white-space:pre-wrap;">
           ${adData.full_content.replace(/\n/g, '<br>')}
       </div>`
       : '';


   card.innerHTML = `
       <div style="display:flex; gap:12px;">
           <!-- Avatar -->
           <div style="flex-shrink:0;">
               <img src="${adData.avatar}"
                    alt="${adData.brand}"
                    style="width:40px; height:40px; border-radius:50%; object-fit:cover;"
                    onerror="this.src='https://abs.twimg.com/icons/apple-touch-icon-192x192.png'" />
           </div>
          
           <!-- Content -->
           <div style="flex:1; min-width:0; padding-right:30px;">
               <!-- Header: Brand name + Ad badge + Bulb icon -->
               <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:2px;">
                   <div style="display:flex; align-items:center; gap:4px; min-width:0;">
                       <span style="font-weight:700; font-size:15px; color:${textPrimary}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                           ${adData.brand}
                       </span>
                       <!-- Verified badge -->
                       <svg viewBox="0 0 22 22" aria-label="Verified" style="width:18px; height:18px; fill:#1d9bf0; flex-shrink:0;">
                           <g><path d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.854-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.688-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.634.433 1.218.877 1.688.47.443 1.054.747 1.687.878.633.132 1.29.084 1.897-.136.274.586.705 1.084 1.246 1.439.54.354 1.17.551 1.816.569.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.239 1.266.296 1.903.164.636-.132 1.22-.447 1.68-.907.46-.46.776-1.044.908-1.681s.075-1.299-.165-1.903c.586-.274 1.084-.705 1.439-1.246.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z"></path></g>
                       </svg>
                   </div>
                   <div style="display:flex; align-items:center; gap:6px; margin-right:-4px;">
                       <span style="font-size:13px; color:${textSecondary}; font-weight:400;">Ad</span>
                   </div>
               </div>
              
               <!-- Description (if exists) -->
               ${adData.description ? `
               <div style="font-size:13px; color:${textSecondary}; margin-bottom:4px; line-height:16px;">
                   ${adData.description}
               </div>
               ` : ''}
              
               <!-- Main ad title -->
               <div style="font-size:15px; color:${textPrimary}; font-weight:400; line-height:20px; margin-top:4px;">
                   ${adData.title}
               </div>
              
               <!-- Full content -->
               ${fullContentHtml}
              
               <!-- Image -->
               ${imageHtml}
              
               <!-- Engagement bar -->
               <div style="display:flex; align-items:center; justify-content:space-between; margin-top:12px; max-width:${adData.image ? '100%' : '425px'};">
                   <div style="display:flex; align-items:center; gap:16px;">
                       <!-- Reply -->
                       <button style="background:none; border:none; cursor:pointer; display:flex; align-items:center; gap:4px; padding:0; color:${textSecondary}; transition:color 0.2s;"
                               onmouseover="this.style.color='#1d9bf0'"
                               onmouseout="this.style.color='${textSecondary}'">
                           <svg viewBox="0 0 24 24" style="width:18px; height:18px; fill:currentColor;">
                               <g><path d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.96-1.607 5.68-4.196 7.11l-8.054 4.46v-3.69h-.067c-4.49.1-8.183-3.51-8.183-8.01zm8.005-6c-3.317 0-6.005 2.69-6.005 6 0 3.37 2.77 6.08 6.138 6.01l.351-.01h1.761v2.3l5.087-2.81c1.951-1.08 3.163-3.13 3.163-5.36 0-3.39-2.744-6.13-6.129-6.13H9.756z"></path></g>
                           </svg>
                       </button>
                      
                       <!-- Repost -->
                       <button style="background:none; border:none; cursor:pointer; display:flex; align-items:center; gap:4px; padding:0; color:${textSecondary}; transition:color 0.2s;"
                               onmouseover="this.style.color='#00ba7c'"
                               onmouseout="this.style.color='${textSecondary}'">
                           <svg viewBox="0 0 24 24" style="width:18px; height:18px; fill:currentColor;">
                               <g><path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"></path></g>
                           </svg>
                       </button>
                      
                       <!-- Like -->
                       <button style="background:none; border:none; cursor:pointer; display:flex; align-items:center; gap:4px; padding:0; color:${textSecondary}; transition:color 0.2s;"
                               onmouseover="this.style.color='#f91880'"
                               onmouseout="this.style.color='${textSecondary}'">
                           <svg viewBox="0 0 24 24" style="width:18px; height:18px; fill:currentColor;">
                               <g><path d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.561-1.13-1.666-1.84-2.908-1.91zm4.187 7.69c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.56 4.798 2.01 1.429-1.45 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.601 3.01.896 1.81.846 4.17-.514 6.67z"></path></g>
                           </svg>
                       </button>
                   </div>
                  
                   <!-- Bookmark (aligned to right) -->
                   <button style="background:none; border:none; cursor:pointer; display:flex; align-items:center; gap:4px; padding:0; color:${textSecondary}; transition:color 0.2s;"
                           onmouseover="this.style.color='#1d9bf0'"
                           onmouseout="this.style.color='${textSecondary}'">
                       <svg viewBox="0 0 24 24" style="width:18px; height:18px; fill:currentColor;">
                           <g><path d="M4 4.5C4 3.12 5.119 2 6.5 2h11C18.881 2 20 3.12 20 4.5v18.44l-8-5.71-8 5.71V4.5zM6.5 4c-.276 0-.5.22-.5.5v14.56l6-4.29 6 4.29V4.5c0-.28-.224-.5-.5-.5h-11z"></path></g>
                       </svg>
                   </button>
               </div>
           </div>
       </div>
   `;


   return card;
}






// -----------------------------------------------------
// ✅ Export as ES module and also expose globally
// -----------------------------------------------------
export { createAdCard };
window.createAdCard = createAdCard;