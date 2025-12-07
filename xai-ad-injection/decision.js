// decision.js

export function shouldInject({
    attentionScore,
    scrollingDown,
    timeSinceLastAd,
    distanceSinceLastAd,
    scoreThreshold = 0.50,    // 50% attention (moderate engagement)
    minSpacing = 600,         // 600px (~2-3 tweets)
    minTime = 3000            // 3 seconds between ads
}) {
    const checks = {
        scrollingDown: scrollingDown,
        attentionScore: attentionScore >= scoreThreshold,
        spacing: distanceSinceLastAd >= minSpacing,
        timing: timeSinceLastAd >= minTime
    };

    const shouldInject = Object.values(checks).every(v => v);

    console.log("[Decision] Should inject ad?", {
        result: shouldInject ? "YES" : "NO",
        checks: {
            scrollingDown: checks.scrollingDown ? "" : "",
            attentionScore: `${checks.attentionScore ? "" : ""} (${attentionScore.toFixed(3)} >= ${scoreThreshold})`,
            spacing: `${checks.spacing ? "" : ""} (${distanceSinceLastAd.toFixed(0)}px >= ${minSpacing}px)`,
            timing: `${checks.timing ? "" : ""} (${timeSinceLastAd.toFixed(0)}ms >= ${minTime}ms)`
        }
    });

    return shouldInject;
}
