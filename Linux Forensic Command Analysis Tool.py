import os
import subprocess
import re
import json
from collections import Counter
import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import pandas as pd
from threading import Timer
import webbrowser
import flask

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
#  Purpose:  Creates an interactive bar chart of command usage frequencies using
#      Plotly, with dropdown-based filtering for top 10, 25, or all commands.
#
#  Parameters:
#      counter (IN) -- A Counter object containing command frequencies.
#
#  Returns:  None (Displays interactive chart in browser and saves as HTML.)
#----------------------------------------------------------------------------
def visualize_command_usage(counter):
    data = counter.most_common()
    if not data:
        print("No data to visualize.")
        return

    df = pd.DataFrame(data, columns=['Command', 'Frequency'])

    # Dash app setup
    app = dash.Dash(__name__)
    server = app.server  # needed to shut it down from within

    app.layout = html.Div([
        html.H2("Command Usage Frequency"),
        dcc.Input(
            id='search-input',
            type='text',
            placeholder='Search for a command...',
            debounce=True,
            style={'width': '50%', 'padding': '10px', 'margin-bottom': '20px'}
        ),
        dcc.Graph(id='bar-chart'),
        html.Button("Save Chart & Quit", id="save-quit-button", n_clicks=0,
                    style={'margin-top': '20px', 'padding': '10px 20px'}),
        html.Div(id="save-message", style={'margin-top': '10px', 'color': 'green'})
    ], style={'padding': '40px', 'font-family': 'Arial, sans-serif'})

    @app.callback(
        Output('bar-chart', 'figure'),
        Input('search-input', 'value')
    )
    def update_chart(search_query):
        filtered_df = df[df['Command'].str.contains(search_query, case=False)] if search_query else df
        fig = px.bar(
            filtered_df,
            x='Command',
            y='Frequency',
            title="Command Usage Frequency",
            labels={'Command': 'Command', 'Frequency': 'Frequency'},
            template='plotly_white',
            height=600
        )
        fig.update_layout(xaxis_tickangle=-45, margin=dict(t=80, b=80, l=60, r=30))
        return fig

    @app.callback(
        Output("save-message", "children"),
        Input("save-quit-button", "n_clicks"),
        State("bar-chart", "figure"),
        prevent_initial_call=True
    )
    def save_and_quit(n_clicks, figure):
        if n_clicks:
            fig = px.bar(pd.DataFrame(figure["data"][0]), x='x', y='y')
            fig.write_image("command_usage_saved.png")
            shutdown_server()
            return "Chart saved as 'command_usage_saved.png'. Quitting..."

    def shutdown_server():
        func = flask.request.environ.get('werkzeug.server.shutdown')
        if func:
            func()

    # Open the browser after short delay
    Timer(1, lambda: webbrowser.open("http://127.0.0.1:8050")).start()

    app.run(debug=False)

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
