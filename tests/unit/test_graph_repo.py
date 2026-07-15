from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from infrastructure.mcp.graph import (
    ATTRIBUTE_COLUMNS,
    OracleGraphRepository,
    _normalizar_atributos,
    _resolver_columna,
)


class TestResolverColumna:
    def test_matches_first_column(self):
        row = {"representante_legal": "Juan", "representante": "", "id_representante": "123"}
        result = _resolver_columna(row, ATTRIBUTE_COLUMNS["representante"])
        assert result == "representante_legal"

    def test_matches_second_column_when_first_empty(self):
        row = {"representante_legal": "", "representante": "Maria", "id_representante": "123"}
        result = _resolver_columna(row, ATTRIBUTE_COLUMNS["representante"])
        assert result == "representante"

    def test_all_empty_strings_returns_none(self):
        row = {"representante_legal": "", "representante": None, "id_representante": ""}
        result = _resolver_columna(row, ATTRIBUTE_COLUMNS["representante"])
        assert result is None

    def test_none_values_returns_none(self):
        row = {"representante_legal": None, "representante": None}
        result = _resolver_columna(row, ("representante_legal", "representante"))
        assert result is None

    def test_missing_columns_returns_none(self):
        row = {"nombre": "foo"}
        result = _resolver_columna(row, ("representante_legal", "representante"))
        assert result is None


class TestNormalizarAtributos:
    def test_maps_all_attribute_columns(self):
        row = {
            "nit": "123",
            "razon_social": "Test SA",
            "representante_legal": "Juan",
            "direccion_principal": "Calle 123",
            "celular": "3001234567",
            "correo_electronico": "test@test.com",
        }
        result = _normalizar_atributos(row)
        assert result["representante"] == "Juan"
        assert result["direccion"] == "Calle 123"
        assert result["telefono"] == "3001234567"
        assert result["correo"] == "test@test.com"

    def test_preserves_original_columns(self):
        row = {"nit": "123", "razon_social": "Test SA"}
        result = _normalizar_atributos(row)
        assert result["nit"] == "123"
        assert result["razon_social"] == "Test SA"

    def test_first_matching_column_wins(self):
        row = {
            "nit": "123",
            "representante_legal": "Juan",
            "representante": "Pedro",
        }
        result = _normalizar_atributos(row)
        assert result["representante"] == "Juan"

    def test_empty_values_leave_normalized_key_unset(self):
        row = {
            "nit": "123",
            "representante_legal": "",
        }
        result = _normalizar_atributos(row)
        assert "representante" not in result

    def test_all_attribute_groups_empty(self):
        row = {"nit": "123", "razon_social": "Test SA"}
        result = _normalizar_atributos(row)
        assert result["nit"] == "123"
        for atributo in ATTRIBUTE_COLUMNS:
            assert atributo not in result


class TestOracleGraphRepository:
    @pytest.mark.asyncio
    @patch("infrastructure.mcp.graph.OracleClient")
    async def test_obtener_contribuyente_found(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_sql = AsyncMock()
        mock_client.execute_sql.return_value = [
            {
                "nit": "123",
                "razon_social": "Test SA",
                "representante_legal": "Juan",
                "direccion": "Calle 123",
                "telefono_principal": "3001234567",
                "correo_electronico": "test@test.com",
            },
        ]

        repo = OracleGraphRepository()
        result = await repo.obtener_contribuyente("123")

        assert result is not None
        assert result["nit"] == "123"
        assert result["representante"] == "Juan"
        assert result["direccion"] == "Calle 123"
        assert result["telefono"] == "3001234567"
        assert result["correo"] == "test@test.com"
        mock_client.execute_sql.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("infrastructure.mcp.graph.OracleClient")
    async def test_obtener_contribuyente_not_found(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_sql = AsyncMock()
        mock_client.execute_sql.return_value = []

        repo = OracleGraphRepository()
        result = await repo.obtener_contribuyente("999")

        assert result is None

    @pytest.mark.asyncio
    @patch("infrastructure.mcp.graph.OracleClient")
    async def test_obtener_relacionados_with_values(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_sql = AsyncMock()

        raw_contribuyente = {
            "nit": "123",
            "razon_social": "Test SA",
            "representante_legal": "Juan",
            "direccion_principal": "",
            "telefono_principal": "3001234567",
            "correo_electronico": "test@test.com",
        }
        contribuyente = _normalizar_atributos(raw_contribuyente)

        mock_client.execute_sql.side_effect = [
            [{"nit": "456", "razon_social": "Rel SA", "representante_legal": "Juan"}],
            [
                {"nit": "789", "razon_social": "Cel SA", "telefono_principal": "3001234567"},
                {"nit": "012", "razon_social": "Movil SA", "telefono_principal": "3001234567"},
            ],
            [{"nit": "345", "razon_social": "Corp SA", "correo_electronico": "test@test.com"}],
        ]

        repo = OracleGraphRepository()
        result = await repo.obtener_relacionados(contribuyente)

        assert "representante" in result
        assert len(result["representante"]) == 1
        assert result["representante"][0]["nit"] == "456"

        assert "direccion" in result
        assert result["direccion"] == []

        assert "telefono" in result
        assert len(result["telefono"]) == 2

        assert "correo" in result
        assert len(result["correo"]) == 1

    @pytest.mark.asyncio
    @patch("infrastructure.mcp.graph.OracleClient")
    async def test_obtener_relacionados_all_empty_values(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_sql = AsyncMock()

        raw_contribuyente = {
            "nit": "123",
            "razon_social": "Test SA",
            "representante_legal": "",
            "direccion_principal": "",
            "telefono_principal": None,
            "correo_electronico": "",
        }
        contribuyente = _normalizar_atributos(raw_contribuyente)

        repo = OracleGraphRepository()
        result = await repo.obtener_relacionados(contribuyente)

        for atributo in ATTRIBUTE_COLUMNS:
            assert atributo in result
            assert result[atributo] == []

        mock_client.execute_sql.assert_not_called()

    @pytest.mark.asyncio
    @patch("infrastructure.mcp.graph.OracleClient")
    async def test_obtener_relacionados_respects_limit(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_sql = AsyncMock()

        raw_contribuyente = {
            "nit": "123",
            "razon_social": "Test SA",
            "representante_legal": "Juan",
            "direccion_principal": "",
            "telefono_principal": "",
            "correo_electronico": "",
        }
        contribuyente = _normalizar_atributos(raw_contribuyente)

        mock_client.execute_sql.return_value = [
            {"nit": "456", "razon_social": "Rel SA", "representante_legal": "Juan"},
        ]

        repo = OracleGraphRepository()
        result = await repo.obtener_relacionados(contribuyente, limit=10)

        assert "representante" in result
        assert len(result["representante"]) == 1

        args = mock_client.execute_sql.call_args[0]
        assert args[1]["limit"] == 10

    @pytest.mark.asyncio
    @patch("infrastructure.mcp.graph.OracleClient")
    async def test_obtener_relacionados_normalizes_results(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.execute_sql = AsyncMock()

        raw_contribuyente = {
            "nit": "123",
            "razon_social": "Test SA",
            "representante_legal": "Juan",
            "direccion_principal": "",
            "telefono_principal": "",
            "correo_electronico": "",
        }
        contribuyente = _normalizar_atributos(raw_contribuyente)

        mock_client.execute_sql.return_value = [
            {"nit": "456", "razon_social": "Rel SA", "representante_legal": "Juan"},
        ]

        repo = OracleGraphRepository()
        result = await repo.obtener_relacionados(contribuyente)

        assert "representante" in result
        assert result["representante"][0]["nit"] == "456"
        assert result["representante"][0].get("representante") == "Juan"
