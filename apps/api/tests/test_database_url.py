from app.db.session import asyncpg_connect_args, prepare_database_url


def test_supabase_url_uses_asyncpg_and_tls() -> None:
    raw = "postgresql://postgres.abcd:secret@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require"

    prepared = prepare_database_url(raw)

    assert prepared.startswith("postgresql+asyncpg://")
    assert "sslmode" not in prepared
    assert asyncpg_connect_args(prepared) == {"ssl": True}


def test_local_url_does_not_force_tls() -> None:
    prepared = prepare_database_url(
        "postgresql+asyncpg://devsphere:devsphere@localhost:5432/devsphere"
    )

    assert asyncpg_connect_args(prepared) == {}
