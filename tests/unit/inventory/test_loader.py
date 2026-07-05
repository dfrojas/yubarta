import pytest
import yaml
from pydantic import ValidationError

from yubarta.inventory.loader import load_inventory

VALID_INVENTORY = {
    "groups": {"ssh-defaults": {"transport": "ssh", "user": "yubarta", "port": 22}},
    "targets": {
        "java-app-1": {
            "group": "ssh-defaults",
            "address": "10.0.0.20",
            "labels": {"service": "java-app"},
            "credential": "sops://secrets/hosts/java-app-1.yaml#ssh_key",
        }
    },
}


def write_yaml(tmp_path, data) -> str:
    path = tmp_path / "inventory.yaml"
    path.write_text(yaml.safe_dump(data))
    return str(path)


def test_valid_inventory_loads_and_merges_group_defaults(tmp_path):
    path = write_yaml(tmp_path, VALID_INVENTORY)
    inventory = load_inventory(path)
    target = inventory.targets["java-app-1"]
    assert target.transport == "ssh"
    assert target.user == "yubarta"
    assert target.port == 22


def test_missing_file_raises_file_not_found_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_inventory(str(tmp_path / "does-not-exist.yaml"))


def test_malformed_yaml_raises_yaml_error(tmp_path):
    path = tmp_path / "inventory.yaml"
    path.write_text("targets: [unclosed")
    with pytest.raises(yaml.YAMLError):
        load_inventory(str(path))


def test_missing_required_field_raises_validation_error(tmp_path):
    data = {
        "groups": VALID_INVENTORY["groups"],
        "targets": {
            "java-app-1": {
                "group": "ssh-defaults",
                "labels": {"service": "java-app"},
                "credential": "sops://secrets/hosts/java-app-1.yaml#ssh_key",
            }
        },
    }
    path = write_yaml(tmp_path, data)
    with pytest.raises(ValidationError):
        load_inventory(path)


def test_unknown_group_reference_raises_validation_error(tmp_path):
    data = {
        "groups": VALID_INVENTORY["groups"],
        "targets": {
            "java-app-1": {
                "group": "does-not-exist",
                "address": "10.0.0.20",
                "labels": {"service": "java-app"},
                "credential": "sops://secrets/hosts/java-app-1.yaml#ssh_key",
            }
        },
    }
    path = write_yaml(tmp_path, data)
    with pytest.raises(ValidationError):
        load_inventory(path)
