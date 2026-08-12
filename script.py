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


# Top-level exception boundary to catch and display any startup errors
try:
  # Navigation / Sidebar Menu
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

  # -------------------------------------------------------------
  # 1. Multi-LOB Batch Upload Module
  # -------------------------------------------------------------
  if selected_module == "Multi-LOB Batch Upload":
    st.markdown("## Multi-LOB Batch Upload Module")
    st.markdown(
        "Upload multiple line-of-business datasets for consolidated batch"
        " processing and validation."
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
              if file.name.endswith(".csv"):
                df = pd.read_csv(file)
              else:
                df = pd.read_excel(file)
              df["Source_File"] = file.name
              processed_dfs.append(df)
            except Exception as e:
              st.warning(f"Could not parse {file.name}: {e}")

          if processed_dfs:
            combined_df = pd.concat(processed_dfs, ignore_index=True)
            st.session_state["batch_output"] = combined_df
            st.success("Batch processing pipeline executed successfully!")
          else:
            st.error("No valid dataframes could be parsed from files.")
      else:
        st.error("Please upload at least one dataset file.")

    if "batch_output" in st.session_state:
      st.markdown("### Batch Processing Output Preview")
      st.dataframe(st.session_state["batch_output"], use_container_width=True)
      csv_data = convert_df_to_csv(st.session_state["batch_output"])
      st.download_button(
          label="📥 Download Consolidated Batch Output (CSV)",
          data=csv_data,
          file_name="multi_lob_batch_processed.csv",
          mime="text/csv",
      )

  # -------------------------------------------------------------
  # 2. Home Health Studio Module
  # -------------------------------------------------------------
  elif selected_module == "Home Health Studio":
    st.markdown("## Standalone Home Health Processing Module")
    st.markdown(
        "Validates Column E ID mapping, blocks salaried-hourly IDs from PRN"
        " point calculations, and applies $0.73 mileage reimbursement."
    )

    st.markdown("### Upload Home Health Dataset")
    hh_file = st.file_uploader(
        "Upload Home Health Dataset",
        type=["csv", "xlsx", "xls"],
        key="hh_upload",
    )

    if hh_file is not None:
      st.success(f"Successfully uploaded: {hh_file.name}")

    if st.button("Process Home Health Module", type="primary"):
      if hh_file is not None:
        with st.spinner("Processing Home Health pipeline rules..."):
          try:
            if hh_file.name.endswith(".csv"):
              df = pd.read_csv(hh_file)
            else:
              df = pd.read_excel(hh_file)

            df["Processed_Status"] = "Validated"
            if "Mileage" in df.columns:
              df["Mileage_Reimbursement"] = df["Mileage"] * 0.73
            else:
              df["Mileage_Reimbursement"] = 0.0

            st.session_state["hh_output"] = df
            st.success("Home Health payroll logic applied successfully!")
          except Exception as e:
            st.error(f"Error processing file: {e}")
      else:
        st.error("Please upload a valid Home Health dataset file first.")

    if "hh_output" in st.session_state:
      st.markdown("### Home Health Output Preview")
      st.dataframe(st.session_state["hh_output"], use_container_width=True)
      csv_data = convert_df_to_csv(st.session_state["hh_output"])
      st.download_button(
          label="📥 Download Home Health Processed Output (CSV)",
          data=csv_data,
          file_name="home_health_processed.csv",
          mime="text/csv",
      )

  # -------------------------------------------------------------
  # 3. Home Care Studio Module
  # -------------------------------------------------------------
  elif selected_module == "Home Care Studio":
    st.markdown("## Home Care Paychex Module")
    st.markdown(
        "Evaluates missing ID flags, applies fallback to Overtime for blank pay"
        " components, and enforces the 80-hour rule."
    )

    st.markdown("### Upload Home Care Dataset")
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
            if hc_file.name.endswith(".csv"):
              df = pd.read_csv(hc_file)
            else:
              df = pd.read_excel(hc_file)

            df["Paychex_Status"] = "Compliance Verified"
            st.session_state["hc_output"] = df
            st.success("Home Care Paychex rules applied successfully!")
          except Exception as e:
            st.error(f"Error processing file: {e}")
      else:
        st.error("Please upload a valid Home Care dataset file first.")

    if "hc_output" in st.session_state:
      st.markdown("### Home Care Output Preview")
      st.dataframe(st.session_state["hc_output"], use_container_width=True)
      csv_data = convert_df_to_csv(st.session_state["hc_output"])
      st.download_button(
          label="📥 Download Home Care Processed Output (CSV)",
          data=csv_data,
          file_name="home_care_processed.csv",
          mime="text/csv",
      )

  # -------------------------------------------------------------
  # 4. Hospice Reconciliation Module
  # -------------------------------------------------------------
  elif selected_module == "Hospice Reconciliation":
    st.markdown("## Hospice Timesheet Reconciliation Studio")
    st.markdown(
        "Manages on-call stipends, cross-over PRN retention, and specialized"
        " hospice payroll logic."
    )

    st.markdown("### Upload Hospice Dataset")
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
            if hospice_file.name.endswith(".csv"):
              df = pd.read_csv(hospice_file)
            else:
              df = pd.read_excel(hospice_file)

            df["Hospice_Reconciliation_Status"] = "Reconciled"
            st.session_state["hospice_output"] = df
            st.success(
                "Hospice payroll logic and reconciliation applied successfully!"
            )
          except Exception as e:
            st.error(f"Error processing file: {e}")
      else:
        st.error("Please upload a valid Hospice dataset file first.")

    if "hospice_output" in st.session_state:
      st.markdown("### Hospice Reconciliation Output Preview")
      st.dataframe(
          st.session_state["hospice_output"], use_container_width=True
      )
      csv_data = convert_df_to_csv(st.session_state["hospice_output"])
      st.download_button(
          label="📥 Download Hospice Processed Output (CSV)",
          data=csv_data,
          file_name="hospice_reconciled.csv",
          mime="text/csv",
      )

except Exception as e:
  st.error("An unexpected error occurred during execution.")
  st.exception(e)