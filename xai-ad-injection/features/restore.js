// restore.js

export function restoreAds(persistentAds, tweets) {
    persistentAds.forEach(adObj => {
        const targetTweet = tweets[adObj.insertIndex];

        if (!targetTweet) return;

        if (!document.body.contains(adObj.element)) {
            targetTweet.after(adObj.element);
        }
    });
}
