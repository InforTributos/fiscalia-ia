# Archive Report: Tests de caracterizacion del modulo MCP

## Summary

Se escribieron 28 tests de caracterizacion para 5 archivos del modulo MCP y `tasks/analisis_task.py` que tenian 0% de cobertura. La cobertura total paso de 72% (116 tests) a 79% (144 tests).

## Decisions Made

- **Characterization testing over TDD estricto**: El codigo ya existia. Se escribieron tests que documentan y verifican el comportamiento actual en lugar de forzar RED→GREEN puro (donde RED seria un test fallido que requiere escribir implementacion nueva).
- **Mock de `streamable_http_client`**: Se mockea como async context manager con `return_value.__aenter__.return_value`. Alternativa descartada: usar `httpx` directamente sin el SDK MCP (requiere reescribir el adapter).
- **`new_callable=AsyncMock` para `with_retry`**: Necesario para mockear correctamente funciones asincronas en `analisis_task.py`. Sin esto, el mock no maneja `await` correctamente.
- **`_Call` indexing**: Descubrimos que `_Call.__getitem__` no indexa argumentos posicionales. `c[0]` retorna `args`, `c[1]` retorna `kwargs`.

## Lessons Learned

1. **Mocking async context managers**: Cadena `mock_cls.return_value.__aenter__.return_value = inner_mock`. El `__aexit__` no se necesita si no se verifica comportamiento en exit.
2. **`call_args` vs `call_args_list`**: Para `AsyncMock`, `call_args` es un objeto `_Call`, no una tupla. Acceder a argumentos posicionales requiere `call.args[n]`.
3. **Pagination SQL**: Los placeholders de `IN (:actividades)` se construyen con `.format()` antes de pasar a `EXECUTE_SQL`. Es importante testear que el SQL resultante sea correcto.
4. **UUID en analisis_task**: La funcion convierte strings a UUID con `uuid.UUID()`. Los tests deben pasar objetos UUID, no strings, en los `assert_any_call`.

## Follow-ups

- LLM providers (anthropic, openai, nvidia, huggingface) siguen sin tests — requieren API keys
- Un punto porcentual para el quality gate de 80% — accesible con tests de providers mockeados
- Stress test con locust pendiente
- Redis para rate limiter y cache distribuida pendiente
