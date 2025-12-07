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

// -----------------------------------------------------
// 🔥 Utility: generate random dummy ads for testing
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



// -----------------------------------------------------
// ✅ Main function: returns a DOM element (not a string)
// -----------------------------------------------------
async function createAdCard() {
    // -------------------------------------------------
    // FUTURE: fetch dynamic API ad
    // -------------------------------------------------
    // Example (disabled for now):
    //
    // const response = await fetch("https://your-api.com/ad");
    // const adData = await response.json();
    //
    // -------------------------------------------------

    // For now: random dummy ad
    const adData = generateDummyAd();

    // -------------------------------------------------
    // ✅ Build DOM element
    // -------------------------------------------------
    const card = document.createElement("article");

    card.className =
        "custom-ad-card";

    card.style.border = "1px solid rgba(255,255,255,0.1)";
    card.style.borderRadius = "16px";
    card.style.padding = "12px";
    card.style.background = "#0f1419";
    card.style.margin = "12px 0";

    card.innerHTML = `
        <div style="display:flex; gap:12px;">
            <img 
                src="${adData.avatar}" 
                style="width:40px;height:40px;border-radius:50%;" 
            />

            <div style="flex:1;">
                <div style="font-weight:700;color:#e7e9ea;">
                    ${adData.brand} · Sponsored
                </div>

                <div style="color:#71767b;font-size:13px;">
                    ${adData.description}
                </div>
            </div>
        </div>

        <div style="margin-top:10px;color:#e7e9ea;font-weight:600;">
            ${adData.title}
        </div>

        <div style="margin-top:10px;">
            <img src="${adData.image}" 
                 style="width:100%;border-radius:12px;" />
        </div>
    `;

    return card;
}



// -----------------------------------------------------
// ✅ Expose globally so content.js can call it
// -----------------------------------------------------
window.createAdCard = createAdCard;
