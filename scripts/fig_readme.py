import os

# Path to your networks folder (local copy of repo)
networks_dir = "../figures/networks"

# GitHub URLs
base_github_folder = "https://github.com/ecastillot/UTDQuake/tree/main/figures/networks"
base_github_raw = "https://raw.githubusercontent.com/ecastillot/UTDQuake/main/figures/networks"

# Output Markdown file
output_file = "networks_table.md"

lines = []

# Markdown table header
lines.append("## Available Networks\n")
lines.append("| Network | Figures Folder | Preview |")
lines.append("|--------|----------------|---------|")

for network in sorted(os.listdir(networks_dir)):

    # Skip hidden files (like .DS_Store)
    if network.startswith("."):
        continue

    folder_url = f"{base_github_folder}/{network}"
    img_url = f"{base_github_raw}/{network}/{network}_overview.png"

    row = f"| {network} | [Open Folder]({folder_url}) | <img src=\"{img_url}\" width=\"200\"> |"
    lines.append(row)

with open(output_file, "w") as f:
    f.write("\n".join(lines))

print(f"Generated {output_file} with {len(os.listdir(networks_dir))} networks.")
