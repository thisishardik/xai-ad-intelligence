export const telemetry = {
    velocity: 0,
    acceleration: 0,
    pauseDuration: 0,
    reverseScroll: false,
    bounce: false
};

let lastY = window.scrollY;
let lastTime = performance.now();
let lastVelocity = 0;
let pauseStart = null;
let scrollTimeout = null;

export function initTelemetry() {
    window.addEventListener("scroll", () => {
        const now = performance.now();
        const dy = window.scrollY - lastY;
        const dt = now - lastTime;

        const velocity = dy / dt;

        telemetry.acceleration = velocity - lastVelocity;
        telemetry.velocity = velocity;

        telemetry.reverseScroll = dy < 0;

        telemetry.bounce =
            Math.sign(lastVelocity) !== Math.sign(velocity) &&
            Math.abs(velocity) < 0.1;

        // Reset pause tracking when scrolling
        if (pauseStart !== null) {
            pauseStart = null;
            telemetry.pauseDuration = 0;
        }

        // Clear existing timeout
        if (scrollTimeout) {
            clearTimeout(scrollTimeout);
        }

        // Set timeout to detect pause (no scroll for 100ms = paused)
        scrollTimeout = setTimeout(() => {
            pauseStart = performance.now();

            // Update pauseDuration periodically while paused
            const updatePause = () => {
                if (pauseStart !== null) {
                    telemetry.pauseDuration = performance.now() - pauseStart;
                    requestAnimationFrame(updatePause);
                }
            };
            updatePause();
        }, 100);

        lastVelocity = velocity;
        lastY = window.scrollY;
        lastTime = now;
    });
}
