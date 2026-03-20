"""
Data Loading for CHEOPS Ageing Monitoring Data Analysis

This module handles reading FITS files and extracting data for analysis.
It provides functions to load data, calculate statistics, and handle
different data sources defined in config.py.
"""

import pandas as pd
import numpy as np
import glob
import os
import re
from datetime import datetime
from astropy.io import fits
from astropy.time import Time
from scipy import stats
import streamlit as st
from functions import calculate_statistics
from config import ANALYSIS_TYPES, DATA_SOURCES, STATISTICS_METRICS, TARGETS_CSV_PATH, LIGHT_CURVE_SOURCES


# =============================================================================
# TARGETS TABLE
# =============================================================================

@st.cache_data
def load_targets_table():
    """
    Load the targets.csv file which maps OR IDs to target names.
    Returns DataFrame with columns: Target, OR ID, (Year, etc.)
    """
    try:
        df = pd.read_csv(TARGETS_CSV_PATH)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.warning(f"Could not load targets.csv: {e}")
        return pd.DataFrame()


def extract_tg_group(tg_str):
    """
    Extract the observation group number from a TG string.

    TG format: TG[4-digit group][optional 2-digit observation suffix].
    Only the first 4 digits are kept as the group identifier.
    """
    match = re.search(r'TG(\d+)', tg_str, re.IGNORECASE)
    if match:
        digits = match.group(1)
        if len(digits) <= 4:
            return int(digits)
        else:
            # Strip optional 2-digit suffix — keep only the group number
            return int(digits[:4])
    return None


def fuzzy_match_or_id(or_id1, or_id2):
    """
    Check whether two OR IDs refer to the same observation group.

    Handles variations in TG number formats (e.g. TG0001 vs TG000101).
    Strips trailing _V<number> version suffixes before comparing.
    """
    # Strip version suffix (e.g. _V1, _V23) and normalise case
    s1 = re.sub(r'_V\d+$', '', or_id1).lower().strip()
    s2 = re.sub(r'_V\d+$', '', or_id2).lower().strip()

    # Exact match after normalisation
    if s1 == s2:
        return True

    # Both must share the same PR (programme) number
    pr1_match = re.search(r'(pr\d+)', s1)
    pr2_match = re.search(r'(pr\d+)', s2)

    if pr1_match and pr2_match:
        pr1 = pr1_match.group(1)
        pr2 = pr2_match.group(1)

        if pr1 != pr2:
            return False  # Different programme — cannot be the same target

        # Compare TG group numbers (ignoring the optional observation suffix)
        tg1 = extract_tg_group(s1)
        tg2 = extract_tg_group(s2)

        if tg1 is not None and tg2 is not None and tg1 == tg2:
            return True

    return False


def get_target_from_or_id(or_id):
    """
    Look up target name from OR ID using targets.csv.
    Returns None if no match is found.
    """
    targets_df = load_targets_table()
    if targets_df.empty:
        return None

    # Strip version suffix for comparison
    clean_or_id = re.sub(r'_V\d+$', '', or_id)

    for _, row in targets_df.iterrows():
        csv_or_id = str(row['OR ID']).strip()
        if fuzzy_match_or_id(clean_or_id, csv_or_id):
            return row['Target']

    return None


def get_or_id_from_filepath(filepath):
    """
    Extract OR ID (e.g. PR100045_TG000101) from a FITS file path.
    Returns None if the pattern is not found.
    """
    path_parts = filepath.replace('\\', '/').split('/')
    for part in path_parts:
        match = re.search(r'(PR\d+_TG\d+)', part)
        if match:
            return match.group(1)
    return None


# =============================================================================
# TARGETS ACCESSIBILITY CHECK
# =============================================================================

@st.cache_data
def get_targets_accessibility_table():
    """
    Build a table showing all targets from targets.csv with file accessibility status.

    For each target (OR ID), checks whether FITS files exist in the three main
    data sources: DRP lightcurve, SCI_RAW metadata, and general report.
    Returns DataFrame with columns: Target, OR ID, Year, Lightcurves, SCI_RAW Data, General report.
    """
    targets_df = load_targets_table()
    if targets_df.empty:
        return pd.DataFrame()

    # Data source keys and display column names to check
    checks = [
        ("DRP_lightcurve",   "Lightcurves"),
        ("sci_raw_metadata", "SCI_RAW Data"),
        ("general_report",   "General report"),
    ]

    # Pre-index available OR IDs per source so the inner loop is fast
    available_or_ids_by_source = {}

    for source_key, col_name in checks:
        source_config = DATA_SOURCES.get(source_key, {})
        if not source_config:
            available_or_ids_by_source[source_key] = set()
            continue

        # Scan actual files on disk for this source
        available_files  = get_fits_files(source_config)
        available_or_ids = set()

        for filepath in available_files:
            or_id = get_or_id_from_filepath(filepath)
            if or_id:
                available_or_ids.add(or_id.lower())

        available_or_ids_by_source[source_key] = available_or_ids

    results = []
    for _, row in targets_df.iterrows():
        target   = row.get("Target", "")
        or_id    = str(row.get("OR ID", "")).strip()
        year     = row.get("Year", "")

        clean_or_id = re.sub(r"_V\d+$", "", or_id).lower()

        out_row = {
            "Target": target,
            "OR ID":  or_id,
            "Year":   year,
        }

        # Check each source — fuzzy-match against the indexed OR IDs
        for source_key, col_name in checks:
            has_data = False
            for avail_or_id in available_or_ids_by_source.get(source_key, set()):
                if fuzzy_match_or_id(clean_or_id, avail_or_id):
                    has_data = True
                    break
            out_row[col_name] = "✓" if has_data else "✗"

        results.append(out_row)

    return pd.DataFrame(results)


def style_accessibility_table(df):
    """Apply green/red colour styling to ✓/✗ cells in the accessibility table."""
    def color_checkmarks(val):
        if val == "✓":
            return "color: green; font-weight: bold;"
        if val == "✗":
            return "color: red; font-weight: bold;"
        return ""
    return df.style.applymap(color_checkmarks)


# =============================================================================
# OUTLIER REMOVAL
# =============================================================================

def remove_outliers_array(data, sigma_threshold=3.0):
    """
    Remove outliers from a data array using MAD-based robust sigma clipping.

    MAD (Median Absolute Deviation) is more robust than standard deviation for
    data with extreme outliers. The robust sigma estimate is: 1.4826 × MAD.

    Returns: (filtered_data, boolean_mask)
    """
    median       = np.nanmedian(data)
    mad          = np.median(np.abs(data - median))
    robust_sigma = 1.4826 * mad  # Scaling factor for Gaussian-equivalent sigma

    # If all values are identical, no outliers can be defined
    if robust_sigma == 0:
        return data, np.ones(len(data), dtype=bool)

    lower = median - sigma_threshold * robust_sigma
    upper = median + sigma_threshold * robust_sigma
    mask  = (data >= lower) & (data <= upper)
    return data[mask], mask


# =============================================================================
# FILE DISCOVERY
# =============================================================================

def get_fits_files(source_config, aperture_radius=None):
    """
    Discover FITS files matching the configured pattern for a data source.

    Searches both the base directory and one level of subdirectories.
    Applies exclude_pattern and exclude_patterns filters after discovery.
    The {radius} placeholder in the pattern is filled from aperture_radius
    or the source's default_radius.
    """
    directory = source_config['directory']
    pattern   = source_config['pattern']

    # Fill in aperture radius placeholder (only relevant for DRP / RPC lightcurves)
    if aperture_radius is not None:
        radius = str(aperture_radius)
    else:
        radius = str(source_config.get('default_radius', 25))
    pattern = pattern.replace('{radius}', radius)

    # Search base directory and one subdirectory level
    fits_files  = glob.glob(f"{directory}/{pattern}", recursive=True)
    fits_files += glob.glob(f"{directory}/**/{pattern}", recursive=True)
    fits_files  = list(set(fits_files))  # Remove duplicates from overlapping globs

    # Apply single exclude pattern (e.g. skip "Fixed" variants)
    exclude_pattern = source_config.get('exclude_pattern', '')
    if exclude_pattern:
        exclude_pattern = exclude_pattern.replace('{radius}', radius)
        fits_files = [f for f in fits_files if exclude_pattern not in f]

    # Apply list of additional exclude patterns
    if 'exclude_patterns' in source_config:
        for exclude in source_config['exclude_patterns']:
            fits_files = [f for f in fits_files if exclude not in f]

    return fits_files


# =============================================================================
# DATA EXTRACTION FROM FITS
# =============================================================================

def extract_visit_date(data, time_column, time_format='utc'):
    """
    Extract the observation date from a FITS data table.

    Handles both UTC string format ('YYYY-MM-DD...') and MJD numeric format.
    Returns a datetime.date object or None if extraction fails.
    """
    if time_column not in data.names:
        return None

    times = data[time_column]
    if len(times) == 0:
        return None

    first_time = times[0]

    if time_format == 'mjd':
        # Convert MJD float to calendar date
        visit_datetime = Time(first_time, format='mjd').datetime
        return datetime(visit_datetime.year, visit_datetime.month, visit_datetime.day)
    else:
        # Parse ISO date string — only the first 10 characters (YYYY-MM-DD) are needed
        if isinstance(first_time, (bytes, str)):
            if isinstance(first_time, bytes):
                date_str = first_time.decode('utf-8').strip()[:10]
            else:
                date_str = str(first_time)[:10]
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                return None
        return None


def extract_target_name(hdul, source_config, filepath=None):
    """
    Extract target name using targets.csv as the PRIMARY source.

    Tries to match the OR ID in the file path to a target in targets.csv.
    Falls back to reading the FITS header (TARGNAME or configured key)
    if the CSV look-up fails.
    """
    # Primary: look up OR ID from the file path in targets.csv
    if filepath:
        or_id = get_or_id_from_filepath(filepath)
        if or_id:
            target = get_target_from_or_id(or_id)
            if target:
                return target

    # Fallback: read target name from FITS header
    target_header = source_config.get('target_header', 'TARGNAME')
    for ext in hdul:
        if hasattr(ext, 'header') and target_header in ext.header:
            return ext.header[target_header]

    return 'Unknown'


def extract_info_from_filename(filename):
    """
    Extract target name and observation date from a FITS filename.

    Used when FITS header information is unavailable (e.g. PSF Shape files
    that do not have a standard TARGNAME header).

    Returns: (target_name, visit_date)
    """
    basename = os.path.basename(filename)

    # Target: look up in targets.csv via OR ID extracted from path
    or_id = get_or_id_from_filepath(filename)
    if or_id:
        target = get_target_from_or_id(or_id)
        if target:
            target_name = target
        else:
            # Fall back to TG number if CSV look-up fails
            target_match = re.search(r'TG(\d+)', basename)
            target_name  = f"TG{target_match.group(1)}" if target_match else "Unknown"
    else:
        target_match = re.search(r'TG(\d+)', basename)
        target_name  = f"TG{target_match.group(1)}" if target_match else "Unknown"

    # Date: extract 'TU<YYYY-MM-DD>' from filename (CHEOPS naming convention)
    date_match = re.search(r'TU(\d{4}-\d{2}-\d{2})', basename)
    if date_match:
        try:
            visit_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
        except:
            visit_date = datetime.now()
    else:
        visit_date = datetime.now()

    return target_name, visit_date


# =============================================================================
# MAIN DATA LOADING FUNCTIONS
# =============================================================================

@st.cache_data
def load_data_for_analysis(analysis_type, remove_outliers_flag=False, sigma_threshold=3.0,
                           selected_params=None, aperture_radius=None):
    """
    Load and process FITS data for the specified analysis type.

    For each FITS file found in the configured directory:
      1. Extract target name (from targets.csv or FITS header)
      2. Extract observation date (from time column)
      3. For each parameter: extract array, optionally remove outliers, calculate statistics
      4. For FLUX in lightcurve sources: also compute pycheops transit noise metrics

    Parameters:
    - analysis_type:        Name of analysis type (key in ANALYSIS_TYPES)
    - remove_outliers_flag: Whether to remove outliers before calculating stats
    - sigma_threshold:      Number of sigma for MAD-based outlier removal
    - selected_params:      List of parameter group names to load (None = all groups)
    - aperture_radius:      Aperture radius for DRP/RPC lightcurve data

    Returns: DataFrame with columns: Target, Date of visit, file, n_observations,
             and one column per statistic (e.g. FLUX_mean, FLUX_sigma, ...)
    """
    if analysis_type not in ANALYSIS_TYPES:
        return pd.DataFrame()

    analysis_config = ANALYSIS_TYPES[analysis_type]
    source_name     = analysis_config['source']
    source_config   = DATA_SOURCES[source_name]

    fits_files = get_fits_files(source_config, aperture_radius)
    if not fits_files:
        return pd.DataFrame()

    calculate_stats = analysis_config.get('calculate_stats', True)
    param_config    = analysis_config['parameters']

    # Restrict to selected parameter groups if specified
    if selected_params:
        param_config = {k: v for k, v in param_config.items() if k in selected_params}

    # Flatten parameter groups into a single list for column scanning
    all_params = []
    for group_params in param_config.values():
        all_params.extend(group_params)

    records = []

    for fits_file in fits_files:
        try:
            with fits.open(fits_file) as hdul:

                # -------------------------
                # Extract target name
                # -------------------------
                target_name = extract_target_name(hdul, source_config, fits_file)

                # If targets.csv look-up failed, try reading from FITS header directly
                if target_name == 'Unknown':
                    target_header = source_config.get('target_header', 'TARGNAME')
                    for ext in hdul:
                        if hasattr(ext, 'header') and target_header in ext.header:
                            target_name = ext.header[target_header]
                            break

                # -------------------------
                # Select FITS extension containing the data table
                # -------------------------
                if 'extension' in source_config:
                    # Access by integer index
                    data_ext = hdul[source_config['extension']]
                elif 'extension_name' in source_config:
                    # Access by extension name (partial match)
                    data_ext = None
                    for ext in hdul:
                        if source_config['extension_name'] in ext.name:
                            data_ext = ext
                            break
                    if data_ext is None:
                        continue
                else:
                    # Default: use the first binary table extension (index 1)
                    data_ext = hdul[1] if len(hdul) > 1 else None

                if data_ext is None or not hasattr(data_ext, 'data') or data_ext.data is None:
                    continue

                data = data_ext.data

                # -------------------------
                # Extract observation date
                # -------------------------
                time_column  = source_config.get('time_column', 'UTC_TIME')
                time_format  = source_config.get('time_format', 'utc')
                visit_date   = extract_visit_date(data, time_column, time_format)

                if visit_date is None:
                    continue

                record = {
                    'Target':         target_name,
                    'Date of visit':  visit_date,
                    'file':           os.path.basename(fits_file),
                    'n_observations': len(data)
                }

                # -------------------------
                # Extract time and flux error arrays for pycheops noise
                # Only relevant for lightcurve sources with a FLUX parameter
                # -------------------------
                lightcurve_sources = LIGHT_CURVE_SOURCES
                time_days      = None
                flux_err_array = None

                if calculate_stats and source_name in lightcurve_sources:
                    try:
                        # Prefer MJD_TIME column; fall back to UTC strings
                        if 'MJD_TIME' in data.names:
                            mjd       = data['MJD_TIME'].astype(float)
                            time_days = mjd - mjd[0]  # Relative time starting at 0
                        elif time_column in data.names and time_format == 'mjd':
                            mjd       = data[time_column].astype(float)
                            time_days = mjd - mjd[0]
                        elif 'UTC_TIME' in data.names:
                            # Convert UTC ISO strings to MJD then to relative days
                            from astropy.time import Time as AstropyTime
                            utc_strs = []
                            for t in data['UTC_TIME']:
                                if isinstance(t, bytes):
                                    utc_strs.append(t.decode('utf-8').strip())
                                else:
                                    utc_strs.append(str(t).strip())
                            try:
                                t_obj = AstropyTime(utc_strs, format='isot')
                            except Exception:
                                t_obj = AstropyTime(utc_strs, format='iso')
                            mjd       = t_obj.mjd
                            time_days = mjd - mjd[0]
                    except:
                        time_days = None

                    # Flux error is needed for the pycheops minerr noise calculation
                    if 'FLUXERR' in data.names:
                        try:
                            flux_err_array = data['FLUXERR'].astype(float)
                        except:
                            flux_err_array = None

                # -------------------------
                # Extract and process each parameter
                # -------------------------
                for param in all_params:
                    if param not in data.names:
                        continue

                    param_data = data[param]

                    # Convert to float — skip parameters that cannot be converted
                    try:
                        param_data = param_data.astype(float)
                    except:
                        continue

                    # Remove NaN values before statistics calculation
                    valid_mask = ~np.isnan(param_data)
                    valid_data = param_data[valid_mask]

                    if len(valid_data) == 0:
                        continue

                    # Keep time and error aligned with FLUX data points (same mask)
                    valid_time_days = None
                    valid_flux_err  = None
                    if param == 'FLUX' and time_days is not None and len(time_days) == len(param_data):
                        valid_time_days = time_days[valid_mask]
                        if flux_err_array is not None and len(flux_err_array) == len(param_data):
                            valid_flux_err = flux_err_array[valid_mask]

                    # Apply MAD-based outlier removal if requested
                    if remove_outliers_flag and calculate_stats:
                        valid_data, outlier_mask = remove_outliers_array(valid_data, sigma_threshold)
                        if valid_time_days is not None:
                            valid_time_days = valid_time_days[outlier_mask]
                        if valid_flux_err is not None:
                            valid_flux_err = valid_flux_err[outlier_mask]

                    if len(valid_data) == 0:
                        continue

                    if calculate_stats:
                        # Compute all statistics (including pycheops noise for FLUX)
                        param_stats = calculate_statistics(valid_data, param, valid_time_days, valid_flux_err)
                        record.update(param_stats)
                    else:
                        # Direct value storage (e.g. PSF Shape — no statistics computed)
                        record[param] = valid_data.tolist() if len(valid_data) > 1 else valid_data[0]

                records.append(record)

        except:
            # Skip files that cannot be opened or parsed (corrupted, wrong format, etc.)
            continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df = df.sort_values('Date of visit')

    return df


def load_raw_fits_data(analysis_type, filename, aperture_radius=None):
    """
    Load raw data rows from a specific FITS file for the Raw FITS Data viewer.

    Returns a DataFrame with one row per FITS table row, including a human-readable
    DateTime column and all configured parameter columns.
    Returns None if the file cannot be found or read.
    """
    if analysis_type not in ANALYSIS_TYPES:
        return None

    analysis_config = ANALYSIS_TYPES[analysis_type]
    source_name     = analysis_config['source']
    source_config   = DATA_SOURCES[source_name]

    # Find the file by matching the filename within the full path list
    fits_files     = get_fits_files(source_config, aperture_radius)
    matching_files = [f for f in fits_files if filename in f]

    if not matching_files:
        return None

    fits_file = matching_files[0]

    # Flatten all parameter groups
    all_params = []
    for group_params in analysis_config['parameters'].values():
        all_params.extend(group_params)

    try:
        with fits.open(fits_file) as hdul:

            # Select the correct FITS extension (same logic as load_data_for_analysis)
            if 'extension' in source_config:
                data_ext = hdul[source_config['extension']]
            elif 'extension_name' in source_config:
                data_ext = None
                for ext in hdul:
                    if source_config['extension_name'] in ext.name:
                        data_ext = ext
                        break
            else:
                data_ext = hdul[1] if len(hdul) > 1 else None

            if data_ext is None or not hasattr(data_ext, 'data') or data_ext.data is None:
                return None

            data = data_ext.data

            result      = {}
            time_column = source_config.get('time_column', 'UTC_TIME')
            time_format = source_config.get('time_format', 'utc')

            # Add a readable DateTime column as the first column
            if time_column in data.names:
                times = data[time_column]
                if time_format == 'mjd':
                    from astropy.time import Time as AstropyTime
                    # Convert MJD floats to ISO strings
                    datetime_values = [
                        AstropyTime(t, format='mjd').datetime.strftime('%Y-%m-%d %H:%M:%S')
                        for t in times
                    ]
                    result['DateTime'] = datetime_values
                else:
                    # Decode bytes or truncate long strings to 'YYYY-MM-DD HH:MM:SS'
                    result['DateTime'] = [
                        t.decode('utf-8').strip() if isinstance(t, bytes) else str(t)[:19]
                        for t in times
                    ]

            # Add each configured parameter column
            for param in all_params:
                if param in data.names:
                    try:
                        result[param] = data[param].astype(float)
                    except:
                        pass  # Skip parameters that cannot be cast to float

            if not result:
                return None

            return pd.DataFrame(result)

    except:
        return None


@st.cache_data
def load_psf_data():
    """
    Load PSF Shape data from general report FITS files.

    Unlike other analysis types, PSF Shape reads direct column values without
    aggregating statistics — each FITS row becomes a separate record.
    """
    source_config = DATA_SOURCES['general_report']
    fits_files    = get_fits_files(source_config)

    records    = []
    psf_columns = ANALYSIS_TYPES['PSF Shape'].get('direct_columns', [])

    for fits_file in fits_files:
        try:
            with fits.open(fits_file) as hdul:
                target_name = extract_target_name(hdul, source_config, fits_file)
                if target_name == 'Unknown':
                    target_name, _ = extract_info_from_filename(fits_file)

                # Use filename-based date for PSF Shape (headers may not have standard date fields)
                _, visit_date = extract_info_from_filename(fits_file)

                for ext in hdul:
                    if not hasattr(ext, 'data') or ext.data is None:
                        continue
                    if not hasattr(ext, 'columns'):
                        continue

                    data = ext.data

                    # Only process extensions that contain at least one PSF column
                    available_cols = [c for c in psf_columns if c in data.names]
                    if not available_cols:
                        continue

                    # One record per FITS table row
                    for i in range(len(data)):
                        record = {
                            'Target':        target_name,
                            'Date of visit': visit_date,
                            'file':          os.path.basename(fits_file),
                            'row_index':     i
                        }
                        for col in available_cols:
                            record[col] = data[col][i]
                        records.append(record)
                    break  # Stop after the first extension with PSF columns

        except:
            continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df = df.sort_values('Date of visit')

    return df
