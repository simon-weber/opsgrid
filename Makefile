web-deploy-prod:
	cd web && \
	ansible-playbook -v -i ansible/production ansible/deploy.yml

ingest-deploy-prod:
	cd ingest && \
	ansible-playbook -v -i ansible/production ansible/deploy.yml

nix-deploy-prod:
	nixops deploy --include golf-simon-codes -d opsgrid

# also consider vacuuming the journal:
#    journalctl --vacuum-size=500M
# and cleaning old nix generations:
#    nix-env --list-generations --profile /nix/var/nix/profiles/system
#  then
#    nix-collect-garbage --delete-older-than 120d --dry-run
cleanup-prod:
	ansible all -i ansible/production -m shell -a "nix-collect-garbage; docker system prune --force; df -h"
