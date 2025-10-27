# Lamavoices
to create a consensus operated robot

# What
I have a VIAM Rover robot https://www.viam.com/resources/rover, and at Solace we have the entanglement demo https://sg.solace.rocks/qr/. How can these be combined to create a consensus based operated robot. It might literally not go anywhere at all if all people push for different directions. Similar to https://www.viam.com/resources/try-viam where one person can control a VIAM Rover robot in a lab but then real-time con trolled by multiple people using Solace event broker, maybe even add Solace Agent Mesh to the mix. This repo provides e a comprehensive plan layout and code framework to get it all working using Python as main programming language on macOS system, where necessary supported by tooling like brew installs, terminal shell scripts etc.

# How
A full end-to-end plan + a ready-to-wire code framework: “Consensus Rover with Solace — Plan & Code Framework (Python/macOS)” covering:

Architecture (operators → Solace → Agent Mesh → VIAM Rover)

Topics & JSON schemas

Consensus strategies (vector averaging, majority, deadlock/tie-break)

Security (TLS/mTLS, rate limiting)

macOS install steps (brew + Python deps)

Runnable Python modules:

MQTT bus to Solace

Consensus agent

Safety gate

VIAM rover runner (using viam-sdk)

QR/entanglement bridge webhook

CLI spammer for testing

Shell scripts to run the consensus and rover processes

Demo flow + troubleshooting

A tiny FastAPI web UI to visualize live intents/consensus

And a MongoDB recorder for replay.

# Notes
The Web UI avoids external JS libs for a zero‑build demo.

Behind HTTPS, enable CORS in FastAPI if your QR page is on another origin.

For demo: mirror the Web UI; let the audience scan the QR and watch the consensus evolve.
