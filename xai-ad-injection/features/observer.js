// observer.js

import { telemetry } from "./telemetry.js";
import { getAttentionScore } from "../model.js";
import { shouldInject } from "../decision.js";
import { createAd, injectAdAfter } from "../inject.js";

// Feature buffer for batching
const featureBuffer = [];
let apiCallCount = 0;
let lastApiCallTime = 0;

// Temporary deterministic insertion: show an ad every N tweets viewed
const TWEETS_PER_AD = 15;

/**
 * Aggregate features from multiple tweets
 * @param {Array} buffer - Array of feature objects
 * @returns {Object} Aggregated features
 */
function aggregateFeatures(buffer) {
    if (buffer.length === 0) return null;

    const velocities = buffer.map(f => f.velocity);
    const accelerations = buffer.map(f => f.acceleration);
    const pauses = buffer.map(f => f.pauseDuration);

    return {
        velocity: velocities.reduce((a, b) => a + b, 0) / velocities.length,
        acceleration: accelerations.reduce((a, b) => a + b, 0) / accelerations.length,
        pauseDuration: Math.max(...pauses), // Use max pause (most significant)
        reverseScroll: buffer[buffer.length - 1].reverseScroll, // Latest value
        bounce: buffer.some(f => f.bounce), // True if any bounce detected
        tweets_since_last_ad: buffer[buffer.length - 1].tweets_since_last_ad,
        time_since_last_ad: buffer[buffer.length - 1].time_since_last_ad
    };
}

export function createTweetObserver(state, persistentAds) {
    return new IntersectionObserver(async (entries) => {
        for (const entry of entries) {
            if (!entry.isIntersecting) continue;

            const tweet = entry.target;

            const scrollingDown = window.scrollY > state.lastScroll;
            state.lastScroll = window.scrollY;

            if (!scrollingDown) continue;

            if (!tweet.dataset.viewed) {
                tweet.dataset.viewed = "true";
                state.tweetsSeen++;
            }

            // Deterministic ad insertion every TWEETS_PER_AD tweets
            const tweetsSinceLastAd = state.tweetsSeen - state.lastAdTweet;
            if (tweetsSinceLastAd >= TWEETS_PER_AD) {
                const ad = await createAd(`Periodic placement: every ${TWEETS_PER_AD} tweets`);
                injectAdAfter(tweet, ad);

                persistentAds.push({
                    element: ad,
                    insertIndex: state.tweetsSeen - 1
                });

                state.adsInserted++;
                state.lastAdTime = performance.now();
                state.lastAdPosition = window.scrollY;
                state.lastAdTweet = state.tweetsSeen;
                featureBuffer.length = 0; // reset attention buffer after forced insertion

                console.log("[Ad Injected - Interval]", {
                    adNumber: state.adsInserted,
                    afterTweet: state.tweetsSeen,
                    reason: `Every ${TWEETS_PER_AD} tweets`
                });

                continue; // Skip attention-based logic for this tweet
            }

            // Collect current features
            const currentFeatures = {
                ...telemetry,
                tweets_since_last_ad: state.tweetsSeen - state.lastAdTweet,
                time_since_last_ad: performance.now() - state.lastAdTime
            };

            // Add to buffer
            featureBuffer.push(currentFeatures);

            // Determine if we should call API (now processes every tweet, or on pause)
            const shouldCallApi =
                featureBuffer.length >= 1 || // Process every tweet
                currentFeatures.pauseDuration > 1000; // High attention moment (1s pause)

            if (!shouldCallApi) {
                console.log(`[Batching] Buffered tweet ${state.tweetsSeen} (${featureBuffer.length}/1), pause: ${currentFeatures.pauseDuration.toFixed(0)}ms`);
                continue;
            }

            // Aggregate features from buffer
            const aggregatedFeatures = aggregateFeatures(featureBuffer);

            console.log(`[Batching] Calling API with ${featureBuffer.length} tweets buffered`, {
                reason: featureBuffer.length >= 3 ? "Batch full" : "High attention detected",
                avgVelocity: aggregatedFeatures.velocity.toFixed(2),
                maxPause: `${aggregatedFeatures.pauseDuration.toFixed(0)}ms`
            });

            // Clear buffer
            featureBuffer.length = 0;

            // Call Grok API
            apiCallCount++;
            lastApiCallTime = performance.now();

            const { attention_score, reason } = await getAttentionScore(aggregatedFeatures);

            console.log(`[API Stats] Total calls: ${apiCallCount}, Last call: ${((performance.now() - lastApiCallTime) / 1000).toFixed(1)}s ago`);

            // Check if this was triggered by pause
            const pauseTriggered = currentFeatures.pauseDuration > 1000;

            const should = shouldInject({
                attentionScore: attention_score,
                scrollingDown,
                timeSinceLastAd: performance.now() - state.lastAdTime,
                distanceSinceLastAd: window.scrollY - state.lastAdPosition,
                pauseTriggered: pauseTriggered  // Pass flag for relaxed thresholds
            });

            if (should) {
                const ad = await createAd(reason);
                injectAdAfter(tweet, ad);

                persistentAds.push({
                    element: ad,
                    insertIndex: state.tweetsSeen - 1
                });

                state.adsInserted++;
                state.lastAdTime = performance.now();
                state.lastAdPosition = window.scrollY;
                state.lastAdTweet = state.tweetsSeen;

                console.log("[Ad Injected]", {
                    adNumber: state.adsInserted,
                    afterTweet: state.tweetsSeen,
                    reason: reason,
                    scrollPosition: `${window.scrollY.toFixed(0)}px`,
                    apiCallsTotal: apiCallCount
                });
            }
        }
    }, {
        threshold: 0.6
    });
}
