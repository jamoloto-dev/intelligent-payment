"""Azure Key Vault integration with environment fallback."""

import os

from shared.logging.logger import get_logger

logger = get_logger("azure_keyvault")


class SecretProvider:
    """Retrieves configuration secrets securely from Azure Key Vault or environment."""

    def __init__(self, keyvault_url: str | None = None):
        self.keyvault_url = keyvault_url or os.getenv("AZURE_KEYVAULT_URL")
        self.client = None

        if self.keyvault_url and os.getenv("USE_AZURE_INTEGRATION", "false").lower() == "true":
            try:
                from azure.identity import DefaultAzureCredential
                from azure.keyvault.secrets import SecretClient

                credential = DefaultAzureCredential()
                self.client = SecretClient(vault_url=self.keyvault_url, credential=credential)
                logger.info(f"Initialized Azure Key Vault client for {self.keyvault_url}")
            except Exception as e:
                logger.warning(
                    f"Could not connect to Azure Key Vault: {e}. Using environment fallback."
                )

    def get_secret(self, secret_name: str, default: str | None = None) -> str | None:
        """Fetch secret from Azure Key Vault, falling back to OS environment variable."""
        if self.client:
            try:
                # Key Vault secret names only allow alphanumeric and dashes
                vault_secret_name = secret_name.replace("_", "-")
                secret = self.client.get_secret(vault_secret_name)
                if secret and secret.value:
                    return secret.value
            except Exception as e:
                logger.warning(f"Failed to fetch secret '{secret_name}' from Key Vault: {e}")

        # Fallback to local environment
        return os.getenv(secret_name, default)
