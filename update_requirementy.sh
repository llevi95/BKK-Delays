#!/bin/bash

# Airflow constraint file - must match the version in Dockerfile
AIRFLOW_CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt"

# Set the base directory for the packages
BASE_DIR="./packages"

for PACKAGE_DIR in "$BASE_DIR"/*; do
    if [ -d "$PACKAGE_DIR" ] && [ -f "$PACKAGE_DIR/pyproject.toml" ]; then
        echo "Updating requirements.txt for package: $(basename "$PACKAGE_DIR")"

        cd "$PACKAGE_DIR" || exit

        # Use uv pip compile to resolve dependencies against the Airflow constraint file.
        # This guarantees the output requirements.txt is compatible with Airflow's
        # pinned versions, avoiding conflicts at Docker build time.
        uv pip compile \
            --constraint "$AIRFLOW_CONSTRAINT_URL" \
            --no-header \
            --strip-extras \
            --output-file requirements.txt \
            pyproject.toml

        if [ $? -eq 0 ]; then
            echo "Successfully updated requirements.txt for $(basename "$PACKAGE_DIR")"
        else
            echo "Failed to update requirements.txt for $(basename "$PACKAGE_DIR") - Check Airflow constraints! "$AIRFLOW_CONSTRAINT_URL""
            exit 1
        fi

        cd - > /dev/null || exit
    else
        echo "Skipping $(basename "$PACKAGE_DIR"): Not a valid package."
    fi
done

echo "All requirements.txt files have been updated."
