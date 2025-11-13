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


def analyze_propellers(prop_data, required_thrust_N, target_thrust_N, output_name="prop_selection_SI"):
    """
    For each propeller that can reach `required_thrust_N`, interpolate and export:
      - RPM, Thrust (N), Power (W), Torque (Nm), Cp, Ct, FOM at required thrust
      - RPM, Thrust (N), Power (W), Torque (Nm), Cp, Ct, FOM at target thrust
    Also includes efficiency (N/W) at both points for ranking.
    Exports CSV and pretty .dat; returns a DataFrame.

    Parameters
    ----------
    prop_data : dict[str, pd.DataFrame]  # from load_prop_data()
    required_thrust_N : float            # required thrust (N)
    target_thrust_N   : float            # target thrust (N)
    output_name       : str              # base filename (no extension)
    """

    # Unit conversion constants
    LBF_TO_N   = 4.44822
    HP_TO_W    = 745.7
    INLBF_TO_NM = 0.113

    def safe_interp(x, xp, fp):
        """Return NaN if x is outside [min(xp), max(xp)], else linear interp."""
        xp = np.asarray(xp); fp = np.asarray(fp)
        if len(xp) == 0 or np.isnan(x) or np.any(np.isnan(xp)) or np.any(np.isnan(fp)):
            return np.nan
        xmin, xmax = np.nanmin(xp), np.nanmax(xp)
        if x < xmin or x > xmax:
            return np.nan
        # np.interp requires strictly increasing xp; sort & deduplicate
        order = np.argsort(xp)
        xp_sorted = xp[order]
        fp_sorted = fp[order]
        # drop duplicate xp to avoid issues
        uniq_mask = np.concatenate(([True], xp_sorted[1:] != xp_sorted[:-1]))
        return float(np.interp(x, xp_sorted[uniq_mask], fp_sorted[uniq_mask]))

    rows = []

    for name, df in prop_data.items():
        # ensure numeric & drop garbage rows
        df = df.apply(pd.to_numeric, errors="coerce").dropna(how="any")

        # Convert to SI
        thrust_N   = df["THRUST"] * LBF_TO_N
        power_W    = df["POWER"]  * HP_TO_W
        torque_Nm  = df["TORQUE"] * INLBF_TO_NM
        rpm        = df["RPM"].to_numpy()
        Cp         = df["Cp"].to_numpy()      if "Cp"  in df.columns else df["Cp".upper()].to_numpy()
        Ct         = df["Ct"].to_numpy()      if "Ct"  in df.columns else df["Ct".upper()].to_numpy()
        FOM        = df["FOM"].to_numpy()     if "FOM" in df.columns else df["FOM".upper()].to_numpy()

        # Skip if prop cannot reach the required thrust
        if (np.nanmax(thrust_N) < required_thrust_N) or (np.nanmin(thrust_N) > target_thrust_N):
            continue

        # Efficiency array (avoid /0)
        #eff = np.divide(thrust_N, power_W, out=np.full_like(thrust_N, np.nan, dtype=float), where=power_W!=0)
        eff = thrust_N / power_W

        # Interpolate at required thrust
        rpm_req     = safe_interp(required_thrust_N, thrust_N, rpm)
        thrust_req  = required_thrust_N
        power_req   = safe_interp(required_thrust_N, thrust_N, power_W)
        torque_req  = safe_interp(required_thrust_N, thrust_N, torque_Nm)
        Cp_req      = safe_interp(required_thrust_N, thrust_N, Cp)
        Ct_req      = safe_interp(required_thrust_N, thrust_N, Ct)
        FOM_req     = safe_interp(required_thrust_N, thrust_N, FOM)
        eff_req     = safe_interp(required_thrust_N, thrust_N, eff)

        # Interpolate at target thrust
        rpm_tgt     = safe_interp(target_thrust_N, thrust_N, rpm)
        thrust_tgt  = target_thrust_N if (np.nanmin(thrust_N) <= target_thrust_N <= np.nanmax(thrust_N)) else np.nan
        power_tgt   = safe_interp(target_thrust_N, thrust_N, power_W)
        torque_tgt  = safe_interp(target_thrust_N, thrust_N, torque_Nm)
        Cp_tgt      = safe_interp(target_thrust_N, thrust_N, Cp)
        Ct_tgt      = safe_interp(target_thrust_N, thrust_N, Ct)
        FOM_tgt     = safe_interp(target_thrust_N, thrust_N, FOM)
        eff_tgt     = safe_interp(target_thrust_N, thrust_N, eff)

        rows.append({
            "Propeller": name,

            # Required thrust block
            f"RPM@{required_thrust_N:.0f}N":                 None if np.isnan(rpm_req)    else int(round(rpm_req)),
            f"Thrust@{required_thrust_N:.0f}N (N)":          round(thrust_req, 3),
            f"Power@{required_thrust_N:.0f}N (W)":           None if np.isnan(power_req)  else round(power_req, 3),
            f"Torque@{required_thrust_N:.0f}N (Nm)":         None if np.isnan(torque_req) else round(torque_req, 4),
            f"Cp@{required_thrust_N:.0f}N":                  None if np.isnan(Cp_req)     else round(Cp_req, 5),
            f"Ct@{required_thrust_N:.0f}N":                  None if np.isnan(Ct_req)     else round(Ct_req, 5),
            f"FOM@{required_thrust_N:.0f}N":                 None if np.isnan(FOM_req)    else round(FOM_req, 5),
            f"Eff@{required_thrust_N:.0f}N (N/W)":           None if np.isnan(eff_req)    else round(eff_req, 6),

            # Target thrust block
            f"RPM@{target_thrust_N:.0f}N":                   None if np.isnan(rpm_tgt)    else int(round(rpm_tgt)),
            f"Thrust@{target_thrust_N:.0f}N (N)":            None if np.isnan(thrust_tgt) else round(thrust_tgt, 3),
            f"Power@{target_thrust_N:.0f}N (W)":             None if np.isnan(power_tgt)  else round(power_tgt, 3),
            f"Torque@{target_thrust_N:.0f}N (Nm)":           None if np.isnan(torque_tgt) else round(torque_tgt, 4),
            f"Cp@{target_thrust_N:.0f}N":                    None if np.isnan(Cp_tgt)     else round(Cp_tgt, 5),
            f"Ct@{target_thrust_N:.0f}N":                    None if np.isnan(Ct_tgt)     else round(Ct_tgt, 5),
            f"FOM@{target_thrust_N:.0f}N":                   None if np.isnan(FOM_tgt)    else round(FOM_tgt, 5),
            f"Eff@{target_thrust_N:.0f}N (N/W)":             None if np.isnan(eff_tgt)    else round(eff_tgt, 6),
        })

    if not rows:
        print("⚠️ No propellers can reach the required thrust.")
        return pd.DataFrame()

    df_out = pd.DataFrame(rows)

    # Rank by lower Power at required thrust (i.e., better efficiency)
    df_out = df_out.sort_values(
        by=f"Power@{required_thrust_N:.0f}N (W)", ascending=True, na_position="last"
    ).reset_index(drop=True)

    # Export
    csv_path = f"{output_name}.csv"
    dat_path = f"{output_name}.dat"
    df_out.to_csv(csv_path, index=False)

    formatted = df_out.to_string(index=False, justify="right", float_format="{:10.4f}".format)
    with open(dat_path, "w") as f:
        f.write(f"# Interpolated propeller performance at {required_thrust_N:.0f} N (required) "
                f"and {target_thrust_N:.0f} N (target)\n")
        f.write("# SI units: Thrust=N, Power=W, Torque=Nm; Cp, Ct, FOM dimensionless; \n")
        f.write("# Sorted by Power at required thrust (ascending)\n")
        f.write("# ---------------------------------------------------------------------------\n\n")
        f.write(formatted)

    print(f"✅ {len(df_out)} propellers can reach {required_thrust_N:.1f} N.")
    print(f"Results exported to '{csv_path}' and '{dat_path}'.")
    return df_out

data = load_propeller_data("PER2_STATIC-2.dat")
analyze_propellers(data, 35, 14, "propeller_select")