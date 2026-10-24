from pathlib import Path
from backend.agent.stages.s0_profile import profile_dataset, save_schema_map

def test_s0_profile_on_dataset():
    dataset_dir = Path("dataset")
    assert dataset_dir.exists()
    
    schema_map, gate0 = profile_dataset(dataset_dir)
    assert gate0.ok is True
    assert gate0.hash_algorithm == "sha256"
    assert gate0.manifest_files_count > 0
    assert len(gate0.errors) == 0
    
    # Verify formats and resource mappings
    assert ".sql" in schema_map.formats
    assert "account" in schema_map.resource_system_map
    assert schema_map.resource_system_map["account"] == "account_service"
    
    # Save schema_map.generated.yaml
    out_yaml = Path("backend/config/schema_map.generated.yaml")
    save_schema_map(schema_map, out_yaml)
    assert out_yaml.exists()
