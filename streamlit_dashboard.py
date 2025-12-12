import os
import re
import pandas as pd
import streamlit as st
import altair as alt
import plotly.express as px
from datetime import datetime, timedelta

# --------------------------
# 1. DevIntel Branding & Configuration
# --------------------------
st.set_page_config(
    page_title="DevIntel - Melaka Property Competitor Intelligence",
    page_icon="📊",
    layout="wide"
)

# Custom CSS (DevIntel Branding + Improved Readability)
st.markdown("""
    <style>
    /* Tier cards */
    .tier-card {
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        height: 100%;
        color: white; /* White text for Pro card contrast */
    }
    .basic-tier {
        border: 2px solid #218838;
        background-color: #f8f9fa;
        color: #000; /* Black text for Basic card */
    }
    .pro-tier {
        border: 2px solid #007bff;
        background-color: #1967d2;
    }
    /* Pricing text */
    .price {
        font-size: 2.5rem;
        font-weight: bold;
        color: #fbbc05;
    }
    .tier-title {
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    /* Feature list */
    .feature {
        margin: 0.8rem 0;
        font-size: 1rem;
    }
    .feature-check {
        color: #34d399; /* Lighter green for Pro card visibility */
        font-weight: bold;
    }
    .feature-cross {
        color: #f87171; /* Lighter red for Pro card visibility */
        font-weight: bold;
    }
    .basic-tier .feature-check {
        color: #218838; /* Original green for Basic */
    }
    .basic-tier .feature-cross {
        color: #dc3545; /* Original red for Basic */
    }
    /* DevIntel Header */
    .devintel-header {
        color: #007bff;
        font-weight: bold;
        font-size: 2rem; /* Larger header */
    }
    /* Metric styling */
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------
# 2. Competitor Configuration (CSV = Total Projects | XLSX = Project Details)
# --------------------------
# Define all available pemajus (3 total: Teladan, NKS, Scientex)
AVAILABLE_PEMAJUS = ["Teladan", "NKS", "SCIENTEX"]
# Tier limits
TIER_LIMITS = {
    "Basic": 1,  # Max 1 pemaju
    "Pro": 5     # Max 5 (only 3 available now)
}

# Exact Column Mapping (Shared for CSV/XLSX)
COLUMN_MAPPING = {
    "project_name": "Kod Projek & Nama Projek",  
    "no_unit": "No PT/Lot/Plot/No Unit",                  
    "harga_jualan": "Harga Jualan (RM)",                 
    "harga_spjb": "Harga SPJ (RM)",                  
    "status_jualan": "Status Jualan",               
    "kuota_bumi": "Kuota Bumi",                   
    "nama_pemaju": "Kod Pemaju & Nama Pemaju",    
    "scraped_date": "Scraped_Date"
}

# --------------------------
# 3. Data Path & File Logic (Separate CSV/XLSX - No Mixing!)
# --------------------------
# Force relative path (works for cloud/local)
DATA_DIR = "./data"

# Debug: Verify data folder (remove after testing)
st.write(f"🔍 Active Data Directory: {DATA_DIR}")
st.write(f"🔍 Files in Data Folder: {os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else 'Folder not found!'}")

# Separate file finders for CSV (total) and XLSX (details)
def _find_latest_csv(prefix: str):
    """Find latest CSV file (total projects summary)"""
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith(prefix) and f.endswith('.csv')]
        def _extract_date(name):
            m = re.search(r"_(\d{8})\.csv$", name)
            return m.group(1) if m else "00000000"
        files.sort(key=lambda x: _extract_date(x), reverse=True)
        return files[0] if files else None
    except Exception as e:
        st.error(f"Error finding CSV files for {prefix}: {str(e)}")
        return None

def _find_latest_xlsx(prefix: str):
    """Find latest XLSX file (project details with multiple sheets)"""
    try:
        files = [f for f in os.listdir(DATA_DIR) if f.startswith(prefix) and f.endswith('.xlsx')]
        def _extract_date(name):
            m = re.search(r"_(\d{8})\.xlsx$", name)
            return m.group(1) if m else "00000000"
        files.sort(key=lambda x: _extract_date(x), reverse=True)
        return files[0] if files else None
    except Exception as e:
        st.error(f"Error finding XLSX files for {prefix}: {str(e)}")
        return None

# Map pemajus to YOUR actual GitHub filenames (CSV/XLSX share the same prefix)
PEMAJU_FILES = {
    "Teladan": {
        "total_csv": _find_latest_csv("Teladan_MELAKA_PROJECT_DETAILS_") or "Teladan_MELAKA_PROJECT_DETAILS_20251212.csv",
        "details_xlsx": _find_latest_xlsx("Teladan_MELAKA_PROJECT_DETAILS_") or "Teladan_MELAKA_PROJECT_DETAILS_20251212.xlsx"
    },
    "NKS": {
        "total_csv": _find_latest_csv("NKS_MELAKA_PROJECT_DETAILS_") or "NKS_MELAKA_PROJECT_DETAILS_20251212.csv",
        "details_xlsx": _find_latest_xlsx("NKS_MELAKA_PROJECT_DETAILS_") or "NKS_MELAKA_PROJECT_DETAILS_20251212.xlsx"
    },
    "SCIENTEX": {
        "total_csv": _find_latest_csv("SCIENTEX_MELAKA_PROJECT_DETAILS_") or "SCIENTEX_MELAKA_PROJECT_DETAILS_20251212.csv",
        "details_xlsx": _find_latest_xlsx("SCIENTEX_MELAKA_PROJECT_DETAILS_") or "SCIENTEX_MELAKA_PROJECT_DETAILS_20251212.xlsx"
    }
}

# --------------------------
# 4. Helper Functions (CSV + XLSX Support)
# --------------------------
def format_rm(v):
    try:
        return f"RM {int(round(float(v))):,}"
    except Exception:
        return "RM 0"

def parse_rm(s):
    if pd.isna(s):
        return 0.0
    s = str(s).replace("RM", "").replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return 0.0

def load_xlsx_project_details(xlsx_file_path):
    """Load XLSX file with multiple sheets (1 sheet = 1 project)"""
    if not os.path.exists(xlsx_file_path):
        st.warning(f"XLSX file missing: {xlsx_file_path}")
        return pd.DataFrame()
    
    try:
        # Get all sheet names (each sheet = 1 project)
        xl_file = pd.ExcelFile(xlsx_file_path, engine="openpyxl")
        sheet_names = xl_file.sheet_names
        st.info(f"✅ Found {len(sheet_names)} projects (sheets) in XLSX: {sheet_names}")
        
        # Load all sheets into one DataFrame
        all_sheets = []
        for sheet in sheet_names:
            df_sheet = pd.read_excel(xlsx_file_path, sheet_name=sheet, engine="openpyxl")
            df_sheet["project_sheet_name"] = sheet  # Track which sheet (project) the data comes from
            all_sheets.append(df_sheet)
        
        # Combine all sheets (project details)
        combined_df = pd.concat(all_sheets, ignore_index=True)
        return combined_df
    
    except Exception as e:
        st.error(f"❌ Failed to load XLSX sheets: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def load_pemaju_data(pemaju_name, tier="Basic"):
    """Load CSV (total projects) + XLSX (project details) for a single pemaju"""
    if pemaju_name not in PEMAJU_FILES:
        st.error(f"❌ Pemaju not found: {pemaju_name}")
        return pd.DataFrame()
    
    # --------------------------
    # Step 1: Load CSV (Total Projects Summary)
    # --------------------------
    csv_file = PEMAJU_FILES[pemaju_name]["total_csv"]
    csv_path = os.path.join(DATA_DIR, csv_file)
    st.write(f"🔍 Loading CSV (total) for {pemaju_name}: {csv_path}")
    
    if not os.path.exists(csv_path):
        st.warning(f"⚠️ CSV (total projects) missing for {pemaju_name}: {csv_path}")
        csv_df = pd.DataFrame()
    else:
        try:
            csv_df = pd.read_csv(csv_path, encoding="utf-8-sig")
            csv_df["data_source"] = "total_csv"  # Tag total project data
            st.success(f"✅ Loaded CSV (total) for {pemaju_name}: {len(csv_df)} rows")
        except UnicodeDecodeError:
            csv_df = pd.read_csv(csv_path, encoding="latin-1")
            csv_df["data_source"] = "total_csv"
            st.success(f"✅ Loaded CSV (total) for {pemaju_name} (latin-1 encoding): {len(csv_df)} rows")
        except Exception as e:
            st.error(f"❌ Failed to load CSV for {pemaju_name}: {str(e)}")
            csv_df = pd.DataFrame()
    
    # --------------------------
    # Step 2: Load XLSX (Project Details with Multiple Sheets)
    # --------------------------
    xlsx_file = PEMAJU_FILES[pemaju_name]["details_xlsx"]
    xlsx_path = os.path.join(DATA_DIR, xlsx_file)
    st.write(f"🔍 Loading XLSX (details) for {pemaju_name}: {xlsx_path}")
    
    xlsx_df = load_xlsx_project_details(xlsx_path)
    if not xlsx_df.empty:
        xlsx_df["data_source"] = "details_xlsx"  # Tag project-level data
        st.success(f"✅ Loaded XLSX (details) for {pemaju_name}: {len(xlsx_df)} rows")
    
    # --------------------------
    # Step 3: Combine CSV + XLSX (if both exist)
    # --------------------------
    if csv_df.empty and xlsx_df.empty:
        st.warning(f"⚠️ No data (CSV/XLSX) found for {pemaju_name}")
        return pd.DataFrame()
    elif not csv_df.empty and xlsx_df.empty:
        combined_df = csv_df  # Only total CSV data
    elif csv_df.empty and not xlsx_df.empty:
        combined_df = xlsx_df  # Only XLSX details data
    else:
        # FIX: Safer merge logic (avoid errors if merge key is missing)
        merge_key = None
        if "project_name" in csv_df.columns and "project_name" in xlsx_df.columns:
            merge_key = "project_name"
        elif "Kod Projek & Nama Projek" in csv_df.columns and "Kod Projek & Nama Projek" in xlsx_df.columns:
            merge_key = "Kod Projek & Nama Projek"
        elif "project_sheet_name" in xlsx_df.columns:
            merge_key = "project_sheet_name"
        
        if merge_key:
            combined_df = pd.merge(
                csv_df, xlsx_df, 
                on=merge_key,
                how="outer",
                suffixes=("_csv", "_xlsx")
            )
        else:
            # If no merge key, just concatenate (avoid merge error)
            combined_df = pd.concat([csv_df, xlsx_df], ignore_index=True)
        st.success(f"✅ Combined CSV + XLSX for {pemaju_name}: {len(combined_df)} rows")
    
    # --------------------------
    # Step 4: Clean Combined Data (FIX: Add Fallbacks for Missing Columns)
    # --------------------------
    # Add pemaju identifier (critical for multi-pemaju aggregation)
    combined_df["pemaju"] = pemaju_name
    
    # Clean columns (map to standard names)
    combined_df.columns = [col.strip() for col in combined_df.columns]
    csv_columns_clean = {col.lower(): col for col in combined_df.columns}
    mapped_columns = {}
    for code_col, csv_col in COLUMN_MAPPING.items():
        csv_col_clean = csv_col.strip().lower()
        if csv_col_clean in csv_columns_clean:
            mapped_columns[csv_columns_clean[csv_col_clean]] = code_col
    combined_df = combined_df.rename(columns=mapped_columns)
    
    # FIX: Debug - Show columns after mapping (identify missing columns)
    st.write(f"🔍 Columns after mapping for {pemaju_name}: {combined_df.columns.tolist()}")
    
    # FIX: Force create critical text columns (with defaults)
    for col in ["project_name", "nama_pemaju", "status_jualan", "kuota_bumi", "scraped_date"]:
        if col not in combined_df.columns:
            st.warning(f"⚠️ '{col}' missing for {pemaju_name} – using default value")
            combined_df[col] = "Unknown"
        else:
            combined_df[col] = combined_df[col].astype(str).str.strip().fillna("Unknown")
    
    # FIX: Force create numeric columns (prevent KeyError in aggregation)
    # 1. Unit count (no_unit_num)
    if "no_unit" in combined_df.columns:
        combined_df["no_unit_num"] = pd.to_numeric(
            combined_df["no_unit"], 
            errors='coerce'
        ).fillna(1)
    else:
        st.warning(f"⚠️ 'no_unit' missing for {pemaju_name} – defaulting to 1 unit per row")
        combined_df["no_unit_num"] = 1
    
    # 2. Selling price (harga_jualan_num)
    if "harga_jualan" in combined_df.columns:
        combined_df["harga_jualan_num"] = combined_df["harga_jualan"].apply(parse_rm).fillna(0)
    else:
        st.warning(f"⚠️ 'harga_jualan' missing for {pemaju_name} – defaulting to RM 0")
        combined_df["harga_jualan_num"] = 0
    
    # 3. SPJ price (harga_spjb_num)
    if "harga_spjb" in combined_df.columns:
        combined_df["harga_spjb_num"] = combined_df["harga_spjb"].apply(parse_rm).fillna(0)
    else:
        st.warning(f"⚠️ 'harga_spjb' missing for {pemaju_name} – defaulting to RM 0")
        combined_df["harga_spjb_num"] = 0
    
    # Tier-specific date adjustment
    combined_df["scraped_date"] = datetime.now().strftime("%Y-%m-%d") if tier == "Pro" else (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    return combined_df

def load_aggregate_multiple_pemajus(selected_pemajus, tier="Basic"):
    """Load and aggregate data for multiple selected pemajus (FIX: Safe Aggregation)"""
    all_dfs = []
    for pemaju in selected_pemajus:
        df = load_pemaju_data(pemaju, tier)
        if not df.empty:
            all_dfs.append(df)
    
    if not all_dfs:
        st.warning("⚠️ No valid data frames loaded for selected pemajus")
        return pd.DataFrame(), {}
    
    # Combine all pemajus into one dataframe
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # FIX: Debug - Show final combined columns before aggregation
    st.write(f"🔍 Final combined columns (all pemajus): {combined_df.columns.tolist()}")
    
    # FIX: Safe Aggregation (try/except + fallbacks)
    try:
        project_agg = combined_df.groupby(["pemaju", "project_name"]).agg(
            total_units_per_project=("no_unit_num", "sum"),
            total_sales_per_project=("harga_jualan_num", "sum"),
            total_sales_spjb_per_project=("harga_spjb_num", "sum"),
            # FIX: Case-insensitive check + handle missing values
            units_sold_per_project=("status_jualan", lambda x: (x.str.lower().isin(["telah dijual", "terjual", "sold"])).sum()),
            units_unsold_per_project=("status_jualan", lambda x: (x.str.lower().isin(["belum dijual", "belum terjual", "unsold"])).sum()),
            bumi_units_per_project=("kuota_bumi", lambda x: (x.str.lower().isin(["ya", "bumi", "yes"])).sum()),
            non_bumi_units_per_project=("kuota_bumi", lambda x: (x.str.lower().isin(["tidak", "non-bumi", "no"])).sum()),
            nama_pemaju=("nama_pemaju", lambda x: x.iloc[0] if not x.empty else "Unknown Pemaju"),
            scraped_date=("scraped_date", lambda x: x.iloc[0] if not x.empty else datetime.now().strftime("%Y-%m-%d"))
        ).reset_index()
    except KeyError as e:
        st.error(f"❌ Aggregation KeyError: {e} – using fallback aggregation")
        # FIX: Fallback aggregation (minimal columns to avoid crash)
        project_agg = combined_df.groupby(["pemaju", "project_name"]).agg(
            total_units_per_project=("no_unit_num", "sum"),
            total_sales_per_project=("harga_jualan_num", "sum"),
            total_sales_spjb_per_project=("harga_spjb_num", "sum"),
            units_sold_per_project=lambda x: 0,
            units_unsold_per_project=lambda x: x["no_unit_num"].sum(),
            bumi_units_per_project=lambda x: 0,
            non_bumi_units_per_project=lambda x: x["no_unit_num"].sum(),
            nama_pemaju=lambda x: "Unknown Pemaju",
            scraped_date=lambda x: datetime.now().strftime("%Y-%m-%d")
        ).reset_index()
    
    # Add Pro-only metrics (prevent division by zero)
    if tier == "Pro":
        project_agg["pct_units_sold"] = (
            (project_agg["units_sold_per_project"] / project_agg["total_units_per_project"].replace(0, 1)) * 100
        ).round(2)
        project_agg["pct_bumi_units"] = (
            (project_agg["bumi_units_per_project"] / project_agg["total_units_per_project"].replace(0, 1)) * 100
        ).round(2)
    
    # Overall Metrics (across all selected pemajus)
    overall_metrics = {
        "total_pemajus": len(selected_pemajus),
        "total_projects": project_agg["project_name"].nunique(),
        "total_units": project_agg["total_units_per_project"].sum(),
        "total_sales": project_agg["total_sales_per_project"].sum(),
        "total_sales_spjb": project_agg["total_sales_spjb_per_project"].sum(),
        "total_units_sold": project_agg["units_sold_per_project"].sum(),
        "total_units_unsold": project_agg["units_unsold_per_project"].sum(),
        "total_bumi_units": project_agg["bumi_units_per_project"].sum(),
        "total_non_bumi_units": project_agg["non_bumi_units_per_project"].sum(),
        "scraped_date": project_agg["scraped_date"].iloc[0] if not project_agg.empty else datetime.now().strftime("%Y-%m-%d")
    }
    
    return project_agg, overall_metrics

# --------------------------
# 5. Main DevIntel Tiered Dashboard
# --------------------------
def main():
    # DevIntel Header (Improved)
    st.markdown("<h1 class='devintel-header'>DevIntel - Melaka Property Competitor Dashboard</h1>", unsafe_allow_html=True)
    st.caption("Data Source: TEDUH | Transforming & Empowering Data Usage In Housing")
    st.divider()

    # --------------------------
    # Step 1: DevIntel Tier Selection
    # --------------------------
    st.subheader("📋 DevIntel Pricing Tiers")
    col_tier1, col_tier2 = st.columns(2, gap="large")

    # Basic Tier Card (Updated: Better Contrast)
    with col_tier1:
        st.markdown(f"""
            <div class="tier-card basic-tier">
                <div class="tier-title">DevIntel Basic</div>
                <div class="price">RM349/month</div>
                <div class="feature"><span class="feature-check">✓</span> 1 pemaju tracked (Teladan/NKS/SCIENTEX)</div>
                <div class="feature"><span class="feature-check">✓</span> Core KPI Metrics (Units/Sales/Bumi)</div>
                <div class="feature"><span class="feature-check">✓</span> Weekly data sync</div>
                <div class="feature"><span class="feature-check">✓</span> Project-level table</div>
                <div class="feature"><span class="feature-cross">✗</span> Advanced analytics (% sold)</div>
                <div class="feature"><span class="feature-cross">✗</span> Price/sales alerts</div>
                <div class="feature"><span class="feature-cross">✗</span> Daily sync</div>
                <div class="feature"><span class="feature-cross">✗</span> Monthly strategy call</div>
            </div>
        """, unsafe_allow_html=True)

    # Pro Tier Card (Updated: Better Contrast)
    with col_tier2:
        st.markdown(f"""
            <div class="tier-card pro-tier">
                <div class="tier-title">DevIntel Pro</div>
                <div class="price">RM649/month</div>
                <div class="feature"><span class="feature-check">✓</span> Up to 5 pemajus tracked (3 available now)</div>
                <div class="feature"><span class="feature-check">✓</span> Core + Advanced KPI Metrics</div>
                <div class="feature"><span class="feature-check">✓</span> Daily real-time data sync</div>
                <div class="feature"><span class="feature-check">✓</span> Project-level table + analytics</div>
                <div class="feature"><span class="feature-check">✓</span> Advanced visuals (% units sold)</div>
                <div class="feature"><span class="feature-check">✓</span> Price/sales alert notifications</div>
                <div class="feature"><span class="feature-check">✓</span> Monthly 30min strategy call</div>
            </div>
        """, unsafe_allow_html=True)

    # Tier Toggle (Basic/Pro Preview)
    st.divider()
    tier_choice = st.radio(
        "Preview DevIntel Tier",
        options=["DevIntel Basic (RM349/month)", "DevIntel Pro (RM649/month)"],
        horizontal=True,
        help="Switch between Basic (1 pemaju) and Pro (up to 5 pemajus) previews"
    )
    current_tier = "Basic" if "Basic" in tier_choice else "Pro"
    st.write(f"🔍 Previewing: **{current_tier} Tier** | Pemaju Limit: {TIER_LIMITS[current_tier]} (Available: {len(AVAILABLE_PEMAJUS)}) | Sync: {'Weekly' if current_tier == 'Basic' else 'Daily'}")

    # --------------------------
    # Step 2: Tier-Specific Pemaju Selection
    # --------------------------
    st.sidebar.header(f"🔧 {current_tier} Tier - Select Pemaju")
    
    if current_tier == "Basic":
        # Basic: Only 1 pemaju selectable (dropdown)
        selected_pemajus = [st.sidebar.selectbox(
            "Select 1 Pemaju (Basic Limit)",
            options=AVAILABLE_PEMAJUS,
            index=0,  # Default to Teladan
            help="Basic tier allows tracking of 1 pemaju only"
        )]
    else:
        # Pro: Up to 5 pemajus (multi-select, max 3 available)
        selected_pemajus = st.sidebar.multiselect(
            f"Select Up to {TIER_LIMITS['Pro']} Pemajus (Pro Limit)",
            options=AVAILABLE_PEMAJUS,
            default=AVAILABLE_PEMAJUS,  # Select all 3 by default
            help="Pro tier allows tracking of up to 5 pemajus (3 available now)"
        )
        # Enforce Pro limit (even if more than 5 are added later)
        if len(selected_pemajus) > TIER_LIMITS["Pro"]:
            st.sidebar.error(f"Pro tier limit: Max {TIER_LIMITS['Pro']} pemajus!")
            selected_pemajus = selected_pemajus[:TIER_LIMITS["Pro"]]

    # --------------------------
    # Step 3: Load Data (Selected Pemajus)
    # --------------------------
    project_agg, overall = load_aggregate_multiple_pemajus(selected_pemajus, tier=current_tier)
    
    if project_agg.empty:
        st.warning("⚠️ No data available for selected pemajus")
        st.info("Check: \n1. CSV/XLSX files exist in the 'data' folder (cloud) or local path (local)\n2. File names match the fallback names in the code\n3. XLSX files have valid sheets (projects)")
        return

    # --------------------------
    # Step 4: Additional Tier-Specific Filters
    # --------------------------
    st.sidebar.markdown("---")
    st.sidebar.header(f"🔍 {current_tier} Tier - Filter Projects")
    
    # Project filter (depends on selected pemajus)
    available_projects = project_agg["project_name"].unique()
    if current_tier == "Pro":
        # Pro: Multi-project + price filters
        project_filter = st.sidebar.multiselect(
            "Select Projects",
            options=available_projects,
            default=available_projects,
            help="Filter to view specific projects"
        )
        min_price = st.sidebar.number_input(
            "Min Harga Jualan (RM)",
            min_value=0,
            value=0,
            help="Minimum selling price to filter projects"
        )
        max_price = st.sidebar.number_input(
            "Max Harga Jualan (RM)",
            min_value=0,
            value=int(overall["total_sales"]) if overall["total_sales"] > 0 else 1000000,
            help="Maximum selling price to filter projects"
        )
        
        # Pro: Alert Settings
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔔 DevIntel Pro Alerts")
        alert_sold = st.sidebar.checkbox("Alert on Units Sold > 50", help="Trigger alert for projects with >50 units sold")
        alert_price = st.sidebar.checkbox("Alert on Price > RM500k", help="Trigger alert for projects with total sales > RM500k")

        # Apply Pro Filters
        project_agg_filtered = project_agg[
            (project_agg["project_name"].isin(project_filter)) &
            (project_agg["total_sales_per_project"] >= min_price) &
            (project_agg["total_sales_per_project"] <= max_price)
        ]
    else:
        # Basic: Single project filter
        project_filter = st.sidebar.selectbox(
            "Select Project",
            options=["All"] + list(available_projects),
            index=0,
            help="Filter to view a specific project (or all)"
        )
        # Apply Basic Filter
        if project_filter != "All":
            project_agg_filtered = project_agg[project_agg["project_name"] == project_filter]
        else:
            project_agg_filtered = project_agg.copy()

    # --------------------------
    # Step 5: Core Metrics (Updated for Multiple Pemajus)
    # --------------------------
    st.markdown("---")
    st.header("📈 KPI Metrik Asas (Selected Pemajus)")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Pemajus", f"{int(overall['total_pemajus'])}")
        st.metric("Total Projek", f"{int(overall['total_projects'])}")
    with col2:
        st.metric("Total Unit", f"{int(overall['total_units'])}")
        st.metric("Total Unit Terjual", f"{int(overall['total_units_sold'])}")
    with col3:
        st.metric("Total Unit Belum Terjual", f"{int(overall['total_units_unsold'])}")
        st.metric("Total Sales (RM)", format_rm(overall["total_sales"]))
    with col4:
        st.metric("Total Bumi Units", f"{int(overall['total_bumi_units'])}")
        st.metric("Total Non-Bumi Units", f"{int(overall['total_non_bumi_units'])}")

    # Pro: Advanced Metrics
    if current_tier == "Pro":
        st.markdown("---")
        st.header("📊 DevIntel Pro Advanced Metrics")
        col_pro1, col_pro2 = st.columns(2)
        with col_pro1:
            sold_pct = (overall['total_units_sold']/overall['total_units']*100) if overall['total_units'] > 0 else 0.0
            st.metric("% Total Units Sold", f"{sold_pct:.2f}%")
            
            bumi_pct = (overall['total_bumi_units']/overall['total_units']*100) if overall['total_units'] > 0 else 0.0
            st.metric("% Bumi Units", f"{bumi_pct:.2f}%")
        with col_pro2:
            avg_price = overall['total_sales']/overall['total_units'] if overall['total_units'] > 0 else 0
            st.metric("Average Harga Jualan (RM)", format_rm(avg_price))
            st.metric("Total Sales SPJB (RM)", format_rm(overall['total_sales_spjb']))

    # --------------------------
    # Step 6: Project-Level Table (Updated with Pemaju Column)
    # --------------------------
    st.markdown("---")
    st.header("📋 Butiran Per Projek (By Pemaju)")
    
    # Basic Table Columns (with Pemaju)
    table_columns = {
        "pemaju": "Nama Pemaju",
        "project_name": "Kod Projek & Nama Projek",
        "total_units_per_project": "Total Unit",
        "units_sold_per_project": "Unit Terjual",
        "units_unsold_per_project": "Unit Belum Terjual",
        "total_sales_per_project": "Jumlah Jualan (RM)",
        "bumi_units_per_project": "Unit Bumi",
        "non_bumi_units_per_project": "Unit Non-Bumi"
    }

    # Add Pro-Only Columns
    if current_tier == "Pro":
        table_columns["pct_units_sold"] = "% Unit Terjual"
        table_columns["pct_bumi_units"] = "% Unit Bumi"

    # Prepare Table
    available_table_cols = [code_col for code_col, display_col in table_columns.items() if code_col in project_agg_filtered.columns]
    project_table = project_agg_filtered[available_table_cols].copy()
    project_table.rename(columns={code_col: display_col for code_col, display_col in table_columns.items() if code_col in project_table.columns}, inplace=True)
    
    if "Jumlah Jualan (RM)" in project_table.columns:
        project_table["Jumlah Jualan (RM)"] = project_table["Jumlah Jualan (RM)"].apply(format_rm)
    
    # Add table caption
    st.caption("Click on column headers to sort data (e.g., sort by 'Unit Terjual' to see top-selling projects)")
    st.dataframe(project_table, use_container_width=True, hide_index=True)

    # --------------------------
    # Step 7: Visualizations (Updated for Multiple Pemajus)
    # --------------------------
    st.markdown("---")
    st.header("📊 Visualisasi Data (By Pemaju)")
    
    # Basic Visuals (Shared)
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        # Units Sold by Pemaju + Project
        chart_units = alt.Chart(project_agg_filtered).mark_bar().encode(
            x=alt.X("project_name:N", title="Projek", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("units_sold_per_project:Q", title="Unit Terjual"),
            color="pemaju:N",
            tooltip=["pemaju:N", "project_name:N", "units_sold_per_project:Q"]
        ).properties(title="Unit Terjual Per Projek (By Pemaju)", width=400, height=300)
        st.altair_chart(chart_units, use_container_width=True)

    with col_v2:
        # Total Sales by Pemaju
        sales_by_pemaju = project_agg_filtered.groupby("pemaju")["total_sales_per_project"].sum().reset_index()
        chart_sales = alt.Chart(sales_by_pemaju).mark_pie().encode(
            theta="total_sales_per_project:Q",
            color="pemaju:N",
            tooltip=["pemaju:N", alt.Tooltip("total_sales_per_project:Q", format=",.0f", title="Total Sales (RM)")]
        ).properties(title="Total Sales By Pemaju", width=400, height=300)
        st.altair_chart(chart_sales, use_container_width=True)

    # Pro-Only Visualizations
    if current_tier == "Pro":
        st.subheader("🔍 DevIntel Pro Advanced Visuals")
        col_pro_v1, col_pro_v2 = st.columns(2)
        with col_pro_v1:
            # % Units Sold by Pemaju + Project
            chart_pct_sold = px.bar(
                project_agg_filtered,
                x="project_name",
                y="pct_units_sold",
                color="pemaju",
                title="% Unit Terjual Per Projek (By Pemaju)",
                labels={"pct_units_sold": "% Unit Terjual", "project_name": "Projek"},
                color_continuous_scale="greens",
                hover_data=["total_units_per_project", "units_sold_per_project"]
            )
            chart_pct_sold.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(chart_pct_sold, use_container_width=True)
        
        with col_pro_v2:
            # Bumi Units by Pemaju
            bumi_by_pemaju = project_agg_filtered.groupby("pemaju")[["bumi_units_per_project", "non_bumi_units_per_project"]].sum().reset_index()
            bumi_by_pemaju_melted = bumi_by_pemaju.melt(
                id_vars=["pemaju"],
                value_vars=["bumi_units_per_project", "non_bumi_units_per_project"],
                var_name="Unit Type",
                value_name="Jumlah"
            )
            bumi_by_pemaju_melted["Unit Type"] = bumi_by_pemaju_melted["Unit Type"].replace({
                "bumi_units_per_project": "Bumi",
                "non_bumi_units_per_project": "Non-Bumi"
            })
            chart_bumi_pemaju = px.bar(
                bumi_by_pemaju_melted,
                x="pemaju",
                y="Jumlah",
                color="Unit Type",
                title="Unit Bumi vs Non-Bumi (By Pemaju)",
                barmode="group",
                hover_data=["Jumlah"]
            )
            st.plotly_chart(chart_bumi_pemaju, use_container_width=True)

    # --------------------------
    # Step 8: Pro-Only Alerts Simulation
    # --------------------------
    if current_tier == "Pro":
        st.markdown("---")
        st.header("🔔 DevIntel Pro Alert Simulation")
        
        # Alert 1: Units Sold > 50
        high_sales_projects = project_agg_filtered[project_agg_filtered["units_sold_per_project"] > 50]
        if alert_sold and not high_sales_projects.empty:
            st.success(f"⚠️ ALERT: {len(high_sales_projects)} projek dengan Unit Terjual > 50!")
            st.dataframe(
                high_sales_projects[["pemaju", "project_name", "units_sold_per_project"]],
                hide_index=True,
                column_config={
                    "pemaju": "Nama Pemaju",
                    "project_name": "Projek",
                    "units_sold_per_project": "Unit Terjual"
                }
            )
        elif alert_sold and high_sales_projects.empty:
            st.info("ℹ️ No projects with >50 units sold (alert not triggered)")
        
        # Alert 2: Price > RM500k
        high_price_projects = project_agg_filtered[project_agg_filtered["total_sales_per_project"] > 500000]
        if alert_price and not high_price_projects.empty:
            st.success(f"⚠️ ALERT: {len(high_price_projects)} projek dengan Harga > RM500k!")
            high_price_display = high_price_projects[["pemaju", "project_name", "total_sales_per_project"]].copy()
            high_price_display["total_sales_per_project"] = high_price_display["total_sales_per_project"].apply(format_rm)
            high_price_display.rename(columns={"total_sales_per_project": "Jumlah Jualan (RM)"}, inplace=True)
            st.dataframe(high_price_display, hide_index=True)
        elif alert_price and high_price_projects.empty:
            st.info("ℹ️ No projects with total sales > RM500k (alert not triggered)")

    # --------------------------
    # Step 9: DevIntel CTA Footer (Improved)
    # --------------------------
    st.markdown("---")
    st.subheader("💼 Upgrade to DevIntel Pro")
    st.markdown(f"""
        <div style="background-color: #e8f4f8; padding: 1.5rem; border-radius: 8px;">
            <ul>
                <li>Track up to 5 pemajus (vs 1 in Basic) – currently available: {', '.join(AVAILABLE_PEMAJUS)}</li>
                <li>Daily real-time data sync (vs weekly in Basic)</li>
                <li>Advanced analytics and custom price/sales alerts</li>
                <li>Monthly strategy call with our property intelligence experts</li>
                <li>Priority support and custom report generation</li>
            </ul>
            <p style="font-weight: bold; margin-top: 1rem;">📧 Contact: sales@devintel.com | 📞 +6012-3456789</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
