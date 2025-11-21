PlantUML diagrams for the library system

Files:
- borrow_activity.puml
- return_activity.puml
- borrow_sequence.puml
- return_backup_sequence.puml

Render helper:
- scripts/render_plantuml.py

How to render (macOS, zsh):

1) Install PlantUML CLI (recommended):

   brew install plantuml

Then run:

```bash
python3 scripts/render_plantuml.py --outdir diagrams/plantuml/output
```

This will create PNG and SVG files in `diagrams/plantuml/output`.

2) Or use plantuml.jar:

- Download `plantuml.jar` from https://plantuml.com/download
- Set `PLANTUML_JAR` environment variable to the jar path, e.g.

```bash
export PLANTUML_JAR="$HOME/tools/plantuml.jar"
python3 scripts/render_plantuml.py --outdir diagrams/plantuml/output
```

Notes & suggestions:
- The .puml files are a close reconstruction from the attached images. You can tweak labels/flow/notes if you want more detail.
- If you prefer SVG only, pass `plantuml -tsvg` or edit the script to skip PNG.
