# Networking

## Local

> Both Podman and Docker are supported. Examples below use `podman`; substitute `docker`
> if that's your runtime.

Containers run on `hydra-net`, a bridge network with DNS enabled. Outbound internet
works via the host's NAT. No egress filtering in local dev (iptables skipped).

```bash
# Create once
podman network create hydra-net
# or: docker network create hydra-net
```

## Kubernetes

Egress is controlled by `manifests/network-policy.yaml` — allows only:
- DNS (UDP/TCP 53)
- HTTPS (443) to `api.anthropic.com`, `github.com`, `api.github.com`

For FQDN-level enforcement (not just IP), use Cilium `CiliumNetworkPolicy` or Calico
`GlobalNetworkPolicy`.
