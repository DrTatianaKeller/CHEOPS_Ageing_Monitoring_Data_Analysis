# Technical Manual
CHEOPS Ageing Monitoring Data Analysis

---

## 1. Introduction

This document provides detailed technical documentation for the CHEOPS Ageing Monitoring Analysis Application.

The application processes original FITS data products and provides statistical and visual analysis tools for instrument monitoring.

---

## 2. System Architecture

The application is composed of the following modules:

- app.py  
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

The selected target applies globally to all views.

---

#### Analysis Types

- DRP Lightcurve (lightcurve data)
- RPC Lightcurve (reprocessed data from analysts — must be requested from analysts)
- PIPE Lightcurve (im) — PIPE processed data for imagette (must be uploaded from PIPE)
- PIPE Lightcurve (sa) — PIPE processed data for subarray (must be uploaded from PIPE)
- Geometry (sci_raw)
- Voltages (sci_raw)
- Temperatures (sci_raw)
- Thermistors (sci_raw)
- Centroids (general_report/centroids)
- Image Background Level Straylight (general_report/cont_data)
- Image Background Variation SAA (general_report/cont_data)
- Encircled Energy (general_report/ee90)
- PSF Shape (general_report/general)

---

#### Aperture Radius Selection (Lightcurve Data)

For lightcurve-based analysis types the application allows the user to select
the **photometric aperture radius** used when loading the lightcurve data.

This control appears in the sidebar whenever the selected analysis type
corresponds to a lightcurve dataset.

The available range is defined in the configuration file (`config.py`).

Example:

```
radius_range = (15, 40)
default_radius = 25
```

The selected radius determines which FITS files are loaded.  
The application dynamically searches for files matching the pattern:

```
*R{radius}_V*.fits
```

For example:

```
CH_PR340001_TG000101_R25_V0300.fits
```

Changing the aperture radius therefore switches the dataset used for
the analysis.

---

#### Purpose

Allowing the aperture radius to be selected interactively enables users to:

- compare noise behaviour for different apertures
- investigate aperture-dependent systematics
- optimise the aperture choice for specific datasets

---

#### Notes

- This option is available **only for lightcurve analysis types**
- The selected radius affects both **statistics calculations** and **raw FITS data viewing**
- The default radius is defined in `config.py`

#### Parameter Groups

Each analysis type contains predefined parameter sets.

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

PIPE Lightcurve (im/sa):
- FLUX
- FLUXERR
- BG (Background)
- XC, YC (Position)

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
- thermAft_1, thermAft_2, thermAft_3, thermAft_4
- thermFront_1, thermFront_3, thermFront_4

Centroids:
- OBS, FSW_INFLIGHT, DRP, FSW_GROUND, IWCOG, EE90 coordinate sets

Image Background Level Straylight:
- SL_BG, SL_MIN, SL_MAX

Image Background Variation SAA:
- SAA_VAR, SAA_MIN, SAA_MAX

PSF Shape:
- location, sigma, radius, height

---

## 5. Navigation Views

The application provides five views accessible from the top navigation bar.

---

### 5.1 Statistic Plots

Time-series plots showing the evolution of each statistical metric for the
selected target and parameter groups.

- One plot per statistic per parameter
- Two-column layout with statistic definitions
- Year separators and quarterly tick marks
- Configurable plot type, dot size, marker symbol, outlier removal

---

### 5.2 Data

Contains three inner tabs:

**Statistics Table**

Displays computed statistics for a selected year and file.  
Selectors: Year → File.

**Raw FITS Data**

Displays raw rows loaded directly from the selected FITS file.  
Configurable maximum number of rows to display.

**Targets Table**

Shows all targets from `targets.csv` with data availability status
(✓ = available, ✗ = missing) for each data source.

---

### 5.3 Dual Parameter Evolution

Dual Y-axis time-series plot for comparing the evolution of two parameters
over time.

- Left Y-axis (Blue) and Right Y-axis (Orange) each configured independently
- Parameter selection from a flat list showing `PARAM [Analysis Type]`
- Independent statistic selection for each axis
- Target is taken from the global sidebar selection
- Supports all standard display options (plot type, dot size, log Y, outlier removal)

This view is designed for monitoring co-evolution and trends between
housekeeping and science parameters.

---

### 5.4 Combined Noise — Noise Evolution

Available only for lightcurve-based analysis types:

- DRP Lightcurve
- RPC Lightcurve
- PIPE Lightcurve (im / sa)

Displays noise evolution for the **FLUX** parameter over time.

#### Functionality

The following metrics can be displayed simultaneously:

- `sigma` — unbinned noise (standard deviation of the data)
- `scaled_noise_1h`
- `scaled_noise_3h`
- `scaled_noise_6h`
- `minerr_noise_1h`
- `minerr_noise_3h`
- `minerr_noise_6h`

The scaled and minimum-error noise metrics are computed using the  
`transit_noise` implementation from the **pycheops** package.

Users can:

- select which noise levels to display  
- toggle logarithmic scaling on the Y-axis  

The plot title displays: **Noise evolution for {Target}**

#### Purpose

The combined plot allows direct comparison between:

- raw scatter in the data (`sigma`)
- expected noise levels for transit-like signals
- noise behaviour across different temporal averaging windows

This helps to:

- evaluate photometric performance
- detect correlated noise
- monitor instrument stability over time

#### Notes

- Only available for analysis types with lightcurve data  
- Noise metrics are calculated only for the **FLUX** parameter  
- Requires valid time information and flux uncertainties (`FLUXERR`)  
- Uses the same time axis as the standard statistic plots  

---

### 5.5 Correlation

Provides 2D and can be uncomment (optional) 3D scatter plots for correlation analysis between any two
parameters across all analysis types.

#### Controls

- **Statistic** — single statistic applied to all selected parameters (e.g. mean)
- **X axis parameter** — flat list showing `PARAM [Analysis Type]`
- **Y axis parameters** — multiselect from the same flat list (multiple Y series supported)
- Target is taken from the global sidebar selection

#### 2D Scatter Plot

- Each point represents one matched observation (same date, same target)
- Colour-coded by Y series
- Hover shows X value, Y value, and date
- Supports log X and log Y axes, dot size, plot mode, marker symbol
- Legend always shown even with a single series
- Title: **Correlation plot for {Target}, {statistic}**

#### 3D Scatter Plot (optional)

Displayed below the 2D plot.

- X axis: same as 2D
- Y axis: same as 2D
- Z axis: **Year** (extracted from observation date)
- Allows visual identification of temporal trends in the correlation
- Interactive: rotatable and zoomable
- All axis labels and tick values displayed in black
- Title: **3D Correlation for {Target}, {statistic}**

---

### 5.6 Display Options (Sidebar)

- **Analysis Type** — selectbox for the active dataset
- **Aperture Radius** — slider (lightcurve types only)
- **Target** — dropdown from targets.csv
- **Date filter** — end-date selection
- **Parameter Groups** — checkboxes for parameter selection
- **Plot Type** — Line / Dots / Line + Dots
- **Dot size** — slider
- **Marker symbol** — selectbox
- **Remove Outliers** — checkbox with configurable sigma threshold
- **Logarithmic Y-axis** — checkbox
- **Logarithmic X-axis** — checkbox (Correlation view)

---

### 5.7 Outlier Removal

Outliers are filtered using MAD-based robust statistics:

robust_sigma = 1.4826 × MAD

Filtering boundaries:

lower = median − k × robust_sigma  
upper = median + k × robust_sigma  

---

## 6. Tables

### 6.1 Targets Table

Accessible under: **Data → Targets Table**

Source:

DATA/tables/targets.csv

Structure:

- Target
- OR_ID
- Year
- Data Available 

---

### 6.2 Statistics Table

Accessible under: **Data → Statistics Table**

Displays computed statistics for selected dataset.

Selectors: Year → File 

---

### 6.3 Raw FITS Data

Accessible under: **Data → Raw FITS Data**

Displays full parameter set from selected FITS file.

Configurable maximum row count (slider).

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

### 8.2 Transit Noise Estimation (Lightcurve Analysis)

For lightcurve-based datasets the application evaluates photometric noise using the  
`transit_noise` from the **pycheops** package.

The application relies on the established CHEOPS analysis methodology implemented in `pycheops`.

---

#### Implemented Noise Metrics

Two noise estimators are computed.

**Scaled Noise**

- `scaled_noise_1h`
- `scaled_noise_3h`
- `scaled_noise_6h`

**Minimum Error Noise**

- `minerr_noise_1h`
- `minerr_noise_3h`
- `minerr_noise_6h`

All values are expressed in **ppm**.

The metrics correspond to the expected noise level for transit-like signals
averaged over **1, 3, and 6 hour windows**.

---

#### Data Preparation

Before the noise calculation is performed, the data are normalized.

Flux normalization:

```
FLUX_norm = FLUX / median(FLUX)
```

Flux error normalization:

```
FLUXERR_norm = FLUXERR / median(FLUX)
```

Time values are converted to relative days:

```
t_rel = MJD − MJD₀
```

These normalized values are then passed to the `transit_noise` function.

---

#### Noise Calculation

Noise is evaluated using the following function from **pycheops**:

```
pycheops.instrument.transit_noise()
```

Two calculation modes are used:

- `scaled` — scaled transit noise estimate  
- `minerr` — minimum-error noise estimate

The calculation is performed separately for each temporal window:

- 1 hour  
- 3 hours  
- 6 hours  

---

#### When Noise Is Computed

Noise metrics are calculated **only for lightcurve datasets** and **only for the `FLUX` parameter**.

The calculation requires:

- valid time information (`MJD_TIME` or `UTC_TIME`)
- flux uncertainties (`FLUXERR`)
- aligned time and flux arrays

If any of these inputs are missing, the noise values are set to **NaN**.

---

**Minimum Error Noise**

Represents the theoretical lower limit assuming purely uncorrelated noise.

**Scaled Noise**

Includes the effect of correlated noise and systematic effects.

If the scaled noise is significantly larger than the minimum-error noise,
this typically indicates the presence of correlated noise in the lightcurve.

---

#### Implementation Notes

- time values are internally converted to **relative days**
- flux and flux errors are normalized by the median flux
- `pycheops` is imported only when the noise calculation is executed
- noise metrics are calculated only for the **FLUX parameter**

(!) These metrics are visualized in the Noise Evolution view (see Section 5.4).

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

```
conda env create -f environment.yml
conda activate cheops_MC_APP
```

---

## 12. Notes

- Fully modular design  
- No need to modify core logic  
- Suitable for long-term monitoring pipelines  

---
