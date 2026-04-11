# Ableton Remote Script Deployment Script
# Standardized deployment pipeline to transfer the Remote Script from the local workspace to the Ableton Live User Library.

$source = "$PSScriptRoot"
$destination = "D:\Sync\00 PC Sharing\Ableton\User Library\Remote Scripts\TextToAbleton"

Write-Host "Starting deployment to: $destination"

# Ensure destination directory exists
if (!(Test-Path $destination)) {
    Write-Host "Creating destination directory..."
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
}

# Copy files, excluding the deployment script itself and internal python files
Write-Host "Copying remote script files..."
Copy-Item -Path "$source\*" -Destination $destination -Recurse -Force -Exclude "deploy.ps1"

Write-Host "Deployment successful!"
Write-Host "Please refresh your Ableton Live Browser or restart Ableton Live to see the changes."
