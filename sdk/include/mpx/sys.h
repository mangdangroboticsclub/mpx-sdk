/* mpx/sys.h — logging, time, parameters, errors, lifecycle.
 *
 * Everything here is available to every skill regardless of what it moves.
 */
#ifndef MPX_SYS_H
#define MPX_SYS_H

#include "mpx/abi.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ═══════════════════════════════════════════════════════════════════════════
 *  Lifecycle
 *
 *  A skill exports one or two functions:
 *
 *      void on_start(void)          required — the robot calls this
 *      void on_stop(int reason)     optional — called when it ends
 *
 *  `reason` is MPX_STOP_DONE (returned normally) or MPX_STOP_TRAPPED (crashed).
 *
 *  on_stop is your chance to leave the robot somewhere sensible. It shares the
 *  run's remaining time budget — it is not a fresh 60 seconds — and it does
 *  NOT run if the watchdog killed you, because by then the instance has
 *  already been torn down. If your skill can run long, park before you hit the
 *  limit rather than relying on on_stop to do it.
 *
 *  When the watchdog does kill a skill the firmware halts the gait on your
 *  behalf. That stops motion; it does not choose a pose. Only you know which
 *  pose is safe for what you were doing.
 * ═══════════════════════════════════════════════════════════════════════════ */

#define MPX_STOP_DONE     0   /**< on_start returned normally.          */
#define MPX_STOP_TRAPPED  1   /**< on_start trapped (bad memory, /0).   */

/* Marks your entry points so wasm-ld exports them. The CLI also passes
 * --export=on_start/--export=on_stop, so this is belt and braces — but it
 * means a hand-rolled clang command line works too. */
#define MPX_EXPORT __attribute__((visibility("default"), used))

/* ═══════════════════════════════════════════════════════════════════════════
 *  Errors
 *
 *  Every host call returns a code. 0 is success; anything negative is one of
 *  these. Calls documented to return data return a non-negative value instead.
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef enum {
    MPX_OK             =  0,  /**< Success.                                   */
    MPX_ERR_ARG        = -1,  /**< Bad argument: id, index or pointer.        */
    MPX_ERR_NOT_LOCKED = -2,  /**< You do not hold the servo bus.             */
    MPX_ERR_NO_REPLY   = -3,  /**< The driver board did not answer.           */
    MPX_ERR_READONLY   = -4,  /**< Calibration parameter; read-only.          */
    MPX_ERR_CANCELLED  = -5,  /**< Your skill was stopped mid-call.           */
    MPX_ERR_STATE      = -6,  /**< Right call, wrong time.                    */
    MPX_ERR_BUSY       = -7,  /**< Another control domain holds the joints.   */
} mpx_err_t;

static inline const char *mpx_strerror(int code)
{
    switch (code) {
    case MPX_OK:             return "ok";
    case MPX_ERR_ARG:        return "bad argument";
    case MPX_ERR_NOT_LOCKED: return "you do not hold the servo bus";
    case MPX_ERR_NO_REPLY:   return "driver board did not answer";
    case MPX_ERR_READONLY:   return "read-only calibration parameter";
    case MPX_ERR_CANCELLED:  return "skill cancelled";
    case MPX_ERR_STATE:      return "right call, wrong time";
    case MPX_ERR_BUSY:       return "another control domain holds the joints";
    default:                 return code < 0 ? "unknown error" : "ok";
    }
}

/* Returns non-zero when the skill has been asked to stop. Any host call
 * returning MPX_ERR_CANCELLED means the same thing: unwind, do not retry. */
#define MPX_CANCELLED(rc)  ((rc) == MPX_ERR_CANCELLED)

/* ═══════════════════════════════════════════════════════════════════════════
 *  Logging  →  `mpx-cli logs -f`
 * ═══════════════════════════════════════════════════════════════════════════ */

static inline int mpx_log_n(const char *s, int len) { return print((int)s, len); }

static inline int mpx_strlen_(const char *s)
{
    int n = 0;
    while (s[n]) ++n;
    return n;
}

/** Log a run-time string (computed, not a literal). */
static inline int mpx_log_s(const char *s) { return print((int)s, mpx_strlen_(s)); }

/** Log a string literal. Cheapest form: the length is a compile-time constant. */
#define MPX_LOG(msg)  mpx_log_n("" msg "", (int)(sizeof(msg) - 1))

/* Render an int into `buf` (>= 12 bytes) and return its length. There is no
 * printf in a freestanding module, and pulling one in costs more code space
 * than most skills have to spare. */
static inline int mpx_itoa_(int v, char *buf)
{
    char tmp[12];
    int n = 0, len = 0;
    unsigned u = (v < 0) ? (unsigned)(-(long)v) : (unsigned)v;
    if (v < 0) buf[len++] = '-';
    do { tmp[n++] = (char)('0' + (u % 10u)); u /= 10u; } while (u);
    while (n) buf[len++] = tmp[--n];
    buf[len] = '\0';
    return len;
}

/** Log "label = 42". */
static inline int mpx_log_i(const char *label, int value)
{
    char buf[64];
    int n = 0;
    while (label[n] && n < 44) { buf[n] = label[n]; ++n; }
    buf[n++] = ' '; buf[n++] = '='; buf[n++] = ' ';
    n += mpx_itoa_(value, buf + n);
    return print((int)buf, n);
}

/** Log "label = 1.234" to three decimals. No float formatting exists here, so
 *  this is fixed-point on purpose: it is exact, small, and enough to debug. */
static inline int mpx_log_f(const char *label, float value)
{
    char buf[80];
    int n = 0, neg = value < 0.0f;
    long milli;
    if (neg) value = -value;
    milli = (long)(value * 1000.0f + 0.5f);
    while (label[n] && n < 44) { buf[n] = label[n]; ++n; }
    buf[n++] = ' '; buf[n++] = '='; buf[n++] = ' ';
    if (neg) buf[n++] = '-';
    n += mpx_itoa_((int)(milli / 1000), buf + n);
    buf[n++] = '.';
    {
        int frac = (int)(milli % 1000);
        buf[n++] = (char)('0' + frac / 100);
        buf[n++] = (char)('0' + (frac / 10) % 10);
        buf[n++] = (char)('0' + frac % 10);
    }
    return print((int)buf, n);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Time
 *
 *  mpx_now() is milliseconds since your on_start() began — it reads 0 on your
 *  first instruction, so a timeline never has to subtract a start it could not
 *  capture.
 *
 *  Prefer mpx_sleep_to(deadline) over mpx_sleep(duration) inside a loop.
 *  Sleeping for a duration lets each frame's own cost accumulate: 600 frames
 *  of mpx_sleep(16) run long by 600 frames' worth of host-call overhead.
 *  Sleeping to a deadline cannot drift, because the deadline was computed from
 *  the start, not from the last frame.
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Milliseconds since on_start() began. */
static inline unsigned mpx_now(void) { return (unsigned)mpx_millis(); }

/** Sleep for a duration. Yields, so the robot stays responsive. */
static inline int mpx_sleep(int ms) { return robot_delay_ms(ms); }

/** Sleep until mpx_now() reaches `t_ms`. Returns immediately if already past. */
static inline int mpx_sleep_to(unsigned t_ms) { return mpx_sleep_until((int)t_ms); }

/* ── Ticker: a fixed-rate loop that cannot drift ─────────────────────────────
 *
 *   mpx_ticker_t t = mpx_ticker(60);            // 60 frames per second
 *   while (mpx_ticker_elapsed(&t) < 2000) {     // for two seconds
 *       ... set joints or feet for this frame ...
 *       mpx_ticker_wait(&t);                    // sends the frame, then sleeps
 *   }
 *
 * mpx_ticker_wait() sends the frame for you, which is why robot_flush() does
 * not appear in code written this way. See mpx/leg.h for what "sends" means.
 */
typedef struct {
    unsigned start_ms;    /**< mpx_now() when the ticker was created.        */
    unsigned period_ms;   /**< Milliseconds per frame.                       */
    unsigned frame;       /**< Frames completed so far.                      */
} mpx_ticker_t;

static inline mpx_ticker_t mpx_ticker(int rate_hz)
{
    mpx_ticker_t t;
    if (rate_hz < 1)   rate_hz = 1;
    if (rate_hz > 200) rate_hz = 200;   /* the servo bus cannot go faster */
    t.start_ms  = mpx_now();
    t.period_ms = (unsigned)(1000 / rate_hz);
    t.frame     = 0;
    return t;
}

/** Milliseconds since the ticker was created. */
static inline unsigned mpx_ticker_elapsed(const mpx_ticker_t *t)
{
    return mpx_now() - t->start_ms;
}

/** 0.0 at the start, 1.0 after `total_ms`. Handy as an animation parameter. */
static inline float mpx_ticker_progress(const mpx_ticker_t *t, unsigned total_ms)
{
    float p;
    if (total_ms == 0) return 1.0f;
    p = (float)mpx_ticker_elapsed(t) / (float)total_ms;
    return p < 0.0f ? 0.0f : (p > 1.0f ? 1.0f : p);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Parameters
 *
 *  Supplied per run, so one skill covers many variations without a rebuild:
 *
 *      mpx-cli run --param speed=0.4 --param repeats=3
 *
 *  Declare them in manifest.json and the robot's web UI renders a control for
 *  each one. A run that supplies nothing falls back to the default you pass
 *  here, so an unparameterised skill behaves exactly as written.
 * ═══════════════════════════════════════════════════════════════════════════ */

static inline float mpx_paramf(const char *name, float fallback)
{
    return mpx_param_f(name, fallback);
}

static inline int mpx_parami(const char *name, int fallback)
{
    return mpx_param_i(name, fallback);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  ABI check
 *
 *  Put this at the top of on_start(). Without it, a module built against a
 *  different firmware shows up as an unexplained trap on the first host call —
 *  the single most confusing failure in this system.
 * ═══════════════════════════════════════════════════════════════════════════ */

#define MPX_REQUIRE_ABI()                                                     \
    do {                                                                       \
        if (mpx_abi_version() != MPX_ABI_VERSION) {                            \
            MPX_LOG("ABI mismatch — rebuild: mpx-cli deploy");                 \
            mpx_log_i("  robot", mpx_abi_version());                           \
            mpx_log_i("  built against", MPX_ABI_VERSION);                     \
            return;                                                            \
        }                                                                      \
    } while (0)

#ifdef __cplusplus
}
#endif
#endif /* MPX_SYS_H */
