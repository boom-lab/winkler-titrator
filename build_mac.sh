#!/bin/bash

# Exit on error
set -e

echo "Cleaning previous builds..."
rm -rf build dist

echo "Building application with PyInstaller..."
pyinstaller winkler.spec

echo "Creating DMG installer..."
# Create a temporary directory for the DMG contents
mkdir -p dist/dmg
rm -rf dist/dmg/*

# Copy the app to the DMG directory
cp -r "dist/Winkler.app" dist/dmg

# Remove any existing DMG
test -f "dist/Winkler.dmg" && rm "dist/Winkler.dmg"

# Create the DMG
create-dmg \
  --volname "Winkler" \
  --volicon "src/main/icons/winkler.icns" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 100 \
  --icon "Winkler.app" 175 120 \
  --hide-extension "Winkler.app" \
  --app-drop-link 425 120 \
  "dist/Winkler.dmg" \
  "dist/dmg/"

echo "Build complete! DMG created at dist/Winkler.dmg" 