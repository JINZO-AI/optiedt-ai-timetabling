"""The provider-agnostic client, and the one that does nothing.

⚠️ **`DisabledAdapter` is the default**, because `assistant_enabled` is False
out of the box. Everything else in the application works with it, which is
invariant 5 exercised by the ordinary configuration rather than by a special
test.

**No vendor SDK.** The specification requires the service be reachable through
a single interface that can be disabled without affecting any other function,
so this speaks HTTP and JSON in the shape every hosted chat completion API
uses. Swapping providers is a `assistant_base_url` and a `assistant_model`.

⚠️ **No test calls a live provider — C-21, decided 2026-08-06 before this file
existed.** A model's output is not fixed by a seed, so such a test would report
the machine and the day rather than the software; it would need a secret, which
`assistant_api_key` must never become; and it would fail with no network. The
adapter is exercised through a fake. **Read a green suite as "the application
behaves correctly around a provider", never as "the assistant was tested
against a language model."** A first live call is a deployment step and belongs
in `docs/demonstration.md`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from optiedt.assistant.interfaces import (
    AssistantUnavailableError,
    ContextPayload,
)


@dataclass(frozen=True, slots=True)
class DisabledAdapter:
    """Implements `AssistantAdapter` by refusing, always.

    Not a null object that returns "": a caller must be able to tell "no model
    spoke" from "the model said nothing", and an empty string collapses the
    two. Raising is what routes the caller to the computed form.
    """

    @property
    def enabled(self) -> bool:
        return False

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        del context, prompt, timeout_seconds
        raise AssistantUnavailableError(
            "the language service is switched off in configuration "
            "(OPTIEDT_ASSISTANT_ENABLED). Every other function is unaffected."
        )


@dataclass(frozen=True, slots=True)
class HttpAssistantAdapter:
    """One hosted chat-completion API, over plain HTTP.

    ⚠️ **Every failure becomes `AssistantUnavailableError`** - a timeout, a
    refusal, a malformed body, an HTTP error, a network error. The caller has
    exactly one thing to do about any of them, which is show the computed form,
    so distinguishing them at this boundary would only invite a caller to
    handle some and not others.
    """

    base_url: str
    api_key: str
    model: str

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def complete(self, context: ContextPayload, prompt: str, timeout_seconds: float) -> str:
        if not self.enabled:
            raise AssistantUnavailableError(
                "the language service is enabled but not configured: "
                "OPTIEDT_ASSISTANT_BASE_URL, _API_KEY and _MODEL are all required."
            )

        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _user_message(context, prompt)},
                ],
            }
        ).encode()

        request = urllib.request.Request(
            url=self.base_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read())
            return str(payload["choices"][0]["message"]["content"])
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise AssistantUnavailableError(f"the language service is unreachable: {exc}") from exc
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise AssistantUnavailableError(
                f"the language service returned an unusable body: {exc}"
            ) from exc


_USER_AGENT = "OptiEDT/0.1.0"
"""How this client identifies itself. **Do not remove it as a redundant header.**

`urllib` sends `Python-urllib/<version>` when no `User-Agent` is given, and
hosted providers behind a CDN reject that value outright: Groq answers
**HTTP 403 with Cloudflare `error code: 1010`** - a client-signature refusal
that never reaches the API, so no key, model or body is at fault and the error
says nothing about any of them. Measured 2026-08-07 on
`api.groq.com/openai/v1/chat/completions`: absent and explicit
`Python-urllib/3.14` are both refused, while `OptiEDT/0.1.0`, `curl/8.0` and a
browser string are all accepted.

⚠️ **An honest name is enough, and that is why one is used.** The block is on
the `Python-urllib` value, not on non-browser clients, so nothing here pretends
to be a browser - identifying the caller truthfully is what RFC 9110 asks for
and it is the only reason this constant exists. Without it this module's own
promise above - that swapping providers is a `assistant_base_url` and a
`assistant_model` - is false for any CDN-fronted provider.
"""

_SYSTEM_PROMPT = """\
Tu expliques des emplois du temps universitaires déjà calculés.

RÈGLES ABSOLUES :
- N'utilise QUE les chiffres présents dans le contexte fourni. N'en calcule
  aucun, n'en invente aucun, n'en arrondis aucun autrement qu'il n'apparaît.
- Tu ne places aucune séance, tu ne calcules aucun score, tu ne décides aucun
  classement. Ces trois choses sont déjà faites et ne t'appartiennent pas.
- Si le contexte ne permet pas de répondre, dis-le explicitement et ne propose
  aucun chiffre.
- Réponds en français, brièvement.

Toute réponse contenant un chiffre absent du contexte est rejetée et remplacée
par la forme calculée.\
"""


def _user_message(context: ContextPayload, prompt: str) -> str:
    """The context as JSON, then the request.

    Sorted, so two identical requests produce an identical message. It does not
    make the model deterministic - nothing does, which is C-21's whole reason -
    but it removes one source of variation that was ours to remove.
    """
    return json.dumps(
        {
            "kind": context.kind.value,
            "figures": dict(sorted(context.figures.items())),
            "identifiers": list(context.identifiers),
            "labels": dict(sorted(context.labels.items())),
            "request": prompt,
        },
        ensure_ascii=False,
        indent=1,
    )
