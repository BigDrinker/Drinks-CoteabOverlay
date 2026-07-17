# GitHub Windows Build

This repository builds a self-contained Windows folder using GitHub Actions.
Players do not need Python, Node.js, npm, or PySide6 installed.

## Upload and build

1. Copy the contents of this folder into the root of your GitHub repository.
2. Commit and push the files.
3. Open **Actions** on GitHub.
4. Select **Build Windows Release** and choose **Run workflow**.
5. Open the completed run and download the artifact.
6. Extract the downloaded artifact, then extract the Windows ZIP inside it.
7. Run `Coteab Macro.exe` beside the `_internal` folder.

## Publish for other players

After testing the artifact, create a GitHub release and attach the generated Windows ZIP. Players should extract the entire ZIP before launching the EXE.

## Current GUI backend

The packaged application uses pywebview with the Qt/PySide6 backend. The PyInstaller spec collects QtWebEngine and its required runtime files so another PC does not need extra software.
