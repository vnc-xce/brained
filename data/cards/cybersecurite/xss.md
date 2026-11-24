---
id: xss
subject: cybersecurite
title: XSS (Cross-Site Scripting)
tags: [web, owasp]
created: 2026-11-24
---

## Question
Qu'est-ce qu'une faille XSS et comment s'en protéger ?

## Réponse
Injection de JavaScript dans une page vue par d'autres utilisateurs.
Protection : échapper les sorties selon le contexte (HTML, attribut, JS),
Content-Security-Policy, cookies HttpOnly.
