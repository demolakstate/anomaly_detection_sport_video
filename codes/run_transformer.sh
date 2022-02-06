#!/bin/bash
module load Python/3.7.4-GCCcore-8.3.0
#module load fosscuda
source ~/virtualenvs/anomaly_sport_video/bin/activate
export PYTHONDONTWRITEBYTECODE=1
python /homes/okerinde/projects/anomaly_detection_sport_video/codes/detecting_risky_tackles_in_sport_videos_using_transformer_beocat_v3.py
