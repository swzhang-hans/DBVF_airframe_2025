import re
import pandas as pd
import numpy as np

def load_propeller_data(filepath):
    """
    Reads an APC propeller static performance text file and splits it
    into DataFrames by propeller name (like '105x45', '105x6', etc.)
    """

    with open(filepath, "r") as f:
        text = f.read()

    # Regex that matches propeller names (allowing leading spaces)
    # Example matches: '   105x45.dat', '10x58EP(F2B).dat'
    blocks = re.split(r'\n\s*(?=\d{1,3}x[0-9A-Za-z\-\(\)]+\.dat)', text)

    prop_data = {}

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 5:
            continue  # skip header chunks or empty blocks

        # Detect the propeller name (e.g. "105x45.dat")
        match = re.search(r'(\d{1,3}x[0-9A-Za-z\-\(\)]+)\.dat', block)
        if not match:
            continue
        prop_name = match.group(1)

        # Find where the actual data starts (line starting with "RPM")
        try:
            header_idx = next(i for i, line in enumerate(lines) if line.strip().startswith("RPM"))
        except StopIteration:
            continue  # skip if table header not found

        # Combine table part and read into a DataFrame
        data_lines = lines[header_idx:]
        df = pd.read_csv(pd.io.common.StringIO("\n".join(data_lines)), sep='\s+')

        prop_data[prop_name] = df

    # Print all found propellers for manual checking
    #if not prop_data:
    #    print("⚠️ No propellers found! Check file formatting or regex pattern.")
    #else:
    #    print("✅ Found the following propellers:")
    #    for name in prop_data.keys():
    #        print(" -", name)

    return prop_data


import numpy as np
import pandas as pd

def analyze_propellers(prop_data, required_thrust_N, target_thrust_N, output_name="propeller_selection_SI"):
    """
    Analyze propeller performance (SI units).

    For each propeller that can exceed the required thrust:
    - Interpolates RPM, Power, Torque, and Efficiency at the required thrust.
    - Also reports RPM, Power, Torque, and Efficiency at a given target thrust.
    - Efficiency is computed as Thrust/Power (N/W).

    Parameters
    ----------
    prop_data : dict[str, pd.DataFrame]
        Output from load_prop_data()
    required_thrust_N : float
        The design or required maximum thrust (N)
    target_thrust_N : float
        A smaller thrust at which performance is also compared (N)
    output_name : str, optional
        Base name for the output files (without extension).
        Example: "prop_test_80N" → "prop_test_80N.csv" and ".dat"

    Returns
    -------
    results_df : pd.DataFrame
        Summary table of propeller performance (SI units)
    """

    # --- Unit conversion constants ---
    LBF_TO_N = 4.44822
    HP_TO_W = 745.7
    INLBF_TO_NM = 0.113

    results = []

    for name, df in prop_data.items():
        # Convert numeric columns safely
        df = df.apply(pd.to_numeric, errors="coerce").dropna()

        # Convert to SI
        df["Thrust_N"] = df["THRUST"] * LBF_TO_N
        df["Power_W"] = df["POWER"] * HP_TO_W
        df["Torque_Nm"] = df["TORQUE"] * INLBF_TO_NM

        # Compute thrust-to-power efficiency [N/W]
        df["efficiency"] = df["Thrust_N"] / df["Power_W"].replace(0, np.nan)

        # Skip propellers that cannot achieve required thrust
        if df["Thrust_N"].max() < required_thrust_N:
            continue

        # --- Interpolate at required thrust (main design point) ---
        rpm_req = np.interp(required_thrust_N, df["Thrust_N"], df["RPM"])
        power_req = np.interp(required_thrust_N, df["Thrust_N"], df["Power_W"])
        torque_req = np.interp(required_thrust_N, df["Thrust_N"], df["Torque_Nm"])
        eff_req = np.interp(required_thrust_N, df["Thrust_N"], df["efficiency"])

        # --- Interpolate at target thrust (secondary point) ---
        rpm_tgt = np.interp(target_thrust_N, df["Thrust_N"], df["RPM"])
        power_tgt = np.interp(target_thrust_N, df["Thrust_N"], df["Power_W"])
        torque_tgt = np.interp(target_thrust_N, df["Thrust_N"], df["Torque_Nm"])
        eff_tgt = np.interp(target_thrust_N, df["Thrust_N"], df["efficiency"])

        results.append({
            "Propeller": name,
            f"RPM at {required_thrust_N:.0f} N": int(rpm_req),
            f"Power at {required_thrust_N:.0f} N (W)": round(power_req, 2),
            f"Torque at {required_thrust_N:.0f} N (Nm)": round(torque_req, 4),
            f"Efficiency at {required_thrust_N:.0f} N (N/W)": round(eff_req, 6),
            f"RPM at {target_thrust_N:.0f} N": int(rpm_tgt),
            f"Power at {target_thrust_N:.0f} N (W)": round(power_tgt, 2),
            f"Torque at {target_thrust_N:.0f} N (Nm)": round(torque_tgt, 4),
            f"Efficiency at {target_thrust_N:.0f} N (N/W)": round(eff_tgt, 6),
        })

    # --- Handle case where no prop meets the requirement ---
    if not results:
        print("⚠️ No propellers meet the required thrust condition.")
        return pd.DataFrame()

    # --- Build and sort DataFrame (best efficiency at required thrust first) ---
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(
        by=f"Efficiency at {required_thrust_N:.0f} N (N/W)",
        ascending=False
    ).reset_index(drop=True)

    # --- Export filenames ---
    csv_path = f"{output_name}.csv"
    dat_path = f"{output_name}.dat"

    # --- Export to CSV (for data processing) ---
    results_df.to_csv(csv_path, index=False)

    # --- Export to .dat (for human readability) ---
    formatted_str = results_df.to_string(
        index=False,
        justify="right",
        float_format="{:10.4f}".format
    )

    with open(dat_path, "w") as f:
        f.write(f"# Propeller performance at {required_thrust_N:.0f} N required thrust\n")
        f.write(f"# Also evaluated at {target_thrust_N:.0f} N target thrust\n")
        f.write("# All units in SI (N, W, Nm, N/W)\n")
        f.write("# ------------------------------------------------------------\n\n")
        f.write(formatted_str)

    print(f"✅ {len(results_df)} propellers exceed {required_thrust_N:.1f} N requirement.")
    print(f"Results exported to '{csv_path}' and '{dat_path}'.")

    return results_df


data = load_propeller_data("PER2_STATIC-2.dat")
analyze_propellers(data, 17, 8.4, "propeller_select_17-84")