"""
Business modules root — auto-discovered on startup.

Contract
--------
Each subdirectory of ``app/business/`` with an ``__init__.py`` is treated as a
business module. ``app/core/autodiscover.py`` will look for these optional
entry points (all are opt-in):

* ``models.py`` or ``models/`` — Tortoise ORM models, registered into
  ``TORTOISE_ORM["apps"]`` automatically.
* ``api/`` package or ``api.py`` — must export ``router: APIRouter``.
  Mounted under ``/api/v1/business/``.
* ``init_data.py`` — may export ``async def init()`` which runs once per
  startup after the system init step and before the Redis cache refresh.
  Use it to seed module-specific menus, buttons, roles, and demo data.

Directories starting with an underscore are skipped.

Recommended layout
------------------
::

    app/business/<name>/
    ├── __init__.py
    ├── config.py          # per-module pydantic settings
    ├── ctx.py             # per-module context vars (if needed)
    ├── dependency.py      # per-module FastAPI dependencies
    ├── models.py          # Tortoise models
    ├── schemas.py         # Pydantic schemas (inherit SchemaBase)
    ├── controllers.py     # CRUDBase subclasses (single-resource)
    ├── services.py        # multi-model orchestration, Redis, transactions
    ├── init_data.py       # async def init() — seed menus/roles/etc.
    └── api/
        ├── __init__.py    # must export `router` aggregating sub-routers
        ├── manage.py
        └── my.py

Rules
-----
* Business modules MUST NOT be imported from ``app.system.*`` — dependency
  flows one way: ``system → utils → business``. Business code should import
  shared helpers from ``app.utils`` only.
* All schemas MUST inherit ``app.core.base_schema.SchemaBase`` (re-exported
  from ``app.utils``) so request/response bodies are camelCase.
* All HTTP routes MUST follow the project-wide API conventions in
  ``CLAUDE.md`` (POST /resources/search for list, no trailing slashes,
  camelCase bodies, ``Success``/``Fail``/``SuccessExtra`` responses).
* Do not auto-run ``makemigrations`` from business init code. Migrations
  are a manual step (``tortoise makemigrations && tortoise migrate``).
"""
