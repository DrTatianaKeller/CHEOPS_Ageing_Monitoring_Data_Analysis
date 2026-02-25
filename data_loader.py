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
from config import ANALYSIS_TYPES, DATA_SOURCES, STATISTICS_METRICS,TARGETS_CSV_PATH, LIGHT_CURVE_SOURCES

# =============================================================================
# TARGETS TABLE
# =============================================================================

@st.cache_data
def load_targets_table():
    """
    Load the targets.csv file which maps OR IDs to target names. 
    This table made from original CHEOPS Ageing Monitoring gogle sheet
    Returns DataFrame with columns: Target, OR ID, Date of visit, Year
    """
    try:
        df = pd.read_csv(TARGETS_CSV_PATH)
        # Clean up column names
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.warning(f"Could not load targets.csv: {e}")
        return pd.DataFrame()


def extract_tg_group(tg_str):
    """
    Extract the target group number from a TG string.
    TG format: TG[4-digit group][2-digit observation optional]
    Examples:
      TG0001 -> 1 (group 1)
      TG000101 -> 1 (group 1, observation 01)
      TG001001 -> 10 (group 10, observation 01)
      TG001802 -> 18 (group 18, observation 02)
    """
    match = re.search(r'TG(\d+)', tg_str, re.IGNORECASE)
    if match:
        digits = match.group(1)
        # Target group is in first 4 digits (or fewer if short format)
        # TG0001 = group 1, TG000101 = group 1 obs 01, TG001001 = group 10 obs 01
        if len(digits) <= 4:
            # Short format: TG0001 means group 1
            return int(digits)
        else:
            # Long format: first 4 digits are the group
            return int(digits[:4])
    return None

## Attention: this is temporal solution, needs to be improved in the future!
def fuzzy_match_or_id(or_id1, or_id2):
    """
    Check if two OR IDs match.
    Handles variations in TG number formats (TG0001 vs TG000101).
    TG0001 matches TG000101 (same group 1) but NOT TG001001 (group 10).
    """
    # Normalize: lowercase and remove version suffix
    s1 = re.sub(r'_V\d+$', '', or_id1).lower().strip()
    s2 = re.sub(r'_V\d+$', '', or_id2).lower().strip()
    
    # Exact match (case-insensitive)
    if s1 == s2:
        return True
    
    # Extract PR number and TG group separately
    pr1_match = re.search(r'(pr\d+)', s1)
    pr2_match = re.search(r'(pr\d+)', s2)
    
    if pr1_match and pr2_match:
        pr1 = pr1_match.group(1)
        pr2 = pr2_match.group(1)
        
        # PR numbers must match exactly
        if pr1 != pr2:
            return False
        
        # Compare TG group numbers
        tg1 = extract_tg_group(s1)
        tg2 = extract_tg_group(s2)
        
        # TG groups must match exactly
        if tg1 is not None and tg2 is not None and tg1 == tg2:
            return True
    
    return False


def get_target_from_or_id(or_id):
    """
    Look up target name from OR ID using targets.csv.
    OR ID format: PR300005_TG000101 (matches directory names without _V0300 suffix)
    Uses fuzzy matching: ignores case and allows 1 character difference.
    """
    targets_df = load_targets_table()
    if targets_df.empty:
        return None
    
    # Clean the or_id by removing version suffix
    clean_or_id = re.sub(r'_V\d+$', '', or_id)
    
    # Try fuzzy match against all OR IDs in the table
    for _, row in targets_df.iterrows():
        csv_or_id = str(row['OR ID']).strip()
        if fuzzy_match_or_id(clean_or_id, csv_or_id):
            return row['Target']
    
    return None


def get_or_id_from_filepath(filepath):
    """
    Extract OR ID from a FITS file path.
    Example: .../PR300005_TG000101_V0300/file.fits -> PR300005_TG000101
    """
    # Extract directory name containing OR ID pattern
    path_parts = filepath.replace('\\', '/').split('/')
    for part in path_parts:
        # Match pattern like PR300005_TG000101 or PR300005_TG000101_V0300
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
    Create a table showing all targets from targets.csv with file accessibility status
    for multiple sources defined in DATA_SOURCES.

    Columns:
      Target | OR ID | Year | Lightcurves | SCI_RAW Data | General report
    """
    targets_df = load_targets_table()
    if targets_df.empty:
        return pd.DataFrame()

    # Which sources to check and how to name the output columns
    checks = [
        ("lightcurve", "Lightcurves"),
        ("sci_raw_metadata", "SCI_RAW Data"),
        ("general_report", "General report"),
    ]

    # Precompute available OR-IDs for each source
    available_or_ids_by_source = {}

    for source_key, col_name in checks:
        source_config = DATA_SOURCES.get(source_key, {})
        if not source_config:
            available_or_ids_by_source[source_key] = set()
            continue

        available_files = get_fits_files(source_config)
        available_or_ids = set()

        for filepath in available_files:
            or_id = get_or_id_from_filepath(filepath)  #  existing helper
            if or_id:
                available_or_ids.add(or_id.lower())

        available_or_ids_by_source[source_key] = available_or_ids

    # Build accessibility table
    results = []
    for _, row in targets_df.iterrows():
        target = row.get("Target", "")
        or_id = str(row.get("OR ID", "")).strip()
        year = row.get("Year", "")

        # Normalize OR-ID from CSV (remove version suffix like _V0300 if present)
        clean_or_id = re.sub(r"_V\d+$", "", or_id).lower()

        out_row = {
            "Target": target,
            "OR ID": or_id,
            "Year": year,
        }

        # Evaluate each requested source
        for source_key, col_name in checks:
            has_data = False
            for avail_or_id in available_or_ids_by_source.get(source_key, set()):
                if fuzzy_match_or_id(clean_or_id, avail_or_id):  # existing fuzzy matcher
                    has_data = True
                    break
            out_row[col_name] = "✓" if has_data else "✗"

        results.append(out_row)

    return pd.DataFrame(results)

def style_accessibility_table(df):
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
    Remove outliers from data using MAD-based robust sigma.
    Points beyond sigma_threshold * robust_sigma from median are removed.
    Returns cleaned data and boolean mask of kept values.
    """
    median = np.nanmedian(data)
    mad = np.median(np.abs(data - median))
    robust_sigma = 1.4826 * mad  # Scale factor for normal distribution
    
    if robust_sigma == 0:
        return data, np.ones(len(data), dtype=bool)
    
    lower = median - sigma_threshold * robust_sigma
    upper = median + sigma_threshold * robust_sigma
    mask = (data >= lower) & (data <= upper)
    return data[mask], mask



# =============================================================================
# FILE DISCOVERY
# =============================================================================

def get_fits_files(source_config):
    """
    Find all FITS files matching the source configuration.
    Applies include/exclude patterns defined in DATA_SOURCES.
    """
    directory = source_config['directory']
    pattern = source_config['pattern']
    
    # Search for files matching pattern
    fits_files = glob.glob(f"{directory}/{pattern}", recursive=True)
    fits_files += glob.glob(f"{directory}/**/{pattern}", recursive=True)
    fits_files = list(set(fits_files))  # Remove duplicates
    
    # Apply exclusion patterns
    if 'exclude_pattern' in source_config:
        fits_files = [f for f in fits_files if source_config['exclude_pattern'] not in f]
    
    if 'exclude_patterns' in source_config:
        for exclude in source_config['exclude_patterns']:
            fits_files = [f for f in fits_files if exclude not in f]
    
    return fits_files

# =============================================================================
# DATA EXTRACTION FROM FITS
# =============================================================================

def extract_visit_date(data, time_column, time_format='utc'):
    """
    Extract observation date from FITS data table.
    Handles both UTC string format and MJD numeric format.
    """
    if time_column not in data.names:
        return None
    
    times = data[time_column]
    if len(times) == 0:
        return None
    
    first_time = times[0]
    
    # Convert MJD (Modified Julian Date) to datetime
    if time_format == 'mjd':
        visit_datetime = Time(first_time, format='mjd').datetime
        return datetime(visit_datetime.year, visit_datetime.month, visit_datetime.day)
    else:
        # Parse UTC string format (YYYY-MM-DD...)
        if isinstance(first_time, (bytes, str)):
            date_str = str(first_time)[:10]
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                return None
        return None


def extract_target_name(hdul, source_config, filepath=None):
    """
    Extract target name using targets.csv as PRIMARY source.
    Falls back to FITS header if not found in CSV.
    
    Priority:
    1. Look up OR ID from filepath in targets.csv
    2. Fall back to FITS header TARGNAME
    """
    # First try: Look up target from OR ID in targets.csv
    if filepath:
        or_id = get_or_id_from_filepath(filepath)
        if or_id:
            target = get_target_from_or_id(or_id)
            if target:
                return target
    
    # Fall back: Extract from FITS header
    target_header = source_config.get('target_header', 'TARGNAME')
    for ext in hdul:
        if hasattr(ext, 'header') and target_header in ext.header:
            return ext.header[target_header]
    return 'Unknown'


def extract_info_from_filename(filename):
    """
    Extract target and date from filename when FITS headers are unavailable.
    Uses targets.csv for target lookup, falls back to TG number from filename.
    Expected format: ...TG<number>...TU<YYYY-MM-DD>...
    """
    basename = os.path.basename(filename)
    
    # First try: Look up target from OR ID in targets.csv
    or_id = get_or_id_from_filepath(filename)
    if or_id:
        target = get_target_from_or_id(or_id)
        if target:
            target_name = target
        else:
            # Fall back to TG number from filename
            target_match = re.search(r'TG(\d+)', basename)
            target_name = f"TG{target_match.group(1)}" if target_match else "Unknown"
    else:
        # Fall back to TG number from filename
        target_match = re.search(r'TG(\d+)', basename)
        target_name = f"TG{target_match.group(1)}" if target_match else "Unknown"
    
    # Extract date (e.g., TU2024-01-15)
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
def load_data_for_analysis(analysis_type, remove_outliers_flag=False, sigma_threshold=3.0, selected_params=None):
    """
    Load and process FITS data for the specified analysis type.
    
    Parameters:
    - analysis_type: Name of analysis (from ANALYSIS_TYPES keys)
    - remove_outliers_flag: Whether to remove outliers before calculating stats
    - sigma_threshold: Number of sigma for outlier removal
    - selected_params: List of parameter groups to load (None = all)
    
    Returns: DataFrame with Target, Date of visit, and statistic columns
    """
    if analysis_type not in ANALYSIS_TYPES:
        return pd.DataFrame()
    
    analysis_config = ANALYSIS_TYPES[analysis_type]
    source_name = analysis_config['source']
    source_config = DATA_SOURCES[source_name]
    
    # Find all matching FITS files
    fits_files = get_fits_files(source_config)
    if not fits_files:
        return pd.DataFrame()
    
    calculate_stats = analysis_config.get('calculate_stats', True)
    param_config = analysis_config['parameters']
    
    # Filter to selected parameter groups if specified
    if selected_params:
        param_config = {k: v for k, v in param_config.items() if k in selected_params}
    
    # Build flat list of all parameters to extract
    all_params = []
    for group_params in param_config.values():
        all_params.extend(group_params)
    
    records = []
    
    # Process each FITS file
    for fits_file in fits_files:
        try:
            with fits.open(fits_file) as hdul:
                target_name = extract_target_name(hdul, source_config, fits_file)
                
                # If target not found in targets.csv, fall back to TARGNAME in FITS header
                if target_name == 'Unknown':
                    target_header = source_config.get('target_header', 'TARGNAME')
                    for ext in hdul:
                        if hasattr(ext, 'header') and target_header in ext.header:
                            target_name = ext.header[target_header]
                            break
                
                # Find the correct data extension
                if 'extension' in source_config:
                    data_ext = hdul[source_config['extension']]
                elif 'extension_name' in source_config:
                    data_ext = None
                    for ext in hdul:
                        if source_config['extension_name'] in ext.name:
                            data_ext = ext
                            break
                    if data_ext is None:
                        continue
                else:
                    data_ext = hdul[1] if len(hdul) > 1 else None
                
                if data_ext is None or not hasattr(data_ext, 'data') or data_ext.data is None:
                    continue
                
                data = data_ext.data
                
                # Extract visit date
                time_column = source_config.get('time_column', 'UTC_TIME')
                time_format = source_config.get('time_format', 'utc')
                visit_date = extract_visit_date(data, time_column, time_format)
                
                if visit_date is None:
                    continue
                
                # Start building record for this file
                record = {
                    'Target': target_name,
                    'Date of visit': visit_date,
                    'file': os.path.basename(fits_file),
                    'n_observations': len(data)
                }

                # Extract time array in hours for binned noise calculation
                # Only for lightcurve analysis types
                times_hours = None
                if calculate_stats and source_name in LIGHT_CURVE_SOURCES:
                    try:
                        if 'MJD_TIME' in data.names:
                            mjd = data['MJD_TIME'].astype(float)
                            times_hours = (mjd - mjd[0]) * 24.0
                        elif time_column in data.names and time_format == 'mjd':
                            mjd = data[time_column].astype(float)
                            times_hours = (mjd - mjd[0]) * 24.0
                        elif 'UTC_TIME' in data.names:
                            utc_strs = [str(t) for t in data['UTC_TIME']]
                            t_obj = Time(utc_strs, format='isot')
                            mjd = t_obj.mjd
                            times_hours = (mjd - mjd[0]) * 24.0
                    except:
                        times_hours = None
                
                # Process each parameter
                for param in all_params:
                    if param not in data.names:
                        continue
                    
                    param_data = data[param]
                    
                    # Convert to float, skip if not possible
                    try:
                        param_data = param_data.astype(float)
                    except:
                        continue
                    
                    # Remove NaN values
                    valid_mask = ~np.isnan(param_data)
                    valid_data = param_data[valid_mask]
                    
                    if len(valid_data) == 0:
                        continue

                     # Get matching time array for valid (non-NaN) data points
                    valid_times = None
                    if times_hours is not None and len(times_hours) == len(param_data):
                        valid_times = times_hours[valid_mask]

                    # Optionally remove outliers
                    if remove_outliers_flag and calculate_stats:
                        valid_data, outlier_mask = remove_outliers_array(valid_data, sigma_threshold)
                        if valid_times is not None:
                            valid_times = valid_times[outlier_mask]
                    
                    if len(valid_data) == 0:
                        continue
                    
                    # Calculate statistics or store raw values
                    if calculate_stats:
                        param_stats = calculate_statistics(valid_data, param, times_hours=valid_times)
                        record.update(param_stats)
                    else:
                        record[param] = valid_data.tolist() if len(valid_data) > 1 else valid_data[0]
                
                records.append(record)
                
        except:
            continue
    
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    df = df.sort_values('Date of visit')
    
    return df


def load_raw_fits_data(analysis_type, filename):
    """
    Load raw data from a specific FITS file for viewing.
    Returns DataFrame with all parameter values used for statistics.
    """
    if analysis_type not in ANALYSIS_TYPES:
        return None
    
    analysis_config = ANALYSIS_TYPES[analysis_type]
    source_name = analysis_config['source']
    source_config = DATA_SOURCES[source_name]
    
    # Find the file
    fits_files = get_fits_files(source_config)
    matching_files = [f for f in fits_files if filename in f]
    
    if not matching_files:
        return None
    
    fits_file = matching_files[0]
    
    # Get parameters to extract
    all_params = []
    for group_params in analysis_config['parameters'].values():
        all_params.extend(group_params)
    
    try:
        with fits.open(fits_file) as hdul:
            # Find data extension
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
            
            # Extract time column first
            result = {}
            time_column = source_config.get('time_column', 'UTC_TIME')
            time_format = source_config.get('time_format', 'utc')
            
            if time_column in data.names:
                times = data[time_column]
                if time_format == 'mjd':
                    # Convert MJD to datetime strings
                    from astropy.time import Time as AstropyTime
                    datetime_values = [AstropyTime(t, format='mjd').datetime.strftime('%Y-%m-%d %H:%M:%S') for t in times]
                    result['DateTime'] = datetime_values
                else:
                    # UTC string format
                    result['DateTime'] = [str(t)[:19] if isinstance(t, (bytes, str)) else str(t) for t in times]
            
            # Extract available parameters
            for param in all_params:
                if param in data.names:
                    try:
                        result[param] = data[param].astype(float)
                    except:
                        pass
            
            if not result:
                return None
            
            return pd.DataFrame(result)
    except:
        return None


@st.cache_data
def load_psf_data():
    """
    Load PSF Shape data from general report FITS files.
    
    PSF data is handled specially because:
    - No statistics are calculated (raw values are displayed)
    - Target/date may need to be extracted from filename
    - Multiple rows per file (one per measurement)
    """
    source_config = DATA_SOURCES['general_report']
    fits_files = get_fits_files(source_config)
    
    records = []
    psf_columns = ANALYSIS_TYPES['PSF Shape'].get('direct_columns', [])
    
    for fits_file in fits_files:
        try:
            with fits.open(fits_file) as hdul:
                # Try to get target from targets.csv, fall back to header/filename
                target_name = extract_target_name(hdul, source_config, fits_file)
                if target_name == 'Unknown':
                    target_name, _ = extract_info_from_filename(fits_file)
                
                # Always extract date from filename for PSF data
                _, visit_date = extract_info_from_filename(fits_file)
                
                # Find extension with PSF data
                for ext in hdul:
                    if not hasattr(ext, 'data') or ext.data is None:
                        continue
                    if not hasattr(ext, 'columns'):
                        continue
                    
                    data = ext.data
                    available_cols = [c for c in psf_columns if c in data.names]
                    
                    if not available_cols:
                        continue
                    
                    # Create one record per row in the table
                    for i in range(len(data)):
                        record = {
                            'Target': target_name,
                            'Date of visit': visit_date,
                            'file': os.path.basename(fits_file),
                            'row_index': i
                        }
                        for col in available_cols:
                            record[col] = data[col][i]
                        records.append(record)
                    break  # Only process first matching extension
                    
        except:
            continue
    
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    df = df.sort_values('Date of visit')
    
    return df

