#!/bin/bash
# Starts SQL Server in the background, waits until it accepts connections,
# runs the one-time init script, then hands control back to sqlservr.

set -e

echo "[entrypoint] Starting SQL Server..."
/opt/mssql/bin/sqlservr &
MSSQL_PID=$!

echo "[entrypoint] Waiting for SQL Server to become available (up to 90s)..."
for i in $(seq 1 45); do
    if /opt/mssql-tools18/bin/sqlcmd \
            -S localhost \
            -U sa \
            -P "$MSSQL_SA_PASSWORD" \
            -Q "SELECT 1" \
            -b \
            -C \
            2>/dev/null; then
        echo "[entrypoint] SQL Server is up."
        break
    fi
    echo "[entrypoint] Attempt $i/45 – not ready yet, retrying in 2s..."
    sleep 2
done

echo "[entrypoint] Running init.sql..."
/opt/mssql-tools18/bin/sqlcmd \
    -S localhost \
    -U sa \
    -P "$MSSQL_SA_PASSWORD" \
    -i /docker-init/init.sql \
    -C

echo "[entrypoint] Initialisation complete."

# Return control to SQL Server
wait $MSSQL_PID
