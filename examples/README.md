# Examples

Six, in order. The first four are **one per control layer** — those are about
*output*. The fifth is **sensing**, which is *input* and works with all of them.
The sixth uses everything.

| | | |
|---|---|---|
| **[01-gaits](01-gaits)** | Layer 1 | you say what you want; the robot does everything |
| **[02-feet](02-feet)** | Layer 2 | you place the feet; the firmware solves the legs |
| **[03-joints](03-joints)** | Layer 3 | you solve the legs |
| **[04-motors](04-motors)** | Layer 4 | you own the motor's control loop too |
| **[05-sensing](05-sensing)** | input | the IMU and joint feedback — moving because of what you read |
| **[06-together](06-together)** | all of it | a real routine, and when to come back **up** |

Each step down a layer gives more control and takes more responsibility. **Use
the highest layer that does what you need** — and read them in order, because
each explains what the one above could not do.

```bash
mpx-cli deploy examples/01-gaits
```

The concepts behind them are in [docs/MOVEMENT.md](../docs/MOVEMENT.md).
