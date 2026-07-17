# Publish a no-install Windows release

This repository is configured so GitHub itself builds the Windows EXE and packages every required Python dependency beside it. Players do not install Python, Node.js, npm, or pip.

## First upload

1. Create a new empty GitHub repository.
2. Upload the contents of this folder, including the hidden `.github` folder.
3. Open the repository's **Actions** tab.
4. Select **Build Windows Release**.
5. Choose **Run workflow**.
6. When it finishes, open the workflow run and download the artifact named `Coteab-Macro-Overlay-v2.2.1-Windows`.
7. Test the ZIP on a second Windows PC before sharing it.

## Publish it on the Releases page

Create and push a tag named `v2.2.1`, or create that tag through GitHub's release editor. The workflow will build the application and attach the Windows ZIP automatically.

Players only need to download the ZIP, extract it, and run `Coteab Macro.exe`.

## Important limitation

The release is self-contained for the application's Python packages and assets. Windows still supplies normal operating-system components such as Microsoft Edge WebView2 and the Microsoft Visual C++ runtime. Standard updated Windows 10/11 systems normally already contain these. No community application can safely bundle every Windows system component inside its own EXE.
