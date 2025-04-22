import subprocess
import sys

# Function to install missing dependencies
def install_package(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# List of required dependencies
required_packages = [
    "os", "subprocess", "re", "json", "collections", "dash", "plotly", "pandas", "kaleido"
]

# Check and install missing packages
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"Package {package} not found. Installing...")
        install_package(package)

import os
import subprocess
import re
import json
from collections import Counter
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
from threading import Timer
import webbrowser

# Configurable paths and settings
HISTORY_FILES = [os.path.expanduser("~/.bash_history"), os.path.expanduser("~/.zsh_history")]
LOG_FILES = ["/var/log/syslog", "/var/log/auth.log"]


#---------------------------- read_shell_history ----------------------------
#  Function read_shell_history
#
#  Purpose:  Reads shell history files (.bash_history, .zsh_history) to extract
#      commands used by the user. It parses each line and extracts the
#      first word (assumed to be the command).
#
#  Parameters:
#      None
#
#  Returns:  A list of command strings (OUT) -- the commands extracted from the 
#      user's shell history.
#----------------------------------------------------------------------------
def read_shell_history():
    commands = []
    for file_path in HISTORY_FILES:
        if os.path.exists(file_path):
            with open(file_path, 'r', errors='ignore') as f:
                for line in f:
                    command = line.strip().split(' ')[0]
                    if command:
                        commands.append(command)
    return commands

#---------------------------- read_process_logs -----------------------------
#  Function read_process_logs
#
#  Purpose:  Uses `ps aux` to get currently running processes and extracts the
#      command portion of each. This captures active commands at runtime.
#
#  Parameters:
#      None
#
#  Returns:  A list of command names (OUT) -- names of running processes.
#----------------------------------------------------------------------------
def read_process_logs():
    commands = []
    try:
        output = subprocess.check_output(['ps', 'aux'], text=True)
        for line in output.strip().split('\n')[1:]:
            parts = line.split()
            if len(parts) > 10:
                command = parts[10].split("/")[-1]
                commands.append(command)
    except Exception as e:
        print(f"Failed to read process logs: {e}")
    return commands

#----------------------------- parse_system_logs ----------------------------
#  Function parse_system_logs
#
#  Purpose:  Parses system log files (e.g., syslog, auth.log) to extract command
#      usage. Looks for the pattern 'COMMAND=' and captures the value.
#
#  Parameters:
#      None
#
#  Returns:  A list of command names (OUT) -- commands found in the system logs.
#----------------------------------------------------------------------------
def parse_system_logs():
    commands = []
    for log_file in LOG_FILES:
        if os.path.exists(log_file):
            with open(log_file, 'r', errors='ignore') as f:
                for line in f:
                    match = re.search(r'COMMAND=([^\s]+)', line)
                    if match:
                        command = match.group(1).split("/")[-1]
                        commands.append(command)
    return commands

#----------------------------- parse_audit_logs -----------------------------
#  Function parse_audit_logs
#
#  Purpose:  Uses `ausearch` to extract EXECVE audit events and identifies the 
#      command used. Useful on systems with auditd enabled for detailed tracking.
#
#  Parameters:
#      None
#
#  Returns:  A list of command names (OUT) -- commands logged by audit framework.
#----------------------------------------------------------------------------
def parse_audit_logs():
    commands = []
    try:
        output = subprocess.check_output(['ausearch', '-m', 'EXECVE'], text=True)
        for line in output.split('\n'):
            match = re.search(r'argc=\d+.*?a0=\"([^\"]+)\"', line)
            if match:
                command = match.group(1).split("/")[-1]
                commands.append(command)
    except Exception as e:
        print(f"Failed to parse audit logs: {e}")
    return commands

#---------------------------- normalize_and_count ---------------------------
#  Function normalize_and_count
#
#  Purpose:  Converts all collected command strings to lowercase and filters 
#      non-alphabetic entries. Then counts the frequency of each unique command.
#
#  Parameters:
#      commands (IN) -- A list of command strings to be normalized and counted.
#
#  Returns:  A Counter object (OUT) -- contains command frequencies.
#----------------------------------------------------------------------------
def normalize_and_count(commands):
    normalized = [cmd.lower() for cmd in commands if cmd.isalpha()]
    return Counter(normalized)

#-------------------------- visualize_command_usage -------------------------
#  Function visualize_command_usage
#
#  Purpose:  Launches a Dash app with search/filter and a "Save & Quit" button
#      that exports the current chart to PNG, hides the chart, and exits the app.
#
#  Parameters:
#      counter (IN) -- A Counter object containing command frequencies.
#
#  Returns:  None (runs a local web server and auto-opens the dashboard)
#----------------------------------------------------------------------------
def visualize_command_usage(counter):
    data = counter.most_common()
    if not data:
        print("No data to visualize.")
        return

    df = pd.DataFrame(data, columns=['Command', 'Frequency'])

    app = dash.Dash(__name__)
    server = app.server

    app.layout = html.Div([
        html.H2("Command Usage Frequency", style={'textAlign': 'center', 'margin-bottom': '30px'}),
        dcc.Input(
            id='search-input',
            type='text',
            placeholder='Search for a command...',
            debounce=True,
            style={'width': '50%', 
                   'padding': '10px', 
                   'margin': 'auto',
                   'display': 'block',
                   'margin-bottom': '20px',
                   'fontSize': '16px'
            }
        ),
        dcc.Graph(id='bar-chart'),
        html.Button("Save Chart & Quit", id="save-quit-button", n_clicks=0,
                    style={'margin-top': '30px', 'padding': '12px 24px', 'fontSize': '16px'}),
        html.Div(id="save-message", style={'margin-top': '15px', 'color': 'green', 'textAlign': 'center'})
    ], style={'padding': '40px', 'font-family': 'Arial, sans-serif'})

    # Store filtered data
    filtered_df_store = {"data": df}

    @app.callback(
        Output('bar-chart', 'figure'),
        Input('search-input', 'value')
    )
    def update_chart(search_query):
        filtered = df[df['Command'].str.contains(search_query, case=False)] if search_query else df
        filtered_df_store["data"] = filtered  # Save for later use
        fig = px.bar(
            filtered,
            x='Command',
            y='Frequency',
            title="Command Usage Frequency",
            labels={'Command': 'Command', 'Frequency': 'Usage Count'},
            template='plotly_white',
            color='Frequency',
            color_continuous_scale='Blues',
            height=600
        )

        fig.update_layout(
            xaxis_tickangle=-45, 
            margin=dict(t=80, b=80, l=60, r=30))
        return fig

    @app.callback(
        Output("save-message", "children"),
        Output('bar-chart', 'style'),  # Hide chart after saving
        Input("save-quit-button", "n_clicks"),
        prevent_initial_call=True
    )
    def save_and_exit(n_clicks):
        if n_clicks > 0:
            try:
                # Save current filtered chart
                fig = px.bar(
                    filtered_df_store["data"],
                    x='Command',
                    y='Frequency',
                    title="Saved Command Usage"
                )
                fig.write_image("command_usage_saved.png")
                # Notify about save success
                save_message = "Chart saved as 'command_usage_saved.png'. Close Window"

            except Exception as e:
                save_message = f"Error saving chart: {str(e)}"
                print(f"Error saving chart: {str(e)}")

            try:
                # Hide the chart and initiate shutdown
                chart_style = {"display": "none"}
                Timer(1, shutdown_server).start()
            
            except Exception as e:
                save_message = f"Error shutting down server: {str(e)}"
                print(f"Error shutting down server: {str(e)}")
                chart_style = {}

            return save_message, chart_style

    def shutdown_server():
        try:
            # Gracefully shut down the app
            os._exit(0)  # Force kill to ensure exit without error
        except Exception as e:
            print(f"Error during server shutdown: {str(e)}")

    # Open browser automatically
    Timer(1, lambda: webbrowser.open("http://127.0.0.1:8050")).start()
    app.run(debug=False, use_reloader=False)  # Disable reloader to prevent issues when exiting

#------------------------------ export_to_json ------------------------------
#  Function export_to_json
#
#  Purpose:  Writes the command frequency data to a JSON file for later use
#      or analysis by other tools or analysts.
#
#  Parameters:
#      counter (IN) -- A Counter object containing command usage frequencies.
#
#  Returns:  None (Writes data to "command_usage.json".)
#----------------------------------------------------------------------------
def export_to_json(counter):
    with open("command_usage.json", "w") as f:
        json.dump(counter.most_common(), f, indent=4)


def main():
    print("\nCollecting command data...")
    commands = []
    commands += read_shell_history()
    commands += read_process_logs()
    commands += parse_system_logs()
    commands += parse_audit_logs()

    print("Processing command data...")
    counter = normalize_and_count(commands)

    print("Exporting and visualizing results...")
    export_to_json(counter)
    visualize_command_usage(counter)
    print("Analysis complete. Results saved to 'command_usage.png' and 'command_usage.json'.")

if __name__ == "__main__":
    main()
