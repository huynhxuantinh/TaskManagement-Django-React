from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().casefold()
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{self.get_ident(request)}:{email}",
        }


class RegisterRateThrottle(AnonRateThrottle):
    scope = "register"


class RefreshRateThrottle(AnonRateThrottle):
    scope = "refresh"
