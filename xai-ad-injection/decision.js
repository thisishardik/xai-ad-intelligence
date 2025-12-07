// decision.js

export function shouldInject({
    attentionScore,
    scrollingDown,
    timeSinceLastAd,
    distanceSinceLastAd,
    pauseTriggered = false,  // NEW: flag for pause-triggered calls
    scoreThreshold = 0.55,    // 50% attention (moderate engagement)
    minSpacing = 700,         // 600px (~2-3 tweets)
    minTime = 3000            // 3 seconds between ads
}) {
    // Relax constraints for pause-triggered insertions
    const effectiveScoreThreshold = pauseTriggered ? 0.55 : scoreThreshold;
    const effectiveMinTime = pauseTriggered ? 3000 : minTime;
    const effectiveMinSpacing = pauseTriggered ? 700 : minSpacing;

    const checks = {
        scrollingDown: scrollingDown,
        attentionScore: attentionScore >= effectiveScoreThreshold,
        spacing: distanceSinceLastAd >= effectiveMinSpacing,
        timing: timeSinceLastAd >= effectiveMinTime
    };

    const shouldInject = Object.values(checks).every(v => v);

    console.log("[Decision] Should inject ad?", {
        result: shouldInject ? "YES ✓" : "NO ✗",
        pauseTriggered: pauseTriggered ? "YES (relaxed thresholds)" : "NO",
        checks: {
            scrollingDown: `${checks.scrollingDown ? "✓" : "✗"}`,
            attentionScore: `${checks.attentionScore ? "✓" : "✗"} (${attentionScore.toFixed(3)} >= ${effectiveScoreThreshold})`,
            spacing: `${checks.spacing ? "✓" : "✗"} (${distanceSinceLastAd.toFixed(0)}px >= ${effectiveMinSpacing}px)`,
            timing: `${checks.timing ? "✓" : "✗"} (${timeSinceLastAd.toFixed(0)}ms >= ${effectiveMinTime}ms)`
        }
    });

    return shouldInject;
}
