# CHEOPS Ageing Monitoring Data Analysis

## Overview

This is a Streamlit application for analysing CHEOPS ageing monitoring data.

The app works directly with original FITS files and allows you to explore long-term behaviour of the instrument, including photometric, thermal, electrical, and geometric parameters.

The code is modular and configuration-based, so new parameters or analysis types can be added without changing the core logic.

---

## Scope

The app is used for:

- monitoring long-term instrument stability  
- studying detector ageing effects  
- checking correlations between parameters  
- supporting calibration work  

---

## Main Features

- Direct FITS processing (no intermediate files or calculations needed)  
- Interactive interface (Streamlitand Plotly)  
- Flexible analysis configuration  
- Statistical analysis with optional outlier removal  
- Time-series (evolution) plots  
- Correlation plot  
- Dual-parameter evolution (two Y-axes)  
- Combined pycheops noise view for lightcurves  

---

## Navigation Views

| View | Description |
|------|-------------|
| Statistic Plots | Time evolution of statistics per parameter |
| Data | Tables: statistics, raw FITS, targets |
| Dual Parameter Evolution | Compare two parameters over time |
| Combined Noise | Noise behaviour for lightcurves |
| Correlation | 2D and 3D (optional) correlation plots |

---

## Statistical Analysis

The app calculates standard statistics:

- mean  
- median  
- standard deviation  
- median absolute deviation (MAD)  
- percentiles  
- skewness  
- kurtosis  

---

### Aperture Radius (Lightcurves)

For lightcurve data you can choose the aperture radius.

This controls which FITS files are loaded.

Files are selected using:

*R{radius}_V*.fits

Example:

CH_PR340001_TG000101_R25_V0300.fits

This makes it easy to compare how aperture choice affects noise.

---

### Transit Noise (Lightcurves)

For lightcurve data the app calculates noise using **pycheops**.

Two types of noise are computed:

- scaled_noise_*  
- minerr_noise_*  

For:

- 1 hour  
- 3 hours  
- 6 hours  

Example:

scaled_noise_1h  
minerr_noise_1h  



Noise is computed only for:

- lightcurve data  
- FLUX parameter  

Requires:

- time (MJD_TIME or UTC_TIME)  
- flux error (FLUXERR)  

If missing → values are NaN.

---

## Repository Structure

CHEOPS_Ageing_Analysis/

├── app.py  
├── config.py  
├── data_loader.py  
├── functions.py  

├── DATA/  
│   ├── general_report/  
│   ├── lightcurve_data/  
│   ├── sci_raw_data/  
│   └── tables/  
│       └── targets.csv   # Must be updated with new visits!  

├── docs/  
│   └── technical_manual.md  

└── README.md  

---

## Installation

conda create -n cheops_MC_APP python=3.10  
conda activate cheops_MC_APP  
pip install streamlit pandas numpy astropy scipy plotly pycheops  

---

## Run the App

streamlit run app_v2.py --server.port 8502  

Access via:

http://localhost:8502   

---

## Data Requirements

The application requires:

- Updated `targets.csv` table containing visit metadata  
- FITS files located in the `DATA/` directory    

### targets.csv

This table is based on the CHEOPS Ageing Monitoring Google Sheet

Important:

- The user must update this table with new visits  
- The application depends on this file for data selection  

Required structure:

| Column        | Description              |
|---------------|--------------------------|
| Target        | Target name              |
| OR ID         | Observation request ID   |
| Date of visit | Observation date         |
| Year          | Observation year         |

---

## Configuration

All analysis settings are in:

config.py  

You can:

- add new analysis types  
- define parameters  
- change data paths  
- adjust statistics  

---

## Documentation

Detailed technical documentation is available in:

docs/technical_manual.md  

## Workflow

1. Add FITS files  
2. Update targets.csv  
3. Adjust config if needed  
4. Run app  

streamlit run app_v2.py --server.port 8502  
---

## Dependencies

- Python ≥ 3.10  
- streamlit  
- pandas  
- numpy  
- astropy  
- scipy  
- plotly  
- pycheops  

---
## Environment Setup
Option 1 conda:

conda env create -f environment.yml  
conda activate cheops_MC_APP  



Option 2 pip:

python3 -m venv cheops_MC_APP
source cheops_MC_APP/bin/activate
pip install -r requirements.txt

## Notes

- Modular design  
- Direct FITS processing  
- No need to change core code  
- Suitable for long-term monitoring  

---

## License

CHEOPS Instrumental Team  

---

## Author

Dr. Tatiana Keller