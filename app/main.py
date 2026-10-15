"""Command Line Interface and Interactive REPL for Smart Archive Agent."""

import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from colorama import Fore, Style, init

from app.agent import SmartArchiveAgent
from app.intent import ActionType, ArchiveIntent

# Initialize colorama for Windows/Unix ANSI compatibility
init(autoreset=True)


def banner():
    """Display CLI banner."""
    click.echo(
        Fore.CYAN
        + r"""
   _____                      _              _     _             
  / ____|                    | |   /\       | |   (_)            
 | (___  _ __ ___   __ _ _ __| |_ /  \   _ _| |__  _ _ __  _ __  
  \___ \| '_ ` _ \ / _` | '__| __/ /\ \ | '__| '_ \| | '_ \| '_ \ 
  ____) | | | | | | (_| | |  | |/ ____ \| |  | | | | | |_) | |_) |
 |_____/|_| |_| |_|\__,_|_|   \__/_/    \_\_|  |_| |_|_| .__/| .__/ 
                                                        | |   | |    
                                                        |_|   |_|    
"""
        + Fore.GREEN
        + "       Smart Archive Agent (v0.1.0) | Team 12\n"
        + Style.RESET_ALL
    )


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Smart Archive Agent - Intelligent, secure file archiving & encryption."""
    if ctx.invoked_subcommand is None:
        banner()
        click.echo("Run 'smart-archive --help' or 'smart-archive interactive' for assistance.\n")


@cli.command("agent")
@click.argument("query", required=False)
@click.option("--dry-run", is_flag=True, help="Simulate without executing changes.")
def agent_cmd(query: Optional[str], dry_run: bool):
    """Execute a natural language request via the Smart Archive Agent."""
    agent = SmartArchiveAgent()

    if not query:
        interactive_loop(agent)
        return

    click.echo(Fore.BLUE + f"[*] Processing query: '{query}'")
    result = agent.execute(query, dry_run=dry_run)

    if result.success:
        click.echo(Fore.GREEN + f"[+] {result.message}")
        if result.plan:
            click.echo(Fore.CYAN + "\nExecution Plan:")
            for p in result.plan:
                click.echo(f"  {p['step']}. {p['name']} -> {p['description']}")
        if result.output_files:
            click.echo(Fore.YELLOW + f"\nArtifacts: {', '.join(result.output_files)}")
    else:
        click.echo(Fore.RED + f"[-] {result.message}")
        sys.exit(1)


@cli.command("archive")
@click.argument("sources", nargs=-1, required=True)
@click.option("-o", "--output", required=True, help="Destination archive path.")
@click.option("-f", "--format", "archive_format", type=click.Choice(["zip", "tar", "tar.gz", "tar.bz2", "tar.xz"]), default=None)
@click.option("--encrypt", is_flag=True, help="Encrypt the generated archive.")
@click.option("-p", "--password", help="Password for encryption.")
@click.option("--filter-ext", multiple=True, help="File extension(s) to include, e.g. .py, .txt")
@click.option("--dry-run", is_flag=True, help="Preview operation steps.")
def archive_cmd(sources: List[str], output: str, archive_format: Optional[str], encrypt: bool, password: Optional[str], filter_ext: tuple, dry_run: bool):
    """Create an archive from specified source files or folders."""
    agent = SmartArchiveAgent()
    filters = {}
    if filter_ext:
        filters["include_extensions"] = [e if e.startswith(".") else f".{e}" for e in filter_ext]

    intent = ArchiveIntent(
        action=ActionType.ARCHIVE,
        sources=list(sources),
        destination=output,
        format=archive_format,
        encrypt=encrypt,
        password=password,
        filters=filters,
        dry_run=dry_run,
    )
    result = agent.execute(intent)

    if result.success:
        click.echo(Fore.GREEN + f"[+] {result.message}")
    else:
        click.echo(Fore.RED + f"[-] {result.message}")
        sys.exit(1)


@cli.command("extract")
@click.argument("archive", required=True)
@click.option("-d", "--dest", required=True, help="Destination directory.")
@click.option("--decrypt", is_flag=True, help="Decrypt archive prior to extraction.")
@click.option("-p", "--password", help="Password for decryption.")
@click.option("--dry-run", is_flag=True, help="Preview extraction without modifying disk.")
def extract_cmd(archive: str, dest: str, decrypt: bool, password: Optional[str], dry_run: bool):
    """Safely extract archive contents with Zip Slip and bomb protections."""
    agent = SmartArchiveAgent()
    intent = ArchiveIntent(
        action=ActionType.EXTRACT,
        sources=[archive],
        destination=dest,
        decrypt=decrypt,
        password=password,
        dry_run=dry_run,
    )
    result = agent.execute(intent)

    if result.success:
        click.echo(Fore.GREEN + f"[+] {result.message}")
    else:
        click.echo(Fore.RED + f"[-] {result.message}")
        sys.exit(1)


@cli.command("encrypt")
@click.argument("source", required=True)
@click.option("-o", "--output", help="Encrypted destination file.")
@click.option("-p", "--password", required=True, prompt=True, hide_input=True, help="Password / Key.")
def encrypt_cmd(source: str, output: Optional[str], password: str):
    """Encrypt a file or archive using AES-256-GCM authenticated cipher."""
    agent = SmartArchiveAgent()
    intent = ArchiveIntent(
        action=ActionType.ENCRYPT,
        sources=[source],
        destination=output,
        password=password,
    )
    result = agent.execute(intent)

    if result.success:
        click.echo(Fore.GREEN + f"[+] {result.message}")
    else:
        click.echo(Fore.RED + f"[-] {result.message}")
        sys.exit(1)


@cli.command("decrypt")
@click.argument("source", required=True)
@click.option("-o", "--output", help="Decrypted destination file.")
@click.option("-p", "--password", required=True, prompt=True, hide_input=True, help="Password / Key.")
def decrypt_cmd(source: str, output: Optional[str], password: str):
    """Decrypt an encrypted file or archive."""
    agent = SmartArchiveAgent()
    intent = ArchiveIntent(
        action=ActionType.DECRYPT,
        sources=[source],
        destination=output,
        password=password,
    )
    result = agent.execute(intent)

    if result.success:
        click.echo(Fore.GREEN + f"[+] {result.message}")
    else:
        click.echo(Fore.RED + f"[-] {result.message}")
        sys.exit(1)


@cli.command("list")
@click.argument("archive", required=True)
def list_cmd(archive: str):
    """List members and metadata inside an archive."""
    agent = SmartArchiveAgent()
    intent = ArchiveIntent(action=ActionType.LIST, sources=[archive])
    result = agent.execute(intent)

    if result.success:
        click.echo(Fore.CYAN + f"\nArchive: {archive}")
        click.echo("-" * 70)
        click.echo(f"{'Filename':<40} {'Size':>10} {'Compressed':>12}")
        click.echo("-" * 70)
        for entry in result.metrics.get("entries", []):
            name = entry["filename"]
            if entry["is_dir"]:
                name += "/"
            click.echo(f"{name:<40} {entry['size']:>10} {entry['compressed_size']:>12}")
        click.echo("-" * 70)
        click.echo(Fore.GREEN + f"Total entries: {result.metrics.get('count', 0)}")
    else:
        click.echo(Fore.RED + f"[-] {result.message}")
        sys.exit(1)


@cli.command("verify")
@click.argument("archive", required=True)
def verify_cmd(archive: str):
    """Verify integrity and structure of an archive."""
    agent = SmartArchiveAgent()
    intent = ArchiveIntent(action=ActionType.VERIFY, sources=[archive])
    result = agent.execute(intent)

    if result.success:
        click.echo(Fore.GREEN + f"[PASS] {result.message}")
        click.echo(f"  SHA-256: {result.metrics.get('sha256')}")
    else:
        click.echo(Fore.RED + f"[FAIL] {result.message}")
        sys.exit(1)


@cli.command("interactive")
def interactive_cmd():
    """Start an interactive agent shell session."""
    agent = SmartArchiveAgent()
    interactive_loop(agent)


def interactive_loop(agent: SmartArchiveAgent):
    """Run interactive REPL loop."""
    banner()
    click.echo("Entering interactive session. Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            user_input = input(Fore.YELLOW + "agent> " + Style.RESET_ALL).strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                click.echo(Fore.CYAN + "Goodbye!")
                break

            result = agent.execute(user_input)
            if result.success:
                click.echo(Fore.GREEN + f"[+] {result.message}")
                if result.output_files:
                    click.echo(Fore.CYAN + f"    Artifacts: {', '.join(result.output_files)}")
            else:
                click.echo(Fore.RED + f"[-] {result.message}")
        except (KeyboardInterrupt, EOFError):
            click.echo("\n" + Fore.CYAN + "Session closed.")
            break


def main():
    cli()


if __name__ == "__main__":
    main()
