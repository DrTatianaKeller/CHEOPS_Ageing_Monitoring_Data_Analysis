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
from config import LIGHT_CURVE_SOURCES, STATISTICS_METRICS, STAT_DEFINITIONS, ANALYSIS_TYPES #,EPS_REL_threshold
import numpy as np
from scipy import stats

# =============================================================================
# CONFIGURATION HELPER FUNCTIONS
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

    For calculate_stats=True:  returns 'PARAM_metric' column names (e.g. FLUX_mean)
    For calculate_stats=False: returns raw parameter names (e.g. PSF Shape direct columns)
    """
    if analysis_type not in ANALYSIS_TYPES:
        return {}

    config = ANALYSIS_TYPES[analysis_type]

    # For direct-value analysis types (e.g. PSF Shape), return raw parameter names
    if not config.get('calculate_stats', True):
        return {group: params for group, params in config['parameters'].items()}

    lightcurve_sources = LIGHT_CURVE_SOURCES
    source             = config.get('source', '')
    is_lightcurve      = source in lightcurve_sources

    # Separate base metrics from pycheops noise metrics
    noise_prefixes = ('scaled_noise_', 'minerr_noise_')
    base_metrics   = [m for m in STATISTICS_METRICS if not m.startswith(noise_prefixes)]

    stat_columns = {}
    for group_name, params in config['parameters'].items():
        stat_columns[group_name] = []
        for param in params:
            # Add standard base statistics for every parameter
            for metric in base_metrics:
                stat_columns[group_name].append(f'{param}_{metric}')
            # Add pycheops noise metrics only for FLUX in lightcurve sources
            if is_lightcurve and param == 'FLUX':
                for metric in STATISTICS_METRICS:
                    if metric.startswith(noise_prefixes):
                        stat_columns[group_name].append(f'{param}_{metric}')
    return stat_columns


def get_stat_definition(stat_name):
    """Get definition for a statistic column name (e.g. 'FLUX_mean')."""
    for key in STAT_DEFINITIONS:
        if stat_name.endswith(f'_{key}') or stat_name == key:
            return STAT_DEFINITIONS[key]
    return ""


def color_checkmarks(val):
    """Pandas Styler callback — green for ✓, red for ✗, unchanged otherwise."""
    if val == "✓":
        return "color: green; font-weight: bold;"
    if val == "✗":
        return "color: red; font-weight: bold;"
    return ""


# =============================================================================
# DATA CACHING
# =============================================================================

@st.cache_data
def get_cached_data(analysis_type, remove_outliers, sigma_threshold, aperture_radius=None):
    """
    Load data with caching — used by the Correlation, Dual Parameter Evolution,
    and Data views to avoid reloading FITS files on every interaction.

    Handles PSF Shape specially (uses load_psf_data instead of the general loader).
    """
    from data_loader import load_data_for_analysis, load_psf_data

    # Use specialized loader for PSF Shape, general loader for all other types
    if analysis_type == 'PSF Shape':
        return load_psf_data()

    return load_data_for_analysis(
        analysis_type,
        remove_outliers_flag=remove_outliers,
        sigma_threshold=sigma_threshold,
        selected_params=None,
        aperture_radius=aperture_radius
    )


# =============================================================================
# MATPLOTLIB FORMAT STRING PARSER
# =============================================================================

def parse_mpl_format(fmt_str):
    """
    Parse a matplotlib-style format string into Plotly parameters.

    Supported line styles: - (solid), -- (dash), -. (dashdot), : (dot)
    Supported markers: o, s, ^, v, <, >, D, d, *, +, x, p, h, H, 8, P, X, 1, 2, 3, 4

    Returns: (mode, line_dash, marker_symbol)

    Examples:
      'o-'  → lines+markers, solid, circle
      '--'  → lines, dash, circle
      '^:'  → lines+markers, dot, triangle-up
      'o'   → markers only, solid, circle
    """
    # Marker character to Plotly symbol name
    marker_map = {
        'o': 'circle',       's': 'square',      '^': 'triangle-up',   'v': 'triangle-down',
        '<': 'triangle-left','>'  : 'triangle-right','D': 'diamond',    'd': 'diamond-thin',
        '*': 'star',         '+': 'cross',        'x': 'x',             'p': 'pentagon',
        'h': 'hexagon',      'H': 'hexagon2',     '8': 'octagon',       'P': 'cross-thin',
        'X': 'x-thin',       '1': 'y-down',       '2': 'y-up',          '3': 'y-left',
        '4': 'y-right'
    }
    # Line style string to Plotly dash name (checked in longest-first order)
    dash_map   = {'--': 'dash', '-.': 'dashdot', '-': 'solid', ':': 'dot'}
    #color_chars = set('rgbcmykw')  # Single-char colour codes 
    if not fmt_str or not fmt_str.strip():
        return 'lines+markers', 'solid', 'circle'

    remaining     = fmt_str.strip()
    has_line      = False
    line_dash     = 'solid'
    has_marker    = False
    marker_symbol = 'circle'

    # Match line style first (longest token wins to avoid '-' matching '--' early)
    for dash_str in ['--', '-.', '-', ':']:
        if dash_str in remaining:
            has_line   = True
            line_dash  = dash_map[dash_str]
            remaining  = remaining.replace(dash_str, '', 1)
            break

    # Match marker character from whatever remains
    for char in remaining:
        if char in marker_map:
            has_marker    = True
            marker_symbol = marker_map[char]
        # skip colour chars and unrecognised characters

    # Default to lines+markers if nothing was recognised
    if not has_line and not has_marker:
        return 'lines+markers', 'solid', 'circle'

    if has_line and has_marker:
        mode = 'lines+markers'
    elif has_line:
        mode = 'lines'
    else:
        mode = 'markers'

    return mode, line_dash, marker_symbol


# =============================================================================
# PLOT FORMATTING HELPERS
# =============================================================================

def get_year_separators(dates):
    """
    Create alternating grey background rectangles — one per odd year.
    These visually separate data by year across all time-series plots.
    Returns a list of Plotly shape dictionaries.
    """
    min_year = dates.dt.year.min()
    max_year = dates.dt.year.max()
    shapes = []

    # Extend one year beyond the data range so edge years are fully covered
    for year in range(min_year - 1, max_year + 2):
        if year % 2 == 1:
            shapes.append(dict(
                type="rect",
                x0=datetime(year,     1, 1),
                x1=datetime(year + 1, 1, 1),
                y0=0, y1=1, yref="paper",
                fillcolor="rgba(200, 200, 200, 0.3)",
                line=dict(width=0),
                layer="below"
            ))
    return shapes


def get_year_ticks(dates):
    """
    Create tick marks for year labels on the top x-axis.

    Ticks are placed at July 1 (centre of each year band) for every year
    that contains data. X-axis range always covers full years:
    Jan 1 of the first year to Jan 1 after the last year.

    Returns: (tick positions, tick labels, x-axis range)
    """
    min_year = dates.dt.year.min()
    max_year = dates.dt.year.max()
    years    = list(range(min_year, max_year + 1))

    # Place tick at the middle of each year band for clean year labelling
    tickvals = [datetime(year, 7, 1) for year in years]
    ticktext = [str(year) for year in years]

    # Range always starts and ends at year boundaries (not at data endpoints)
    x_range = [datetime(min_year, 1, 1), datetime(max_year + 1, 1, 1)]

    return tickvals, ticktext, x_range


# =============================================================================
# PLOTTING FUNCTIONS
# =============================================================================

def create_plot(df, column, mode, year_shapes, year_tickvals, year_ticktext, x_range,
                log_y=False, dot_size=6, line_dash='solid', marker_symbol='circle'):
    """
    Create a single time-series plot for one statistic column.

    The bottom x-axis shows month ticks (quarterly); the top x-axis shows year labels.
    Alternating grey bands from get_year_separators() are added as background shapes.
    """
    fig = go.Figure()

    # Main data trace
    fig.add_trace(go.Scatter(
        x=df['Date of visit'], y=df[column],
        mode=mode, name=column,
        line=dict(color='#1f77b4', dash=line_dash),
        marker=dict(color='#1f77b4', size=dot_size, symbol=marker_symbol),
        showlegend=False
    ))

    yaxis_type = 'log' if log_y else 'linear'

    fig.update_layout(
        title=dict(text=column, x=0.5, xanchor='center', font=dict(color='black', size=14)),
        # Bottom x-axis: monthly ticks, quarterly grid marks
        xaxis=dict(
            tickformat="%b", dtick="M3", showgrid=True, gridcolor='lightgray',
            tickfont=dict(color='black'), range=x_range
        ),
        # Top x-axis: year labels (centred in each year band via tickvals)
        xaxis2=dict(
            overlaying='x', side='top', tickvals=year_tickvals, ticktext=year_ticktext,
            tickfont=dict(size=11, color='black'), showgrid=False, range=x_range
        ),
        yaxis=dict(
            title=dict(text=column, font=dict(color='black')),
            showgrid=True, gridcolor='lightgray', tickfont=dict(color='black'),
            type=yaxis_type, exponentformat='none', minexponent=4
        ),
        height=350,
        margin=dict(l=60, r=20, t=60, b=40),
        shapes=year_shapes,
        plot_bgcolor='white', paper_bgcolor='white',
        showlegend=False
    )

    # Invisible dummy trace on xaxis2 forces Plotly to actually render the top axis
    fig.add_trace(go.Scatter(x=[x_range[0], x_range[1]], y=[None, None], xaxis='x2', showlegend=False))

    return fig


def create_dual_axis_plot(left_dates, left_values, left_label, right_dates, right_values, right_label,
                          target, mode, year_shapes, year_tickvals, year_ticktext, x_range,
                          log_y=False, dot_size=6, line_dash='solid', marker_symbol='circle'):
    """
    Create a dual Y-axis time-series plot for the Dual Parameter Evolution view.

    Left axis (blue) and right axis (orange) are independent — different scales,
    different parameters, same x-axis time range.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Left series (blue) on primary y-axis
    fig.add_trace(
        go.Scatter(x=left_dates, y=left_values, mode=mode, name=left_label,
                   line=dict(color='#1f77b4', dash=line_dash),
                   marker=dict(color='#1f77b4', size=dot_size, symbol=marker_symbol)),
        secondary_y=False
    )

    # Right series (orange) on secondary y-axis
    fig.add_trace(
        go.Scatter(x=right_dates, y=right_values, mode=mode, name=right_label,
                   line=dict(color='#ff7f0e', dash=line_dash),
                   marker=dict(color='#ff7f0e', size=dot_size, symbol=marker_symbol)),
        secondary_y=True
    )

    yaxis_type = 'log' if log_y else 'linear'

    fig.update_layout(
        title=dict(
            text=f"Dual Parameter Evolution for {target}",
            x=0.5, xanchor='center', font=dict(color='black', size=16)
        ),
        xaxis=dict(
            tickformat="%b", dtick="M3", showgrid=True, gridcolor='lightgray',
            tickfont=dict(color='black'), range=x_range
        ),
        xaxis2=dict(
            overlaying='x', side='top', tickvals=year_tickvals, ticktext=year_ticktext,
            tickfont=dict(size=12, color='black'), showgrid=False, range=x_range
        ),
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.08,
                    xanchor="right", x=1, font=dict(color='black')),
        shapes=year_shapes,
        plot_bgcolor='white', paper_bgcolor='white'
    )

    # Left y-axis label in blue to match the series colour
    fig.update_yaxes(
        title_text=left_label, secondary_y=False,
        title_font=dict(color='#1f77b4'), tickfont=dict(color='black'),
        showgrid=True, gridcolor='lightgray',
        type=yaxis_type, exponentformat='none', minexponent=4
    )

    # Right y-axis label in orange to match the series colour; no grid (avoids double grid)
    fig.update_yaxes(
        title_text=right_label, secondary_y=True,
        title_font=dict(color='#ff7f0e'), tickfont=dict(color='black'),
        showgrid=False,
        type=yaxis_type, exponentformat='none', minexponent=4
    )

    # Invisible dummy trace forces Plotly to render the top x-axis
    fig.add_trace(go.Scatter(x=[x_range[0], x_range[1]], y=[None, None], xaxis='x2', showlegend=False))

    return fig


def create_combined_noise_plot(df, param, mode, year_shapes, year_tickvals, year_ticktext, x_range,
                               selected_levels=None, log_y=False, dot_size=6,
                               line_dash='solid', marker_symbol='circle', target=''):
    """
    Create a combined noise-level plot for the FLUX parameter.

    Shows selected noise levels (sigma, scaled_1/3/6h, minerr_1/3/6h) on a single
    plot with a shared y-axis so they can be compared directly.
    The plot title always reads "Noise evolution for {target}".
    """
    if selected_levels is None:
        # Default: show all levels
        selected_levels = ['sigma', 'scaled_1h', 'scaled_3h', 'scaled_6h',
                           'minerr_1h', 'minerr_3h', 'minerr_6h']

    fig = go.Figure()

    # Map level keys to (column name, display label, colour)
    all_traces = {
        'sigma':     (f'{param}_sigma',             'sigma (unbinned)', '#d62728'),
        'scaled_1h': (f'{param}_scaled_noise_1h',   'Scaled 1h',        '#1f77b4'),
        'scaled_3h': (f'{param}_scaled_noise_3h',   'Scaled 3h',        '#ff7f0e'),
        'scaled_6h': (f'{param}_scaled_noise_6h',   'Scaled 6h',        '#2ca02c'),
        'minerr_1h': (f'{param}_minerr_noise_1h',   'MinErr 1h',        '#9467bd'),
        'minerr_3h': (f'{param}_minerr_noise_3h',   'MinErr 3h',        '#8c564b'),
        'minerr_6h': (f'{param}_minerr_noise_6h',   'MinErr 6h',        '#e377c2'),
    }

    # Add one trace per selected noise level (skip if column absent in data)
    for level in selected_levels:
        if level not in all_traces:
            continue
        col, name, color = all_traces[level]
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df['Date of visit'], y=df[col],
                mode=mode, name=name,
                line=dict(color=color, dash=line_dash),
                marker=dict(color=color, size=dot_size, symbol=marker_symbol)
            ))

    # Plot title always shows target name
    title_text = f"Noise evolution for {target}" if target else f"{param} — Noise"

    yaxis_type = 'log' if log_y else 'linear'

    fig.update_layout(
        title=dict(text=title_text, x=0.5, xanchor='center', font=dict(color='black', size=14)),
        xaxis=dict(
            tickformat="%b", dtick="M3", showgrid=True, gridcolor='lightgray',
            tickfont=dict(color='black'), range=x_range
        ),
        xaxis2=dict(
            overlaying='x', side='top', tickvals=year_tickvals, ticktext=year_ticktext,
            tickfont=dict(size=11, color='black'), showgrid=False, range=x_range
        ),
        yaxis=dict(
            title=dict(text="Noise", font=dict(color='black')),
            showgrid=True, gridcolor='lightgray', tickfont=dict(color='black'),
            type=yaxis_type, exponentformat='none', minexponent=4
        ),
        height=400,
        margin=dict(l=60, r=20, t=60, b=40),
        shapes=year_shapes,
        plot_bgcolor='white', paper_bgcolor='white',
        # Legend placed to the right of the plot for readability
        legend=dict(orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.02, font=dict(color='black'))
    )

    # Invisible dummy trace forces Plotly to render the top x-axis
    fig.add_trace(go.Scatter(x=[x_range[0], x_range[1]], y=[None, None], xaxis='x2', showlegend=False))

    return fig


# =============================================================================
# STATISTICS HELPER FUNCTIONS
# =============================================================================

def get_available_stats(analysis_type, param_group=None):
    """
    Get list of available statistic columns for an analysis type.

    For regular analysis types: returns columns like 'FLUX_mean', 'FLUX_median'
    For PSF Shape (calculate_stats=False): returns direct column names
    """
    config = ANALYSIS_TYPES.get(analysis_type, {})

    # PSF Shape uses raw column names, not 'param_metric' format
    if not config.get('calculate_stats', True):
        return config.get('direct_columns', [])

    stat_columns = get_stat_columns(analysis_type)

    if param_group and param_group in stat_columns:
        return stat_columns[param_group]

    # Flatten all groups into a single list
    all_stats = []
    for cols in stat_columns.values():
        all_stats.extend(cols)
    return all_stats


# =============================================================================
# PYCHEOPS NOISE CALCULATION
# =============================================================================

def calculate_pycheops_noise(flux, flux_err, time_days, width_hours):
    """
    Calculate transit noise using the pycheops transit_noise function.

    Parameters:
    - flux:        normalised flux array 
    - flux_err:    normalised flux error array 
    - time_days:   time array in days (starting from 0)
    - width_hours: transit window width in hours (1, 3, or 6)

    Returns: (scaled_noise_ppm, minerr_noise_ppm) — NaN on failure or insufficient data.

    """
    try:
        from pycheops.instrument import transit_noise

        # Remove NaN and non-positive error values before passing to pycheops
        valid = (
            np.isfinite(time_days)  &
            np.isfinite(flux)       &
            np.isfinite(flux_err)   &
            (flux_err > 0)
        )
        if valid.sum() < 4:
            return np.nan, np.nan

        t = np.asarray(time_days[valid], dtype=float)
        f = np.asarray(flux[valid],      dtype=float)
        e = np.asarray(flux_err[valid],  dtype=float)

        # 'scaled' method
        scaled_result    = transit_noise(t, f, e, width=width_hours, method='scaled')
        scaled_noise_ppm = scaled_result[0]

        # 'minerr' method
        minerr_noise_ppm = transit_noise(t, f, e, width=width_hours, method='minerr')

        return float(scaled_noise_ppm), float(minerr_noise_ppm)

    except Exception as ex:
        import warnings
        warnings.warn(f"pycheops noise failed (width={width_hours}h): {ex}")
        return np.nan, np.nan

# =============================================================================
# CORRELATION PLOT  
# =============================================================================

@st.fragment # don't delete - important widget interactions rerun only this fragment, not the full APP, another case will all the time return to the main page of the APP

def scatter_plot_tab(all_param_entries, all_param_labels, label_to_entry,
                     scatter_target, dot_size, plot_mode, line_dash, marker_symbol,
                     remove_outliers, sigma_threshold, log_x, log_y):
    
    """Correlation plot rendered as a fragment.

    Display options (remove_outliers, sigma_threshold, log_x, log_y, dot_size,
    plot_mode, line_dash, marker_symbol) come from the global sidebar so they
    are consistent with all other views.

    Widget interactions within the fragment (Statistic, X/Y parameter selectors)
    only rerun the fragment, not the full page.
    """

    # ------------------------------------------------------------------
    # Centered section header
    # ------------------------------------------------------------------
    st.markdown(
        "<h3 style='text-align: center; margin-top: 0.2rem; margin-bottom: 0.1rem;'>Correlation</h3>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #888; margin-top: 0; margin-bottom: 1rem;'>"
        "Correlate any parameters across all analysis types"
        "</p>",
        unsafe_allow_html=True,
    )

    if not all_param_entries:
        st.info("No parameters with statistics available.")
        return

    # ------------------------------------------------------------------
    # Statistic and parameter selectors
    # One statistic applies to all parameters (X and all Y series)
    # ------------------------------------------------------------------
    scatter_stat = st.selectbox(
        "Statistic", STATISTICS_METRICS, key="scatter_stat",
        help="One statistic applies to all selected parameters — e.g. 'mean' plots mean(X) vs mean(Y₁), mean(Y₂), …"
    )

    col_x_sc, col_y_sc = st.columns(2)
    with col_x_sc:
        x_label = st.selectbox("X axis parameter", all_param_labels, key="scatter_x")
    with col_y_sc:
        y_labels = st.multiselect("Y axis parameters", all_param_labels, key="scatter_y")

    if not y_labels:
        st.info("Select at least one Y axis parameter.")
        return

    # ------------------------------------------------------------------
    # Load X axis data for the selected target
    # ------------------------------------------------------------------
    x_entry = label_to_entry[x_label]
    x_col = f"{x_entry['param']}_{scatter_stat}"

    x_df_full = get_cached_data(x_entry['analysis_type'], remove_outliers, sigma_threshold, x_entry['radius'])
    if x_df_full is not None and not x_df_full.empty and x_col in x_df_full.columns:
        keep_x = ['Date of visit', x_col] + (['file'] if 'file' in x_df_full.columns else [])
        x_base = x_df_full[x_df_full['Target'] == scatter_target][keep_x].dropna(subset=[x_col])
    else:
        x_base = pd.DataFrame()

    if x_base.empty:
        st.warning(f"No data for X parameter '{x_entry['param']}' ({scatter_stat}) with target '{scatter_target}'.")
        return

    # Colour palette for multiple Y series
    palette = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]

    # ------------------------------------------------------------------
    # Collect merged data for all Y series on 'Date of visit'
    # The same merged data is reused by both the 2D and 3D plots below
    # ------------------------------------------------------------------
    series_data = []
    for i, y_label in enumerate(y_labels):
        y_entry = label_to_entry[y_label]
        y_col = f"{y_entry['param']}_{scatter_stat}"
        y_df_full = get_cached_data(y_entry['analysis_type'], remove_outliers, sigma_threshold, y_entry['radius'])
        if y_df_full is None or y_df_full.empty or y_col not in y_df_full.columns:
            st.warning(f"No data for '{y_entry['param']}' ({scatter_stat}).")
            continue
        y_data = y_df_full[y_df_full['Target'] == scatter_target][['Date of visit', y_col]].dropna(subset=[y_col])
        merged = pd.merge(x_base, y_data, on='Date of visit', how='inner')
        if merged.empty:
            st.warning(f"No matched observations for '{y_entry['param']}' vs '{x_entry['param']}' on target '{scatter_target}'.")
            continue
        series_data.append((i, y_label, y_col, merged))

    if series_data:
        x_axis_type = "log" if log_x else "linear"
        y_axis_type = "log" if log_y else "linear"
        x_title = f"{x_entry['param']}  [{x_entry['analysis_type']}]  ({scatter_stat})"

        # ------------------------------------------------------------------
        # 2D scatter plot — X vs Y, coloured by series
        # ------------------------------------------------------------------
        fig2d = go.Figure()
        for i, y_label, y_col, merged in series_data:
            fig2d.add_trace(go.Scatter(
                x=merged[x_col],
                y=merged[y_col],
                mode=plot_mode,
                name=y_label,
                marker=dict(size=dot_size, color=palette[i % len(palette)],
                            opacity=0.8, symbol=marker_symbol),
                line=dict(dash=line_dash, color=palette[i % len(palette)]),
                text=merged['Date of visit'].dt.strftime('%Y-%m-%d'),
                hovertemplate=(
                    f"<b>{y_label}</b><br>"
                    f"X: %{{x:.4g}}<br>"
                    f"Y: %{{y:.4g}}<br>"
                    "Date: %{text}<extra></extra>"
                )
            ))
        fig2d.update_layout(
            title=dict(
                text=f"Correlation plot for {scatter_target}, {scatter_stat}",
                x=0.5, xanchor='center', font=dict(color='black', size=16),
            ),
            xaxis=dict(
                title=dict(text=x_title, font=dict(color='black')),
                type=x_axis_type, showgrid=True, gridcolor='lightgray',
                zeroline=False, tickfont=dict(color='black'),
            ),
            yaxis=dict(
                title=dict(text=scatter_stat, font=dict(color='black')),
                type=y_axis_type, showgrid=True, gridcolor='lightgray',
                zeroline=False, tickfont=dict(color='black'),
            ),
            height=550, plot_bgcolor='white', paper_bgcolor='white',
            showlegend=True,  # Always show legend even with a single Y series
            legend=dict(orientation="v", yanchor="middle", y=0.5,
                        xanchor="left", x=1.02, font=dict(color='black')),
        )
        st.plotly_chart(fig2d, width='stretch')
        st.caption(
            f"Statistic: **{scatter_stat}** | Target: **{scatter_target}** | "
            "Each point = one matched observation | Hover for date and values"
        )

        # ------------------------------------------------------------------
        # 3D scatter plot — same X and Y, Z axis = Year
        # Allows visual identification of temporal trends in the correlation
        # ------------------------------------------------------------------
        # ! You can uncomment it if you want to have also a 3D plot with time dimention in Z-axis
        '''
        st.divider()
        fig3d = go.Figure()
        for i, y_label, y_col, merged in series_data:
            z_vals = merged['Date of visit'].dt.year   # Year extracted from observation date
            fig3d.add_trace(go.Scatter3d(
                x=merged[x_col],
                y=merged[y_col],
                z=z_vals,
                mode='markers',
                name=y_label,
                marker=dict(size=dot_size, color=palette[i % len(palette)],
                            opacity=0.8, symbol='circle'),
                text=merged['Date of visit'].dt.strftime('%Y-%m-%d'),
                hovertemplate=(
                    f"<b>{y_label}</b><br>"
                    f"X: %{{x:.4g}}<br>"
                    f"Y: %{{y:.4g}}<br>"
                    "Year: %{z}<br>"
                    "Date: %{text}<extra></extra>"
                )
            ))
        fig3d.update_layout(
            title=dict(
                text=f"3D Correlation for {scatter_target}, {scatter_stat}",
                x=0.5, xanchor='center', font=dict(color='black', size=16),
            ),
            scene=dict(
                xaxis=dict(title=dict(text=x_title, font=dict(color='black')),
                           backgroundcolor='white', gridcolor='lightgray',
                           showbackground=True, tickfont=dict(color='black')),
                yaxis=dict(title=dict(text=scatter_stat, font=dict(color='black')),
                           backgroundcolor='white', gridcolor='lightgray',
                           showbackground=True, tickfont=dict(color='black')),
                zaxis=dict(title=dict(text='Year', font=dict(color='black')),
                           backgroundcolor='white', gridcolor='lightgray',
                           showbackground=True, tickformat='d',
                           tickfont=dict(color='black')),
            ),
            height=650, paper_bgcolor='white',
            showlegend=True,
            legend=dict(font=dict(color='black')),
            margin=dict(l=0, r=0, t=60, b=0),
        )
        st.plotly_chart(fig3d, width='stretch')

'''
# =============================================================================
# STATISTICS CALCULATION
# =============================================================================

def calculate_statistics(data, prefix, time_days=None, flux_err=None):
    """
    Calculate all statistics for a data array.

    For FLUX parameter with valid time and error arrays (lightcurve sources),
    also computes pycheops transit noise metrics (scaled and minerr, for 1h, 3h, 6h).

    Returns dictionary with keys: '{prefix}_mean', '{prefix}_median', etc.
    """
    result = {
        f'{prefix}_mean':     np.mean(data),
        f'{prefix}_median':   np.median(data),
        f'{prefix}_sigma':    np.std(data),
        f'{prefix}_mad':      np.median(np.abs(data - np.median(data))),
        f'{prefix}_min':      np.min(data),
        f'{prefix}_max':      np.max(data),
        f'{prefix}_ptp':      np.ptp(data),
        f'{prefix}_p01':      np.percentile(data, 1),
        f'{prefix}_p99':      np.percentile(data, 99),
        f'{prefix}_skew':     stats.skew(data),
        f'{prefix}_kurtosis': stats.kurtosis(data)
    }

    # Pycheops noise is only meaningful for normalised flux with valid time and error arrays
    median_val = np.median(data)
    can_compute_noise = (
        time_days is not None  and
        flux_err  is not None  and
        len(time_days) == len(data) and
        median_val != 0        and
        np.isfinite(median_val)
    )

    if can_compute_noise:
        # Normalise flux and errors by the median before passing to pycheops
        flux_norm     = data     / median_val
        flux_err_norm = flux_err / median_val

        for width in [1, 3, 6]:
            s_noise, m_noise = calculate_pycheops_noise(flux_norm, flux_err_norm, time_days, width)
            result[f'{prefix}_scaled_noise_{width}h'] = s_noise
            result[f'{prefix}_minerr_noise_{width}h'] = m_noise
    else:
        # Store NaN placeholders so the column schema is consistent across all files
        for width in [1, 3, 6]:
            result[f'{prefix}_scaled_noise_{width}h'] = np.nan
            result[f'{prefix}_minerr_noise_{width}h'] = np.nan

    return result
