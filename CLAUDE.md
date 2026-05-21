## Repository Structure

- **Blue/** — Blue team defensive operations (exploits patches, service hardening)
- **Red/** — Red team offensive operations (exploits, attack automation)
- **Scripts/** — Utility scripts (web crawler for grounding AI context)
- **Strategy/** — Deployment playbooks, hardening scripts, monitoring setup
- **Documentation/** — Additional docs and prompts


## Monitoring Architecture

Client VMs run **Suricata** (IDS with EVE JSON output) and **tcpdump** (rotating PCAPs every 60s). A cron job rsyncs logs every minute to the central **Tulip** server over SSH. Tulip provides a web UI for flow analysis, filtering, tagging, and Suricata alert correlation. Configure target VMs in `services/api/configurations.py` within the Tulip clone.