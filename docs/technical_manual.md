# Technical Manual
CHEOPS Ageing Monitoring Data Analysis

---

## 1. Introduction

This document provides detailed technical documentation for the CHEOPS Ageing Monitoring Analysis Application.

The application processes original FITS data products and provides statistical and visual analysis tools for instrument monitoring.

---

## 2. System Architecture

The application is composed of the following modules:

- app_v2.py  
  Main Streamlit interface and application logic  

- config.py  
  Central configuration of analysis types, parameters, and data paths  

- data_loader.py  
  FITS file ingestion and data extraction  

- functions.py  
  Plotting and utility functions  

---

## 3. Data Flow

1. User selects target and analysis type  
2. FITS files are loaded dynamically  
3. Parameters are extracted  
4. Statistics are computed  
5. Results are visualized  

All processing is performed directly on FITS data.

---

## 4. Application Interface

### 4.1 Settings Panel

Located on the left side of the interface.

#### Target Selection

Selection of target based on `targets.csv`.

---

#### Analysis Types

- Lightcurve (lightcurve data)  
- Geometry (sci_raw)  
- Voltages (sci_raw)  
- Temperatures (sci_raw)  
- Thermistors (sci_raw)  
- Centroids (general_report/centroids)  
- Background Level (general_report/cont_data)  
- Background Variation (general_report/cont_data)  
- Encircled Energy (general_report/ee90)  
- PSF Shape (general_report/general)  

---

#### Parameter Groups

Each analysis type contains predefined parameter sets.

Example:

Lightcurve:
- FLUX
- BACKGROUND
- CONTA_LC
- SMEARING_LC

Geometry:
- LOS_TO_SUN_ANGLE
- LOS_TO_MOON_ANGLE
- LOS_TO_EARTH_ANGLE

Voltages:
- HK_VOLT_FEE_VOD
- HK_VOLT_FEE_VRD
- HK_VOLT_FEE_VOG
- HK_VOLT_FEE_VSS

Temperatures:
- HK_TEMP_FEE_CCD
- HK_TEMP_FEE_ADC
- HK_TEMP_FEE_BIAS

Thermistors:
- thermAft_*
- thermFront_*

Centroids:
- OBS, FSW, DRP, EE90 coordinate sets

Background:
- SL_BG, SAA_VAR

PSF Shape:
- location, sigma, radius, height

---

## 5. Display Options

- Time filtering (end date selection)
- Plot type selection:
  - line
  - dot
  - combined

---

### 5.1 Correlation Analysis

- Dual Y-axis visualization
- Flexible parameter selection:
  - analysis type
  - parameter
  - statistic

---

### 5.2 Outlier Removal

Outliers are filtered using MAD-based robust statistics:

robust_sigma = 1.4826 × MAD

Filtering boundaries:

lower = median − k × robust_sigma  
upper = median + k × robust_sigma  

---

## 6. Tables

### 6.1 Targets Table

Source:

DATA/tables/targets.csv

Structure:

- Target
- OR_ID
- Year
- Data Available

---

### 6.2 Statistics Table

Displays computed statistics for selected dataset.

---

### 6.3 Raw FITS Data

Displays full parameter set from selected FITS file.

---

## 7. Input Data

### 7.1 targets.csv

Derived from:

CHEOPS Ageing Monitoring Google Sheet

Users must update this table with new visits.

Required fields:

- Target
- OR ID
- Date of visit
- Year

---

### 7.2 FITS Files

All FITS files must be stored in the DATA directory.

Paths are defined in config.py.

---

## 8. Statistical Methods

Implemented metrics:

- mean
- median
- standard deviation (sigma)
- MAD
- min / max
- ptp
- percentiles (p01, p99)
- skewness
- kurtosis

---

## 9. Configuration

All configuration is centralized in:

config.py

Allows:
- adding new analysis types
- defining parameters
- modifying data paths
- adjusting statistics

---

## 10. Workflow

1. Update FITS data  
2. Update targets.csv  
3. Configure analysis  
4. Run application  

---

## 11. Environment

Recommended setup:

conda env create -f environment.yml  
conda activate cheops_MC_APP  

---

## 12. Notes

- Fully modular design  
- No need to modify core logic  
- Suitable for long-term monitoring pipelines  

---
