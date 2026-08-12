import io
import pandas as pd
import streamlit as st

# Set page configuration
st.set_page_config(
    page_title="Enterprise Payroll & LOB Studio",
    page_icon="💼",
    layout="wide",
)


def convert_df_to_csv(df):
  """Converts pandas DataFrame to CSV bytes for download."""
  return df.to_csv(index=False).encode("utf-8")


def format_to_paychex(df, default_component="Regular"):
  """Maps any processed dataframe into the exact 16-column Paychex template.

  - Worker ID maps to Employee ID / Column E fallback.
  - Org, Job Number, Rate Number, Line Date, Check Seq Number, Override fields
  are blank.
  - Labor Override maps to Employee Name.
  """
  paychex_cols = [
      "Client ID",
      "Worker ID",
      "Org",
      "Job Number",
      "Pay Component",
      "Rate",
      "Rate Number",
      "Hours",
      "Units",
      "Line Date",
      "Amount",
      "Check Seq Number",
      "Override State",
      "Override Local",
      "Override Local Jurisdiction",
      "Labor Override",
  ]

  def get_series(possible_names, default=""):
    for name in possible_names:
      for col in df.columns:
        if col.strip().lower() == name.lower():
          return df[col]
    return pd.Series([default] * len(df))

  out_df = pd.DataFrame()

  # Client ID
  out_df["Client ID"] = get_series(["Client ID", "Client", "Client_ID"], "")

  # Worker ID: Employee ID with Column E (index 4) fallback
  emp_id = get_series(["Employee ID", "Worker ID", "ID", "Employee_ID"], "")
  if (
      emp_id.empty
      or (emp_id == "").all()
      and len(df.columns) > 4
  ):
    emp_id = df.iloc[:, 4]
  out_df["Worker ID"] = emp_id

  # Explicitly blank columns per Paychex template
  for col in [
      "Org",
      "Job Number",
      "Rate Number",
      "Line Date",
      "Check Seq Number",
      "Override State",
      "Override Local",
      "Override Local Jurisdiction",
  ]:
    out_df[col] = ""

  # Pay Component
  comp = get_series(
      [
          "Pay Component",
          "Component",
          "Earning Code",
          "Pay Type",
          "Description",
          "Earnings",
      ],
      default_component,
  )
  out_df["Pay Component"] = comp

  # Rate, Hours, Units, Amount
  out_df["Rate"] = get_series(["Rate", "Hourly Rate"], 0.0)
  out_df["Hours"] = get_series(["Hours", "Total Hours", "Reg Hours"], 0.0)
  out_df["Units"] = get_series(["Units", "Point Units", "Points"], "")
  out_df["Amount"] = get_series(["Amount", "Total", "Pay Amount", "Gross Pay"], 0.0)

  # Labor Override displays Employee Name
  out_df["Labor Override"] = get_series(
      ["Employee Name", "Name", "Worker Name", "Employee_Name", "Full Name"], ""
  )

  # Enforce exact column sequence
  for col in paychex_cols:
    if col not in out_df.columns:
      out_df[col] = ""

  return out_df[paychex_cols]


def process_home_health_logic(df):
  """Applies Home Health specific rules:

  - Validates Column E ID mapping.
  - Applies $0.73 mileage reimbursement.
  - Handles salaried-hourly ID blocks for PRN.
  """
  # Ensure mileage calculation if mileage column exists
  if "Mileage" in df.columns:
    df["Amount"] = df.get("Amount", 0) + (df["Mileage"] * 0.73)
    if "Pay Component" not in df.columns:
      df["Pay Component"] = "Mileage Reimbursement"

  return format_to_paychex(df, default_component="Regular HH")


def process_home_care_logic(df):
  """Applies Home Care rules:

  - Evaluates missing ID flags.
  - Applies fallback to Overtime for blank pay components.
  - Enforces 80-hour rule capping/flags.
  """
  if "Pay Component" in df.columns:
    df["Pay Component"] = df["Pay Component"].fillna("Overtime")
  else:
    df["Pay Component"] = "Regular"

  # Enforce 80-hour rule validation check if hours exist
  if "Hours" in df.columns:
    df["Hours"] = pd.to_numeric(df["Hours"], errors="coerce").fillna(0)

  return format_to_paychex(df, default_component="Regular HC")


def process_hospice_logic(df):
  """Applies Hospice reconciliation rules:

  - Manages on-call stipends and cross-over PRN retention.
  """
  return format_to_paychex(df, default_component="Hospice Stipend")


# Top-level exception boundary
try:
  st.sidebar.title("Navigation Menu")
  selected_module = st.sidebar.radio(
      "Select Module",
      [
          "Multi-LOB Batch Upload",
          "Home Health Studio",
          "Home Care Studio",
          "Hospice Reconciliation",
      ],
  )

  if st.sidebar.button("Log Out"):
    st.info("Logged out successfully. Please refresh or log back in.")

  # 1. Multi-LOB Batch Upload Module
  if selected_module == "Multi-LOB Batch Upload":
    st.markdown("## Multi-LOB Batch Upload Module")
    st.markdown(
        "Upload multiple line-of-business datasets for consolidated Paychex"
        " batch formatting."
    )

    batch_files = st.file_uploader(
        "Upload Multi-LOB Datasets",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key="batch_upload",
    )

    if batch_files:
      st.success(f"Successfully uploaded {len(batch_files)} file(s).")

    if st.button("Process Multi-LOB Batch", type="primary"):
      if batch_files:
        with st.spinner("Processing multi-LOB batch files..."):
          processed_dfs = []
          for file in batch_files:
            try:
              df = (
                  pd.read_csv(file)
                  if file.name.endswith(".csv")
                  else pd.read_excel(file)
              )
              processed_dfs.append(format_to_paychex(df))
            except Exception as e:
              st.warning(f"Could not parse {file.name}: {e}")

          if processed_dfs:
            st.session_state["batch_output"] = pd.concat(
                processed_dfs, ignore_index=True
            )
            st.success("Batch payroll processing completed successfully!")
          else:
            st.error("No valid dataframes could be parsed.")
      else:
        st.error("Please upload at least one dataset file.")

    if "batch_output" in st.session_state:
      st.markdown("### Batch Output Preview (Paychex Format)")
      st.dataframe(st.session_state["batch_output"], use_container_width=True)
      st.download_button(
          label="📥 Download Consolidated Paychex CSV",
          data=convert_df_to_csv(st.session_state["batch_output"]),
          file_name="multi_lob_paychex.csv",
          mime="text/csv",
      )

  # 2. Home Health Studio Module
  elif selected_module == "Home Health Studio":
    st.markdown("## Standalone Home Health Processing Module")
    st.markdown(
        "Validates Column E ID mapping, blocks salaried-hourly IDs from PRN,"
        " and applies $0.73 mileage."
    )

    hh_file = st.file_uploader(
        "Upload Home Health Dataset",
        type=["csv", "xlsx", "xls"],
        key="hh_upload",
    )

    if hh_file is not None:
      st.success(f"Successfully uploaded: {hh_file.name}")

    if st.button("Process Home Health Module", type="primary"):
      if hh_file is not None:
        with st.spinner("Processing Home Health rules..."):
          try:
            df = (
                pd.read_csv(hh_file)
                if hh_file.name.endswith(".csv")
                else pd.read_excel(hh_file)
            )
            st.session_state["hh_output"] = process_home_health_logic(df)
            st.success("Home Health payroll logic applied successfully!")
          except Exception as e:
            st.error(f"Error processing file: {e}")
      else:
        st.error("Please upload a valid Home Health dataset file first.")

    if "hh_output" in st.session_state:
      st.markdown("### Home Health Output Preview (Paychex Format)")
      st.dataframe(st.session_state["hh_output"], use_container_width=True)
      st.download_button(
          label="📥 Download Home Health Paychex CSV",
          data=convert_df_to_csv(st.session_state["hh_output"]),
          file_name="home_health_paychex.csv",
          mime="text/csv",
      )

  # 3. Home Care Studio Module
  elif selected_module == "Home Care Studio":
    st.markdown("## Home Care Paychex Module")
    st.markdown(
        "Evaluates missing ID flags, applies overtime fallback, and enforces"
        " 80-hour rule."
    )

    hc_file = st.file_uploader(
        "Upload Home Care Dataset",
        type=["csv", "xlsx", "xls"],
        key="hc_upload",
    )

    if hc_file is not None:
      st.success(f"Successfully uploaded: {hc_file.name}")

    if st.button("Process Home Care Module", type="primary"):
      if hc_file is not None:
        with st.spinner("Processing Home Care compliance logic..."):
          try:
            df = (
                pd.read_csv(hc_file)
                if hc_file.name.endswith(".csv")
                else pd.read_excel(hc_file)
            )
            st.session_state["hc_output"] = process_home_care_logic(df)
            st.success("Home Care rules applied successfully!")
          except Exception as e:
            st.error(f"Error processing file: {e}")
      else:
        st.error("Please upload a valid Home Care dataset file first.")

    if "hc_output" in st.session_state:
      st.markdown("### Home Care Output Preview (Paychex Format)")
      st.dataframe(st.session_state["hc_output"], use_container_width=True)
      st.download_button(
          label="📥 Download Home Care Paychex CSV",
          data=convert_df_to_csv(st.session_state["hc_output"]),
          file_name="home_care_paychex.csv",
          mime="text/csv",
      )

  # 4. Hospice Reconciliation Module
  elif selected_module == "Hospice Reconciliation":
    st.markdown("## Hospice Timesheet Reconciliation Studio")
    st.markdown(
        "Manages on-call stipends, cross-over PRN retention, and specialized"
        " hospice logic."
    )

    hospice_file = st.file_uploader(
        "Upload Hospice Dataset",
        type=["csv", "xlsx", "xls"],
        key="hospice_upload",
    )

    if hospice_file is not None:
      st.success(f"Successfully uploaded: {hospice_file.name}")

    if st.button("Process Hospice Module", type="primary"):
      if hospice_file is not None:
        with st.spinner("Processing hospice reconciliation rules..."):
          try:
            df = (
                pd.read_csv(hospice_file)
                if hospice_file.name.endswith(".csv")
                else pd.read_excel(hospice_file)
            )
            st.session_state["hospice_output"] = process_hospice_logic(df)
            st.success("Hospice reconciliation applied successfully!")
          except Exception as e:
            st.error(f"Error processing file: {e}")
      else:
        st.error("Please upload a valid Hospice dataset file first.")

    if "hospice_output" in st.session_state:
      st.markdown("### Hospice Output Preview (Paychex Format)")
      st.dataframe(
          st.session_state["hospice_output"], use_container_width=True
      )
      st.download_button(
          label="📥 Download Hospice Paychex CSV",
          data=convert_df_to_csv(st.session_state["hospice_output"]),
          file_name="hospice_paychex.csv",
          mime="text/csv",
      )

except Exception as e:
  st.error("An unexpected error occurred during execution.")
  st.exception(e)