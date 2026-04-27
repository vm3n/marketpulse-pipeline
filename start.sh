#!/bin/bash
# Run pipeline first to create and populate the database
echo "Running initial pipeline..."
python run_pipeline.py

# Then start the dashboard server
echo "Starting dashboard server..."
python dashboard/server.py
