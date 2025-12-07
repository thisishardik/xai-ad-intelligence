(function () {

    // ----------------------------------------------------------
    // ✅ Dynamic Ad Builder (returns DOM element, not string)
    // ----------------------------------------------------------
    function buildSponsoredAd(data) {
        // Outer card
        const card = document.createElement("div");
        card.className = "css-175oi2r r-1igl3o0 r-qklmqi r-1adg3ll r-1ny4l3l";
        card.style.padding = "12px 16px";
        card.style.background = "#16181c";
        card.style.borderRadius = "16px";
        card.style.margin = "12px 0";

        // Sponsored Label
        const labelRow = document.createElement("div");
        labelRow.style.display = "flex";
        labelRow.style.alignItems = "center";
        labelRow.style.gap = "8px";
        labelRow.style.marginBottom = "6px";

        const label = document.createElement("span");
        label.textContent = "Sponsored";
        label.style.color = "#8b98a5";
        label.style.fontSize = "13px";
        label.style.fontWeight = "600";

        labelRow.appendChild(label);
        card.appendChild(labelRow);

        // Header Row (avatar + title + follow button)
        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.alignItems = "center";
        header.style.gap = "12px";
        header.style.marginBottom = "10px";

        // Avatar
        const avatar = document.createElement("div");
        avatar.style.width = "40px";
        avatar.style.height = "40px";
        avatar.style.borderRadius = "50%";
        avatar.style.background = "#333";
        avatar.style.backgroundImage = `url(${data.avatar})`;
        avatar.style.backgroundSize = "cover";

        // Title + handle
        const titleBox = document.createElement("div");
        titleBox.style.flex = "1";

        const title = document.createElement("div");
        title.textContent = data.title;
        title.style.fontSize = "15px";
        title.style.color = "#e7e9ea";
        title.style.fontWeight = "600";

        const handle = document.createElement("div");
        handle.textContent = data.handle;
        handle.style.fontSize = "13px";
        handle.style.color = "#8b98a5";

        titleBox.appendChild(title);
        titleBox.appendChild(handle);

        // Follow button
        const followBtn = document.createElement("button");
        followBtn.textContent = "Follow";
        followBtn.style.background = "#fff";
        followBtn.style.color = "#000";
        followBtn.style.padding = "6px 12px";
        followBtn.style.border = "none";
        followBtn.style.borderRadius = "20px";
        followBtn.style.fontWeight = "600";
        followBtn.style.fontSize = "14px";

        header.appendChild(avatar);
        header.appendChild(titleBox);
        header.appendChild(followBtn);

        card.appendChild(header);

        // Ad text
        const adText = document.createElement("div");
        adText.textContent = data.text;
        adText.style.fontSize = "15px";
        adText.style.color = "#e7e9ea";
        adText.style.lineHeight = "1.4";
        adText.style.marginBottom = "10px";

        card.appendChild(adText);

        // Optional Image
        if (data.image) {
            const img = document.createElement("div");
            img.style.width = "100%";
            img.style.height = "220px";
            img.style.borderRadius = "12px";
            img.style.background = "#222";
            img.style.backgroundImage = `url(${data.image})`;
            img.style.backgroundSize = "cover";
            img.style.backgroundPosition = "center";
            img.style.marginBottom = "10px";

            card.appendChild(img);
        }

        // CTA Button
        const cta = document.createElement("button");
        cta.textContent = data.cta;
        cta.style.width = "100%";
        cta.style.padding = "10px";
        cta.style.background = "#1d9bf0";
        cta.style.color = "white";
        cta.style.border = "none";
        cta.style.borderRadius = "8px";
        cta.style.fontSize = "15px";
        cta.style.fontWeight = "600";

        card.appendChild(cta);

        return card;
    }

    // ----------------------------------------------------------
    // ✅ Static Ad Data (replace later with dynamic API data)
    // ----------------------------------------------------------
    const AD_DATA = {
        avatar: "https://pbs.twimg.com/profile_images/1498070100393754625/C2V-fbll_normal.jpg",
        title: "AdBrand",
        handle: "@adbrand",
        text: "🚀 Upgrade your experience with AdBrand — tools built for creators.",
        image: "https://pbs.twimg.com/media/G7iXzxiaYAAZvCG?format=jpg&name=large",
        cta: "Learn More"
    };

    // Track indices where ads are already inserted
    const inserted = new Set();

    // Insert ad after tweet[index]
    function insertAdAfter(index) {
        const tweets = document.querySelectorAll("article");

        if (index >= tweets.length) return;
        if (inserted.has(index)) return;

        const adElement = buildSponsoredAd(AD_DATA);
        tweets[index].after(adElement);

        inserted.add(index);
        console.log("Inserted ad after tweet:", index + 1);
    }

    // Insert after every 5th tweet → indices: 4,9,14,...
    function processTweets() {
        const tweets = document.querySelectorAll("article");

        for (let i = 4; i < tweets.length; i += 5) {
            insertAdAfter(i);
        }
    }

    // ----------------------------------------------------------
    // ✅ MutationObserver → best for infinite feed on X
    // ----------------------------------------------------------
    const observer = new MutationObserver(() => {
        processTweets();
    });

    function start() {
        const feed = document.querySelector("div[data-testid='primaryColumn']");

        if (!feed) {
            setTimeout(start, 500);
            return;
        }

        observer.observe(feed, {
            childList: true,
            subtree: true
        });

        processTweets();
    }

    start();
})();
