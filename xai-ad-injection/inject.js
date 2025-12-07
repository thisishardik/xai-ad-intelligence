// inject.js

/**
 * Create an ad card with attention-based timing reason
 * @param {string} reason - Reason for ad insertion (from attention model)
 * @returns {Promise<HTMLElement>} Ad card element
 */
export async function createAd(reason = "Intelligent ad timing") {
    // Fetch ad card from server (or fallback)
    // Note: createAdCard is exposed globally via window.createAdCard in adCard.js
    const adCard = await window.createAdCard();

    // Wrap it in a container with attention tooltip
    const container = document.createElement("div");
    container.className = "xai-ad-card";
    container.style.position = "relative";
    container.style.margin = "20px 0";

    // Add attention tooltip to the ad card
    const tooltipWrapper = document.createElement("div");
    tooltipWrapper.className = "attention-tooltip";
    tooltipWrapper.style.cssText = `
        position: absolute;
        top: 16px;
        right: 12px;
        z-index: 10;
        cursor: help;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    `;

    tooltipWrapper.innerHTML = `
        <span style="font-size: 22px; color: #1d9bf0;">💡</span>
        <div class="tooltip-text" style="
            visibility: hidden;
            opacity: 0;
            width: 250px;
            background-color: #1d9bf0;
            color: #fff;
            text-align: center;
            border-radius: 8px;
            padding: 8px;
            position: absolute;
            z-index: 1000;
            top: 100%;
            right: 0;
            margin-top: 8px;
            font-size: 12px;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            transition: opacity 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        ">
            <strong>Why now?</strong><br>${reason}
        </div>
    `;

    // Add hover effect for tooltip
    const tooltipText = tooltipWrapper.querySelector('.tooltip-text');
    tooltipWrapper.addEventListener('mouseenter', () => {
        tooltipText.style.visibility = 'visible';
        tooltipText.style.opacity = '1';
    });
    tooltipWrapper.addEventListener('mouseleave', () => {
        tooltipText.style.visibility = 'hidden';
        tooltipText.style.opacity = '0';
    });

    // Append ad card and tooltip
    container.appendChild(adCard);
    container.appendChild(tooltipWrapper);

    return container;
}

export function injectAdAfter(tweet, adEl) {
    tweet.after(adEl);
}
