from httpx import AsyncClient


async def test_product_openapi_excludes_health(client: AsyncClient) -> None:
    product = await client.get("/api/v1/openapi.json")
    platform = await client.get("/openapi.json")

    assert product.status_code == 200
    document = product.json()
    assert document["info"]["title"] == "DevSphere API"
    assert document["openapi"].startswith("3.")
    assert "/health" not in document["paths"]
    assert platform.status_code == 404
