import streamlit as st
import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd
from packaging import version

def search_xml_files(directory):
    """Searches the specified directory for XML files."""
    # Ensure the path is handled correctly across OS styles
    search_path = os.path.join(directory, "*.xml")
    
    try:
        # glob.glob returns a list of matching file paths
        files = glob.glob(search_path)
        return files
    except Exception as e:
        return f"Error accessing directory: {e}"

def get_product_info(root):
    """Extracts product information from the XML root element."""
    data = []
    for product in root.findall('Product'):
        # check for any dependencies elements and extract the latest version info
        latest_dependency = get_latest_dependency(product)
        # to do: set relevant dependency fields for critical applications
        row = {
            "Name": product.findtext('Name'),
            "Company": product.findtext('Company'),
            "UPID": product.findtext('UPID'),
            "Type": product.findtext('Type'),
            "AuthAppID": product.findtext('AuthAppID')
        }
        # log_to_ui(product.findtext('Name'))
        data.append(row)

    # log_to_ui(f"Number of rows extracted: {len(data)}")
    return data

def get_dependencies(root):
    """Extracts dependency application names from the XML root element."""
    data = []
    log_to_ui("get_dependencies called")
    for product in root.findall('Product'):
        dependencies = product.find('Dependencies')
        # extract the latest dependency info for this product
        latest_dependency = get_latest_dependency(product)
        # to do: enumerate the AppDependency elements and extract the application names, and append them to the list
    return data

def get_latest_dependency(product_element):
    """
    Finds the Dependencies element with the highest version.
    Prioritizes maxVersion, falls back to minVersion.
    """
    best_element = None
    highest_v = None

    # Find all Dependencies tags within this specific Product
    dependencies = product_element.findall('Dependencies')
    
    for dep in dependencies:
        # 1. Determine the 'representative' version for this tag
        # We prefer maxVersion if it exists; otherwise, use minVersion
        v_string = dep.get('maxVersion') or dep.get('minVersion')
        
        if not v_string:
            v_string = "0.0.0"  # Default to a very low version if neither is present
            
        current_v = version.parse(v_string)
        
        # 2. Compare against the highest version found so far
        if highest_v is None or current_v > highest_v:
            highest_v = current_v
            best_element = dep
            
    return best_element

def parse_relevant_data(file_list, task_id):
    """Parses a list of XML files into a single pandas DataFrame."""
    data = []
    st.session_state.data_frame = None
    
    # process each file and extract relevant data based on the task_id
    for file in file_list:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            
            # Call the appropriate function based on task_id
            if task_id in task_map:
                extracted_data = task_map[task_id](root)
                if extracted_data:
                    # add all rows to the main data list
                    data.extend(extracted_data)
        except Exception as e:
            st.error(f"Could not parse {file}: {e}")

        if st.session_state.data_frame is not None and st.session_state.data_frame.empty:
            log_to_ui("No relevant data found in the XML files.")
        else:
            st.session_state.data_frame = pd.DataFrame(data)

        # to do: remove duplicates from the dataframe

    return pd.DataFrame(data)


def parse_xml_to_dataframe(file_list):
    """Parses a list of XML files into a single pandas DataFrame."""
    data = []
    
    for file in file_list:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            
            # Navigate to the <Product> tag
            for product in root.findall('Product'):
                # Extract fields based on your FIN-RETRO.xml example
                row = {
                    "Name": product.findtext('Name'),
                    "Company": product.findtext('Company'),
                    "UPID": product.findtext('UPID'),
                    "Type": product.findtext('Type'),
                    "AuthAppID": product.findtext('AuthAppID'),
                    "File_Source": os.path.basename(file)
                }
                data.append(row)
        except Exception as e:
            st.error(f"Could not parse {file}: {e}")
            
    return pd.DataFrame(data)

task_map = {
    1: get_product_info,
    2: get_dependencies
}

def log_to_ui(message):
    """Logs a message to the Streamlit UI."""
    st.session_state.log_container.write(message)

def main():
    st.session_state.log_container = st.expander("Log Output", expanded=True)

    st.title("Native DB App")
    # initialize session state variables
    if ('files_not_found' not in st.session_state):
        st.session_state.files_not_found = True
        st.session_state.last_task_id = 0
        st.session_state.data_frame = None
    results = []

    # 1. User-editable text field with your default path
    default_path = r"C:\Program Files\Common Files\Native Instruments\Service Center"
    dir_path = st.text_input("Enter the path where your Native Access XML files reside:", value=default_path)

    # 2. Button to trigger the search
    if st.button("Search for XML Files"):
        if os.path.isdir(dir_path):
            with st.spinner("Searching..."):
                results = search_xml_files(dir_path)
                
                if isinstance(results, list):
                    if results:
                        st.success(f"Found {len(results)} XML file(s):")
                        st.session_state.files_not_found = False
                        # for file in results:
                        #     st.write(f"- {os.path.basename(file)}")
                        # df = parse_xml_to_dataframe(results)
                        # st.dataframe(df)
                        # csv = df.to_csv(index=False).encode('utf-8')
                        # st.download_button(
                        #     label="Download CSV",
                        #     data=csv,
                        #     file_name="parsed_xml_data.csv",
                        #     mime="text/csv"
                        # )
                    else:
                        st.warning("No XML files found in this directory.")
                else:
                    st.error(results)
        else:
            st.error("The specified path is not a valid directory or is inaccessible.")

    # set up buttons (dependent on finding XML files)
    st.button("Get Product Info", disabled=st.session_state.files_not_found, on_click=parse_relevant_data, args=(results, 1))
    st.button("Get Dependencies", disabled=st.session_state.files_not_found, on_click=parse_relevant_data, args=(results, 2))

    if st.session_state.data_frame is not None:
        log_to_ui("Displaying parsed data...")
        st.dataframe(st.session_state.data_frame)
if __name__ == "__main__":
    main()