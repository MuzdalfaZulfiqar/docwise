up:        ; docker compose up --build
down:      ; docker compose down
test:      ; cd backend && pytest -q
lint:      ; cd backend && ruff check .
eval:      ; cd backend && python -m eval.run_eval --strategy structure --mode hybrid
eval-all:  ; cd backend && python -m eval.run_all
