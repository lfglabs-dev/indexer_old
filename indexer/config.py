import os
import toml
import shutil


class Config:
    def get_path(self, name):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), name
        )

    def extract_config(self, file_name, template_name):
        config_file = self.get_path(file_name)
        if not os.path.isfile(config_file):
            print(f"config {file_name} doesn't exist, copying template!")
            shutil.copyfile(self.get_path(template_name), config_file)
        return config_file


class TomlConfig(Config):
    def __init__(self, file_name, template_name):
        config_file = self.extract_config(file_name, template_name)
        self.load_config(config_file)

    def load_config(self, config_file):
        config = toml.load(config_file)

        server = config["server"]
        self.server_port = server["port"]

        contract = config["contract"]
        self.starknetid_contract = contract["starknetid"]
        self.naming_contract = contract["naming"]
        self.braavos_contract = contract["braavos"]

        apibara = config["apibara"]
        self.indexer_id = apibara["indexer_id"]
        self.reset_state = apibara["reset_state"]
        self.starting_block = apibara["starting_block"]
        self.connection_string = apibara["connection_string"]
        self.apibara_stream = apibara["apibara_stream"]
        self.token = apibara["token"]
