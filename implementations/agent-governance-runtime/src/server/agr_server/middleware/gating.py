"""Infrastructure-level gating middleware for AGR.

Provides hard enforcement at the API/network layer:

1. **Token-scoped rate limiting** — per-agent request limits enforced at HTTP level
2. **IP allow-listing** — restrict which networks can reach the AGR server
3. **Mutual TLS readiness** — header-based client cert identity extraction
4. **API gateway integration** — headers for Azure API Management, AWS API Gateway

These controls complement the governance evaluation logic with infrastructure-
level enforcement that cannot be bypassed by a misbehaving agent.

Enable via environment variables:
    AGR_ENFORCE_RATE_LIMIT=true     — Hard rate limiting per agent token
    AGR_ALLOWED_NETWORKS=10.0.0.0/8,172.16.0.0/12  — IP allow-list
    AGR_REQUIRE_GATEWAY=true        — Require X-Gateway-Token header
    AGR_GATEWAY_SECRET=<secret>     — Shared secret for gateway auth
"""

from __future__ import annotations

import ipaddress
import os
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-token sliding-window rate limiter.

    Enforces request limits at the HTTP layer BEFORE reaching governance
    evaluation. This means a rogue agent cannot even reach /governance/evaluate
    if its token has exceeded the rate limit.

    Config:
        AGR_ENFORCE_RATE_LIMIT=true
        AGR_RATE_LIMIT_DEFAULT=100        — Requests per window (default)
        AGR_RATE_LIMIT_WINDOW_SECONDS=3600 — Window size in seconds
    """

    def __init__(self, app, *, default_limit: int = 100, window_seconds: int = 3600):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        # token → list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)

        token = auth[7:]
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune old entries
        timestamps = self._requests[token]
        self._requests[token] = [t for t in timestamps if t > cutoff]

        if len(self._requests[token]) >= self.default_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": self.default_limit,
                    "window_seconds": self.window_seconds,
                    "retry_after_seconds": int(self._requests[token][0] - cutoff),
                },
                headers={"Retry-After": str(int(self._requests[token][0] - cutoff))},
            )

        self._requests[token].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(
            self.default_limit - len(self._requests[token])
        )
        return response


class NetworkGatingMiddleware(BaseHTTPMiddleware):
    """IP-based network gating.

    Only allows requests from specified CIDR ranges. Useful for restricting
    AGR access to internal networks, VPNs, or specific cloud VNETs.

    Config:
        AGR_ALLOWED_NETWORKS=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
    """

    def __init__(self, app, *, allowed_networks: list[str]):
        super().__init__(app)
        self.networks = [ipaddress.ip_network(n, strict=False) for n in allowed_networks]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "0.0.0.0"

        # Check X-Forwarded-For for proxied requests
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        try:
            addr = ipaddress.ip_address(client_ip)
        except ValueError:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Invalid client IP: {client_ip}"},
            )

        if not any(addr in network for network in self.networks):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied: client IP not in allowed networks",
                    "client_ip": str(addr),
                },
            )

        return await call_next(request)


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    """API Gateway authentication middleware.

    Ensures requests pass through an authorized API gateway (Azure API Management,
    AWS API Gateway, etc.) by validating a shared secret header.

    The gateway adds X-Gateway-Token on every forwarded request.
    This middleware rejects direct calls that bypass the gateway.

    Config:
        AGR_REQUIRE_GATEWAY=true
        AGR_GATEWAY_SECRET=<shared-secret>

    For Azure API Management, configure an outbound policy:
        <set-header name="X-Gateway-Token" exists-action="override">
            <value>{{gateway-secret}}</value>
        </set-header>
    """

    def __init__(self, app, *, gateway_secret: str):
        super().__init__(app)
        self.gateway_secret = gateway_secret

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Allow health check without gateway
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        gateway_token = request.headers.get("x-gateway-token", "")
        if gateway_token != self.gateway_secret:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied: requests must pass through the API gateway",
                    "hint": "Direct access to the AGR server is not allowed",
                },
            )

        return await call_next(request)


class MutualTLSMiddleware(BaseHTTPMiddleware):
    """Extract client certificate identity from reverse proxy headers.

    When running behind a TLS-terminating proxy (Azure App Gateway, nginx, etc.),
    the client certificate CN is forwarded via X-Client-Cert-CN header.

    This middleware adds the cert identity to the request state for downstream
    handlers to use as an additional trust signal.

    Config:
        AGR_REQUIRE_MTLS=true
    """

    def __init__(self, app, *, required: bool = False):
        super().__init__(app)
        self.required = required

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cert_cn = request.headers.get("x-client-cert-cn", "")
        cert_thumbprint = request.headers.get("x-client-cert-thumbprint", "")

        if self.required and not cert_cn:
            # Allow health check
            if request.url.path not in ("/health", "/docs", "/redoc", "/openapi.json"):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Client certificate required (mTLS)"},
                )

        # Attach to request state for downstream use
        request.state.client_cert_cn = cert_cn
        request.state.client_cert_thumbprint = cert_thumbprint

        return await call_next(request)


def configure_gating(app) -> None:
    """Configure infrastructure gating middleware based on environment variables.

    Call this from the FastAPI app setup to enable gating.
    Middleware is added in reverse order (last added = first executed).
    """
    # mTLS
    require_mtls = os.environ.get("AGR_REQUIRE_MTLS", "").lower() == "true"
    if require_mtls:
        app.add_middleware(MutualTLSMiddleware, required=True)

    # Gateway auth
    gateway_secret = os.environ.get("AGR_GATEWAY_SECRET", "")
    require_gateway = os.environ.get("AGR_REQUIRE_GATEWAY", "").lower() == "true"
    if require_gateway and gateway_secret:
        app.add_middleware(GatewayAuthMiddleware, gateway_secret=gateway_secret)

    # Network gating
    allowed_networks = os.environ.get("AGR_ALLOWED_NETWORKS", "")
    if allowed_networks:
        networks = [n.strip() for n in allowed_networks.split(",") if n.strip()]
        if networks:
            app.add_middleware(NetworkGatingMiddleware, allowed_networks=networks)

    # Rate limiting
    enforce_rate_limit = os.environ.get("AGR_ENFORCE_RATE_LIMIT", "").lower() == "true"
    if enforce_rate_limit:
        default_limit = int(os.environ.get("AGR_RATE_LIMIT_DEFAULT", "100"))
        window_seconds = int(os.environ.get("AGR_RATE_LIMIT_WINDOW_SECONDS", "3600"))
        app.add_middleware(
            RateLimitMiddleware,
            default_limit=default_limit,
            window_seconds=window_seconds,
        )
