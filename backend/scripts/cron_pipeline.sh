#!/bin/bash
# LangDive Daily Pipeline — run via cron at 06:00
cd /Users/yangxuan/PycharmProjects/A01-LangDive/langdive/backend
source .venv/bin/activate
python -m scripts.run_pipeline >> /tmp/langdive-pipeline.log 2>&1
echo "$(date): Pipeline completed" >> /tmp/langdive-pipeline.log
