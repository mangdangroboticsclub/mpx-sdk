"""\
mpx-cli — MPX-Dog Skill Development Kit

A Python CLI for developing, building, and deploying
WASM skills to the MPX-Dog quadruped robot.

Commands:
  init     Scaffold a new skill project
  build    Compile C/WAT/TS source to .wasm
  upload   Upload a .wasm skill to the robot
  run      Execute a skill on the robot
  list     List skills installed on the robot
  delete   Delete a skill from the robot

Environment variables:
  MPX_HOST      Robot IP address (default: 192.168.2.1)
  MPX_PORT      HTTP port (default: 80)
"""

__version__ = "0.1.0"
