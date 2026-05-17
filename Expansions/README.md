# Expansions

This folder holds optional add-ons for your myPKA scaffold.

Each Expansion is a folder. Drop it in. Larry walks you through the install on the next session — confirms the manifest, runs the security review, merges the new agents and SOPs into your team, wires any connectors, and validates the result. Uninstall whenever — Larry runs the symmetric flow and your myPKA returns to its prior shape.

Some Expansions ship from the myICOR AI Library. Some are written by other people. Treat third-party Expansions the way you'd treat any code you didn't write: skim the folder before you trust it. Larry will ask you once per Expansion and remember the answer.

Nothing here is required. The scaffold runs without it. Expansions are how the team grows beyond the nine pre-hired specialists — new agents, new connectors, new runtimes — never capability the scaffold lacks.

A list of installed Expansions lives in `INDEX.md`, regenerated each session. The full install procedure lives in [[WS-003-install-an-expansion]].

---

## Legal

**Expansions are third-party code.** When you drop an Expansion folder into your `Expansions/` directory, you are choosing to run software written by its author on your machine, with access to your myPKA. Paperless Movement S.L. does not vet, audit, sandbox, or guarantee third-party Expansions, and is not the data controller (GDPR Art. 4(7)) for any processing an Expansion performs.

**Trust is yours to grant.** Read the Expansion's `LICENSE`, `README.md`, and `expansion.yaml` `env_vars:` and `mcp_servers:` declarations before installing. If an Expansion transmits data outside your machine, the Expansion's author is solely responsible for lawfully handling that data under GDPR, CCPA, or any other applicable law.

**Official myICOR-issued Expansions** are published by Paperless Movement S.L. through the myICOR AI Library and are governed by the myICOR AI Library Software License. These are the only Expansions for which Paperless Movement S.L. accepts authorial responsibility. They pass Vex's security review and are hash-pinned in the canonical `.trusted-sources` registry — maintained in the private `mypka-expansions` repository and generated automatically by the Expansion release pipeline. (myPKA itself no longer ships a `.trusted-sources` copy.)
