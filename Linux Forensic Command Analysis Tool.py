import os
import subprocess
import re
import json
from collections import Counter
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

    # Prepare all filter levels
    filters = {
        "Top 10": data[:10],
        "Top 25": data[:25],
        "All": data
    }

    # Create traces for each filter level
    traces = []
    visibility = []
    buttons = []

    for i, (label, subset) in enumerate(filters.items()):
        cmds, freqs = zip(*subset)
        trace = go.Bar(
            x=cmds,
            y=freqs,
            name=label,
            marker_color='lightskyblue',
            hovertemplate='%{x}<br>Frequency: %{y}<extra></extra>',
        )
        traces.append(trace)
        visibility.append([j == i for j in range(len(filters))])
        buttons.append(dict(
            label=label,
            method="update",
            args=[{"visible": visibility[-1]},
                  {"title": f"{label} Commands by Frequency"}]
        ))

    fig = go.Figure(data=traces)

    # Add dropdown menu
    fig.update_layout(
        updatemenus=[dict(
            active=0,
            buttons=buttons,
            direction="down",
            x=0.0,
            xanchor="left",
            y=1.15,
            yanchor="top"
        )],
        title="Top 10 Commands by Frequency",
        xaxis_title="Command",
        yaxis_title="Frequency",
        template="plotly_white",
        showlegend=False,
        margin=dict(t=80, b=80, l=60, r=30),
        height=600
    )

    fig.update_xaxes(tickangle=-45)
    fig.write_html("command_usage.html")
    fig.show()

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
