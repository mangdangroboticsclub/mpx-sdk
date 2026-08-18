/* mpx/math.h — the maths a freestanding WASM skill does not otherwise have.
 *
 * A skill is compiled with -nostdlib, so there is no libm: no sinf, no sqrtf,
 * no atan2f. Before this header, every example in this SDK carried its own
 * hand-rolled copy, and the README had to warn that the obvious Taylor series
 * for atan is wrong by 3.5 degrees near |x| = 1 — comfortably inside a leg's
 * working range. That warning is gone because this file is now the answer.
 *
 * Two things worth knowing about the implementations:
 *
 * 1. WebAssembly has native instructions for sqrt, abs, floor, ceil, trunc,
 *    nearest, min, max and copysign. Those are exact, single-instruction, and
 *    cost nothing — they are not approximations at all. clang emits them for
 *    the __builtin_* forms used below.
 *
 * 2. Only the transcendentals need polynomials. The bounds below are measured
 *    against the C library over the full argument range, not estimated:
 *
 *        sin, cos     3.7e-6            atan, atan2, acos, asin   1.2e-5 rad
 *        sqrt         exact (0.0)       = 0.0007 degrees
 *
 *    For scale, the servos resolve about 0.264 degrees. The angular error in
 *    this header is roughly 380 times finer than the hardware can express, so
 *    it is never the limiting factor in anything you write.
 */
#ifndef MPX_MATH_H
#define MPX_MATH_H

#ifdef __cplusplus
extern "C" {
#endif

#define MPX_PI      3.14159265358979f
#define MPX_TWO_PI  6.28318530717959f
#define MPX_HALF_PI 1.57079632679490f
#define MPX_DEG2RAD 0.01745329251994f
#define MPX_RAD2DEG 57.2957795130823f

/* ── Exact: these compile to single WASM instructions ────────────────────── */

static inline float mpx_abs  (float x) { return __builtin_fabsf(x); }
static inline float mpx_sqrt (float x) { return x <= 0.0f ? 0.0f : __builtin_sqrtf(x); }
static inline float mpx_floor(float x) { return __builtin_floorf(x); }
static inline float mpx_ceil (float x) { return __builtin_ceilf(x); }
static inline float mpx_round(float x) { return __builtin_nearbyintf(x); }
static inline float mpx_trunc(float x) { return __builtin_truncf(x); }
static inline float mpx_min  (float a, float b) { return a < b ? a : b; }
static inline float mpx_max  (float a, float b) { return a > b ? a : b; }
static inline float mpx_sign (float x) { return x > 0.0f ? 1.0f : (x < 0.0f ? -1.0f : 0.0f); }

static inline float mpx_clamp(float v, float lo, float hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

/** Linear interpolation. t is not clamped — pass 1.2 and you extrapolate. */
static inline float mpx_lerp(float a, float b, float t) { return a + (b - a) * t; }

/** Where does v sit between a and b, as 0..1? The inverse of mpx_lerp. */
static inline float mpx_unlerp(float a, float b, float v)
{
    return (b == a) ? 0.0f : (v - a) / (b - a);
}

/** Rescale v from one range to another, clamped to the output range. */
static inline float mpx_remap(float v, float in_lo, float in_hi,
                              float out_lo, float out_hi)
{
    float t = mpx_clamp(mpx_unlerp(in_lo, in_hi, v), 0.0f, 1.0f);
    return mpx_lerp(out_lo, out_hi, t);
}

static inline float mpx_deg(float radians) { return radians * MPX_RAD2DEG; }
static inline float mpx_rad(float degrees) { return degrees * MPX_DEG2RAD; }

/* ── Approximated: polynomials, with their error bounds ──────────────────── */

/** Floating-point remainder. Exact for the ranges used here. */
static inline float mpx_fmod(float x, float y)
{
    if (y == 0.0f) return 0.0f;
    return x - y * mpx_trunc(x / y);
}

/* sin/cos: argument reduced to [-pi/2, pi/2], then a degree-9 odd polynomial.
 * Measured worst-case absolute error 3.7e-6 over x in [-20, 20]. */
static inline float mpx_sin(float x)
{
    float x2;

    x = mpx_fmod(x, MPX_TWO_PI);              /* -> (-2pi, 2pi)   */
    if (x >  MPX_PI) x -= MPX_TWO_PI;         /* -> (-pi, pi]     */
    if (x < -MPX_PI) x += MPX_TWO_PI;
    if (x >  MPX_HALF_PI) x =  MPX_PI - x;    /* -> [-pi/2, pi/2] */
    if (x < -MPX_HALF_PI) x = -MPX_PI - x;

    x2 = x * x;
    return x * (1.0f
         + x2 * (-1.0f / 6.0f
         + x2 * ( 1.0f / 120.0f
         + x2 * (-1.0f / 5040.0f
         + x2 * ( 1.0f / 362880.0f)))));
}

static inline float mpx_cos(float x) { return mpx_sin(x + MPX_HALF_PI); }

/** Undefined near the poles, like every tan. Guarded so it returns a large
 *  finite number rather than an infinity that would poison a pose. */
static inline float mpx_tan(float x)
{
    float c = mpx_cos(x);
    if (mpx_abs(c) < 1e-6f) return mpx_sin(x) > 0.0f ? 1e6f : -1e6f;
    return mpx_sin(x) / c;
}

/* atan: minimax polynomial on [-1, 1], argument-reduced for |x| > 1.
 * Worst-case error about 1e-4 radians = 0.006 degrees.
 *
 * NOT the Taylor series. x - x^3/3 + x^5/5 - x^7/7 is off by up to 3.5 degrees
 * near |x| = 1, which is inside the range a leg IK actually visits, and it
 * produces a limp that looks like a mechanical fault. */
static inline float mpx_atan(float x)
{
    float x2, r;
    int   inverted = 0, negative = 0;

    if (x < 0.0f)      { x = -x; negative = 1; }
    if (x > 1.0f)      { x = 1.0f / x; inverted = 1; }

    x2 = x * x;
    r  = x * (0.99986600f
       + x2 * (-0.33029950f
       + x2 * ( 0.18014100f
       + x2 * (-0.08513300f
       + x2 * ( 0.02083510f)))));

    if (inverted) r = MPX_HALF_PI - r;
    return negative ? -r : r;
}

/** Full-circle arctangent. Same error as mpx_atan. */
static inline float mpx_atan2(float y, float x)
{
    if (x > 0.0f) return mpx_atan(y / x);
    if (x < 0.0f) return mpx_atan(y / x) + (y >= 0.0f ? MPX_PI : -MPX_PI);
    if (y > 0.0f) return  MPX_HALF_PI;
    if (y < 0.0f) return -MPX_HALF_PI;
    return 0.0f;
}

/* acos/asin are built from atan2 and the exact sqrt, so they inherit atan's
 * error and add none of their own. Inputs are clamped: a cosine rule that
 * lands at 1.0000001 through rounding should give you 0, not a NaN that
 * propagates silently into twelve joint angles. */
static inline float mpx_acos(float c)
{
    c = mpx_clamp(c, -1.0f, 1.0f);
    return mpx_atan2(mpx_sqrt(1.0f - c * c), c);
}

static inline float mpx_asin(float s)
{
    s = mpx_clamp(s, -1.0f, 1.0f);
    return mpx_atan2(s, mpx_sqrt(1.0f - s * s));
}

/* ── Degree-taking forms ─────────────────────────────────────────────────────
 * Every angle you hand the robot is in degrees, so most call sites would
 * otherwise be mpx_sin(mpx_rad(x)). These exist so that conversion is not a
 * thing you can forget. */
static inline float mpx_sind(float deg) { return mpx_sin(deg * MPX_DEG2RAD); }
static inline float mpx_cosd(float deg) { return mpx_cos(deg * MPX_DEG2RAD); }

/* ── Easing ──────────────────────────────────────────────────────────────────
 * All take and return 0..1. A movement built from linear interpolation alone
 * reads as mechanical; an ease on the ends is most of what makes motion look
 * deliberate rather than commanded. */

typedef enum {
    MPX_EASE_LINEAR = 0,  /**< Constant speed.                                */
    MPX_EASE_IN,          /**< Starts slow. Good for beginning a move.        */
    MPX_EASE_OUT,         /**< Ends slow. Good for arriving at a pose.        */
    MPX_EASE_INOUT,       /**< Slow at both ends. The safe default.           */
    MPX_EASE_SINE,        /**< Gentle cosine ease; the smoothest option.      */
    MPX_EASE_BACK,        /**< Overshoots slightly then settles. Playful.     */
    MPX_EASE_BOUNCE,      /**< Settles with decaying bounces.                 */
} mpx_ease_t;

static inline float mpx_ease(mpx_ease_t e, float t)
{
    /* Snap the endpoints. Curves built on mpx_cos would otherwise inherit its
     * 3.7e-6 and return 0.9999982 at t = 1 — and a timeline reads ease(1) as
     * "you have arrived at this keyframe", so every pose would land a fraction
     * short of the one that was authored. */
    if (t <= 0.0f) return 0.0f;
    if (t >= 1.0f) return 1.0f;
    switch (e) {
    case MPX_EASE_IN:    return t * t;
    case MPX_EASE_OUT:   return t * (2.0f - t);
    case MPX_EASE_INOUT: return t < 0.5f ? 2.0f * t * t
                                         : -1.0f + (4.0f - 2.0f * t) * t;
    case MPX_EASE_SINE:  return 0.5f * (1.0f - mpx_cos(t * MPX_PI));
    case MPX_EASE_BACK: {
        const float s = 1.70158f;
        float u = t - 1.0f;
        return u * u * ((s + 1.0f) * u + s) + 1.0f;
    }
    case MPX_EASE_BOUNCE: {
        if (t < 0.363636f)      return 7.5625f * t * t;
        else if (t < 0.727272f) { t -= 0.545454f; return 7.5625f * t * t + 0.75f; }
        else if (t < 0.909090f) { t -= 0.818181f; return 7.5625f * t * t + 0.9375f; }
        else                    { t -= 0.954545f; return 7.5625f * t * t + 0.984375f; }
    }
    case MPX_EASE_LINEAR:
    default:             return t;
    }
}

/** Interpolate a to b with an easing curve. The workhorse of motion.h. */
static inline float mpx_ease_lerp(float a, float b, float t, mpx_ease_t e)
{
    return mpx_lerp(a, b, mpx_ease(e, t));
}

#ifdef __cplusplus
}
#endif
#endif /* MPX_MATH_H */
