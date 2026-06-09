# Substation Simulation using Gazebo

A compact 3-phase transmission substation for Gazebo Sim with engineered conductor routing.

## Electrical Flow

```
Transmission Tower (north)
        ↓
   Incoming Gantry
        ↓
   Disconnector → CT → Breaker
        ↓
   3-Phase Busbar (yard center)
   /      |        \
 PT    Transformer   Outgoing Feeder (south)
```

## Phase Standards

| Phase | Color  | X column | Conductor Z |
|-------|--------|----------|-------------|
| A     | Red    | -3 m     | 5.0 m       |
| B     | Yellow |  0 m     | 5.4 m       |
| C     | Blue   | +3 m     | 5.8 m       |

## Features

- Lattice transmission tower (12 m, 2×2 m base, 3 m crossarm)
- Orthogonal 90° conductor routing (no crossings)
- Insulators at gantry, busbar, PT, transformer, outgoing gantry
- Single transformer bay + surge arrester
- Gravel switchyard texture, oil containment, walkway, cable trench
- Default isometric overview camera

## Run

```bash
cd ~/Desktop/intern_ws
colcon build --packages-select substation_world
source install/setup.bash
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:$(ros2 pkg prefix substation_world)/share/substation_world/models
gz sim $(ros2 pkg prefix substation_world)/share/substation_world/worlds/substation_phase2.sdf
```

## Regenerate wiring / world

```bash
cd ~/Desktop/intern_ws/src/substation_world
python3 scripts/generate_world.py
```

This rebuilds all conductor segments and writes `worlds/substation_phase2.sdf`.

## Software

- Ubuntu 24.04 · Gazebo Sim · ROS 2 Jazzy
