"""Create ai_learn_test if missing (dev helper)."""

from sqlalchemy import create_engine, text

from app.config import get_settings

get_settings.cache_clear()
s = get_settings()
root_url = (
    f"mysql+pymysql://{s.mysql_user}:{s.mysql_password}"
    f"@{s.mysql_host}:{s.mysql_port}/?charset=utf8mb4"
)
engine = create_engine(root_url)
with engine.begin() as conn:
    dbs = [
        row[0]
        for row in conn.execute(text("SHOW DATABASES LIKE 'ai_learn%'")).fetchall()
    ]
    print("schemas:", dbs)
    conn.execute(
        text(
            "CREATE DATABASE IF NOT EXISTS ai_learn_test "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    )
    print("ensured ai_learn_test")
