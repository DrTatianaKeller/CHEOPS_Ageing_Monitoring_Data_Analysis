"""
Configuration for CHEOPS Ageing Monitoring Data Analysis

This file contains all configuration settings for the application.
To add new analysis types, parameters, or statistics, simply update the 
dictionaries below without modifying the core application code.
"""

# =============================================================================
# STATISTICS CONFIGURATION
# =============================================================================

# List of statistical metrics calculated for each parameter
# These are appended to parameter names (e.g., FLUX_mean, FLUX_median)
STATISTICS_METRICS = ['mean', 'median', 'sigma', 'mad', 
                      'min', 'max', 'ptp', 'p01', 'p99', 'skew', 'kurtosis']

# Human-readable descriptions for each statistic
# Displayed in the sidebar and as plot captions
STAT_DEFINITIONS = {
    'mean': "Average value",
    'median': "Middle value (less sensitive to outliers)",
    'sigma': "Standard deviation",
    'mad': "Median Absolute Deviation",
    'min': "Minimum value",
    'max': "Maximum value",
    'ptp': "Peak-to-peak range (max - min)",
    'p01': "1st percentile",
    'p99': "99th percentile",
    'skew': "Distribution asymmetry",
    'kurtosis': "Distribution tail heaviness"
}



# =============================================================================
# DATA SOURCES CONFIGURATION
# =============================================================================

# Defines where to find FITS files for each data type
# Each source specifies: directory, file pattern, extension to read, 
# time column for dates, and target header for target names
data_directory = '../DATA'
general_report_directory = f'{data_directory}/general_report'
DRP_lightcurve_directory = f'{data_directory}/lightcurve_data'
RPC_lightcurve_directory = f'{data_directory}/lightcurve_data'
PIPE_lightcurve_directory = f'{data_directory}/PIPE_lightcurve'
SCI_RAW_directory = f'{data_directory}/sci_raw_data'

# Path to targets.csv file containing target-to-directory mapping
TARGETS_CSV_PATH = f'{data_directory}/tables/targets.csv'


DATA_SOURCES = {
    'DRP_lightcurve': {
        'directory': DRP_lightcurve_directory,
        'pattern': '**/*R25_V*.fits',
        'exclude_pattern': 'R25_Fixed',
        'extension': 1,
        'time_column': 'UTC_TIME',
        'target_header': 'TARGNAME'
    },
    'RPC_lightcurve': {
        'directory': RPC_lightcurve_directory,
        'pattern': '**/*R25_V*.fits',
        'exclude_pattern': 'R25_Fixed',
        'extension': 1,
        'time_column': 'UTC_TIME',
        'target_header': 'TARGNAME'
    },
    'PIPE_lightcurve_sa': {
        'directory': PIPE_lightcurve_directory,
        'pattern': '**/*_sa.fits',
        'exclude_pattern': 'im.fits',
        'extension': 1,
        'time_column': 'MJD_TIME',
        'time_format': 'mjd',
        'target_header': 'TARGNAME'
    },
     'PIPE_lightcurve_im': {
        'directory': PIPE_lightcurve_directory,
        'pattern': '**/*_im.fits',
        'exclude_pattern': 'sa.fits',
        'extension': 1,
        'time_column': 'MJD_TIME',
        'time_format': 'mjd',
        'target_header': 'TARGNAME'
    },

    'sci_raw_metadata': {
        'directory': SCI_RAW_directory,
        'pattern': '**/*SCI_RAW_SubArray*.fits',
        'exclude_patterns': ['_centroid_stat', '_cont_data', '_ee90', '_general'],
        'extension_name': 'SCI_RAW_ImageMetadata',
        'time_column': 'UTC_TIME',
        'target_header': 'TARGNAME'
    },
    'centroid_subarray': {
        'directory': general_report_directory,
        'pattern': '**/*_centroids.fits',
        'exclude_patterns': ['_centroid_stat'],
        'extension': 1,
        'time_column': 'OBS_MJD',
        'time_format': 'mjd',
        'target_header': 'TARGNAME'
    },
    'cont_data': {
        'directory': general_report_directory,
        'pattern': '**/*_cont_data.fits',
        'extension': 1,
        'time_column': 'MJD_TIME',
        'time_format': 'mjd',
        'target_header': 'TARGNAME'
    },
    'ee90_data': {
        'directory': general_report_directory,
        'pattern': '**/*_ee90.fits',
        'extension': 1,
        'time_column': 'EE90_MJD',
        'time_format': 'mjd',
        'target_header': 'TARGNAME'
    },
    'general_report': {
        'directory': general_report_directory,
        'pattern': '**/*_general.fits',
        'extension': 1,
        'target_header': 'TARGNAME'
    }
}

# =============================================================================
# ANALYSIS TYPES CONFIGURATION
# =============================================================================

# Each analysis type defines:
# - source: which DATA_SOURCES entry to use for FITS files
# - calculate_stats: True = compute statistics, False = use raw values
# - parameters: grouped parameters to extract from FITS data
# - description: shown in the sidebar "About" section
ANALYSIS_TYPES = {
    'DRP Lightcurve': {
        'source': 'DRP_lightcurve',
        'calculate_stats': True,
        'parameters': {
            'FLUX': ['FLUX'],
            'BACKGROUND': ['BACKGROUND'],
            'CONTA_LC': ['CONTA_LC'],
            'SMEARING_LC': ['SMEARING_LC']
        },
        'description': 'Time-series RAW photometric data'
    },
     'RPC Lightcurve': {
        'source': 'RPC_lightcurve',
        'calculate_stats': True,
        'parameters': {
            'FLUX': ['FLUX'],
            'BACKGROUND': ['BACKGROUND'],
            'CONTA_LC': ['CONTA_LC'],
            'SMEARING_LC': ['SMEARING_LC']
        },
        'description': 'Time-series processed photometric data'
    },

    'PIPE Lightcurve (sa)': {
        'source': 'PIPE_lightcurve_sa',
        'calculate_stats': True,
        'parameters': {
            'FLUX': ['FLUX'],
            'FLUXERR': ['FLUXERR'],
            'Background': ['BG'],
            'Position': ['XC', 'YC'],
            'Roll': ['ROLL'],
            'thermFront_2': ['thermFront_2']
        },
        'description': 'PIPE lightcurve from SubArray data'
    },
      'PIPE Lightcurve (im)': {
        'source': 'PIPE_lightcurve_im',
        'calculate_stats': True,
        'parameters': {
            'FLUX': ['FLUX'],
            'FLUXERR': ['FLUXERR'],
            'Background': ['BG'],
            'Position': ['XC', 'YC'],
            'Roll': ['ROLL'],
            'thermFront_2': ['thermFront_2']
        },
        'description': 'PIPE lightcurve from Imagette data'
    },

    'Geometry': {
        'source': 'sci_raw_metadata',
        'calculate_stats': True,
        'parameters': {
            'Sun Angle': ['LOS_TO_SUN_ANGLE'],
            'Moon Angle': ['LOS_TO_MOON_ANGLE'],
            'Earth Angle': ['LOS_TO_EARTH_ANGLE']
        },
        'description': 'Geometric angles during observations'
    },
    'Voltages': {
        'source': 'sci_raw_metadata',
        'calculate_stats': True,
        'parameters': {
            'VOD': ['HK_VOLT_FEE_VOD'],
            'VRD': ['HK_VOLT_FEE_VRD'],
            'VOG': ['HK_VOLT_FEE_VOG'],
            'VSS': ['HK_VOLT_FEE_VSS']
        },
        'description': 'CCD voltage readings'
    },
    'Temperatures': {
        'source': 'sci_raw_metadata',
        'calculate_stats': True,
        'parameters': {
            'CCD Temp': ['HK_TEMP_FEE_CCD'],
            'ADC Temp': ['HK_TEMP_FEE_ADC'],
            'Bias Temp': ['HK_TEMP_FEE_BIAS']
        },
        'description': 'Temperature sensor readings'
    },
    'Thermistors': {
        'source': 'sci_raw_metadata',
        'calculate_stats': True,
        'parameters': {
            'Aft Thermistors': ['thermAft_1', 'thermAft_2', 'thermAft_3', 'thermAft_4'],
            'Front Thermistors': ['thermFront_1', 'thermFront_2', 'thermFront_3', 'thermFront_4']
        },
        'description': 'Thermistor readings'
    },
    'Centroids': {
        'source': 'centroid_subarray',
        'calculate_stats': True,
        'parameters': {
            'OBS': ['OBS_OFF_X', 'OBS_OFF_Y', 'OBS_LOC_X', 'OBS_LOC_Y'],
            'FSW_INFLIGHT': ['FSW_INFLIGHT_LOC_X', 'FSW_INFLIGHT_LOC_Y', 'FSW_INFLIGHT_X', 'FSW_INFLIGHT_Y'],
            'DRP': ['DRP_LOC_X', 'DRP_LOC_Y', 'DRP_X', 'DRP_Y'],
            'FSW_GROUND': ['FSW_GROUND_LOC_X', 'FSW_GROUND_LOC_Y', 'FSW_GROUND_X', 'FSW_GROUND_Y'],
            'IWCOG': ['IWCOG_LOC_X', 'IWCOG_LOC_Y', 'IWCOG_X', 'IWCOG_Y'],
            'EE90': ['EE90_LOC_X', 'EE90_LOC_Y', 'EE90_X', 'EE90_Y']
        },
        'description': 'Centroid positions by method'
    },
    'Background Level': {
        'source': 'cont_data',
        'calculate_stats': True,
        'parameters': {
            'Straylight BG': ['SL_BG', 'SL_MIN', 'SL_MAX']
        },
        'description': 'Straylight background levels'
    },
    'Background Variation': {
        'source': 'cont_data',
        'calculate_stats': True,
        'parameters': {
            'SAA Variance': ['SAA_VAR', 'SAA_MIN', 'SAA_MAX']
        },
        'description': 'South Atlantic Anomaly variance'
    },
    'Encircled Energy': {
        'source': 'ee90_data',
        'calculate_stats': True,
        'parameters': {
            'EE90': ['EE90']#,
            #'Apertures': ['AP1', 'AP2', 'AP3', 'AP4', 'AP5', 'AP6']
        },
        'description': '90% encircled energy measurements'
    },
    # PSF Shape uses calculate_stats: False to display raw values from FITS
    'PSF Shape': {
        'source': 'general_report',
        'calculate_stats': False,
        'parameters': {
            'Location': ['cntr', 'loc_x', 'loc_y'],
            'Sigma': ['sy_std', 'sx_std', 'sy_max', 'sx_max', 'sy_diff', 'sx_diff'],
            'Radius': ['ry_max', 'rx_max', 'ry_min', 'rx_min', 'ry_avr', 'rx_avr', 'ry_std', 'rx_std'],
            'Height': ['h_avr', 'h_std', 'h_max', 'h_min']
        },
        'description': 'PSF shape parameters (direct values)',
        'direct_columns': ['cntr', 'loc_x', 'loc_y', 'sy_std', 'sx_std', 'sy_max', 'sx_max', 
                          'sy_diff', 'sx_diff', 'ry_max', 'rx_max', 'ry_min', 'rx_min', 
                          'ry_avr', 'rx_avr', 'ry_std', 'rx_std', 'h_avr', 'h_std', 'h_max', 'h_min']
    }
}

