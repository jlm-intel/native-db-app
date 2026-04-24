import streamlit as st  # web app framework
import os  # path functions and directory access
import glob  # file searching with wildcard support
import xml.etree.ElementTree as ET  # XML parsing
import pandas as pd  # data manipulation and DataFrame support
from packaging import version  # version parsing and comparison
from collections import Counter  # counting occurrences of dependencies


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
        p_company = product.findtext('Company')
        p_type = product.findtext('Type')
        row = {
            "Name": product.findtext('Name'),
            "Company": p_company,
            "Type": p_type
        }

        # log all unique company names and product types to session state sets for use in the filter dropdowns
        st.session_state.company_names.add(p_company)
        st.session_state.product_types.add(p_type)

        # log_to_ui(product.findtext('Name'))
        data.append(row)

    # log_to_ui(f"Number of rows extracted: {len(data)}")
    return data


def get_dependencies(root):
    """Extracts dependency application names from the XML root element and counts the number of times each is referenced."""
    # log_to_ui("get_dependencies called")
    dep_counts = Counter()

    for product in root.findall('Product'):
        # extract the latest dependency info for this product
        latest_dependency = get_latest_dependency(product)
        # print the contents of latest_dependency if not None
        if latest_dependency is not None:
            # log_to_ui(f"Latest dependency for {product.findtext('Name')}: {ET.tostring(latest_dependency, encoding='unicode')}")
            for cur_app in latest_dependency.findall('AppDependency'):
                app_name = cur_app.text
                if app_name:
                    dep_counts[app_name] += 1
                else:
                    log_to_ui(
                        "AppDependency element without a name attribute found.")
    return dep_counts


def get_dependency_apps(file_list):
    """
    Counts all instances of all application dependencies for products in XML files. Stores the unique application names in session state for use in the app filter dropdown.

    Returns:
        Counter: A Counter object mapping application names to their total counts across all products.
    """
    # log_to_ui("get_dependency_apps called")
    data = []
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
    data = [{"AppDependency": app, "Count": count}
            for app, count in dep_counts.items()]

    if len(data) == 0:
        log_to_ui("No relevant data found in the XML files.")
    else:
        st.session_state.app_list = sorted(dep_counts.keys(), key=str.lower)

    return dep_counts


def get_latest_dependency(product_element):
    """
    Finds the Dependencies element with the highest version.
    Prioritizes maxVersion, falls back to minVersion.
    It's not common, but a single product can have multiple sets of dependencies, tied to the product's specific version. 
    For the purposes of this app, I just want to get the details for the most recent production version of the product.
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
    log_to_ui(f"Finding products that depend on {app_name}...")
    data = []
    st.session_state.data_frame_dep = None

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
        st.session_state.data_frame_dep = pd.DataFrame(data)
        st.session_state.dependency_view = True

    return pd.DataFrame(data)


def parse_relevant_data(file_list, task_id):
    """Parses a list of XML files into a single pandas DataFrame. I orignally intended this to be a generic function
      that performs actions on the complete file list, but currently I only have a single use for it. Might refactor later."""
    data = []
    st.session_state.data_frame_all = None

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
        st.session_state.data_frame_all = pd.DataFrame(data)
        st.session_state.dependency_view = False

    return pd.DataFrame(data)


# function constants and task map (for use with parse_relevant_data's task_id parameter)
FUNC_PRODUCT_INFO = 1
# FUNC_DEPENDENCIES = 2

task_map = {
    FUNC_PRODUCT_INFO: get_product_info,
    # FUNC_DEPENDENCIES: get_dependencies
}


def log_to_ui(message):
    """Logs a message to the Streamlit UI."""
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(message)
    if st.session_state.log_container is not None:
        st.session_state.log_container.write(message)


def populate_lists():
    """Searches for XML files and populates the file list and app list in session state."""
    log_to_ui(f"Searching for XML files in {st.session_state.dir_path}...")
    process_complete = False

    with st.spinner(f"Searching for XML files in {st.session_state.dir_path}..."):
        st.session_state.file_list = search_xml_files(
            st.session_state.dir_path)
        if (isinstance(st.session_state.file_list, list)) and (len(st.session_state.file_list) > 0):
            st.success(
                f"Found {len(st.session_state.file_list)} XML file(s) in {st.session_state.dir_path}.")
            st.session_state.files_not_found = False
            with st.spinner("Loading product information..."):
                parse_relevant_data(
                    st.session_state.file_list, FUNC_PRODUCT_INFO)
            with st.spinner("Loading dependency information..."):
                get_dependency_apps(st.session_state.file_list)
            process_complete = True

    return process_complete


def main():

    st.title("Native DB App")

    # initialize session state variables
    if ('files_not_found' not in st.session_state):
        st.session_state.files_not_found = True
        st.session_state.last_task_id = 0
        st.session_state.data_frame_all = None
        st.session_state.data_frame_dep = None
        st.session_state.file_list = []
        st.session_state.app_list = []
        st.session_state.log_container = None
        # default windows system path below. mac os default would be "[System HD]/Library/Application Support/Native Instruments/Service Center"
        st.session_state.dir_path = r"C:\Program Files\Common Files\Native Instruments\Service Center"
        st.session_state.company_names = set()
        st.session_state.product_types = set()
        st.session_state.dependency_view = False

    # if no xml files are found at the default path, prompt the user to enter a path and search for XML files
    if st.session_state.files_not_found:
        if (not populate_lists()):
            st.session_state.dir_path = st.text_input(
                "Enter the path where your Native Access XML files reside:", value=st.session_state.dir_path)
            if st.button("Search for XML Files"):
                if os.path.isdir(st.session_state.dir_path):
                    with st.spinner("Searching..."):
                        populate_lists()
                else:
                    st.error(
                        "The specified path is not a valid directory or is inaccessible.")

    # always show the display options sidebar, but disable the filter options if no XML files were found
    st.sidebar.header("Display Options")

    # populate the UI when we have located XML files and loaded the appriopriate data into session state variables. The filters and data table will only be shown if XML files were found and parsed successfully.
    if not st.session_state.files_not_found:

        # set up buttons (dependent on finding XML files)
        dependency_filter = ["None"] + st.session_state.app_list
        selected_app = st.sidebar.selectbox(
            "Filter by dependency:", options=dependency_filter, help="Select an application to filter the product list to only show products that depend on that application.")
        if (selected_app != "None") and (selected_app in st.session_state.app_list):
            data_view = find_app_dependencies(
                st.session_state.file_list, selected_app)
        else:
            data_view = st.session_state.data_frame_all.copy(
            ) if st.session_state.data_frame_all is not None else None

        company_filter = ["All"] + \
            sorted(st.session_state.company_names, key=str.lower)
        selected_company = st.sidebar.selectbox(
            "Filter by company:", options=company_filter, help="Select a company to display only products from that company. Select 'All' to show products from all companies.")
        if selected_company != "All" and data_view is not None and 'Company' in data_view.columns:
            data_view = data_view[data_view['Company'] == selected_company]

        type_filter = ["All"] + \
            sorted(st.session_state.product_types, key=str.lower)
        selected_type = st.sidebar.selectbox(
            "Filter by product type:", options=type_filter, help="Select a product type to display only products of that type. Select 'All' to show products of all types.")
        if selected_type != "All" and data_view is not None and 'Type' in data_view.columns:
            data_view = data_view[data_view['Type'] == selected_type]

        # NOTE: The "Reset Filters" button is currently commented out because it doesn't work well with the way Streamlit handles state updates and re-renders.
        #       Clicking the button wouldn't clear all selection states, and the (now deleted) session state variables were causing problems with some selectbox interactions.
        #       A more robust filter reset implementation would require a different approach to managing the filter states and ensuring that all components update correctly when the filters are reset.
        # st.sidebar.button("Reset Filters", on_click=reset_filters,
        #                   help="Reset all filters to their default values.")

        st.button("Reload all products", disabled=st.session_state.files_not_found,
                  on_click=parse_relevant_data, args=(st.session_state.file_list, FUNC_PRODUCT_INFO), help="This will reload the full product list without any application dependency filters.")

        if data_view is not None:
            st.subheader("Table of products:")
            # log_to_ui("Displaying parsed data...")
            st.dataframe(data_view)

    show_logs = st.sidebar.checkbox("Show Log Console", value=False)
    if show_logs:
        st.session_state.log_container = st.expander(
            "Log Console", expanded=True)
    else:
        st.session_state.log_container = None

    with st.sidebar:
        st.header("About this app")
        st.info("""
This app uses XML database files of Native Access (the Native Instruments installer) to display information about supported products and their dependencies. There are display options for filtering the results. You must have Native Access installed, or at least have a local directory that contains the NativeAccess.xml file.
                """)


if __name__ == "__main__":
    main()
