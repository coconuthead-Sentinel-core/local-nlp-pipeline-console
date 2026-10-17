r"""Verify the sources of truth agree -- run it, do not trust a claim.

    py -3 tools\verify_sources.py

SCOPE.md section 3 lists as an acceptance criterion: "the worktree, the
live install, and GitHub agree at the same commit." That line was a
promise kept by hand, which is the same shape as the defect FB-013
recorded -- an acceptance claim with nothing that could fail. This runs
the checks instead.

Every stage prints its own verdict, because a copy that disagrees should
say WHICH copy and HOW, not just fail. Deliberately stores no manifest:
a checked-in list of hashes goes stale the moment anything is committed
and then reads as authority while being wrong. Git already holds the
hashes; this asks git.

Exit code 0 only when every stage passes.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args, cwd=ROOT):
    """Run a git command and return (ok, output)."""
    try:
        out = subprocess.run(("git",) + args, cwd=cwd, capture_output=True,
                             text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"git could not run: {exc}"
    return out.returncode == 0, (out.stdout + out.stderr).strip()


def stage(name, ok, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if detail:
        for line in str(detail).splitlines()[:6]:
            print(f"         {line}")
    return ok


def check_working_tree():
    """Does the live install match the commit it claims to be on?"""
    ok, out = git("status", "--porcelain")
    if not ok:
        return stage("live install is a git repository", False, out)
    if out:
        n = len(out.splitlines())
        return stage("live install matches its own commit", False,
                     f"{n} file(s) differ from HEAD:\n" + out)
    return stage("live install matches its own commit", True, "")


def check_remote():
    """Is the local commit the one GitHub has?"""
    fetched, out = git("fetch", "origin", "--quiet")
    if not fetched:
        return stage("GitHub reachable", False, out)
    ok_a, local = git("rev-parse", "HEAD")
    ok_b, remote = git("rev-parse", "origin/main")
    if not (ok_a and ok_b):
        return stage("commits readable", False, local + remote)
    if local != remote:
        ahead, a_out = git("rev-list", "--count", "origin/main..HEAD")
        behind, b_out = git("rev-list", "--count", "HEAD..origin/main")
        return stage("live install agrees with GitHub", False,
                     f"local  {local[:7]}\norigin {remote[:7]}\n"
                     f"{a_out} commit(s) unpushed, {b_out} unpulled")
    return stage("live install agrees with GitHub", True,
                 f"both at {local[:7]}")


def check_worktrees():
    """Every git worktree on this machine, and whether it agrees."""
    ok, out = git("worktree", "list")
    if not ok:
        return stage("worktrees readable", False, out)
    ok_head, head = git("rev-parse", "HEAD")
    agreed = True
    lines = [ln for ln in out.splitlines() if ln.strip()]
    for line in lines:
        path = line.split()[0]
        if os.path.abspath(path) == os.path.abspath(ROOT):
            continue
        ok_w, sha = git("rev-parse", "HEAD", cwd=path)
        label = os.path.basename(path.rstrip("\\/")) or path
        if not ok_w:
            agreed = stage(f"worktree {label} readable", False, sha) and agreed
            continue
        if sha != head:
            agreed = stage(f"worktree {label} agrees", False,
                           f"{sha[:7]} vs {head[:7]}") and agreed
        else:
            stage(f"worktree {label} agrees", True, f"at {sha[:7]}")
    if len(lines) <= 1:
        print("         (no secondary worktrees on this machine)")
    return agreed


def check_object_store():
    """Is the repository itself intact? A synced .git can be corrupted."""
    ok, out = git("fsck", "--no-progress", "--no-dangling")
    if not ok:
        return stage("object store intact", False, out)
    bad = [ln for ln in out.splitlines()
           if ln.strip() and not ln.lower().startswith(("checking", "verifying"))]
    if bad:
        return stage("object store intact", False, "\n".join(bad))
    return stage("object store intact", True, "")


def check_onedrive():
    """Is the live install inside OneDrive, with real local bytes?

    A cloud-only placeholder is not a backup of anything -- it is a
    pointer. Equally, a local file OneDrive has not uploaded yet is not
    yet a second copy. This verifies what it can see and says plainly
    what it cannot: upload state is not exposed to a script, so the
    OneDrive activity centre remains the only honest check for "the
    cloud has today's bytes."
    """
    root = os.environ.get("OneDrive") or ""
    if not root or not ROOT.lower().startswith(root.lower()):
        return stage("live install is inside OneDrive", False,
                     f"OneDrive root: {root or '(not set)'}")
    stage("live install is inside OneDrive", True, root)

    ok, out = git("ls-files")
    if not ok:
        return stage("tracked files readable", False, out)
    placeholders = []
    for rel in out.splitlines():
        full = os.path.join(ROOT, rel)
        try:
            attrs = os.stat(full).st_file_attributes
        except (OSError, AttributeError):
            continue
        # FILE_ATTRIBUTE_OFFLINE / RECALL_ON_DATA_ACCESS: content is not
        # on this disk, so this copy is a pointer, not a copy.
        if attrs & 0x1000 or attrs & 0x400000:
            placeholders.append(rel)
    if placeholders:
        return stage("every tracked file has local bytes", False,
                     f"{len(placeholders)} cloud-only:\n"
                     + "\n".join(placeholders[:5]))
    return stage("every tracked file has local bytes", True,
                 f"{len(out.splitlines())} files")


def main():
    print(__doc__.strip().splitlines()[0])
    print()
    results = [
        check_working_tree(),
        check_remote(),
        check_worktrees(),
        check_object_store(),
        check_onedrive(),
    ]
    print()
    if all(results):
        print("ALL SOURCES AGREE.")
        print("Not checked, because no script can: whether OneDrive has")
        print("finished UPLOADING today's bytes. The activity centre in the")
        print("system tray is the only honest answer to that one.")
        return 0
    print("A SOURCE DISAGREES -- see the FAIL line(s) above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
