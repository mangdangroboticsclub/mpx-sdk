/* mpx.h — the whole SDK.
 *
 *     #include "mpx.h"
 *
 *     MPX_EXPORT void on_start(void)
 *     {
 *         MPX_REQUIRE_ABI();
 *         MPX_LOG("hello");
 *         mpx_gait_for(MPX_GAIT_FORWARD, 2000);
 *         mpx_stand();
 *     }
 *
 * Everything is header-only and `static inline`, so including all of it costs
 * nothing in the binary — only what you call is emitted.
 *
 * The layers, outermost first. Use the highest one that does what you need;
 * each one below gives more control and takes more responsibility.
 *
 *   mpx/sys.h     log, time, parameters, errors, the ticker      always useful
 *   mpx/math.h    sin, sqrt, atan2, easing                       always useful
 *   mpx/motion.h  keyframes and timelines                        AUTHOR HERE
 *   mpx/robot.h   gaits, driving, body attitude                  whole robot
 *   mpx/gaits.h   the catalogue of built-in movements
 *   mpx/leg.h     feet, joints, frames, your own IK              one leg
 *   mpx/bus.h     gains, torque, the motor's control loop        one motor
 *   mpx/abi.h     the raw host imports                           rarely
 *
 * docs/MOVEMENT.md explains how they fit together and, more importantly,
 * what happens when two of them want the same joint.
 */
#ifndef MPX_H
#define MPX_H

#include "mpx/abi.h"
#include "mpx/sys.h"
#include "mpx/math.h"
#include "mpx/gaits.h"
#include "mpx/robot.h"
#include "mpx/leg.h"
#include "mpx/bus.h"
#include "mpx/motion.h"
#include "mpx/live.h"

#endif /* MPX_H */
