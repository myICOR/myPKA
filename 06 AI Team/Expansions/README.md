# Expansions

Optional packs extend your AI Team with agents, procedures, templates or
content conversions. They sit on top of myPKA; they do not replace its
shared entry contract, core team or knowledge architecture.

Download packs from Tool Lab on myICOR (https://app.myicor.com/tool-lab)
with a monthly, Inner Circle or lifetime membership. Extract a pack into
its own folder here, then tell your AI:

> I added an expansion to `06 AI Team/Expansions`. Inspect it, explain
> what it adds and install it through the expansion workflow.

Your AI also checks this folder at session start. Finding a pack starts
an inspection, not silent execution. Installation is guided by your LLM,
not by an Obsidian plugin or a background service.

The pack format, boundaries and lifecycle are defined once in
[[GL-1012-ai-team-expansions]]. The installation procedure is
[[WS-1006-install-an-ai-team-expansion]].

Keep each downloaded pack folder here after installation. What a pack
owns is recorded OUTSIDE the pack, written by the install tool and read
by nothing else: `.icor-for-life/expansions/<pack-id>.json` when myPKA
shares one folder with ICOR for Life (mode A), `.mypka/expansions/<pack-id>.json`
when myPKA has its own folder (mode B). A receipt shipped inside a pack
folder is ignored, and a pack that carries one is refused at install
until you have looked at it.

A pack folder is not a credential store. Never put API keys in a pack.

Packs install readable text: agent contracts, procedures, templates.
They cannot install anything under `06 AI Team/AI Team Knowledge/Scripts/`
and cannot install a compiled or loadable file type. The installer runs
nothing from a pack, and that is a statement about the installer, not a
promise that a copied file is inert.

Something that runs (a dashboard, a chatbot, a server) is not a pack and
never installs from this folder. Tool Lab lists it as its own download:
it gets a security review, and you start it yourself.
