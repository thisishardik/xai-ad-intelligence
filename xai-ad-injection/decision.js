// decision.js

export function shouldInject({
    attentionScore,
    scrollingDown,
    timeSinceLastAd,
    distanceSinceLastAd,
    pauseTriggered = false,  // NEW: flag for pause-triggered calls
    scoreThreshold = 0.60,    // 60% attention (filters out fast scrolling)
    minSpacing = 300,         // 300px (~1-2 tweets, allows ads every 4-5 tweets)
    minTime = 2000            // 2 seconds between ads (faster rotation)
}) {
    // Relax constraints for pause-triggered insertions (lower thresholds = easier to pass)
    const effectiveScoreThreshold = pauseTriggered ? 0.45 : scoreThreshold;  // 45% vs 60%
    const effectiveMinTime = pauseTriggered ? 1500 : minTime;                // 1.5s vs 2s
    const effectiveMinSpacing = pauseTriggered ? 200 : minSpacing;           // 200px vs 300px

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
