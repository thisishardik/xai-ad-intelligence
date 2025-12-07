// observer.js

import { telemetry } from "./telemetry.js";
import { getAttentionScore } from "../model.js";
import { shouldInject } from "../decision.js";
import { createAd, injectAdAfter } from "../inject.js";

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

            const features = {
                ...telemetry,
                tweets_since_last_ad: state.tweetsSeen - (state.adsInserted * 5),
                time_since_last_ad: performance.now() - state.lastAdTime
            };

            const { attention_score, reason } = await getAttentionScore(features);

            const should = shouldInject({
                attentionScore: attention_score,
                scrollingDown,
                timeSinceLastAd: performance.now() - state.lastAdTime,
                distanceSinceLastAd: window.scrollY - state.lastAdPosition
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

                console.log("[Ad Injected]", {
                    adNumber: state.adsInserted,
                    afterTweet: state.tweetsSeen,
                    reason: reason,
                    scrollPosition: `${window.scrollY.toFixed(0)}px`
                });
            }
        }
    }, {
        threshold: 0.6
    });
}
