# DE házi feladat

## Mi ez a repo?

Ez egy lokális Airflow fejlesztői környezet. Elő van készítve, hogy az infrastruktúrával ne kelljen foglalkozni — koncentrálj a DAG-ok írására és az adatmérnöki logikára. Bármit megváltoztathatsz, ami nem tetszik.

A repo tartalmaz:

- **Apache Airflow 2.10.4** Dockerben futtatva (webserver + scheduler + Postgres metaadatbázis)
- **`packages/template_package`** — egy Python csomag, ami szerkeszthető módban van telepítve Airflow-ba. Ide kerüljön az újrafelhasználható logika (DB kapcsolatok, transzformációk, segédfüggvények stb.), és a DAG-okból importálható
- **`dags/`** — DAG fájlok; minden ide kerülő `.py` fájlt automatikusan felvesz az Airflow (volume-mount, nincs szükség újraépítésre)

---

## Előfeltételek

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (lokális fejlesztéshez és csomagok hozzáadásához)

---

## Első indítás

```bash
docker compose up --build
```

Ez felépíti az image-t, inicializálja az Airflow adatbázist, létrehozza az admin felhasználót, és elindítja az összes szolgáltatást. Kódváltozás nélküli újraindításhoz elég:

```bash
docker compose up
```

---

## Airflow UI

Futás közben elérhető: **http://localhost:8085**

| Felhasználónév | Jelszó  |
|----------------|---------|
| `admin`        | `admin` |

---

## Projekt struktúra

```
.
├── dags/                         # A DAG fájlok ide kerülnek
│   └── example_dag.py
├── packages/
│   └── template_package/         # Az újrafelhasználható Python csomag
│       ├── pyproject.toml        # Függőségek definíciója (ezt szerkeszd)
│       ├── requirements.txt      # Auto-generált — NE szerkeszd kézzel
│       └── template_package/     # A tényleges Python forráskód
├── Dockerfile
├── docker-compose.yml
└── update_requirementy.sh        # Requirements.txt biztonságos újragenerálása
```

---

## DAG-ok írása

A DAG-ok volume-mountolva vannak — hozz létre egy `.py` fájlt a `dags/` mappában, és az Airflow másodperceken belül felveszi. **Nincs szükség újraépítésre.**

A `template_package`-ből való importálás DAG-ban:

```python
from template_package.example_module import my_function
```

A `template_package` **szerkeszthető módban** (editable install) van telepítve a konténerekben, így a forrásfájlok változásai azonnal érvényesülnek újraépítés nélkül.

---

## Python függőség hozzáadása

> ⚠️ Mindig ebben a sorrendben kövesd a lépéseket. A `requirements.txt`-t **ne szerkeszd kézzel**.

```bash
# 1. Csomag hozzáadása uv-vel (frissíti a pyproject.toml-t és a uv.lock-ot)
cd packages/template_package
uv add <csomagnév>

# 2. Vissza a repo gyökerére, requirements.txt újragenerálása
cd ../..
bash update_requirementy.sh

# 3. Docker image újraépítése az új csomag telepítéséhez
docker compose build --no-cache
docker compose up
```

**Miért kell a script?** A `requirements.txt`-t a `uv pip compile` generálja az Airflow constraint fájl felhasználásával. Ez garantálja, hogy az új függőség kompatibilis az Airflow saját pinned verzióival — ha nem az, a script jól látható hibával áll le, mielőtt bármi eltörne.

---

## Requirements frissítése

Ha kézzel szerkesztetted a `pyproject.toml`-t, vagy upstream változásokat húztál be:

```bash
bash update_requirementy.sh
docker compose build --no-cache
docker compose up
```

---

## Tesztek futtatása

```bash
cd packages/template_package
uv sync                 # dev függőségek lokális telepítése
uv run pytest
```

---

## Leállítás és takarítás

```bash
# Konténerek leállítása (adatok megmaradnak)
docker compose down

# Leállítás és az összes adat törlése (Postgres + MSSQL volume is)
docker compose down -v
```

---

## Célrendszer (MSSQL)

A stack részeként fut egy Microsoft SQL Server 2022 példány. Úgy kell kezelni, mint egy távoli adatbázis-szervert — a feladat: kapcsolódj hozzá, hozz létre egy sémát, és írj bele adatot.

### Kapcsolódási adatok

| Tulajdonság | Érték |
|---|---|
| Host (Docker-ből / DAG kódból) | `mssql` |
| Host (saját gépről) | `localhost` |
| Port | `1433` |
| Adatbázis | `candidate_db` |
| Felhasználónév | `candidate` |
| Jelszó | `HwC4ndidate#2026` |

### Kapcsolódás DAG-ból

A kapcsolódási adatok előre be vannak töltve **Airflow Variable**-ként, így nem kell hardcode-olni:

```python
from airflow.models import Variable
import pymssql

conn = pymssql.connect(
    server=Variable.get("mssql_host"),
    port=int(Variable.get("mssql_port")),
    database=Variable.get("mssql_database"),
    user=Variable.get("mssql_user"),
    password=Variable.get("mssql_password"),
)
```

SQLAlchemy-vel:

```python
from sqlalchemy import create_engine
from airflow.models import Variable

engine = create_engine(
    f"mssql+pymssql://{Variable.get('mssql_user')}:{Variable.get('mssql_password')}"
    f"@{Variable.get('mssql_host')}:{Variable.get('mssql_port')}"
    f"/{Variable.get('mssql_database')}"
)
```

> **Miért `pymssql` és nem pyodbc?**  
> A `pymssql` önálló wheel-ként érkezik — nem szükséges rendszerszintű ODBC driver telepítése.  
> Már szerepel a `requirements.txt`-ben és telepítve van az Airflow konténerekbe.

---

## Függőségkezelés — hogyan működik

A `requirements.txt` **nem** egy sima pip requirements fájl. A `uv pip compile` állítja elő az [Airflow 2.10.4 constraint fájl](https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.12.txt) felhasználásával.

Ez azt jelenti:
- Minden pinned verzió garantáltan kompatibilis az Airflow-val
- A `requirements.txt` kommentjei megmutatják, miért éppen az adott verzió lett választva
- A `bash update_requirementy.sh` futtatása mindig biztonságos — ütközés esetén jól látható hibával leáll, ahelyett hogy csendben törött image-t hozna létre
