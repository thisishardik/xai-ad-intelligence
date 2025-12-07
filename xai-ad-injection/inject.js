// inject.js

export async function createAd(reason = "Intelligent ad timing") {
    const container = document.createElement("div");
    container.className = "xai-ad-card";
    container.style.padding = "20px";
    container.style.margin = "20px 0";
    container.style.background = "#111";
    container.style.borderRadius = "12px";
    container.style.position = "relative";

    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <h2 style="margin: 0; color: #e7e9ea;">Sponsored • XAI</h2>
            <div class="attention-tooltip" style="position: relative; display: inline-block; cursor: help;">
                <span style="font-size: 18px; color: #1d9bf0;">💡</span>
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
                    transition: opacity 0.3s;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                ">
                    <strong>Why now?</strong><br>${reason}
                </div>
            </div>
        </div>
        <p style="color: #71767b; margin-top: 8px;">This is an intelligent ad powered by residual attention.</p>
    `;

    // Add hover effect for tooltip
    const tooltip = container.querySelector('.attention-tooltip');
    const tooltipText = container.querySelector('.tooltip-text');

    tooltip.addEventListener('mouseenter', () => {
        tooltipText.style.visibility = 'visible';
        tooltipText.style.opacity = '1';
    });

    tooltip.addEventListener('mouseleave', () => {
        tooltipText.style.visibility = 'hidden';
        tooltipText.style.opacity = '0';
    });

    return container;
}

export function injectAdAfter(tweet, adEl) {
    tweet.after(adEl);
}
