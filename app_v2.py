"""
CHEOPS Ageing Monitoring Data Analysis

Main Streamlit application for CHEOPS Ageing Monitoring Data Analysis.

File structure:
- app.py (this file): Main UI logic and page layout
- config.py: Configuration for analysis types, parameters, and statistics
- data_loader.py: FITS file reading and data processing
- functions.py: Plotting utilities and helper functions
"""

import streamlit as st
import pandas as pd

from config import * #ANALYSIS_TYPES, STATISTICS_METRICS, STAT_DEFINITIONS
from data_loader import *  #load_data_for_analysis, load_psf_data, get_targets_accessibility_table
from functions import * #(get_cached_data, get_year_separators, get_year_ticks, 
                        #create_plot, create_dual_axis_plot, get_available_stats, get_stat_columns, get_stat_definition)
from data_loader import load_raw_fits_data

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(page_title="CHEOPS Ageing Monitoring Data Analysis", layout="wide")
st.title("CHEOPS Ageing Monitoring Data Analysis")

# =============================================================================
# SIDEBAR: ANALYSIS TYPE SELECTION
# =============================================================================

analysis_types_list = list(ANALYSIS_TYPES.keys())
target_placeholder = st.sidebar.empty()  # Placeholder for target selector (filled after data loads)
analysis_type = st.sidebar.radio("Analysis Type", analysis_types_list)
analysis_config = ANALYSIS_TYPES[analysis_type]
param_groups = list(analysis_config['parameters'].keys())

# =============================================================================
# SIDEBAR: PARAMETER GROUP SELECTION
# =============================================================================

st.sidebar.markdown("---")
st.sidebar.subheader("Parameters")
selected_groups = []
for group in param_groups:
    if st.sidebar.checkbox(group, value=True, key=f"param_{analysis_type}_{group}"):
        selected_groups.append(group)

# Stop execution if no groups selected
if not selected_groups:
    st.warning("Please select at least one parameter group to display.")
    st.stop()

calculate_stats = analysis_config.get('calculate_stats', True)

# =============================================================================
# SIDEBAR: DISPLAY OPTIONS
# =============================================================================

remove_outliers = False
sigma_threshold = 3.0
show_correlation = True

# Display Options section
st.sidebar.markdown("---")
st.sidebar.subheader("Display Options")

# Placeholders for date and plot type (filled after data loads)
date_placeholder = st.sidebar.empty()
plot_type_placeholder = st.sidebar.empty()

# Display Options section
st.sidebar.markdown("---")
st.sidebar.subheader("Plot's Options")

# Only show correlation/outlier options for analysis types that calculate statistics
if calculate_stats:
    show_correlation = st.sidebar.checkbox("Show Correlation Analysis", value=True)
    remove_outliers = st.sidebar.checkbox("Remove Outliers", value=False)
    if remove_outliers:
        sigma_threshold = st.sidebar.slider("Sigma Threshold", 1.0, 5.0, 3.0, 0.5)

# Display Tables section - all table viewing options
st.sidebar.markdown("---")
st.sidebar.subheader("Display Tables")
show_targets_table = st.sidebar.checkbox("Show Targets Table", value=False)
show_stats_table = st.sidebar.checkbox("Show Statistics Table", value=False)
show_files = st.sidebar.checkbox("Show Raw FITS Data", value=False)

# =============================================================================
# LOAD DATA
# =============================================================================

# Use specialized loader for PSF Shape, general loader for others
if analysis_type == 'PSF Shape':
    df = load_psf_data()
else:
    df = load_data_for_analysis(analysis_type, remove_outliers, sigma_threshold, selected_groups)

# =============================================================================
# MAIN CONTENT
# =============================================================================

if df.empty:
    st.error(f"No data found for {analysis_type}. Check that FITS files are in the correct directory.")
else:
    # Target selection in sidebar
    targets = sorted(df['Target'].unique().tolist())
    selected_target = target_placeholder.selectbox("Select Target", targets)
    
    # Date range filter (in Display Options section via placeholder)
    min_date = df['Date of visit'].min().date()
    max_date = df['Date of visit'].max().date()
    end_date = date_placeholder.date_input("Show data till date", value=max_date, min_value=min_date, max_value=max_date)
    
    # Plot type selection (in Display Options section via placeholder)
    plot_type = plot_type_placeholder.selectbox("Plot Type", ["Line + Dots","Line", "Dots"])
    mode_map = { "Line + Dots": "lines+markers","Line": "lines", "Dots": "markers"}
    plot_mode = mode_map[plot_type]
    
    # Filter data by target and date
    filtered_df = df[(df['Target'] == selected_target) & (df['Date of visit'].dt.date <= end_date)].sort_values('Date of visit')
    
    # Show file counts in sidebar
    st.sidebar.markdown("---")
    st.sidebar.info(f"Total files: {len(df)}")
    st.sidebar.info(f"Files for {selected_target}: {len(filtered_df)}")
    
    if filtered_df.empty:
        st.warning("No data available for the selected target and date range.")
    else:
        st.markdown("---")
       
        
        # =========================================================================
        # TARGETS TABLE SECTION (shows file accessibility status)
        # =========================================================================
        if show_targets_table:
            st.subheader("Targets Overview")
            st.caption("Shows all targets from targets.csv with file accessibility status (✓ = available, ✗ = missing)")

            targets_accessibility = get_targets_accessibility_table()

            if not targets_accessibility.empty:
                # Which availability columns exist (in case you later add more)
                availability_cols = [c for c in ["Lightcurves", "SCI_RAW Data", "General report"] if c in targets_accessibility.columns]

                # Summary counts per column
                for col in availability_cols:
                    available_count = (targets_accessibility[col] == "✓").sum()
                    total_count = len(targets_accessibility)
                    st.info(f"{col}: {available_count} of {total_count} entries ({available_count/total_count*100:.1f}%)")

                # Apply style only to availability columns (keeps Target/OR ID normal)
                styled = targets_accessibility.style
                if availability_cols:
                    styled = styled.applymap(color_checkmarks, subset=availability_cols)

                # Render styled table
                st.write(styled)
            else:
                st.warning("Could not load targets.csv file.")

            st.markdown("---")



        # =========================================================================
        # TABLE DISPLAY FOR RAW DATA AND STATISTICS - SELECTION OPTIONS
        # =========================================================================
        if show_stats_table or show_files:
        
            st.subheader("Tables to check RAW Data and Statistics")
            
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                sel_analysis_type = st.selectbox("Analysis Type", analysis_types_list, key="shared_analysis")
                sel_analysis_config = ANALYSIS_TYPES[sel_analysis_type]
                sel_calculate_stats = sel_analysis_config.get("calculate_stats", True)  # if you use this flag
                sel_param_groups = list(sel_analysis_config['parameters'].keys())

            # Load the dataframe for the chosen analysis type
            # (this should be the SAME df you later use for plots/stats)
            df_analysis = get_cached_data(sel_analysis_type, remove_outliers, sigma_threshold)

            if df_analysis is None or df_analysis.empty:
                st.warning("No data available for the selected analysis type.")
                selected_row = None
            else:
                # Target options depend on analysis type
                all_targets = sorted(df_analysis["Target"].dropna().unique().tolist())
                with col2:
                    sel_target = st.selectbox("Target", all_targets, key="shared_target")

                df_t = df_analysis[df_analysis["Target"] == sel_target].copy()

                # Year options depend on analysis type + target
                available_years = sorted(df_t["Date of visit"].dt.year.dropna().unique().tolist())
                with col3:
                    sel_year = st.selectbox("Year", available_years, key="shared_year") if available_years else None

                selected_row = None
                with col4:
                    if sel_year is not None:
                        df_ty = df_t[df_t["Date of visit"].dt.year == sel_year].sort_values("Date of visit").copy()

                        if not df_ty.empty:
                            df_ty["file_label"] = (
                                df_ty["Date of visit"].dt.strftime("%Y-%m-%d")
                                + " — " + df_ty["file"].astype(str)
                            )

                            sel_label = st.selectbox("File", df_ty["file_label"].tolist(), key="shared_file")
                            selected_row = df_ty.loc[df_ty["file_label"] == sel_label].iloc[0]
                        else:
                            st.info("No files for this target/year.")
                    else:
                        st.info("No years available for this target.")

        

            df = df_analysis
            filtered_df = df_analysis[df_analysis["Target"] == sel_target].copy() if (df_analysis is not None and not df_analysis.empty) else pd.DataFrame()

            
        # =========================================================================
        # STATISTICS TABLE SECTION (depends on selection upper)
        # =========================================================================
        if show_stats_table and sel_calculate_stats:
            st.subheader("Statistics Table")
            st.caption("Calculated statistics for the selected Analysis type/Target/Year/File")

            if selected_row is None:
                st.info("Select Analysis type, Target, Year and File in the Data selection section above.")
            else:
                st.markdown(
                    f"**Statistics for {sel_target} — {selected_row['Date of visit'].strftime('%Y-%m-%d')}**"
                )

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
                    stats_df = pd.DataFrame(stats_data)
                    st.dataframe(stats_df, use_container_width=True)
                else:
                    st.warning("No statistics available for selected parameters.")

            st.markdown("---")
        elif show_stats_table and not sel_calculate_stats:
            st.info(f"{sel_analysis_type} does not calculate statistics - showing direct values instead.")
            st.markdown("---")
       
        
        # =========================================================================
        # RAW DATA VIEWER SECTION (depends on selections upper)
        # =========================================================================
        if show_files:
            st.subheader(f"Raw FITS Data for {sel_analysis_type}")
            st.caption("Raw table rows from the SAME observation selected in the Statistics Table")

            # We can only show raw data if the user already selected a row in Statistics table
            if not (show_stats_table and sel_calculate_stats):
                st.info("Enable the Statistics Table and select Analysis Type/ Target/Year/File there to view raw data.")
            elif "selected_row" not in locals() or selected_row is None:
                st.info("Select Target, Year and File in the Statistics Table above.")
            else:
                # Use the exact file selected in Statistics table
                selected_file = selected_row.get("file", None)

                if not selected_file or pd.isna(selected_file):
                    st.warning("Selected statistics row has no 'file' value.")
                else:
                    from data_loader import load_raw_fits_data

                    raw_data = load_raw_fits_data(sel_analysis_type, selected_file)

                    if raw_data is not None and not raw_data.empty:
                        st.success(f"Loaded {len(raw_data)} rows from {selected_file}")

                        max_rows = st.slider("Max rows to display", 10, 10000, 1000, step=100, key="raw_max_rows")
                        st.dataframe(raw_data.head(max_rows), use_container_width=True)

                        st.caption(f"Columns: {', '.join(raw_data.columns.tolist())}")
                    else:
                        st.warning("Could not load raw data from this file.")

            st.markdown("---")




        
        # Prepare year formatting for plots
        year_shapes = get_year_separators(filtered_df['Date of visit'])
        year_tickvals, year_ticktext,year_x_range = get_year_ticks(filtered_df['Date of visit'])
        



        st.header(f"Evolution of {analysis_type} Statistics for {selected_target}")
        # =========================================================================
        # STATISTICS ANALYSIS (for most analysis types)
        # =========================================================================
        if calculate_stats:
            # Filter to only available columns
            stat_columns = get_stat_columns(analysis_type)
            filtered_stat_columns = {}
            for group in selected_groups:
                if group in stat_columns:
                    available = [c for c in stat_columns[group] if c in filtered_df.columns]
                    if available:
                        filtered_stat_columns[group] = available
            
            # ---------------------------------------------------------------------
            # CORRELATION ANALYSIS SECTION
            # ---------------------------------------------------------------------
            if show_correlation:
                st.subheader("Correlation Analysis (Dual Y-Axis)")
                st.caption("Compare any statistic from any analysis type on the same plot")
                
                # Get analysis types that have plottable data
                analysis_for_corr = [at for at in analysis_types_list 
                                      if ANALYSIS_TYPES[at].get('calculate_stats', True) or ANALYSIS_TYPES[at].get('direct_columns')]
                
                col_left, col_right = st.columns(2)
                
                # Left axis selectors
                with col_left:
                    st.markdown("**Left Y-Axis (Blue)**")
                    left_analysis = st.selectbox("Analysis Type", analysis_for_corr, 
                                                  index=analysis_for_corr.index(analysis_type) if analysis_type in analysis_for_corr else 0, 
                                                  key="left_analysis")
                    left_groups = list(ANALYSIS_TYPES[left_analysis]['parameters'].keys())
                    left_group = st.selectbox("Parameter Group", left_groups, key="left_group")
                    left_stats = get_available_stats(left_analysis, left_group)
                    left_stat = st.selectbox("Statistic", left_stats, key="left_stat") if left_stats else None
                
                # Right axis selectors
                with col_right:
                    st.markdown("**Right Y-Axis (Orange)**")
                    right_analysis = st.selectbox("Analysis Type", analysis_for_corr,
                                                   index=analysis_for_corr.index(analysis_type) if analysis_type in analysis_for_corr else 0,
                                                   key="right_analysis")
                    right_groups = list(ANALYSIS_TYPES[right_analysis]['parameters'].keys())
                    right_group = st.selectbox("Parameter Group", right_groups, key="right_group")
                    right_stats = get_available_stats(right_analysis, right_group)
                    right_stat = st.selectbox("Statistic", right_stats, 
                                               index=min(1, len(right_stats)-1) if right_stats else 0, 
                                               key="right_stat") if right_stats else None
                
                # Create dual-axis plot if both stats selected
                if left_stat and right_stat:
                    left_df = get_cached_data(left_analysis, remove_outliers, sigma_threshold)
                    right_df = get_cached_data(right_analysis, remove_outliers, sigma_threshold)
                    
                    # Filter to selected target and date
                    left_target_df = left_df[(left_df['Target'] == selected_target) & 
                                              (left_df['Date of visit'].dt.date <= end_date)].sort_values('Date of visit') if not left_df.empty else pd.DataFrame()
                    right_target_df = right_df[(right_df['Target'] == selected_target) & 
                                                (right_df['Date of visit'].dt.date <= end_date)].sort_values('Date of visit') if not right_df.empty else pd.DataFrame()
                    
                    left_ok = not left_target_df.empty and left_stat in left_target_df.columns
                    right_ok = not right_target_df.empty and right_stat in right_target_df.columns
                    
                    if left_ok and right_ok:
                        fig = create_dual_axis_plot(
                            left_target_df['Date of visit'], left_target_df[left_stat], f"{left_analysis}: {left_stat}",
                            right_target_df['Date of visit'], right_target_df[right_stat], f"{right_analysis}: {right_stat}",
                            selected_target, plot_mode, year_shapes, year_tickvals, year_ticktext, year_x_range
                        )
                        st.plotly_chart(fig, width='stretch')
                    else:
                        missing = []
                        if not left_ok:
                            missing.append(f"Left ({left_analysis}: {left_stat})")
                        if not right_ok:
                            missing.append(f"Right ({right_analysis}: {right_stat})")
                        st.warning(f"No data for: {', '.join(missing)}")
                else:
                    st.info("Select statistics for both axes to display correlation plot.")
                
                st.markdown("---")
            
            # ---------------------------------------------------------------------
            # INDIVIDUAL STATISTIC PLOTS SECTION
            # ---------------------------------------------------------------------
            st.subheader("Statistic Plots")
            
            # Display plots for each selected parameter group
            for group_name in selected_groups:
                if group_name not in filtered_stat_columns:
                    continue
                
                cols = filtered_stat_columns[group_name]
                if not cols:
                    continue
                
                st.markdown(f"#### {group_name}")
                
                # Display plots in pairs (2 columns)
                for i in range(0, len(cols), 2):
                    left = cols[i]
                    right = cols[i + 1] if i + 1 < len(cols) else None
                    
                    # Show statistic definitions
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"**{left}**: {get_stat_definition(left)}")
                    with col2:
                        if right:
                            st.caption(f"**{right}**: {get_stat_definition(right)}")
                    
                    # Show plots
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = create_plot(filtered_df, left, plot_mode, year_shapes, year_tickvals, year_ticktext,year_x_range)
                        st.plotly_chart(fig, width='stretch')
                    with col2:
                        if right:
                            fig = create_plot(filtered_df, right, plot_mode, year_shapes, year_tickvals, year_ticktext,year_x_range)
                            st.plotly_chart(fig, width='stretch')
        
        # =========================================================================
        # DIRECT VALUES (for PSF Shape analysis)
        # =========================================================================
        else:
            st.subheader("Direct Parameter Values")
            st.info("This analysis shows raw values from FITS files without statistics.")
            
            # Display plots for each parameter group
            for group_name in selected_groups:
                if group_name not in analysis_config['parameters']:
                    continue
                group_cols = [c for c in analysis_config['parameters'][group_name] if c in filtered_df.columns]
                if not group_cols:
                    continue
                
                st.markdown(f"### {group_name}")
                for col in group_cols:
                    st.markdown(f"#### {col}")
                    fig = create_plot(filtered_df, col, plot_mode, year_shapes, year_tickvals, year_ticktext,year_x_range)
                    st.plotly_chart(fig, width='stretch')
        
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
