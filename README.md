# CHEOPS Ageing Monitoring Data Analysis

## Overview

Streamlit-based application for statistical analysis of CHEOPS ageing monitoring data.

The tool processes original FITS files directly and enables interactive exploration of long-term instrument behaviour, including photometric, thermal, electrical, and geometric parameters.

The application is modular and configuration-driven, allowing extension without modification of core logic.

---

## Scope

The software is designed for:

- monitoring long-term instrument stability  
- analysing detector and system ageing effects  
- exploring correlations between housekeeping and science parameters  
- supporting calibration and validation activities  

---

## Main Features

- Direct FITS file processing (no intermediate formats required)  
- Interactive data exploration via Streamlit  
- Configurable analysis types and parameter groups  
- Robust statistical analysis (including MAD-based filtering)  
- Time-series and correlation analysis  

---

## Repository Structure

CHEOPS_Ageing_Analysis/

├── app_v2.py  
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

pip install streamlit pandas numpy astropy scipy plotly  

---

## Execution

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

All analysis definitions are controlled via:

config.py  

This includes:

- analysis types  
- parameter groups  
- data paths  
- statistical metrics  

Example:

ANALYSIS_TYPES = { ... }

---

## Documentation

Detailed technical documentation is available in:

docs/technical_manual.md  

---

## Workflow

1. Add FITS data into DATA directory  
2. Update targets.csv  
3. Configure analysis in config.py  
4. Run application  

streamlit run app_v2.py --server.port 8502  

---

## Dependencies

python >= 3.10  
streamlit  
pandas  
numpy  
astropy  
scipy  
plotly  

---

## Environment Setup

conda env create -f environment.yml  
conda activate cheops_MC_APP  

---

## Notes

- Modular architecture  
- Configuration-driven design  
- Direct FITS processing  
- Extendable without modifying core logic  
- Suitable for reproducible scientific workflows  

---

## License

CHEOPS Instrumental Team  

---

## Author

Dr. Tatiana Keller
