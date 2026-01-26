#!/bin/bash
# Fix for Vercel client reference manifest issue with route groups
next build

# Create missing manifest files for route groups
mkdir -p .next/server/app/\(dashboard\)
touch ".next/server/app/(dashboard)/page_client-reference-manifest.js"
echo "module.exports = {}" > ".next/server/app/(dashboard)/page_client-reference-manifest.js"
