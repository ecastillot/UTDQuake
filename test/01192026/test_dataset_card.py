from utdquake.utils.dataset_card import generate_hf_manifest


manifest_folder = "/groups/igonin/ecastillo/UTDQuake/_hf_stage/manifests"
yaml_path = "/groups/igonin/ecastillo/utdquake/test/01192026/test_dataset_card.md"
generate_hf_manifest(manifest_folder,yaml_path,
                      config="network" )