// // // (function () {
// // //     let lastScroll = window.scrollY;

// // //     let tweetsSeen = 0;        // number of tweets you actually viewed
// // //     let adsInserted = 0;       // number of ads already inserted

// // //     const observer = new IntersectionObserver((entries) => {
// // //         entries.forEach(entry => {
// // //             if (!entry.isIntersecting) return;

// // //             const tweet = entry.target;

// // //             // Count only once
// // //             if (!tweet.dataset.viewed) {
// // //                 tweet.dataset.viewed = "true";
// // //                 tweetsSeen++;
// // //             }

// // //             // Only insert when scrolling down
// // //             const isScrollingDown = window.scrollY > lastScroll;
// // //             lastScroll = window.scrollY;

// // //             if (!isScrollingDown) return;

// // //             // next threshold = (adsInserted + 1) * 5
// // //             const nextThreshold = (adsInserted + 1) * 5;

// // //             if (tweetsSeen >= nextThreshold) {
// // //                 insertAdAfterTweet(tweet);
// // //                 adsInserted++;
// // //             }
// // //         });
// // //     }, {
// // //         threshold: 0.6  // tweet is considered "seen" when 60% visible
// // //     });

// // //     // Observe tweets dynamically as they appear
// // //     const mutationObserver = new MutationObserver(() => {
// // //         document.querySelectorAll("article[data-testid='tweet']")
// // //             .forEach(tweet => observer.observe(tweet));
// // //     });

// // //     mutationObserver.observe(document.body, {
// // //         childList: true,
// // //         subtree: true
// // //     });


// // //     function insertAdAfterTweet(tweetElement) {
// // //         const ad = createAdCard();
// // //         tweetElement.after(ad);
// // //     }
// // // })();


// // (function () {
// //     let lastScroll = window.scrollY;

// //     let tweetsSeen = 0;       // number of tweets actually viewed
// //     let adsInserted = 0;      // number of ads already inserted

// //     const persistentAds = []; // store ads forever

// //     // -------------------------------------------------------------
// //     // 1. IntersectionObserver → count tweets when they become visible
// //     // -------------------------------------------------------------
// //     const io = new IntersectionObserver(async (entries) => {
// //         for (const entry of entries) {
// //             if (!entry.isIntersecting) continue;

// //             const tweet = entry.target;

// //             // Count only once per tweet
// //             if (!tweet.dataset.viewed) {
// //                 tweet.dataset.viewed = "true";
// //                 tweetsSeen++;
// //             }

// //             // detect scroll direction
// //             const scrollingDown = window.scrollY > lastScroll;
// //             lastScroll = window.scrollY;

// //             if (!scrollingDown) continue;

// //             const nextThreshold = (adsInserted + 1) * 5;

// //             // ✅ time to insert a new ad
// //             if (tweetsSeen >= nextThreshold) {
// //                 const ad = await createAdCard(); // async dynamic card

// //                 tweet.after(ad);

// //                 persistentAds.push({
// //                     threshold: nextThreshold,
// //                     element: ad
// //                 });

// //                 adsInserted++;
// //             }
// //         }
// //     }, {
// //         threshold: 0.6 // tweet considered viewed when 60% visible
// //     });


// //     // -------------------------------------------------------------
// //     // 2. MutationObserver → observe tweets + restore ads if needed
// //     // -------------------------------------------------------------
// //     const mutation = new MutationObserver(() => {
// //         const tweets = document.querySelectorAll("article[data-testid='tweet']");

// //         tweets.forEach(t => io.observe(t));

// //         // ✅ restore persistent ads only if they disappeared
// //         persistentAds.forEach(adObj => {
// //             const idx = adObj.threshold - 1;

// //             if (!tweets[idx]) return;

// //             // if ad node disappeared due to virtualization → reinsert
// //             if (!document.body.contains(adObj.element)) {
// //                 tweets[idx].after(adObj.element);
// //             }
// //         });
// //     });

// //     mutation.observe(document.body, {
// //         childList: true,
// //         subtree: true
// //     });
// // })();

// (function () {
//     let lastScroll = window.scrollY;

//     let tweetsSeen = 0;          // how many tweets viewed while scrolling down
//     let adsInserted = 0;         // how many ads already added

//     const persistentAds = [];    // persistent storage of ads

//     // -------------------------------------------------------------
//     // 1. Count tweets ONLY when scrolling down + insert ads
//     // -------------------------------------------------------------
//     const io = new IntersectionObserver(async (entries) => {
//         for (const entry of entries) {
//             if (!entry.isIntersecting) continue;

//             const tweet = entry.target;

//             // -------------------------------------------------
//             // ✅ Determine scroll direction FIRST
//             // -------------------------------------------------
//             const scrollingDown = window.scrollY > lastScroll;
//             lastScroll = window.scrollY;

//             // ✅ If scrolling UP → DO NOT count → DO NOT insert
//             if (!scrollingDown) {
//                 continue;
//             }

//             // -------------------------------------------------
//             // ✅ Count tweet only when scrolling DOWN
//             // -------------------------------------------------
//             if (!tweet.dataset.viewed) {
//                 tweet.dataset.viewed = "true";
//                 tweetsSeen++;
//             }

//             // -------------------------------------------------
//             // ✅ Check whether we reached next threshold
//             // -------------------------------------------------
//             const nextThreshold = (adsInserted + 1) * 5;

//             if (tweetsSeen >= nextThreshold) {
//                 const ad = await createAdCard();

//                 tweet.after(ad);

//                 persistentAds.push({
//                     threshold: nextThreshold,
//                     element: ad
//                 });

//                 adsInserted++;
//             }
//         }
//     }, {
//         threshold: 0.6
//     });


//     // -------------------------------------------------------------
//     // 2. Watch DOM → restore persistent ads (only if missing)
//     // -------------------------------------------------------------
//     const mutation = new MutationObserver(() => {
//         const tweets = document.querySelectorAll("article[data-testid='tweet']");

//         // observe tweets for counting
//         tweets.forEach(t => io.observe(t));

//         // restore ads only when they disappeared (virtualization)
//         persistentAds.forEach(adObj => {
//             const idx = adObj.threshold - 1;

//             if (!tweets[idx]) return;

//             if (!document.body.contains(adObj.element)) {
//                 tweets[idx].after(adObj.element);
//             }
//         });
//     });

//     mutation.observe(document.body, {
//         childList: true,
//         subtree: true
//     });
// })();


import { initTelemetry } from "./features/telemetry.js";
import { createTweetObserver } from "./features/observer.js";
import { restoreAds } from "./features/restore.js";

// ------------------------------------------------------------
// GLOBAL STATE
// ------------------------------------------------------------
const state = {
    lastScroll: window.scrollY,
    tweetsSeen: 0,
    adsInserted: 0,
    lastAdTime: performance.now(),
    lastAdPosition: 0,
    lastAdTweet: 0
};

const persistentAds = [];

// ------------------------------------------------------------
// INIT SCROLL TELEMETRY
// ------------------------------------------------------------
initTelemetry();

// ------------------------------------------------------------
// CREATE OBSERVER
// ------------------------------------------------------------
const io = createTweetObserver(state, persistentAds);

// ------------------------------------------------------------
// DOM Mutation Observer -> restore ads
// ------------------------------------------------------------
const mutation = new MutationObserver(() => {
    const tweets = document.querySelectorAll("article[data-testid='tweet']");
    tweets.forEach(t => io.observe(t));
    restoreAds(persistentAds, tweets);
});

mutation.observe(document.body, {
    childList: true,
    subtree: true
});
