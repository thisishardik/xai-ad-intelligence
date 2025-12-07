// model.js
// Uses Grok API to predict user attention score based on scroll telemetry

const XAI_API_KEY = "xai-DrStGxoc3EHG0ribsAEp0RsZOVEuww9031WKNEsSvXW8o0lXdLAWk2kyetcM5bRKjVq76eEil6YGWzBO";
const XAI_API_URL = "https://api.x.ai/v1/chat/completions";
const MODEL = "grok-4-1-fast-non-reasoning";

/**
 * Get attention score from Grok API based on scroll telemetry features
 * @param {Object} features - Scroll telemetry and timing features
 * @returns {Promise<{attention_score: number, reason: string}>}
 */
export async function getAttentionScore(features) {
    try {
        // Log input features
        console.log("[Residual Attention Model] Input Features:", {
            velocity: features.velocity.toFixed(3),
            acceleration: features.acceleration.toFixed(3),
            pauseDuration: `${features.pauseDuration.toFixed(0)}ms`,
            reverseScroll: features.reverseScroll,
            bounce: features.bounce,
            tweets_since_last_ad: features.tweets_since_last_ad,
            time_since_last_ad: `${features.time_since_last_ad.toFixed(0)}ms`
        });

        const prompt = buildAttentionPrompt(features);

        const response = await fetch(XAI_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${XAI_API_KEY}`
            },
            body: JSON.stringify({
                model: MODEL,
                messages: [
                    {
                        role: "system",
                        content: "You are an expert at analyzing user scroll behavior to predict attention and engagement. Return only valid JSON."
                    },
                    {
                        role: "user",
                        content: prompt
                    }
                ],
                temperature: 0.3,
                max_tokens: 150
            })
        });

        if (!response.ok) {
            throw new Error(`Grok API error: ${response.status}`);
        }

        const data = await response.json();
        const content = data.choices[0].message.content.trim();

        // Parse JSON response (handle code blocks if present)
        let result;
        if (content.includes("```")) {
            const jsonMatch = content.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
            if (jsonMatch) {
                result = JSON.parse(jsonMatch[1]);
            } else {
                throw new Error("Could not extract JSON from response");
            }
        } else {
            result = JSON.parse(content);
        }

        // Validate response format
        if (typeof result.attention_score !== 'number' || typeof result.reason !== 'string') {
            throw new Error("Invalid response format from Grok");
        }

        // Clamp attention score to [0, 1]
        result.attention_score = Math.max(0, Math.min(1, result.attention_score));

        // Log prediction result
        console.log("[Attention Model] Prediction:", {
            attention_score: result.attention_score.toFixed(3),
            reason: result.reason
        });

        return result;

    } catch (err) {
        console.warn("Grok attention model failed:", err.message);
        return {
            attention_score: 0.0,
            reason: "Model unavailable - using fallback score"
        };
    }
}

/**
 * Build the prompt for Grok to analyze scroll behavior
 * @param {Object} features - Scroll telemetry features
 * @returns {string} Formatted prompt
 */
function buildAttentionPrompt(features) {
    return `Analyze this user's scroll behavior and predict their attention level for viewing an ad.

SCROLL TELEMETRY:
- Velocity: ${features.velocity.toFixed(3)} px/ms (scroll speed)
- Acceleration: ${features.acceleration.toFixed(3)} px/ms² (speed change)
- Pause Duration: ${features.pauseDuration.toFixed(0)} ms (time paused)
- Reverse Scroll: ${features.reverseScroll ? 'Yes' : 'No'} (scrolling up?)
- Bounce: ${features.bounce ? 'Yes' : 'No'} (rapid direction change)

AD TIMING:
- Tweets Since Last Ad: ${features.tweets_since_last_ad}
- Time Since Last Ad: ${features.time_since_last_ad.toFixed(0)} ms

TASK:
Based on this data, predict:
1. **attention_score** (0.0 to 1.0): How likely is the user to notice and engage with an ad right now?
   - High score (0.7-1.0): User is slowing down, pausing, or showing high engagement
   - Medium score (0.4-0.7): Normal scrolling behavior
   - Low score (0.0-0.4): Fast scrolling, bouncing, or distracted

2. **reason**: A brief, fun explanation (1 sentence) of why this is a good/bad moment to show an ad.
   Examples:
   - "User slowed down and paused 320ms after fast scrolling."
   - "Rapid scrolling detected - user is skimming content."
   - "User paused for 2.1s, indicating high engagement."

Return ONLY valid JSON in this exact format:
{
  "attention_score": 0.83,
  "reason": "User slowed down and paused 320ms after fast scrolling."
}`;
}
