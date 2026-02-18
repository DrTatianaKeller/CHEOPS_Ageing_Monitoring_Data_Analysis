"""
Plotting and utility functions for CHEOPS Ageing Monitoring Data Analysis

This module contains visualization functions for creating time-series plots
and dual-axis correlation plots, plus helper functions for data caching, data configurations
and statistics retrieval.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit as st
from config import STATISTICS_METRICS, STAT_DEFINITIONS, ANALYSIS_TYPES

from data_loader import load_data_for_analysis, load_psf_data

# =============================================================================
# CONFIGURATIONS HELPER FUNCTIONS
# =============================================================================

def get_all_parameters(analysis_type):
    """Get flat list of all parameter names for an analysis type."""
    if analysis_type not in ANALYSIS_TYPES:
        return []
    params = []
    for group_params in ANALYSIS_TYPES[analysis_type]['parameters'].values():
        params.extend(group_params)
    return params


def get_stat_columns(analysis_type):
    """
    Get dictionary of statistic column names grouped by parameter group.
    For calculate_stats=True: returns param_metric names (e.g., FLUX_mean)
    For calculate_stats=False: returns raw parameter names
    """
    if analysis_type not in ANALYSIS_TYPES:
        return {}
    
    config = ANALYSIS_TYPES[analysis_type]
    
    # For direct value analysis, just return the raw parameter names
    if not config.get('calculate_stats', True):
        return {group: params for group, params in config['parameters'].items()}
    
    # Build statistic column names for each parameter group
    stat_columns = {}
    for group_name, params in config['parameters'].items():
        stat_columns[group_name] = []
        for param in params:
            for metric in STATISTICS_METRICS:
                stat_columns[group_name].append(f'{param}_{metric}')
    return stat_columns


def get_stat_definition(stat_name):
    """Get definition for a statistic column name."""
    for key in STAT_DEFINITIONS:
        if stat_name.endswith(f'_{key}') or stat_name == key:
            return STAT_DEFINITIONS[key]
    return ""

 # ---- colored table (needs pandas Styler) ----
def color_checkmarks(val):
    if val == "✓":
        return "color: green; font-weight: bold;"
    if val == "✗":
        return "color: red; font-weight: bold;"
    return ""

# =============================================================================
# DATA CACHING
# =============================================================================

@st.cache_data
def get_cached_data(analysis_type, remove_outliers, sigma_threshold):
    """
    Load data with caching for the correlation analysis.
    """
    if analysis_type == 'PSF Shape':
        return load_psf_data()
    return load_data_for_analysis(analysis_type, remove_outliers, sigma_threshold, None)

# =============================================================================
# PLOT FORMATTING HELPERS
# =============================================================================

def get_year_separators(dates):
    """
    Create grey background rectangles for alternating years.
    These help visually separate data by year on the plots.
    Returns list of Plotly shape dictionaries.
    """
    min_year = dates.dt.year.min()
    max_year = dates.dt.year.max()
    shapes = []
    
    # Cover range including neighboring years for proper shading at edges
    for year in range(min_year - 1, max_year + 2):
        if year % 2 == 1:
            shapes.append(dict(
                type="rect",
                x0=datetime(year, 1, 1),
                x1=datetime(year + 1, 1, 1),
                y0=0, y1=1, yref="paper",
                fillcolor="rgba(200, 200, 200, 0.3)",
                line=dict(width=0),
                layer="below"
            ))
    return shapes


def get_year_ticks(dates):
    """
    Create tick marks for year labels on top x-axis.
    Places ticks at July 1 (center of each year band) for every year
    that contains data. Returns (tick positions, tick labels, x-axis range).
    The range always covers full years: Jan 1 of first year to Jan 1 after last year.
    """
    min_year = dates.dt.year.min()
    max_year = dates.dt.year.max()
    years = list(range(min_year, max_year + 1))
    
    # Position ticks at July 1 of each year (center of the Jan-Dec band)
    tickvals = [datetime(year, 7, 1) for year in years]
    ticktext = [str(year) for year in years]
    
    # Range covers exactly the years that have data
    x_range = [datetime(min_year, 1, 1), datetime(max_year + 1, 1, 1)]
    
    return tickvals, ticktext, x_range

# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================

def create_plot(df, column, mode, year_shapes, year_tickvals, year_ticktext, x_range):
    """
    Create a single time-series plot for one statistic.
    
    Parameters:
    - df: DataFrame with 'Date of visit' and the column to plot
    - column: Name of the column to plot
    - mode: Plotly line mode ('lines', 'markers', or 'lines+markers')
    - year_shapes: Grey rectangles for alternating years
    - year_tickvals, year_ticktext: Tick marks for year axis
    - x_range: [start, end] for the x-axis covering full years
    
    Returns: Plotly Figure object
    """
    fig = go.Figure()
    
    # Add main data trace
    fig.add_trace(go.Scatter(
        x=df['Date of visit'], y=df[column],
        mode=mode, name=column,
        line=dict(color='#1f77b4'),
        marker=dict(color='#1f77b4'),
        showlegend=False
    ))
    
    # Configure layout with dual x-axes
    fig.update_layout(
        title=dict(text=column, x=0.5, xanchor='center', font=dict(color='black', size=14)),
        # Bottom axis: quarterly month labels
        xaxis=dict(tickformat="%b", dtick="M3", showgrid=True, gridcolor='lightgray',
                   tickfont=dict(color='black'), range=x_range),
        # Top axis: year labels at July 1, centered in each year band
        xaxis2=dict(overlaying='x', side='top', tickvals=year_tickvals, ticktext=year_ticktext, 
                    tickfont=dict(size=11, color='black'), showgrid=False, range=x_range),
        yaxis=dict(title=dict(text=column, font=dict(color='black')), showgrid=True, 
                   gridcolor='lightgray', tickfont=dict(color='black')),
        height=350, margin=dict(l=60, r=20, t=60, b=40),
        shapes=year_shapes, plot_bgcolor='white', paper_bgcolor='white', showlegend=False
    )
    
    # Add invisible trace spanning full range to activate the top x-axis
    fig.add_trace(go.Scatter(x=[x_range[0], x_range[1]], y=[None, None], xaxis='x2', showlegend=False))
    
    return fig


def create_dual_axis_plot(left_dates, left_values, left_label, right_dates, right_values, right_label, target, mode, year_shapes, year_tickvals, year_ticktext, x_range):
    """
    Create a correlation plot with two y-axes.
    Allows comparing any two statistics from different analysis types.
    
    Parameters:
    - left_dates, left_values: Data for left y-axis (blue)
    - right_dates, right_values: Data for right y-axis (orange)
    - left_label, right_label: Axis titles
    - target: Target name for plot title
    - mode: Plotly line mode
    - year_shapes, year_tickvals, year_ticktext: Year formatting
    - x_range: [start, end] for the x-axis covering full years
    
    Returns: Plotly Figure object
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add traces for left (blue) and right (orange) axes
    fig.add_trace(go.Scatter(x=left_dates, y=left_values, mode=mode, name=left_label,
                              line=dict(color='#1f77b4'), marker=dict(color='#1f77b4')), secondary_y=False)
    fig.add_trace(go.Scatter(x=right_dates, y=right_values, mode=mode, name=right_label,
                              line=dict(color='#ff7f0e'), marker=dict(color='#ff7f0e')), secondary_y=True)
    
    # Configure layout
    fig.update_layout(
        title=dict(text=f"Correlation Analysis for {target}", x=0.5, xanchor='center', font=dict(color='black', size=16)),
        xaxis=dict(tickformat="%b", dtick="M3", showgrid=True, gridcolor='lightgray',
                   tickfont=dict(color='black'), range=x_range),
        xaxis2=dict(overlaying='x', side='top', tickvals=year_tickvals, ticktext=year_ticktext,
                    tickfont=dict(size=12, color='black'), showgrid=False, range=x_range),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1, font=dict(color='black')),
        shapes=year_shapes, plot_bgcolor='white', paper_bgcolor='white'
    )
    
    # Configure y-axes with matching colors
    fig.update_yaxes(title_text=left_label, secondary_y=False, title_font=dict(color='#1f77b4'),
                     tickfont=dict(color='black'), showgrid=True, gridcolor='lightgray')
    fig.update_yaxes(title_text=right_label, secondary_y=True, title_font=dict(color='#ff7f0e'),
                     tickfont=dict(color='black'), showgrid=False)
    
    # Add invisible trace spanning full range to activate top x-axis
    fig.add_trace(go.Scatter(x=[x_range[0], x_range[1]], y=[None, None], xaxis='x2', showlegend=False))
    
    return fig

# =============================================================================
# STATISTICS HELPERS
# =============================================================================

def get_available_stats(analysis_type, param_group=None):
    """
    Get list of available statistic columns for an analysis type.
    
    For regular analysis types: returns columns like 'FLUX_mean', 'FLUX_median'
    For PSF Shape (calculate_stats=False): returns direct column names
    
    Parameters:
    - analysis_type: Name of analysis from ANALYSIS_TYPES
    - param_group: Optional parameter group to filter by
    
    Returns: List of column names
    """
    config = ANALYSIS_TYPES.get(analysis_type, {})
    
    # For direct value analysis (PSF Shape), return the column names
    if not config.get('calculate_stats', True):
        return config.get('direct_columns', [])
    
    # Get statistic columns organized by group
    stat_columns = get_stat_columns(analysis_type)
    
    # Return just the requested group if specified
    if param_group and param_group in stat_columns:
        return stat_columns[param_group]
    
    # Otherwise return all statistics
    all_stats = []
    for cols in stat_columns.values():
        all_stats.extend(cols)
    return all_stats
