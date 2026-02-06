import os

# Path to your networks folder (local copy of repo)
networks_dir = "../figures/networks"

# GitHub URLs
base_github_folder = "https://github.com/ecastillot/UTDQuake/tree/main/figures/networks"
base_github_raw = "https://raw.githubusercontent.com/ecastillot/UTDQuake/main/figures/networks"

# Output .rst file
output_file = "networks_table.rst"

lines = []
lines.append(".. list-table:: Available Networks")
lines.append("   :widths: 15 25 30")
lines.append("   :header-rows: 1\n")
lines.append("   * - Network")
lines.append("     - Figures Folder")
lines.append("     - Preview\n")

for network in sorted(os.listdir(networks_dir)):
    folder_url = f"{base_github_folder}/{network}"
    # Assuming each network has a summary GIF named NETWORK_summary.gif
    img_url = f"{base_github_raw}/{network}/{network}_overview.png"

    lines.append(f"   * - {network}")
    lines.append(f"     - `Open Folder <{folder_url}>`_")
    lines.append(f"     - .. image:: {img_url}")
    lines.append(f"          :width: 200px\n")

with open(output_file, "w") as f:
    f.write("\n".join(lines))

print(f"Generated {output_file} with {len(os.listdir(networks_dir))} networks.")
