"""SI-unit kinematic / quasi-static screening; no structural or hardware validation."""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def standee_geometry(p):
    """Uniform sheet scaled in Y/Z about its bottom; fixed X and thickness."""
    reference = p["standee_reference"]
    scale = p["standee_height_m"] / reference["height_m"]
    if scale <= 0 or p["standee_bottom_m"] < 0:
        raise ValueError("Standee height must be positive and bottom must not be below ground")
    area = reference["area_m2"] * scale ** 2
    override = p.get("standee_mass_override_kg")
    mass = reference["mass_kg"] * scale ** 2 if override is None else override
    if mass <= 0:
        raise ValueError("Standee mass must be positive")
    xyz = [reference["centroid_x_m"], reference["centroid_y_m"] * scale,
           p["standee_bottom_m"] + reference["centroid_z_above_bottom_m"] * scale]
    return {"area_m2": area, "mass_kg": mass, "center_of_mass_m": xyz,
            "pressure_center_z_m": xyz[2], "height_m": p["standee_height_m"],
            "bottom_m": p["standee_bottom_m"], "top_m": p["standee_bottom_m"] + p["standee_height_m"],
            "mass_model": "explicit override" if override is not None else "constant reference areal density"}


def mass_properties(p, ballast_kg=None):
    board = standee_geometry(p)
    parts = p["components"] + [{"mass_kg": p["ballast_kg"] if ballast_kg is None else ballast_kg,
                                "position_m": p["ballast_position_m"]},
                               {"mass_kg": board["mass_kg"], "position_m": board["center_of_mass_m"]}]
    mass = sum(c["mass_kg"] for c in parts)
    cg = [sum(c["mass_kg"] * c["position_m"][k] for c in parts) / mass for k in range(3)]
    return mass, cg


def wheel_speeds(speed, radius, track, diameter):
    """Positive radius: left turn. Left wheel at +Y; +X is forward."""
    omega = 0.0 if radius is None else speed / radius
    left, right = speed - omega * track / 2, speed + omega * track / 2
    rpm_factor = 60 / (math.pi * diameter)
    return {"left_mps": left, "right_mps": right,
            "left_rpm": left * rpm_factor, "right_rpm": right * rpm_factor,
            "yaw_rate_rad_s": omega}


def stopping_distance(speed, deceleration, timeout=0.0):
    return speed * timeout + speed ** 2 / (2 * deceleration)


def stability(p, ballast_kg=None, speed=None, radius=None, wind_mps=0.0, slope_deg=0.0):
    """Worst-direction brake/turn/wind/slope screening on a rectangular contact polygon.

    Uniform front-on wind; entire board area is used, including case overlap.
    Positive slope is defined as the adverse downhill direction (+X). No wind shielding.
    For slope, normal force is mg*cos(theta); tangential gravity shifts contact by h*tan(theta).
    The envelope chooses signs toward the nearest edge; it is not one simultaneous trajectory.
    """
    mass, cg = mass_properties(p, ballast_kg)
    board = standee_geometry(p)
    speed = p["speed_mps"] if speed is None else speed
    radius = p["minimum_turn_radius_m"] if radius is None else radius
    normal = mass * p["gravity"] * math.cos(math.radians(slope_deg))
    drag = 0.5 * p["air_density_kg_m3"] * p["drag_coefficient_assumed"] * board["area_m2"] * wind_mps ** 2
    wind_shift = drag * board["pressure_center_z_m"] / normal
    # At rest, commanded acceleration is retained as a forward start envelope.
    acceleration = max(p["acceleration_mps2"], p["braking_deceleration_mps2"])
    acceleration_shift = mass * acceleration * cg[2] / normal
    lateral_acceleration = 0.0 if math.isinf(radius) else speed ** 2 / abs(radius)
    lateral_shift = mass * lateral_acceleration * cg[2] / normal
    slope_shift = cg[2] * abs(math.tan(math.radians(slope_deg)))
    margin_x = p["contact_half_length_m"] - abs(cg[0])
    margin_y = p["contact_half_width_m"] - abs(cg[1])
    available_wind_moment = max(0.0, (margin_x - acceleration_shift - slope_shift) * normal)
    wind_denominator = 0.5 * p["air_density_kg_m3"] * p["drag_coefficient_assumed"] * board["area_m2"] * board["pressure_center_z_m"]
    return {
        "mass_kg": mass, "center_of_mass_m": cg,
        "static_margin_x_m": margin_x, "static_margin_y_m": margin_y,
        "critical_longitudinal_acceleration_no_wind_mps2": p["gravity"] * margin_x / cg[2],
        "critical_lateral_acceleration_no_wind_mps2": p["gravity"] * margin_y / cg[2],
        "critical_longitudinal_slope_static_deg": math.degrees(math.atan2(margin_x, cg[2])),
        "front_on_wind_mps": wind_mps, "wind_force_N": drag,
        "wind_contact_shift_x_m": wind_shift,
        "adverse_slope_deg": slope_deg,
        "start_brake_contact_shift_x_m": acceleration_shift,
        "turn_contact_shift_y_m": lateral_shift,
        "worst_case_contact_x_m": abs(cg[0]) + wind_shift + acceleration_shift + slope_shift,
        "worst_case_contact_y_m": abs(cg[1]) + lateral_shift,
        "remaining_margin_x_m": margin_x - wind_shift - acceleration_shift - slope_shift,
        "remaining_margin_y_m": margin_y - lateral_shift,
        "wind_tip_threshold_with_start_brake_mps": math.sqrt(available_wind_moment / wind_denominator),
        "criterion": "positive margins only pass this quasi-static assumed-parameter screen; no safety certification"
    }


def torque_selection(p, diameter, slope_deg, ballast_kg=None):
    """Equal wheel tractive force assumption; motor output is after gearbox, before external losses."""
    mass, _ = mass_properties(p, ballast_kg)
    angle = math.radians(slope_deg)
    force = mass * (p["acceleration_mps2"] + p["gravity"] *
                    (p["rolling_resistance_coefficient"] * math.cos(angle) + math.sin(angle)))
    wheel_torque = force * diameter / 4
    return {"wheel_diameter_m": diameter, "slope_deg": slope_deg,
            "tractive_force_total_N": force,
            "wheel_contact_torque_each_Nm": wheel_torque,
            "gearbox_output_torque_each_with_loss_and_factor_Nm": wheel_torque / p["drivetrain_efficiency"] * p["torque_selection_factor"],
            "assumptions": "equal drive loads, rolling resistance 0.03; efficiency 0.7; selection factor 2; caster scrub/step impact not modeled"}


def trajectory(p, radius=None, disconnect=False, dt=0.01):
    """Begins at cruise; brake command or radio loss at t=2s. Exact arc integration per segment."""
    speed, decel = p["speed_mps"], p["braking_deceleration_mps2"]
    trigger = 2.0
    delay = p["communication_timeout_s"] if disconnect else 0.0
    brake_at = trigger + delay
    final_t = brake_at + speed / decel
    x = y = heading = t = distance_after_trigger = 0.0
    samples = [{"t_s": 0.0, "x_m": x, "y_m": y, "yaw_rad": heading, "speed_mps": speed}]
    boundaries = sorted(set([0.0, trigger, brake_at, final_t] +
                            [min(i * dt, final_t) for i in range(1, math.ceil(final_t / dt) + 1)]))
    def speed_at(time):
        return max(0.0, speed - decel * max(0.0, time - brake_at))
    for index, end in enumerate(boundaries[1:]):
        distance = (speed_at(t) + speed_at(end)) / 2 * (end - t)
        if t >= trigger - 1e-9:
            distance_after_trigger += distance
        if radius is None:
            x += distance * math.cos(heading)
            y += distance * math.sin(heading)
        else:
            new_heading = heading + distance / radius
            x += radius * (math.sin(new_heading) - math.sin(heading))
            y += radius * (math.cos(heading) - math.cos(new_heading))
            heading = new_heading
        t = end
        if index % 10 == 0 or abs(t - final_t) < 1e-9:
            samples.append({"t_s": t, "x_m": x, "y_m": y, "yaw_rad": heading, "speed_mps": speed_at(t)})
    return {"trigger_s": trigger, "brake_starts_s": brake_at, "stopped_s": final_t,
            "distance_after_trigger_m": distance_after_trigger, "samples": samples}


def validate(p):
    assert stopping_distance(0, 0.25, 0.2) == 0
    assert math.isclose(stopping_distance(0.3, 0.25, 0.2), 0.24)
    assert stability(p, wind_mps=0)["wind_force_N"] == 0
    straight = wheel_speeds(0.3, None, 0.4, 0.05)
    left = wheel_speeds(0.3, 1.5, 0.4, 0.05)
    right = wheel_speeds(0.3, -1.5, 0.4, 0.05)
    assert straight["left_rpm"] == straight["right_rpm"]
    assert 0 < left["left_rpm"] < left["right_rpm"]
    assert left["left_rpm"] == right["right_rpm"]
    assert wheel_speeds(0, 1.5, 0.4, 0.05)["yaw_rate_rad_s"] == 0
    assert mass_properties(p, 6)[1][2] < mass_properties(p, 0)[1][2]
    assert stability(p, wind_mps=5)["remaining_margin_x_m"] < stability(p, wind_mps=0)["remaining_margin_x_m"]
    assert stability(p, speed=0)["turn_contact_shift_y_m"] == 0
    for disconnected in [False, True]:
        sim = trajectory(p, disconnect=disconnected)
        exact = stopping_distance(p["speed_mps"], p["braking_deceleration_mps2"],
                                  p["communication_timeout_s"] if disconnected else 0)
        assert math.isclose(sim["distance_after_trigger_m"], exact, abs_tol=1e-9)
        assert sim["samples"][-1]["speed_mps"] < 1e-9
    arc = trajectory(p, radius=1.5)["samples"][-1]
    assert math.isclose(arc["x_m"] ** 2 + (arc["y_m"] - 1.5) ** 2, 1.5 ** 2, abs_tol=1e-9)
    short = copy.deepcopy(p)
    short.update(standee_height_m=1.6, standee_bottom_m=0.02, standee_mass_override_kg=None)
    tall = copy.deepcopy(short)
    tall["standee_height_m"] = 1.8
    base_board, tall_board = standee_geometry(short), standee_geometry(tall)
    assert math.isclose(tall_board["area_m2"] / base_board["area_m2"], (1.8 / 1.6) ** 2)
    assert math.isclose(tall_board["mass_kg"] / base_board["mass_kg"], (1.8 / 1.6) ** 2)
    assert tall_board["center_of_mass_m"][2] > base_board["center_of_mass_m"][2]
    assert mass_properties(tall)[1][2] > mass_properties(short)[1][2]
    assert stability(tall, wind_mps=3)["wind_contact_shift_x_m"] > stability(short, wind_mps=3)["wind_contact_shift_x_m"]
    raised = copy.deepcopy(short)
    raised["standee_bottom_m"] += 0.1
    raised_board = standee_geometry(raised)
    assert math.isclose(raised_board["pressure_center_z_m"] - base_board["pressure_center_z_m"], 0.1)
    assert raised_board["area_m2"] == base_board["area_m2"]
    assert raised_board["mass_kg"] == base_board["mass_kg"]
    tall["standee_mass_override_kg"] = 1.75
    assert standee_geometry(tall)["mass_kg"] == 1.75
    return "24 assertions passed: speed/wind boundaries, wheel symmetry, ballast, exact stop/arc geometry, height/area/mass/COM/wind scaling, bottom translation and mass override"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", type=Path, default=HERE / "parameters.json")
    parser.add_argument("--output", type=Path, default=HERE / "results.json")
    parser.add_argument("--height", type=float, help="standee height in metres; scales width, area and mass")
    parser.add_argument("--bottom", type=float, help="standee bottom height above ground in metres")
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text(encoding="utf-8"))
    if args.height is not None:
        p["standee_height_m"] = args.height
    if args.bottom is not None:
        p["standee_bottom_m"] = args.bottom
    verification = validate(p)
    results = {
        "scope": "deterministic differential-drive kinematics + quasi-static tipping and torque screening; no multibody/contact/FEA/real robot simulation",
        "parameters": p,
        "standee_resolved": standee_geometry(p),
        "height_comparison": [{"standee": standee_geometry(dict(p, standee_height_m=h)),
                               "stability_zero_wind": stability(dict(p, standee_height_m=h)),
                               "stability_wind_5mps": stability(dict(p, standee_height_m=h), wind_mps=5)}
                              for h in [1.6, 1.7, 1.8]],
        "verification": verification,
        "default": stability(p),
        "wheel_speeds": {str(d): {"straight": wheel_speeds(p["speed_mps"], None, p["track_m"], d),
                                  "left_turn": wheel_speeds(p["speed_mps"], p["minimum_turn_radius_m"], p["track_m"], d)}
                         for d in p["wheel_diameters_m"]},
        "stop_distance_m": {"commanded": stopping_distance(p["speed_mps"], p["braking_deceleration_mps2"]),
                            "disconnect_healthy_controller": stopping_distance(p["speed_mps"], p["braking_deceleration_mps2"], p["communication_timeout_s"])},
        "scenarios": {"straight_controlled_stop": trajectory(p),
                      "minimum_radius_turn_controlled_stop": trajectory(p, radius=p["minimum_turn_radius_m"]),
                      "radio_loss_controlled_stop": trajectory(p, disconnect=True)},
        "torque_selection": [torque_selection(p, diameter=d, slope_deg=s)
                             for d in p["wheel_diameters_m"] for s in [0, 5]],
        "screening_sweep": [dict(ballast_kg=b, **stability(p, ballast_kg=b, wind_mps=w, slope_deg=s))
                            for b in [0, 3, 6, 8] for w in [0, 3, 5, 8] for s in [0, 5]],
        "limitations": ["The four current CAD suitcase wheels are passive, not an implemented drive system.",
                        "Support polygon idealizes swivel caster contact centers; caster offset/contact uncertainty must be measured.",
                        "50 mm matches current wheel diameter; 80 mm is an alternate requiring changed wheel wells and heights.",
                        "Radio loss assumes the motor controller remains powered and executes a verified brake ramp; power loss and controller failure are different.",
                        "No traction/slip, caster scrub, obstacle impact, KT flex, clamp strength, wind gust dynamics, or brake holding has been validated.",
                        "Wind threshold is a mathematical tipping boundary, never an allowed operating wind."]
    }
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verification": verification, "mass_kg": results["default"]["mass_kg"],
                      "cg_m": results["default"]["center_of_mass_m"],
                      "stop_distance_m": results["stop_distance_m"], "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
