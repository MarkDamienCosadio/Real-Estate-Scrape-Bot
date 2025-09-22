import streamlit as st
import pandas as pd
import os
import subprocess

st.set_page_config(page_title="Listings Dashboard", layout="wide")
st.title("Real Estate Listings Dashboard")

csv_file = 'main_listing.csv'
orch_file = 'orchestrator.py'

# Load data


if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
else:
    st.warning(f"{csv_file} not found.")

# Trigger orchestrator

st.header("Get New Leads")
if st.button("Get Leads"):
    if os.path.exists(orch_file):
        result = subprocess.run(['python', orch_file], capture_output=True, text=True)
        st.success("Orchestrator script executed.")
        st.text(result.stdout)
        if result.stderr:
            st.error(result.stderr)
    else:
        st.error(f"{orch_file} not found.")

# Only show the filtered view
if os.path.exists(csv_file):
    st.sidebar.header("Filters")
    zipcodes_list = [
        '33009', '33019', '33119', '33128', '33129', '33130',
        '33131', '33139', '33140', '33141', '33149', '33154',
        '33160', '33180', '33239'
    ]
    zipcode = st.sidebar.selectbox("Zipcode", options=["Show All"] + zipcodes_list)
    source = st.sidebar.selectbox("Source", options=['Show All', 'ZLW', 'RLTR', 'RDFN'])
    sort_option = st.sidebar.selectbox("Sort By", options=["Newest", "Oldest", "Highest Price", "Lowest Price"])
    filtered = df.copy()
    if zipcode:
        if zipcode != "Show All":
            filtered = filtered[filtered['ZIPCODE'].astype(str) == zipcode]
    if source and source != 'Show All':
        filtered = filtered[filtered['SOURCE'] == source]
    # Sorting logic
    if sort_option == "Newest":
        if 'DAYS_ON_MARKET' in filtered.columns:
            def days_on_market_to_hours(val):
                if pd.isna(val):
                    return float('inf')
                val = str(val).strip().lower()
                if 'hour' in val:
                    try:
                        return int(val.split()[0])
                    except:
                        return float('inf')
                elif 'day' in val:
                    try:
                        return int(val.split()[0]) * 24
                    except:
                        return float('inf')
                else:
                    return float('inf')
            filtered = filtered.copy()
            filtered['DAYS_ON_MARKET_HOURS'] = filtered['DAYS_ON_MARKET'].apply(days_on_market_to_hours)
            filtered = filtered.sort_values(by='DAYS_ON_MARKET_HOURS', ascending=True)
            filtered = filtered.drop(columns=['DAYS_ON_MARKET_HOURS'])
    elif sort_option == "Oldest":
        if 'DAYS_ON_MARKET' in filtered.columns:
            def days_on_market_to_hours(val):
                if pd.isna(val):
                    return float('inf')
                val = str(val).strip().lower()
                if 'hour' in val:
                    try:
                        return int(val.split()[0])
                    except:
                        return float('inf')
                elif 'day' in val:
                    try:
                        return int(val.split()[0]) * 24
                    except:
                        return float('inf')
                else:
                    return float('inf')
            filtered = filtered.copy()
            filtered['DAYS_ON_MARKET_HOURS'] = filtered['DAYS_ON_MARKET'].apply(days_on_market_to_hours)
            filtered = filtered.sort_values(by='DAYS_ON_MARKET_HOURS', ascending=False)
            filtered = filtered.drop(columns=['DAYS_ON_MARKET_HOURS'])
    elif sort_option == "Highest Price":
        if 'PRICE' in filtered.columns:
            filtered = filtered.copy()
            def price_to_number(val):
                try:
                    val = str(val).replace('$', '').replace(',', '').strip()
                    return float(val)
                except:
                    return float('-inf')
            filtered['PRICE_NUM'] = filtered['PRICE'].apply(price_to_number)
            filtered = filtered.sort_values(by='PRICE_NUM', ascending=False)
            filtered = filtered.drop(columns=['PRICE_NUM'])
    elif sort_option == "Lowest Price":
        if 'PRICE' in filtered.columns:
            filtered = filtered.copy()
            def price_to_number(val):
                try:
                    val = str(val).replace('$', '').replace(',', '').strip()
                    return float(val)
                except:
                    return float('inf')
            filtered['PRICE_NUM'] = filtered['PRICE'].apply(price_to_number)
            filtered = filtered.sort_values(by='PRICE_NUM', ascending=True)
            filtered = filtered.drop(columns=['PRICE_NUM'])
    st.subheader("Listings")
    # Make URLs clickable
    if not filtered.empty:
        display_df = filtered.copy()
        # Rename headers: replace '_' with space
        display_df.columns = [col.replace('_', ' ') for col in display_df.columns]
        # Move Agent Phone and Email columns beside Agent Name
        agent_name_col = 'AGENT NAME'
        agent_phone_col = 'AGENT PHONE'
        email_col = 'EMAIL'
        # Ensure columns exist and are in correct order
        cols = list(display_df.columns)
        def move_col(cols, col, after_col):
            if col in cols and after_col in cols:
                cols.remove(col)
                idx = cols.index(after_col)
                cols.insert(idx+1, col)
            return cols
        if agent_name_col in cols and agent_phone_col in cols:
            cols = move_col(cols, agent_phone_col, agent_name_col)
        if agent_name_col in cols and email_col in cols:
            cols = move_col(cols, email_col, agent_phone_col if agent_phone_col in cols else agent_name_col)
        display_df = display_df[cols]
        # Add button beside agent name inside the cell, aligned right
        agent_col_name = 'AGENT NAME' if 'AGENT NAME' in display_df.columns else None

        for col in ['URL', 'MAPS_URL']:
            col_space = col.replace('_', ' ')
            if col_space in display_df.columns:
                display_df[col_space] = display_df[col_space].apply(lambda x: f'<a href="{x}" target="_blank">link</a>' if pd.notna(x) and str(x).startswith('http') else x)
        # Generate HTML table with ellipsis CSS, sticky header, and custom column widths
        # Inject inline style for Agent Phone column
        def inject_phone_width(html):
            import re
            # Find the Agent Phone column index
            cols = list(display_df.columns)
            try:
                phone_idx = cols.index('AGENT PHONE') + 1
            except ValueError:
                return html
            # Add style to th and td for Agent Phone
            html = re.sub(rf'(<th[^>]*>AGENT PHONE</th>)', r'<th style="width:150px;max-width:150px;min-width:150px;">AGENT PHONE</th>', html)
            html = re.sub(rf'(<td[^>]*)(>[^<]*</td>)', lambda m: m.group(1) + ' style="width:150px;max-width:150px;min-width:150px;"' + m.group(2) if m.start() and html[:m.start()].count('<td') % len(cols) == (phone_idx-1) else m.group(0), html)
            return html
        table_html = display_df.to_html(escape=False, index=False)
        table_html = inject_phone_width(table_html)
        css = '''<style>
        a {
            color: #ff9800 !important;
        }
        tr:hover td {
            background: #00897b !important;
        }
        th:nth-child(1), td:nth-child(1) {max-width: 100px; width: 100px;} /* Zipcode */
        th:nth-child(12), td:nth-child(12) {max-width: 100px; width: 100px;} /* Source */
        th:nth-child(3), td:nth-child(3) {max-width: 130px; width: 130px;} /* Price */
        .scroll-table-wrapper {
            max-height: 500px;
            overflow-y: auto;
            overflow-x: auto;
            border: 1px solid #ddd;
            display: block;
        }
        table {
            width: max-content;
            min-width: 100%;
            border-collapse: collapse;
            table-layout: auto;
        }
        td {text-overflow: ellipsis; white-space: nowrap; overflow: hidden;}
        th {
            position: sticky;
            top: 0;
            background: #f0f2f6;
            color: #333;
            z-index: 2;
            border-bottom: 2px solid #aaa;
            white-space: normal;
            text-overflow: unset;
            overflow: visible;
            text-align: center !important;
            vertical-align: middle;
            word-break: break-word;
        }
        th, td {padding: 4px;}
        /* Custom widths for specific columns */
        th:nth-child(2), td:nth-child(2) {
            max-width: 130px;
            width: 130px;
            white-space: normal;
            text-overflow: unset;
            overflow: visible;
        } /* MLS */
        th:nth-child(4), td:nth-child(4) {max-width: 280px; width: 280px;} /* Address */
        th:nth-child(5), td:nth-child(5) {max-width: 70px; width: 70px;} /* Beds */
        th:nth-child(6), td:nth-child(6) {max-width: 75px; width: 75px;} /* Baths */
        th:nth-child(7), td:nth-child(7) {max-width: 70px; width: 70px;} /* Sqft */
        th:nth-child(8), td:nth-child(8) {max-width: 70px; width: 70px;} /* URL */
        th:nth-child(9), td:nth-child(9) {max-width: 70px; width: 70px;} /* Maps URL */
        th:nth-child(10), td:nth-child(10) {max-width: 100px; width: 100px;} /* Days on the market */
        /* Make Agent Name fully readable */
        th, td {
            word-break: break-word;
        }
        /* Set Agent Name column width to 250px, allow horizontal scroll */
        th[data-label="AGENT NAME"], td[data-label="AGENT NAME"] {
            max-width: 250px !important;
            width: 250px !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        th[data-label="AGENT PHONE"], td[data-label="AGENT PHONE"] {
            width: 200px !important;
            max-width: 200px !important;
            min-width: 200px !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        /* Also target by column index for compatibility */
        th, td {
            word-break: break-word;
        }
        th:nth-child(3), td:nth-child(3) {
            width: 200px !important;
            max-width: 200px !important;
            min-width: 200px !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        th[data-label="EMAIL"], td[data-label="EMAIL"] {
            max-width: none !important;
            width: auto !important;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
        }
        /* Remove conflicting Agent Name full width rule */
        </style>'''
        st.markdown(css + f'<div class="scroll-table-wrapper">{table_html}</div>', unsafe_allow_html=True)
    else:
        st.info("No listings match the filter.")
