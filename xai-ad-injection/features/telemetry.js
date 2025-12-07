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
let pauseStart = performance.now();

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

        if (Math.abs(dy) < 2) {
            telemetry.pauseDuration = now - pauseStart;
        } else {
            pauseStart = now;
            telemetry.pauseDuration = 0;
        }

        lastVelocity = velocity;
        lastY = window.scrollY;
        lastTime = now;
    });
}
