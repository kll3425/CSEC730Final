## Overview  
This project is a Linux forensic analysis and visualization tool that collects, processes, and visualizes command usage data from various sources such as shell history, running processes, system logs, and audit logs. The results are presented in an interactive web dashboard built using Dash and Plotly, and can be exported as a PNG and JSON file.

## Features 
* Extracts command data from:  
  * Shell history (~/.bash_history, ~/.zsh_history)
  * Running processes (ps aux)
  * System logs (/var/log/syslog, /var/log/auth.log)
  * Audit logs (ausearch on systems with auditd)
* Visualizes command frequency in an interactive dashboard
* Includes search/filter functionality 
* Saves results as:  
  * JSON file (command_usage.json)  
  * Bar chart PNG (command_usage.png)
* Auto-opens in your default browser

## Requirements
* Linux OS
* Python 3.x
* auditd and ausearch (installed and running)
* Python packages: dash, plotly, pandas, kaleido

**Install Requirements**  
``sudo apt update``  
``sudo apt install auditd``  
``pip install dash plotly pandas kaleido``  

## Usage
``Python3 Linux\ Forensic\ Command\ Analysis\ Tool.py``

## Example Use Cases
* Investigate most used commands for system forensic analysis
* Audit command patterns on a multi-use server
* Enhance security monitoring pipelines with behaviorial data
