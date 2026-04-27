#!/bin/bash
echo "Running initial pipeline..."
python run_pipeline.py

echo "Starting scheduler + dashboard..."
python scheduler.py &
python dashboard/server.py
