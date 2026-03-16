import argparse
import csv
import sqlite3
from pathlib import Path


def get_table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [row[0] for row in rows]


def export_table(conn: sqlite3.Connection, table_name: str, output_file: Path) -> int:
    cursor = conn.execute(f'SELECT * FROM "{table_name}"')
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export SQLite tables to CSV files."
    )
    parser.add_argument(
        "--db",
        default="data/quote_replier.sqlite3",
        help="SQLite file path (default: data/quote_replier.sqlite3)",
    )
    parser.add_argument(
        "--out",
        default="data/csv_export",
        help="Output directory for CSV files (default: data/csv_export)",
    )
    parser.add_argument(
        "--table",
        action="append",
        help="Table name to export. Can be used multiple times. If omitted, export all tables.",
    )

    args = parser.parse_args()
    db_path = Path(args.db)
    out_dir = Path(args.out)

    if not db_path.exists():
        raise FileNotFoundError(f"SQLite file not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        available_tables = get_table_names(conn)
        if not available_tables:
            print("No user tables found in database.")
            return

        target_tables = args.table if args.table else available_tables

        invalid_tables = [t for t in target_tables if t not in available_tables]
        if invalid_tables:
            raise ValueError(
                f"Table(s) not found: {', '.join(invalid_tables)}. "
                f"Available tables: {', '.join(available_tables)}"
            )

        for table in target_tables:
            row_count = export_table(conn, table, out_dir / f"{table}.csv")
            print(f"Exported {table}: {row_count} rows -> {out_dir / f'{table}.csv'}")


if __name__ == "__main__":
    main()
