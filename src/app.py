import streamlit as st
import os
import glob
import xml.etree.ElementTree as ET
import pandas as pd
from packaging import version
from collections import Counter

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
            "Type": product.findtext('Type')
        }
        # log_to_ui(product.findtext('Name'))
        data.append(row)

    # log_to_ui(f"Number of rows extracted: {len(data)}")
    return data

def get_dependencies(root):
    """Extracts dependency application names from the XML root element."""
    # log_to_ui("get_dependencies called")
    dep_counts = Counter()

    for product in root.findall('Product'):
        # extract the latest dependency info for this product
        latest_dependency = get_latest_dependency(product)
        # print the contents of latest_dependency if not None
        if latest_dependency is not None:
            # log_to_ui(f"Latest dependency for {product.findtext('Name')}: {ET.tostring(latest_dependency, encoding='unicode')}")
            # to do: enumerate the AppDependency elements and extract the application names, and append them to the list
            for cur_app in latest_dependency.findall('AppDependency'):
                app_name = cur_app.text
                if app_name:
                    dep_counts[app_name] += 1
                else:
                    log_to_ui("AppDependency element without a name attribute found.")
    return dep_counts

def get_dependency_apps(file_list):
    """Counts all instances of all application dependencies."""
    # log_to_ui("get_dependency_apps called")
    data = []
    st.session_state.data_frame = None
    dep_counts = Counter()

    # process each file and extract relevant data based on the task_id
    for file in file_list:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            
            # Call the appropriate function based on task_id
            # log_to_ui(f"Processing file: {file}")
            extracted_data = get_dependencies(root)
            if extracted_data:
                # log_to_ui(f"Extracted dependencies from {file}: {extracted_data}")
                dep_counts.update(extracted_data)
        except Exception as e:
            st.error(f"Could not parse {file}: {e}")

    # convert the Counter to a list of dicts for DataFrame construction
    data = [{"AppDependency": app, "Count": count} for app, count in dep_counts.items()]

    if len(data) == 0:
        log_to_ui("No relevant data found in the XML files.")
    else:
        st.session_state.data_frame = pd.DataFrame(data)
        st.session_state.app_list = sorted(dep_counts.keys())
        
    # to do: remove duplicates from the dataframe

    return pd.DataFrame(data)


def get_latest_dependency(product_element):
    """
    Finds the Dependencies element with the highest version.
    Prioritizes maxVersion, falls back to minVersion.
    """
    # log_to_ui(f"Finding latest dependency for product: {product_element.findtext('Name')}")
    best_element = None
    highest_v = None

    # Find all Dependencies tags within this specific Product
    dependencies = product_element.findall('Dependencies')
    
    for dep in dependencies:
        # 1. Determine the 'representative' version for this tag
        # We prefer maxVersion if it exists; otherwise, use minVersion
        v_string = dep.get('maxVersion') or dep.get('minVersion')
        
        if not v_string:
            v_string = "1.0.0"  # Default to a very low version if neither is present
            
        current_v = version.parse(v_string)
        
        # 2. Compare against the highest version found so far
        if highest_v is None or current_v > highest_v:
            highest_v = current_v
            best_element = dep
            
    return best_element

def find_app_dependencies(file_list, app_name):
    """Finds all products that depend on the specified application."""
    data = []
    st.session_state.data_frame = None

    for file in file_list:
        try:
            tree = ET.parse(file)
            root = tree.getroot()
            
            for product in root.findall('Product'):
                latest_dependency = get_latest_dependency(product)
                if latest_dependency is not None:
                    for cur_app in latest_dependency.findall('AppDependency'):
                        if cur_app.text == app_name:
                            v_string = cur_app.get('minVersion') or "1.0.0"
                            row = {
                                "Name": product.findtext('Name'),
                                "Company": product.findtext('Company'),
                                f"Min. {app_name} ver.": v_string,
                                "Type": product.findtext('Type')
                            }
                            data.append(row)
        except Exception as e:
            st.error(f"Could not parse {file}: {e}")

    if len(data) == 0:
        log_to_ui(f"No products found that depend on {app_name}.")
    else:
        st.session_state.data_frame = pd.DataFrame(data)

    return pd.DataFrame(data)

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

    if len(data) == 0:
        log_to_ui("No relevant data found in the XML files.")
    else:
        st.session_state.data_frame = pd.DataFrame(data)
        st.session_state.company_list = sorted(st.session_state.data_frame['Company'].unique().tolist()) if 'Company' in st.session_state.data_frame.columns else []

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
                    "Type": product.findtext('Type'),
                    "File_Source": os.path.basename(file)
                }
                data.append(row)
        except Exception as e:
            st.error(f"Could not parse {file}: {e}")
            
    return pd.DataFrame(data)

# function constants
FUNC_PRODUCT_INFO = 1
#FUNC_DEPENDENCIES = 2

task_map = {
    FUNC_PRODUCT_INFO: get_product_info,
    #FUNC_DEPENDENCIES: get_dependencies
}

def log_to_ui(message):
    """Logs a message to the Streamlit UI."""
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(message)
    if st.session_state.log_container:
        st.session_state.log_container.write(message)

def main():
    st.session_state.log_container = st.expander("Log Output", expanded=True)

    st.title("Native DB App")
    # initialize session state variables
    if ('files_not_found' not in st.session_state):
        st.session_state.files_not_found = True
        st.session_state.last_task_id = 0
        st.session_state.data_frame = None
        st.session_state.file_list = []
        st.session_state.app_list = []
        st.session_state.company_list = []

    st.sidebar.header("Filter Options")
    #company_filter = ["All"] + sorted({row["Company"] for row in st.session_state.data_frame.to_dict('records')}) if st.session_state.data_frame is not None else ["All"]
    company_filter = ["All"] + st.session_state.company_list
    selected_company = st.sidebar.selectbox("Select a Company:", options=company_filter)
    data_view = st.session_state.data_frame.copy() if st.session_state.data_frame is not None else None
    if selected_company != "All" and st.session_state.data_frame is not None and 'Company' in st.session_state.data_frame.columns:
        data_view = st.session_state.data_frame[st.session_state.data_frame['Company'] == selected_company]   

    # 1. User-editable text field with your default path
    default_path = r"C:\Program Files\Common Files\Native Instruments\Service Center"
    dir_path = st.text_input("Enter the path where your Native Access XML files reside:", value=default_path)

    # 2. Button to trigger the search
    if st.button("Search for XML Files"):
        if os.path.isdir(dir_path):
            with st.spinner("Searching..."):
                st.session_state.file_list = search_xml_files(dir_path)
                if isinstance(st.session_state.file_list, list):
                    if st.session_state.file_list:
                        st.success(f"Found {len(st.session_state.file_list)} XML file(s):")
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
    st.button("Get Product Info", disabled=st.session_state.files_not_found, on_click=parse_relevant_data, args=(st.session_state.file_list, FUNC_PRODUCT_INFO))
    st.button("Get Dependencies", disabled=st.session_state.files_not_found, on_click=get_dependency_apps, args=(st.session_state.file_list,))
    selected_app = st.selectbox("Select an application to filter by:", options=st.session_state.app_list)
    if (selected_app):
        st.button(f"List {selected_app} dependencies", on_click=find_app_dependencies, args=(st.session_state.file_list, selected_app))

    if data_view is not None:
        # log_to_ui("Displaying parsed data...")
        st.dataframe(data_view)
if __name__ == "__main__":
    main()