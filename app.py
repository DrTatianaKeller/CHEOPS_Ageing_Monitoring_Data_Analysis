"""
CHEOPS Ageing Monitoring Data Analysis

Main Streamlit application for CHEOPS Ageing Monitoring Data Analysis.

File structure:
- app.py : Main UI logic and page layout
- config.py: Configuration for analysis types, parameters, and statistics
- data_loader.py: FITS file reading and data processing
- functions.py: Plotting utilities and helper functions
"""

import streamlit as st
import pandas as pd

from config import *       # ANALYSIS_TYPES, DATA_SOURCES, STATISTICS_METRICS, STAT_DEFINITIONS, LIGHT_CURVE_SOURCES
from data_loader import *  # load_data_for_analysis, load_psf_data, get_targets_accessibility_table, load_raw_fits_data
from functions import *    # get_cached_data, get_year_separators, get_year_ticks, create_plot, create_dual_axis_plot




# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(page_title="CHEOPS Ageing Monitoring Data Analysis", layout="wide")
st.title("CHEOPS Ageing Monitoring Data Analysis")

# =============================================================================
# NAVIGATION BAR STYLING
# Streamlit has no built-in horizontal tab bar that persists its selection when one interacts with sidebar widgets.  
# PROBLEM: st.tabs resets to tab 1 on every sidebar change!

# SOLUTION: use st.radio (whose value is stored in session_state and never resets) 
# There is a solution what I found after long search , just to apply CSS to make it look and behave exactly like st.tabs —
# hiding the radio circles, adding the underline bar, hover colours, etc.
# !!! You can change it to the other solution with st.tabs if you prefer the native Streamlit tabs and don't mind that the selection resets on every sidebar interaction.
# =============================================================================

st.markdown("""
<style>
/* ── Navigation radio → tab-bar appearance ── */

/* Container: stretch across full width, add bottom border rule */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 0 !important;
    padding: 0 !important;
    border-bottom: 1px solid rgba(49, 51, 63, 0.2);
    width: 100%;
    margin-bottom: 1rem;
}

/* Each option wrapper */
div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    display: flex !important;
    align-items: center !important;
    padding: 8px 18px 10px !important;
    margin-bottom: -1px !important;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    color: rgba(49, 51, 63, 0.55);
    font-size: 14px;
    font-weight: 400;
    white-space: nowrap;
    transition: color 0.15s ease, border-color 0.15s ease;
    user-select: none;
    background: transparent !important;
}

/* Hide the radio dot / circle */
div[data-testid="stRadio"] > div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}

/* Hover state (inactive tab) */
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
    color: rgba(49, 51, 63, 0.85);
    border-bottom-color: rgba(49, 51, 63, 0.35);
}

/* Active / selected tab — red underline matching Streamlit native tabs */
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    color: rgb(255, 75, 75);
    border-bottom-color: rgb(255, 75, 75);
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR: ANALYSIS TYPE SELECTION
# =============================================================================

analysis_types_list = list(ANALYSIS_TYPES.keys())
target_placeholder = st.sidebar.empty()  # Placeholder for target selector (filled after data loads)
analysis_type = st.sidebar.selectbox("Analysis Type", analysis_types_list)
analysis_config = ANALYSIS_TYPES[analysis_type]

param_groups = list(analysis_config['parameters'].keys())

# =============================================================================
# SIDEBAR: APERTURE RADIUS (Lightcurve only)
# =============================================================================

aperture_radius = None
source_name = analysis_config.get('source', '')
source_config = DATA_SOURCES.get(source_name, {})

# Show aperture radius slider only for lightcurve analysis types
if 'radius_range' in source_config:
    r_min, r_max = source_config['radius_range']
    r_default = source_config.get('default_radius', 25)
    st.sidebar.markdown("---")
    aperture_radius = st.sidebar.slider("Aperture Radius", r_min, r_max, r_default, 1)

# All parameter groups are selected by default (no per-group checkboxes in current version)
selected_groups = param_groups

calculate_stats = analysis_config.get('calculate_stats', True)

# =============================================================================
# SIDEBAR: DISPLAY OPTIONS
# =============================================================================

remove_outliers = False
sigma_threshold = 3.0
log_x = False

st.sidebar.markdown("---")
st.sidebar.subheader("Display Options")

# Check if the selected analysis type is a lightcurve source
is_lightcurve = analysis_config.get('source', '') in LIGHT_CURVE_SOURCES

# Reserve placeholder positions in the sidebar in the desired visual order:
# Date from , Date to , Format , Dot size , Remove Outliers , Log X , Log Y
# Placeholders are filled after data is loaded (so date range can reflect actual data)
start_date_placeholder = st.sidebar.empty()
end_date_placeholder   = st.sidebar.empty()
fmt_placeholder        = st.sidebar.empty()
dot_size_placeholder   = st.sidebar.empty()
outlier_container      = st.sidebar.container()   # Remove Outliers + Sigma (positioned after Dot size)
log_x_placeholder      = st.sidebar.empty()
log_y_placeholder      = st.sidebar.empty()

# Read outlier / log-x values NOW (before data load) so they affect data loading.
# Each widget uses its pre-reserved placeholder so the visual order is preserved.
if calculate_stats:
    remove_outliers = outlier_container.checkbox("Remove Outliers", value=False)
    if remove_outliers:
        sigma_threshold = outlier_container.slider("Sigma Threshold", 1.0, 5.0, 3.0, 0.5)

log_x = log_x_placeholder.checkbox("Logarithmic X-axis", value=False)
log_y = log_y_placeholder.checkbox("Logarithmic Y-axis", value=False)

# =============================================================================
# LOAD DATA
# =============================================================================

# Use specialized loader for PSF Shape as there no need statistic calculation, 
# general loader for all other types, when statistic calculation is required
if analysis_type == 'PSF Shape':
    df = load_psf_data()
else:
    df = load_data_for_analysis(analysis_type, remove_outliers, sigma_threshold, selected_groups, aperture_radius)

# =============================================================================
# MAIN CONTENT
# =============================================================================

if df.empty:
    st.error(f"No data found for {analysis_type}. Check that FITS files are in the correct directory.")
else:
    # Get statistic column names grouped by parameter group
    stat_columns = get_stat_columns(analysis_type)

    # Filter to columns that actually exist in the loaded dataframe
    filtered_stat_columns = {
        group: [c for c in cols if c in df.columns]
        for group, cols in stat_columns.items()
    }

    # Target selection in sidebar (rendered in pre-reserved placeholder)
    targets = sorted(df['Target'].unique().tolist())
    selected_target = target_placeholder.selectbox("Select Target", targets)

    # Date range filter (filled in pre-reserved placeholders in Display Options)
    min_date = df['Date of visit'].min().date()
    max_date = df['Date of visit'].max().date()
    start_date = start_date_placeholder.date_input("Date from", value=min_date, min_value=min_date, max_value=max_date)
    end_date   = end_date_placeholder.date_input("Date to",   value=max_date, min_value=min_date, max_value=max_date)

    # Plot format string (matplotlib style) and display options, as Attila requested
    fmt_str = fmt_placeholder.text_input(
        "Plot format (matplotlib style)", value="o-",
        help=(
        "Line: -(solid)  --(dash)  -.(dashdot)  :(dot)\n\n"
        "Marker: o (circle)  s (square)  ^ (triangle-up)  v (triangle-down)  D (diamond)  * (star)  + (plus)  x (cross)  p (pentagon)  h (hexagon)\n\n"
        "Examples: o- (dots+line)  -- (line only)  ^ (dots only)"
        )
    )
    dot_size = dot_size_placeholder.slider("Dot size", 1, 20, 6)
   

    # Parse Matplotlib format string into Plotly parameters
    plot_mode, line_dash, marker_symbol = parse_mpl_format(fmt_str)

    # Filter data by selected target and date range
    filtered_df = df[
        (df['Target'] == selected_target) &
        (df['Date of visit'].dt.date >= start_date) &
        (df['Date of visit'].dt.date <= end_date)
    ].sort_values('Date of visit')

    # Show file counts in sidebar for quick reference
    st.sidebar.markdown("---")
    st.sidebar.info(f"Total files: {len(df)}")
    st.sidebar.info(f"Files for {selected_target}: {len(filtered_df)}")

    # =========================================================================
    # GLOBAL NAVIGATION
    # St.radio widget value persists in session_state across all reruns, so switching views never resets sidebar selections
    # =========================================================================
    VIEW_NAMES = [
        "Statistic Plots", "Data",
        "Dual Parameter Evolution", "Combined Noise", "Correlation"
    ]
    active_view = st.radio(
        "View", VIEW_NAMES, horizontal=True,
        key="active_view", label_visibility="collapsed"
    )

    # -------------------------------------------------------------------------
    # VIEW 1: STATISTIC PLOTS
    # Time-series of each statistic metric for the selected target
    # -------------------------------------------------------------------------
    if active_view == "Statistic Plots":
        if filtered_df.empty:
            st.warning("No data available for the selected target and date range.")
        else:
            # Prepare year formatting for all plots in this view
            year_shapes = get_year_separators(filtered_df['Date of visit'])
            year_tickvals, year_ticktext, year_x_range = get_year_ticks(filtered_df['Date of visit'])

            if aperture_radius is not None:
                st.header(f"Evolution of {analysis_type} (R{aperture_radius}) Statistics for {selected_target}")
            else:
                st.header(f"Evolution of {analysis_type} Statistics for {selected_target}")

            if calculate_stats:
                # Build (param, stat_cols) pairs for all selected parameter groups
                param_tab_data = []
                for group_name in selected_groups:
                    for param in analysis_config['parameters'].get(group_name, []):
                        param_cols = [
                            c for c in filtered_stat_columns.get(group_name, [])
                            if c.startswith(f"{param}_")
                        ]
                        if param_cols:
                            param_tab_data.append((param, param_cols))

                if param_tab_data:
                    # One tab per parameter — plots displayed in 2-column pairs
                    param_tabs = st.tabs([param for param, _ in param_tab_data])
                    for param_tab, (param, param_cols) in zip(param_tabs, param_tab_data):
                        with param_tab:
                            # Display plots in pairs (2 columns per row)
                            for i in range(0, len(param_cols), 2):
                                left  = param_cols[i]
                                right = param_cols[i + 1] if i + 1 < len(param_cols) else None

                                # Show statistic definitions above each pair
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.caption(f"**{left}**: {get_stat_definition(left)}")
                                with col2:
                                    if right:
                                        st.caption(f"**{right}**: {get_stat_definition(right)}")

                                # Show plots
                                col1, col2 = st.columns(2)
                                with col1:
                                    fig = create_plot(filtered_df, left, plot_mode, year_shapes, year_tickvals, year_ticktext, year_x_range,
                                                      log_y=log_y, dot_size=dot_size, line_dash=line_dash, marker_symbol=marker_symbol)
                                    st.plotly_chart(fig, width='stretch')
                                with col2:
                                    if right:
                                        fig = create_plot(filtered_df, right, plot_mode, year_shapes, year_tickvals, year_ticktext, year_x_range,
                                                          log_y=log_y, dot_size=dot_size, line_dash=line_dash, marker_symbol=marker_symbol)
                                        st.plotly_chart(fig, width='stretch')
                else:
                    st.info("No statistic columns found for the selected parameter groups.")

            else:
                # =========================================================
                # DIRECT VALUES (for PSF Shape — no statistics calculated)
                # =========================================================
                st.subheader("Direct Parameter Values")
                st.info("This analysis shows raw values from FITS files without statistics calculations.")

                # Display plots for each parameter group
                for group_name in selected_groups:
                    if group_name not in analysis_config['parameters']:
                        continue
                    group_cols = [c for c in analysis_config['parameters'][group_name] if c in filtered_df.columns]
                    if not group_cols:
                        continue
                    st.markdown(f"### {group_name}")
                    for col in group_cols:
                        col_descriptions = analysis_config.get('column_descriptions', {})
                        desc = col_descriptions.get(col, '')
                        st.markdown(f"#### {desc if desc else col}")
                        fig = create_plot(filtered_df, col, plot_mode, year_shapes, year_tickvals, year_ticktext, year_x_range,
                                          log_y=log_y, dot_size=dot_size, line_dash=line_dash, marker_symbol=marker_symbol)
                        st.plotly_chart(fig, width='stretch')

    # -------------------------------------------------------------------------
    # VIEW 2: DATA  (Statistics Table | Raw FITS Data | Targets Table)
    # Three inner tabs share a common Year / File selector at the top
    # -------------------------------------------------------------------------
    elif active_view == "Data":
        sel_analysis_type   = analysis_type
        sel_analysis_config = analysis_config
        sel_calculate_stats = calculate_stats
        sel_param_groups    = param_groups
        sel_target          = selected_target
        selected_row        = None  # Set once user selects Year + File

        st.caption(f"Analysis Type: **{sel_analysis_type}** — Target: **{sel_target}**")

        # Load the dataframe for the current analysis type (cached)
        df_analysis = get_cached_data(sel_analysis_type, remove_outliers, sigma_threshold, aperture_radius)

        # Year and File selectors — shared by Statistics Table and Raw FITS Data tabs
        if df_analysis is not None and not df_analysis.empty:
            df_t = df_analysis[df_analysis["Target"] == sel_target].copy()
            if not df_t.empty:
                available_years = sorted(df_t["Date of visit"].dt.year.dropna().unique().tolist())
                col_year, col_file = st.columns(2)
                with col_year:
                    sel_year = st.selectbox("Year", available_years, key="shared_year") if available_years else None
                with col_file:
                    if sel_year is not None:
                        df_ty = df_t[df_t["Date of visit"].dt.year == sel_year].sort_values("Date of visit").copy()
                        if not df_ty.empty:
                            # Build human-readable file label: date — filename
                            df_ty["file_label"] = (
                                df_ty["Date of visit"].dt.strftime("%Y-%m-%d")
                                + " — " + df_ty["file"].astype(str)
                            )
                            sel_label    = st.selectbox("File", df_ty["file_label"].tolist(), key="shared_file")
                            selected_row = df_ty.loc[df_ty["file_label"] == sel_label].iloc[0]

        inner_tab_stats, inner_tab_raw, inner_tab_targets = st.tabs(
            ["Statistics Table", "Raw FITS Data", "Targets Table"]
        )

        # -----------------------------------------------------------------
        # INNER TAB: STATISTICS TABLE
        # Computed statistics for the selected Year / File
        # -----------------------------------------------------------------
        with inner_tab_stats:
            if df_analysis is None or df_analysis.empty:
                st.warning("No data available for the selected analysis type.")
            elif not sel_calculate_stats:
                st.info(f"{sel_analysis_type} does not calculate statistics — showing direct values instead.")
            elif selected_row is None:
                st.info("Select Year and File above.")
            else:
                st.markdown(
                    f"**Statistics for {sel_target} — {selected_row['Date of visit'].strftime('%Y-%m-%d')}**"
                )
                # Build statistics grid: rows = statistics, columns = parameters
                stats_data = []
                for group in sel_param_groups:
                    params = sel_analysis_config["parameters"].get(group, [])
                    for param in params:
                        param_stats = {"Parameter": param}
                        for stat in STATISTICS_METRICS:
                            col_name = f"{param}_{stat}"
                            if col_name in selected_row.index:
                                value = selected_row[col_name]
                                if pd.notna(value):
                                    param_stats[stat] = f"{value:.4g}" if isinstance(value, (float, np.floating)) else value
                                else:
                                    param_stats[stat] = "N/A"
                        stats_data.append(param_stats)
                if stats_data:
                    stats_df = pd.DataFrame(stats_data).set_index("Parameter").T
                    stats_df.index.name = "Statistic"
                    st.dataframe(stats_df, use_container_width=True)
                else:
                    st.warning("No statistics available for selected parameters.")

        # -----------------------------------------------------------------
        # INNER TAB: RAW FITS DATA
        # Raw table rows loaded directly from the selected FITS file
        # -----------------------------------------------------------------
        with inner_tab_raw:
            if selected_row is None:
                st.info("Select Year and File above.")
            else:
                # Use the exact file selected in the Year / File selectors above
                selected_file = selected_row.get("file", None)
                if not selected_file or pd.isna(selected_file):
                    st.warning("Selected row has no 'file' value.")
                else:
                    raw_data = load_raw_fits_data(sel_analysis_type, selected_file, aperture_radius)
                    if raw_data is not None and not raw_data.empty:
                        max_rows = st.slider("Max rows to display", 10, 10000, 1000, step=100, key="raw_max_rows")
                        st.dataframe(raw_data.head(max_rows), use_container_width=True)
                        st.caption(f"Columns: {', '.join(raw_data.columns.tolist())}")
                        st.success(f"Loaded {len(raw_data)} rows from {selected_file}")
                    else:
                        st.warning("Could not load raw data from this file.")

        # -----------------------------------------------------------------
        # INNER TAB: TARGETS TABLE
        # All targets from targets.csv with file accessibility status
        # -----------------------------------------------------------------
        with inner_tab_targets:
            st.subheader("Targets Overview")
            st.caption("Shows all targets from targets.csv with file accessibility status (✓ = available, ✗ = missing)")

            targets_accessibility = get_targets_accessibility_table()
            if not targets_accessibility.empty:
                # Which availability columns exist (in case more are added later)
                availability_cols = [c for c in ["Lightcurves", "SCI_RAW Data", "General report"] if c in targets_accessibility.columns]

                # Summary counts per data source column
                for col in availability_cols:
                    available_count = (targets_accessibility[col] == "✓").sum()
                    total_count     = len(targets_accessibility)
                    st.info(f"{col}: {available_count} of {total_count} entries ({available_count/total_count*100:.1f}%)")

                # Apply colour style only to availability columns (keeps Target/OR ID normal)
                styled = targets_accessibility.style
                if availability_cols:
                    styled = styled.applymap(color_checkmarks, subset=availability_cols)

                # Render styled table
                st.write(styled)
            else:
                st.warning("Could not load targets.csv file.")

    # -------------------------------------------------------------------------
    # VIEW 3: DUAL PARAMETER EVOLUTION
    # Dual Y-axis time-series comparing evolution of two parameters over time
    # -------------------------------------------------------------------------
    elif active_view == "Dual Parameter Evolution":
        st.subheader("Dual Parameter Evolution")
        st.caption("Compare any statistic from any analysis type on the same plot")

        # Build flat parameter list — same style as Correlation view
        # Label format: "PARAMETER  [Analysis Type]"
        corr_param_entries = []
        for at_name, at_config in ANALYSIS_TYPES.items():
            if not at_config.get('calculate_stats', True):
                continue  # Skip PSF Shape and other direct-value types
            at_source_cfg    = DATA_SOURCES.get(at_config.get('source', ''), {})
            at_default_radius = at_source_cfg.get('default_radius', None) if 'radius_range' in at_source_cfg else None
            for group, params in at_config['parameters'].items():
                for param in params:
                    corr_param_entries.append({
                        'label':         f"{param}  [{at_name}]",
                        'param':          param,
                        'analysis_type':  at_name,
                        'radius':         at_default_radius,
                    })
        corr_param_labels    = [e['label'] for e in corr_param_entries]
        corr_label_to_entry  = {e['label']: e for e in corr_param_entries}

        if not corr_param_entries:
            st.info("No parameters with statistics available.")
        else:
            col_left, col_right = st.columns(2)

            # ---------------------------
            # LEFT AXIS SELECTORS
            # ---------------------------
            with col_left:
                st.markdown("**Left Y-Axis (Blue)**")
                left_label    = st.selectbox("Parameter", corr_param_labels, key="left_param_label")
                left_entry    = corr_label_to_entry[left_label]
                left_stat_sel = st.selectbox("Statistic", STATISTICS_METRICS, key="left_stat")
                left_stat     = f"{left_entry['param']}_{left_stat_sel}"

            # ---------------------------
            # RIGHT AXIS SELECTORS
            # ---------------------------
            with col_right:
                st.markdown("**Right Y-Axis (Orange)**")
                right_label    = st.selectbox("Parameter", corr_param_labels, key="right_param_label")
                right_entry    = corr_label_to_entry[right_label]
                right_stat_sel = st.selectbox("Statistic", STATISTICS_METRICS,
                                              index=min(1, len(STATISTICS_METRICS) - 1), key="right_stat")
                right_stat     = f"{right_entry['param']}_{right_stat_sel}"

            # ---------------------------
            # LOAD DATA AND CREATE PLOT
            # ---------------------------
            left_df  = get_cached_data(left_entry['analysis_type'],  remove_outliers, sigma_threshold, left_entry['radius'])
            right_df = get_cached_data(right_entry['analysis_type'], remove_outliers, sigma_threshold, right_entry['radius'])

            # Filter to the globally selected target
            left_target_df  = left_df[left_df['Target']   == selected_target].sort_values('Date of visit') if left_df  is not None and not left_df.empty  else pd.DataFrame()
            right_target_df = right_df[right_df['Target'] == selected_target].sort_values('Date of visit') if right_df is not None and not right_df.empty else pd.DataFrame()

            left_ok  = not left_target_df.empty  and left_stat  in left_target_df.columns
            right_ok = not right_target_df.empty and right_stat in right_target_df.columns

            if left_ok and right_ok:
                # Combine dates from both series for consistent x-axis range and year ticks
                all_corr_dates   = pd.concat([left_target_df['Date of visit'], right_target_df['Date of visit']])
                corr_year_shapes = get_year_separators(all_corr_dates)
                corr_year_tickvals, corr_year_ticktext, corr_year_x_range = get_year_ticks(all_corr_dates)
                fig = create_dual_axis_plot(
                    left_target_df['Date of visit'],  left_target_df[left_stat],
                    f"{left_entry['label']}: {left_stat_sel}",
                    right_target_df['Date of visit'], right_target_df[right_stat],
                    f"{right_entry['label']}: {right_stat_sel}",
                    selected_target, plot_mode, corr_year_shapes, corr_year_tickvals, corr_year_ticktext,
                    corr_year_x_range, log_y=log_y, dot_size=dot_size, line_dash=line_dash,
                    marker_symbol=marker_symbol
                )
                st.plotly_chart(fig, width='stretch')
            else:
                # Report which axis has missing data
                missing = []
                if not left_ok:
                    missing.append(f"Left ({left_entry['label']}: {left_stat_sel})")
                if not right_ok:
                    missing.append(f"Right ({right_entry['label']}: {right_stat_sel})")
                st.warning(f"No data for: {', '.join(missing)}")

    # -------------------------------------------------------------------------
    # VIEW 4: COMBINED NOISE — NOISE EVOLUTION
    # Available only for lightcurve analysis types; plots FLUX pycheops noise metrics
    # -------------------------------------------------------------------------
    elif active_view == "Combined Noise":
        if filtered_df.empty:
            st.warning("No data available for the selected target and date range.")
        elif not calculate_stats:
            st.info("Combined noise is not available for this analysis type.")
        elif not is_lightcurve:
            st.info("Combined noise plot is only available for lightcurve analysis types (DRP, RPC, PIPE).")
        else:
            # Prepare year formatting for this view
            year_shapes_n = get_year_separators(filtered_df['Date of visit'])
            year_tickvals_n, year_ticktext_n, year_x_range_n = get_year_ticks(filtered_df['Date of visit'])

            st.subheader(f"Noise evolution for {selected_target}")
            st.caption("Pycheops transit_noise per parameter")

            # Noise level options shown in the multiselect
            noise_options = {
                'sigma (unbinned)': 'sigma',
                'Scaled 1h': 'scaled_1h', 'Scaled 3h': 'scaled_3h', 'Scaled 6h': 'scaled_6h',
                'MinErr 1h': 'minerr_1h', 'MinErr 3h': 'minerr_3h', 'MinErr 6h': 'minerr_6h'
            }
            selected_noise = st.multiselect(
            "Select noise levels to display",
            options=list(noise_options.keys()),
            default=list(noise_options.keys())
)

            selected_noise_keys = [noise_options[s] for s in selected_noise]

            # Noise metrics are plotted only for the FLUX parameter
            param = 'FLUX'
            noise_cols = [f'{param}_sigma'] + [f'{param}_scaled_noise_{b}h' for b in [1, 3, 6]] + [f'{param}_minerr_noise_{b}h' for b in [1, 3, 6]]
            if any(c in filtered_df.columns for c in noise_cols):
                fig = create_combined_noise_plot(
                    filtered_df, param, plot_mode,
                    year_shapes_n, year_tickvals_n, year_ticktext_n, year_x_range_n,
                    selected_levels=selected_noise_keys, log_y=log_y,
                    dot_size=dot_size, line_dash=line_dash, marker_symbol=marker_symbol,
                    target=selected_target
                )
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No FLUX noise columns found for this dataset.")

    # -------------------------------------------------------------------------
    # VIEW 5: CORRELATION
    # 2D and (optional) 3D scatter plots for parameter correlation analysis
    # Rendered as @st.fragment — parameter selectors inside the fragment
    # to rerun only the fragment, not the full page
    # -------------------------------------------------------------------------
    elif active_view == "Correlation":
        # Build flat parameter list 
        # Label format: "PARAM  [Analysis Type]"
        all_param_entries = []
        for at_name, at_config in ANALYSIS_TYPES.items():
            if not at_config.get('calculate_stats', True):
                continue  # Skip PSF Shape and other direct-value types
            at_source     = at_config.get('source', '')
            at_source_cfg = DATA_SOURCES.get(at_source, {})
            at_default_radius = at_source_cfg.get('default_radius', None) if 'radius_range' in at_source_cfg else None
            for group, params in at_config['parameters'].items():
                for param in params:
                    all_param_entries.append({
                        'label':         f"{param}  [{at_name}]",
                        'param':          param,
                        'analysis_type':  at_name,
                        'radius':         at_default_radius,
                    })

        all_param_labels = [e['label'] for e in all_param_entries]
        label_to_entry   = {e['label']: e for e in all_param_entries}

        # Call the fragment function — passes all global display options as arguments
        # (st.sidebar widgets cannot be called inside @st.fragment)
        
        scatter_plot_tab(
            all_param_entries, all_param_labels, label_to_entry,
            selected_target, dot_size, plot_mode, line_dash, marker_symbol,
            remove_outliers, sigma_threshold, log_x, log_y
        )

# =============================================================================
# SIDEBAR: ABOUT AND DEFINITIONS
# =============================================================================

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown(f"**{analysis_type}**: {analysis_config.get('description', '')}")
st.sidebar.markdown("---")
st.sidebar.markdown("### Statistics Definitions")
with st.sidebar.expander("View Definitions"):
    for metric in STATISTICS_METRICS:
        st.markdown(f"**{metric}**: {STAT_DEFINITIONS.get(metric, '')}")
