# native-db-app
This is a python app that provides helpful information about Native Instruments and other NKS-ready products. It is designed to run as an online web app (in which case it uses some pre-uploaded Service Center XML files) or locally on a computer (in which case it will load the Service Center files on your computer.)

The web app version is here: https://native-db-app.streamlit.app/

The local PC version is available at this GitHub repo: https://github.com/jlm-intel/native-db-app

In order to run locally you must have the following installed on your computer:
- Git 2.53 or later
- Python 3.14 or later
- The versions of pandas, streamlit, and lxml listed in the requirements.txt at the root of this repo.

After cloning the repo locally you can run the app by doing the following:
```
cd src
streamlit run app.py
```

The app will launch in your default browser. If you are running on Windows, it will probably find your Service Center files and load them automatically.

If you are running on Mac (or Linux), it will prompt you to enter a path to search. There are some pre-loaded XML files in the src/webdata directory, which you can point to in the case of Linux.

If you are running on MacOS, the default path will be something like, "[System HD]/Library/Application Support/Native Instruments/Service Center"

This project was a way for me to learn the Streamlit framework and the pandas API.

For more detailed documentation, check my blog: https://medium.ultimateoutsider.com/

PACKAGING NOTES
As of 2026/05/13 Native DB App now supports being packaged as a Windows executable. Some notes in order to get packaging to work:
- You will probably have to run this command from the VS Code terminal in order to build the packages without errors: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
- You will also have to enable Developer Mode in Windows Settings: Settings > System > Advanced > Developer Mode > ENABLED
- Run this command to install stlite (assuming you have already installed Node.js): npm install --save-dev @stlite/desktop
