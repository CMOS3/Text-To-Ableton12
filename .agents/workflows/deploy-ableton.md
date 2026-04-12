---
description: Standardized deployment pipeline to transfer the Remote Script from the local workspace to the Ableton Live User Library on Windows 11.
---

# Deploy Ableton Remote Script

This workflow orchestrates the secure transfer of the MCP bridge files to the Ableton environment, ensuring the correct Python environment is utilized for file operations.

## Steps

1. **Environment Initialization**: Activate the isolated Python interpreter located at `.\backend\.venv\Scripts\python.exe` to ensure all script execution permissions are maintained.
2. **Execute Deployment**: Run the PowerShell deployment script `.\remote_script\deploy.ps1`. 
3. **Path Verification**: Confirm that the target directory `D:\Sync\00 PC Sharing\Ableton\User Library\Remote Scripts\TextToAbleton` now contains the updated script files.
4. **Integrity Check**: Verify that the `__init__.py` file in the destination folder contains the mandatory TCP binding to `127.0.0.1` on port `9877`.
5. **Final Status**: Report the success of the deployment to the terminal and advise the user to perform a "Refresh" in the Ableton Live browser or restart the software to initialize the new Remote Script.