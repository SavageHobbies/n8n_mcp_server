#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Running post-create setup for Polyglot AI Vibe Programming ---"

# --- 1. Kilo Code Specific Setup ---
# Check if kilo-code CLI exists and perform its setup/MCP load.
# Replace 'kilo-code' with the actual command name if different.
# The 'load-mcp' command is hypothetical, check Kilo Code's actual documentation.
if command -v kilo-code &> /dev/null; then
    echo "Initializing Kilo Code and loading custom MCPs..."
    kilo-code setup || echo "Kilo Code setup failed. Check Kilo Code docs."
    
    # This command is CRITICAL for AI context.
    # It tells Kilo Code to load your custom context from the _mcp folder.
    # The path /workspaces/${localWorkspaceFolderBasename}/_mcp is where your project's _mcp folder is mounted.
    kilo-code load-mcp --source-dir "/workspaces/${localWorkspaceFolderBasename}/_mcp" || echo "Failed to load MCPs into Kilo Code. Check Kilo Code docs for correct command."
else
    echo "Kilo Code CLI not found (or not installed), skipping Kilo Code setup. Please ensure it's in your Dockerfile."
fi

# --- 2. Install Project Dependencies ---
# This section assumes your project has a Node.js (package.json) and/or Python (requirements.txt) component.

# Node.js dependencies
echo "Installing Node.js project dependencies..."
if [ -f "package.json" ]; then
    # Use npm or yarn based on your project's setup
    if [ -f "yarn.lock" ]; then
        yarn install || echo "Yarn install failed."
    else
        npm install || echo "NPM install failed."
    fi
else
    echo "No package.json found, skipping Node.js dependency install."
fi

# Python dependencies
echo "Installing Python project dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt || echo "Pip install failed."
else
    echo "No requirements.txt found, skipping Python dependency install."
fi

# --- 3. Other Tool Initializations ---

# Playwright Browser Installation
# If you added Playwright as a feature, you typically need to install its browsers.
echo "Installing Playwright browsers..."
if command -v playwright &> /dev/null; then
    playwright install || echo "Playwright browser install failed."
else
    echo "Playwright CLI not found, skipping browser installation."
fi

# n8n Setup (if you added the n8n feature and need it initialized)
# If n8n runs as a separate service in docker-compose.yml, you might not need this here.
# But if the n8n feature installs the CLI/server directly in your 'app' container,
# and it requires an init command, put it here.
echo "Initializing n8n (if installed)..."
if command -v n8n &> /dev/null; then
    # This is a placeholder; check n8n's specific initialization command if any.
    # For example, to start its setup, or create initial config.
    # n8n start --tunnel # Or whatever init command is relevant for your dev workflow
    echo "n8n CLI found. If initialization is needed, add specific n8n commands here."
else
    echo "n8n CLI not found, skipping n8n setup."
fi


# --- 4. Database Migrations / Seeding (if your app manages its own migrations) ---
# This is crucial if your Node.js app is responsible for setting up the database schema.
# Your app should now connect to your DigitalOcean DB.

echo "Running database migrations and seeding (if applicable)..."
# Replace with your project's specific commands for migrations/seeding.
# Examples:
# For Prisma:
# npx prisma migrate deploy || echo "Prisma migrations failed."
# npx prisma db seed || echo "Prisma seeding failed."

# For Knex.js:
# npx knex migrate:latest || echo "Knex migrations failed."
# npx knex seed:run || echo "Knex seeding failed."

# For Sequelize:
# npx sequelize db:migrate || echo "Sequelize migrations failed."
# npx sequelize db:seed:all || echo "Sequelize seeding failed."

# Generic npm script (if you have "db:migrate" in your package.json scripts)
# npm run db:migrate || echo "Database migrations via npm script failed."

# If your database is external (DigitalOcean), ensure your app's code is configured
# to connect to it using the environment variables passed in docker-compose.yml.
# These commands will then interact with the DO database.


echo "--- Dev container setup complete! Happy AI Vibe Programming! ---"