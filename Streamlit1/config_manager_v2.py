"""
Secure configuration management with encryption.

This module handles loading, saving, and encrypting application configuration,
including OAuth tokens and database credentials.
"""

import json
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
import base64

from .models import AppConfig, ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

# Configuration file paths
CONFIG_FILE = "saved_config.json"
KEY_FILE = ".config_key"  # Hidden file for encryption key


class ConfigManager:
    """
    Manages application configuration with encryption for sensitive data.
    """

    def __init__(self, config_file: str = CONFIG_FILE, key_file: str = KEY_FILE):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to configuration file
            key_file: Path to encryption key file
        """
        self.config_file = config_file
        self.key_file = key_file
        self._fernet: Optional[Fernet] = None

    def _get_or_create_key(self) -> bytes:
        """
        Get encryption key from file or create new one.

        Returns:
            Encryption key bytes

        Raises:
            ConfigurationError: If key operations fail
        """
        try:
            if os.path.exists(self.key_file):
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                logger.debug("Loaded existing encryption key")
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                logger.info("Generated new encryption key")

                # Hide the key file on Windows
                if os.name == 'nt':
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(self.key_file, 2)  # FILE_ATTRIBUTE_HIDDEN

            return key

        except Exception as e:
            raise ConfigurationError(f"Failed to manage encryption key: {str(e)}")

    def _get_cipher(self) -> Fernet:
        """
        Get or create Fernet cipher instance.

        Returns:
            Fernet cipher
        """
        if self._fernet is None:
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet

    def _encrypt_value(self, value: str) -> str:
        """
        Encrypt a string value.

        Args:
            value: Plain text value

        Returns:
            Base64-encoded encrypted value
        """
        if not value:
            return ""

        cipher = self._get_cipher()
        encrypted = cipher.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()

    def _decrypt_value(self, encrypted_value: str) -> str:
        """
        Decrypt an encrypted value.

        Args:
            encrypted_value: Base64-encoded encrypted value

        Returns:
            Decrypted plain text

        Raises:
            ConfigurationError: If decryption fails
        """
        if not encrypted_value:
            return ""

        try:
            cipher = self._get_cipher()
            encrypted = base64.b64decode(encrypted_value.encode())
            decrypted = cipher.decrypt(encrypted)
            return decrypted.decode()

        except Exception as e:
            raise ConfigurationError(f"Failed to decrypt value: {str(e)}")

    def save_config(self, config: AppConfig) -> bool:
        """
        Save configuration to encrypted file.

        Args:
            config: Application configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert config to dict
            config_dict = config.model_dump()

            # Encrypt sensitive fields
            encrypted_dict = {
                "version": "2.0",  # Mark as encrypted format
                "datasphere": {
                    "host": config.dsp_host,
                    "space": config.dsp_space or ""
                },
                "database": {
                    "address": config.hdb_address,
                    "port": config.hdb_port,
                    "user": config.hdb_user,
                    "password_encrypted": self._encrypt_value(config.hdb_password)
                },
                "oauth": {
                    "client_id": config.client_id,
                    "client_secret_encrypted": self._encrypt_value(config.client_secret),
                    "authorization_url": config.authorization_url,
                    "token_url": config.token_url
                },
                "token": {
                    "access_token_encrypted": self._encrypt_value(config.access_token or ""),
                    "refresh_token_encrypted": self._encrypt_value(config.refresh_token or ""),
                    "expires_in": config.token_expires_in,
                    "expire_time": config.token_expire_time.isoformat() if config.token_expire_time else None
                }
            }

            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(encrypted_dict, f, indent=2)

            logger.info(f"Configuration saved to {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def load_config(self) -> Optional[AppConfig]:
        """
        Load configuration from encrypted file.

        Returns:
            AppConfig instance or None if file doesn't exist

        Raises:
            ConfigurationError: If loading/decryption fails
        """
        if not os.path.exists(self.config_file):
            logger.info("No saved configuration found")
            return None

        try:
            with open(self.config_file, 'r') as f:
                encrypted_dict = json.load(f)

            # Check version
            version = encrypted_dict.get("version", "1.0")

            if version == "2.0":
                # New encrypted format
                config = AppConfig(
                    dsp_host=encrypted_dict["datasphere"]["host"],
                    dsp_space=encrypted_dict["datasphere"].get("space"),
                    hdb_address=encrypted_dict["database"]["address"],
                    hdb_port=encrypted_dict["database"]["port"],
                    hdb_user=encrypted_dict["database"]["user"],
                    hdb_password=self._decrypt_value(encrypted_dict["database"]["password_encrypted"]),
                    client_id=encrypted_dict["oauth"]["client_id"],
                    client_secret=self._decrypt_value(encrypted_dict["oauth"]["client_secret_encrypted"]),
                    authorization_url=encrypted_dict["oauth"]["authorization_url"],
                    token_url=encrypted_dict["oauth"]["token_url"],
                    access_token=self._decrypt_value(encrypted_dict["token"].get("access_token_encrypted", "")),
                    refresh_token=self._decrypt_value(encrypted_dict["token"].get("refresh_token_encrypted", "")),
                    token_expires_in=encrypted_dict["token"].get("expires_in"),
                    token_expire_time=datetime.fromisoformat(encrypted_dict["token"]["expire_time"])
                        if encrypted_dict["token"].get("expire_time") else None
                )

                logger.info("Loaded encrypted configuration")
                return config

            else:
                # Legacy unencrypted format - migrate to encrypted
                logger.warning("Loading legacy unencrypted configuration. Will migrate on next save.")

                config = AppConfig(
                    dsp_host=encrypted_dict.get("DATASPHERE", {}).get("dsp_host", ""),
                    dsp_space=encrypted_dict.get("DATASPHERE", {}).get("dsp_space"),
                    hdb_address=encrypted_dict.get("HDB", {}).get("hdb_address", ""),
                    hdb_port=encrypted_dict.get("HDB", {}).get("hdb_port", 443),
                    hdb_user=encrypted_dict.get("HDB", {}).get("hdb_user", ""),
                    hdb_password=encrypted_dict.get("HDB", {}).get("hdb_password", ""),
                    # For legacy format, OAuth and tokens need to be set separately
                    client_id="",
                    client_secret="",
                    authorization_url="",
                    token_url=""
                )

                return config

        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")

    def delete_config(self) -> bool:
        """
        Delete saved configuration file.

        Returns:
            True if successful
        """
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
                logger.info("Configuration file deleted")

            return True

        except Exception as e:
            logger.error(f"Failed to delete configuration: {e}")
            return False

    def config_exists(self) -> bool:
        """Check if configuration file exists."""
        return os.path.exists(self.config_file)

    def export_template(self, output_file: str = "config_template.json") -> bool:
        """
        Export configuration template for manual editing.

        Args:
            output_file: Output file path

        Returns:
            True if successful
        """
        try:
            template = {
                "DATASPHERE": {
                    "dsp_host": "https://your-tenant.hcs.cloud.sap",
                    "dsp_space": "YOUR_SPACE_ID (optional)"
                },
                "HDB": {
                    "hdb_address": "your-hana-address.hanacloud.ondemand.com",
                    "hdb_port": 443,
                    "hdb_user": "DWCDBUSER#YOURUSER",
                    "hdb_password": "your_password"
                },
                "OAUTH": {
                    "client_id": "your_client_id",
                    "client_secret": "your_client_secret",
                    "authorization_url": "https://your-tenant.hcs.cloud.sap/oauth/authorize",
                    "token_url": "https://your-tenant.hcs.cloud.sap/oauth/token"
                }
            }

            with open(output_file, 'w') as f:
                json.dump(template, f, indent=2)

            logger.info(f"Template exported to {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to export template: {e}")
            return False


def migrate_legacy_config() -> bool:
    """
    Migrate legacy configuration files to new encrypted format.

    Returns:
        True if migration was performed
    """
    try:
        config_manager = ConfigManager()

        # Check for legacy files
        legacy_files = {
            "config": "config.json",
            "secret": "secret.json",
            "token": "token.json"
        }

        all_exist = all(os.path.exists(f) for f in legacy_files.values())

        if not all_exist:
            return False

        logger.info("Found legacy configuration files, migrating...")

        # Load legacy files
        with open(legacy_files["config"], 'r') as f:
            config_data = json.load(f)

        with open(legacy_files["secret"], 'r') as f:
            secret_data = json.load(f)

        with open(legacy_files["token"], 'r') as f:
            token_data = json.load(f)

        # Create new config
        config = AppConfig(
            dsp_host=config_data.get("DATASPHERE", {}).get("dsp_host", ""),
            dsp_space=config_data.get("DATASPHERE", {}).get("dsp_space"),
            hdb_address=config_data.get("HDB", {}).get("hdb_address", ""),
            hdb_port=config_data.get("HDB", {}).get("hdb_port", 443),
            hdb_user=config_data.get("HDB", {}).get("hdb_user", ""),
            hdb_password=config_data.get("HDB", {}).get("hdb_password", ""),
            client_id=secret_data.get("client_id", ""),
            client_secret=secret_data.get("client_secret", ""),
            authorization_url=secret_data.get("authorization_url", ""),
            token_url=secret_data.get("token_url", ""),
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_expires_in=token_data.get("expires_in"),
            token_expire_time=datetime.fromisoformat(token_data["expire"])
                if token_data.get("expire") else None
        )

        # Save to new format
        config_manager.save_config(config)

        # Backup legacy files
        for name, file in legacy_files.items():
            backup_file = f"{file}.backup"
            os.rename(file, backup_file)
            logger.info(f"Backed up {file} to {backup_file}")

        logger.info("Migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
