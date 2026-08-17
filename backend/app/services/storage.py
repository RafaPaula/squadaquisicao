"""Armazenamento dos arquivos originais de curriculo.

STORAGE_BACKEND=local guarda em disco (bom para desenvolvimento).
STORAGE_BACKEND=azure_blob guarda em Azure Blob Storage (uso em produção,
alinhado ao plano de hospedar o software no Azure).
"""

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings


class ResumeStorage(ABC):
    @abstractmethod
    def save(self, filename: str, content: bytes) -> str:
        """Salva o arquivo e retorna um path/identificador para recuperá-lo depois."""

    @abstractmethod
    def read(self, storage_path: str) -> bytes:
        ...


class LocalResumeStorage(ResumeStorage):
    def __init__(self) -> None:
        self._root = Path(settings.STORAGE_LOCAL_PATH)
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> str:
        path = self._root / filename
        path.write_bytes(content)
        return str(path)

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()


class AzureBlobResumeStorage(ResumeStorage):
    def __init__(self) -> None:
        from azure.storage.blob import BlobServiceClient

        self._client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self._container = settings.AZURE_STORAGE_CONTAINER
        self._client.create_container(self._container) if not self._container_exists() else None

    def _container_exists(self) -> bool:
        return self._client.get_container_client(self._container).exists()

    def save(self, filename: str, content: bytes) -> str:
        blob = self._client.get_blob_client(container=self._container, blob=filename)
        blob.upload_blob(content, overwrite=True)
        return filename

    def read(self, storage_path: str) -> bytes:
        blob = self._client.get_blob_client(container=self._container, blob=storage_path)
        return blob.download_blob().readall()


def get_storage() -> ResumeStorage:
    if settings.STORAGE_BACKEND == "azure_blob":
        return AzureBlobResumeStorage()
    return LocalResumeStorage()
