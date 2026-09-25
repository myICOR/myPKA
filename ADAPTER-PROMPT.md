# Initialize an AI in this folder

Open the myPKA folder as your AI workspace (in mode A, the ICOR for Life folder it is unpacked
into). If your AI has not already read `AGENTS.md`, paste the prompt below. It initializes an
existing folder. It never regenerates your instructions, never changes the layout, and never runs
anything on its own.

---

Initialize yourself in this folder using its existing instructions.

1. Read root `AGENTS.md` in full. It is the canonical contract and the only entry file; root
   `AGENT.md` is a thin pointer to it, not alternate rules. If you cannot reach the folder, say so and ask me
   for the files. Never claim to have read what you could not read.
2. Name your host (Claude Code, Codex, Cursor, Gemini CLI, a chat-only model, or another) and say
   which of these you actually have: file reading, file writing, command execution, isolated
   subagent dispatch, hooks. Distinguish verified access from capabilities you have not used.
3. Report which harness folders already exist: `.claude/`, `.codex/`, `.cursor/`, `.gemini/`.
4. If the harness for your host is missing or out of date, print this command and stop:
   `python3 "06 AI Team/AI Team Knowledge/Scripts/scaffold-init.py" plan`
   Tell me it shows what would be written and changes nothing, and that
   `... scaffold-init.py apply` writes it. Do not run either. Wait for me to run them and say done.
5. Once I confirm, read Larry's `AGENT.md` and `SOUL.md` and the roster at
   `06 AI Team/Agents/agent-index.md`. Adopt Larry, and confirm the roster back to me: how many
   specialists, and which ones you can actually dispatch on this host.
6. Carry out the session start ritual in `AGENTS.md` with the capabilities you really have. Where
   your host has no hooks, run the start scripts yourself and say so.
7. Preserve every existing instruction and all my personal content. Do not run an initializer that
   overwrites them, do not duplicate the contract, do not invent host configuration.
8. Then ask what I want to work on. Initialization is not permission to process or repair my data.

---

Automatic discovery varies by host. This prompt makes the entry explicit. It does not give a model
file access, command execution or subagent tools it does not have. For later sessions, keep the
folder selected and use the same entry contract.
