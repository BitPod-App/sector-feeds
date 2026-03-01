PYTHON ?= $(shell if [ -x .venv311/bin/python ]; then echo .venv311/bin/python; elif [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
SHOW_KEY ?= jack_mallers_show
INTAKE_JSON ?= ../bitregime-core/artifacts/intake/$(SHOW_KEY)_intake.json
DECK_ID ?= deck_weekly_btc

.PHONY: test audit legacy-tuesday-track legacy-friday-track experimental-track print-show-contract feed-identity-check track-status-board track-status-check daily-ops-check preflight release-ready ops-cycle dns-set-fast dns-restore-default today-run today-run-no-dns handoff-refresh smoke-public stale-check bootstrap-show intake-handshake-check intake-gate-daily intake-gate-triage intake-gate-weekly-summary taylor-keepalive final-check

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

audit:
	bash scripts/check_repo_size.sh
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

legacy-tuesday-track:
	bash scripts/run_legacy_tuesday_track.sh $(SHOW_KEY)

legacy-friday-track:
	bash scripts/run_legacy_friday_track.sh $(SHOW_KEY)

experimental-track:
	bash scripts/run_experimental_track.sh $(SHOW_KEY)

print-show-contract:
	bash scripts/print_show_contract.sh $(SHOW_KEY)

feed-identity-check:
	bash scripts/check_feed_identity_contract.sh $(SHOW_KEY)

track-status-board:
	bash scripts/render_track_status_board.sh $(SHOW_KEY)

track-status-check:
	bash scripts/check_track_status_board.sh $(SHOW_KEY)

daily-ops-check:
	bash scripts/run_daily_ops_check.sh $(SHOW_KEY)

preflight:
	bash scripts/check_feed_identity_contract.sh $(SHOW_KEY)
	bash scripts/print_show_contract.sh $(SHOW_KEY)
	bash scripts/check_track_status_board.sh $(SHOW_KEY)
	bash scripts/run_daily_ops_check.sh $(SHOW_KEY)

release-ready:
	$(MAKE) preflight SHOW_KEY=$(SHOW_KEY)
	$(PYTHON) -m unittest tests.test_storage tests.test_intake
	@echo "release_ready=PASS"
	@echo "deploy_command=bash scripts/deploy_public_permalinks_pages.sh"

ops-cycle:
	$(MAKE) legacy-tuesday-track SHOW_KEY=$(SHOW_KEY)
	$(MAKE) legacy-friday-track SHOW_KEY=$(SHOW_KEY)
	$(MAKE) experimental-track SHOW_KEY=$(SHOW_KEY)
	$(MAKE) track-status-board SHOW_KEY=$(SHOW_KEY)
	$(MAKE) track-status-check SHOW_KEY=$(SHOW_KEY)

dns-set-fast:
	bash scripts/dns_set_fast.sh

dns-restore-default:
	bash scripts/dns_restore_default.sh

today-run:
	$(MAKE) dns-set-fast
	$(MAKE) ops-cycle SHOW_KEY=$(SHOW_KEY)
	$(MAKE) release-ready SHOW_KEY=$(SHOW_KEY)
	$(MAKE) dns-restore-default

today-run-no-dns:
	$(MAKE) ops-cycle SHOW_KEY=$(SHOW_KEY)
	$(MAKE) release-ready SHOW_KEY=$(SHOW_KEY)

handoff-refresh:
	bash scripts/handoff_refresh.sh $(SHOW_KEY)

smoke-public:
	bash scripts/smoke_public.sh $(SHOW_KEY)

stale-check:
	bash scripts/stale_check.sh $(SHOW_KEY)

bootstrap-show:
	@echo "Usage: bash scripts/bootstrap_show.sh <show_key> <rss_url> <stable_pointer_md> <sector> [format_tag] [youtube_handle] [youtube_channel_id]"

intake-handshake-check:
	bash scripts/check_bitregime_core_intake_handshake.sh "$(INTAKE_JSON)" "$(DECK_ID)"

intake-gate-daily:
	bash scripts/run_intake_gate_daily.sh "$(INTAKE_JSON)" "$(DECK_ID)"

intake-gate-triage:
	bash scripts/run_intake_gate_triage.sh "$(INTAKE_JSON)" "$(DECK_ID)"

intake-gate-weekly-summary:
	bash scripts/report_intake_gate_weekly.sh

taylor-keepalive:
	bash scripts/taylor_runtime_keepalive.sh

final-check:
	$(MAKE) today-run-no-dns SHOW_KEY=$(SHOW_KEY)
	$(MAKE) handoff-refresh SHOW_KEY=$(SHOW_KEY)
	$(MAKE) smoke-public SHOW_KEY=$(SHOW_KEY)
