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

- DRP Lightcurve (lightcurve data) 
- RPC Lightcurve (reprocessed data from analysits) - this data need to be requested from Analysts
- PIPE Lightcurve (im) - PIPE processed data for imagette - this data need to be upload from PIPE
- PIPE Lightcurve (sa) - PIPE processed data for subarray - this data need to be upload from PIPE  
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

DRP Lightcurve:
- FLUX
- BACKGROUND
- CONTA_LC
- SMEARING_LC

RPC Lightcurve:
- FLUX
- BACKGROUND
- CONTA_LC
- SMEARING_LC

PIPE Lightcurve (im/sa)
- 'FLUX'
- 'FLUXERR'
- 'Background'
- 'XC'
- 'YC'
- 'ROLL'
- 'thermFront_2'


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

### 5.3 Combined Noise Plot (Lightcurve Only)

This option is available for lightcurve-based analysis types:

- DRP Lightcurve  
- RPC Lightcurve  
- PIPE Lightcurve (im / sa)  

The Combined Noise Plot provides a unified visualization of noise metrics for each parameter.

#### Functionality

For a selected parameter, the following metrics can be displayed simultaneously:

- sigma (unbinned noise)  
- bin_noise_1h  
- bin_noise_3h  
- bin_noise_6h  

Users can:

- select which noise levels to display  
- toggle logarithmic scaling on the Y-axis  

---

#### Purpose

The combined plot allows direct comparison between:

- raw noise (sigma)  
- noise after temporal averaging  

This helps to:

- assess noise reduction efficiency  
- detect correlated noise  
- evaluate instrument performance over time  

---

#### Interpretation

- If noise decreases with bin size → consistent with white noise  
- If noise remains constant or decreases slowly → indicates correlated noise  

---

#### Notes

- Only available for analysis types with lightcurve data  
- Requires computed binned noise metrics  
- Uses the same time axis as standard statistic plots  


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


### 8.1 Standard Metrics

The application computes the following statistical descriptors for each parameter:

- mean — average value  
- median — central value (robust to outliers)  
- sigma — standard deviation  
- MAD — median absolute deviation  
- min / max — extrema  
- ptp — peak-to-peak range  
- p01 / p99 — percentiles  
- skew — distribution asymmetry  
- kurtosis — distribution tail heaviness  

---

### 8.2 Binned Noise Estimation (Lightcurve Analysis)

#### Purpose

Binned noise metrics quantify how noise behaves when data are averaged over increasing time scales.

These metrics are particularly useful for:

- instrument stability assessment  
- detection of correlated noise  
- identification of time-dependent systematics  

---

#### Method

Given a time series:

xᵢ = x(tᵢ)

Time is converted to elapsed hours:

tᵢ(h) = (tᵢ − t₀) × 24

For a bin size Δt, the data are partitioned into time bins:

[t₀, t₀ + Δt), [t₀ + Δt, t₀ + 2Δt), ...

For each bin k, the mean value is computed:

x̄ₖ = mean(xᵢ in bin k)

The binned noise is defined as:

σ_bin = std(x̄ₖ)

---

#### Implemented Metrics

- bin_noise_1h — noise in 1-hour bins  
- bin_noise_3h — noise in 3-hour bins  
- bin_noise_6h — noise in 6-hour bins  

---

#### Interpretation

For uncorrelated (white) noise, the expected behaviour is:

σ_bin ∝ σ₀ / √N

Deviations from this relation indicate:

- correlated noise  
- instrumental systematics  
- astrophysical variability  

---

#### Requirements

Binned noise is computed only if:

- time information is available (e.g., `MJD_TIME` or `UTC_TIME`)  
- time and parameter arrays are aligned  
- at least two valid bins can be formed  

Otherwise, the result is set to NaN.

---

#### Limitations

- uneven sampling may bias bin statistics  
- large temporal gaps reduce the number of valid bins  
- short observations may not produce meaningful results  

---

#### Implementation Notes

- time is internally converted to relative hours  
- binning uses uniform intervals starting from the first observation  
- the final bin includes the right boundary  
- empty bins are ignored  

---

(!) These metrics are visualized in the Combined Noise Plot (see Section 5.3).

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
