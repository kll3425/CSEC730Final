## Overview  
(overview here)

## Features 
Extracts command data from:  
  * Shell history (~/.bash_history, ~/.zsh_history)
  * Running processes (ps aux)
  * System logs (/var/log/syslog, /var/log/auth.log)
  * Audit logs via ausearch
Counts and ranks most frequently used commands  

Saves results as:  
  * JSON file (command_usage.json)  
  * Bar chart PNG (command_usage.png)  

Useful for detecting anomalies, insider threats, unauthorized access, and general forensic analysis

## Requirements
* Linux OS
* Python 3.x
* Matplotlib (Python Library)
* auditd and ausearch (installed and running)

**Install Requirements**  
``sudo apt update``  
``sudo apt install auditd``  
``pip install matplotlib``  


## Usage
(usage here)
