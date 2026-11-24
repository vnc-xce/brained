---
id: xss
subject: cybersecurity
title: XSS (Cross-Site Scripting)
tags: [web, owasp]
created: 2026-11-24
---

## Question
What is an XSS vulnerability and how do you protect against it?

## Answer
Injecting JavaScript into a page viewed by other users.
Protection: escape output for its context (HTML, attribute, JS),
Content-Security-Policy, HttpOnly cookies.
