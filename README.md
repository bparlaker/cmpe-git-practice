# cmpe-git-practice

A practice repository for learning **Git version management**, **GitHub Issues**, **labels**, and **Wiki** documentation.

> 📚 Full notes live in the [Wiki](https://github.com/bparlaker/cmpe-git-practice/wiki). This README is the quick tour.

---

## 👋 About Me

Hi! I'm **Berker Parlaker**.

| | |
|---|---|
| **Program / Year** | SWE / 2 |
| **Interests** | Sports |
| **Currently learning** | Git, GitHub workflows |

This repository is where I practise the Git and GitHub workflow we discussed in class: version control, issues, labels and documentation.

---

## 🗂 Repository Contents

| Item | Where |
|---|---|
| Introduction & Git cheat sheet | this README |
| Detailed Git guides | [Wiki](https://github.com/bparlaker/cmpe-git-practice/wiki) |
| Label system & rationale | [Wiki → Issue Labels](https://github.com/bparlaker/cmpe-git-practice/wiki/Issue-Labels) |
| How to write a good issue | [Wiki → Writing Good Issues](https://github.com/bparlaker/cmpe-git-practice/wiki/Writing-Good-Issues) |
| Work items | [Issues](https://github.com/bparlaker/cmpe-git-practice/issues) |

---

## 🎨 Term Project: Local Art Archive

A website for sharing and discovering **local and traditional art** (kilim, ebru, çini, miniature painting, works of local artists). Every craft entry is saved as **structured data**: the craft type decides the fields (sizes with units, colors, patterns, materials, a map pin). The only free text is the personal story.

**Status:** the MVP is done. Users can sign up, add a kilim (or ebru, çini, miniature) with units, colors, patterns and a map pin, define new craft types, use tag suggestions, browse, search and filter, report wrong data to the admin, see all entries on a map and export them as JSON. Next: the site on Render and the final release (comments, user manual, demo).

- **What and why:** [Project Overview](https://github.com/bparlaker/cmpe-git-practice/wiki/Project-Overview)
- **What it must do:** [Requirements](https://github.com/bparlaker/cmpe-git-practice/wiki/Requirements), with requirement validation
- **Data model:** [Domain Model](https://github.com/bparlaker/cmpe-git-practice/wiki/Domain-Model), with the Kilim example
- **How people use it:** [Use Cases](https://github.com/bparlaker/cmpe-git-practice/wiki/Use-Cases), with diagrams and user stories
- **Screens:** [Mockups](https://github.com/bparlaker/cmpe-git-practice/wiki/Mockups)
- **Tools, time, milestones, risks:** [Resources and Plan](https://github.com/bparlaker/cmpe-git-practice/wiki/Resources-and-Plan)
- **Work items:** [Milestones](https://github.com/bparlaker/cmpe-git-practice/milestones) and [Issues](https://github.com/bparlaker/cmpe-git-practice/issues)

**Stack:** Python, Django, PostgreSQL (SQLite on my laptop), Bootstrap, Leaflet/OpenStreetMap, Docker, Render

### Run the project

With Python 3.12 on your computer:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py load_initial_data   # categories, colors, tags and 4 craft types (Kilim, Ebru, Çini, Miniature)
python manage.py createsuperuser     # an admin account, needed for the report queue
python manage.py runserver
```

Then open http://127.0.0.1:8000

With Docker (app + PostgreSQL):

```bash
docker compose up --build
```

Run the tests:

```bash
python manage.py test
```

### Where the code is

- `localart/`: project settings and main URLs
- `archive/`: my app (models, forms, views, tests, the `load_initial_data` command)
- `templates/` and `static/`: the pages, CSS and JavaScript (map, tag suggestions)
- `render.yaml` and `build.sh`: deploy on Render

---

## 🌱 Why Git?

Git is a **distributed version control system**. Every clone is a full copy of the project history, so you can:

- see **who** changed **what**, **when**, and **why** (`git log`, `git blame`)
- experiment safely on **branches** and throw them away
- go back to any earlier state of the project
- collaborate without overwriting each other's work

### The three areas

```
 Working Directory  --git add-->  Staging Area (Index)  --git commit-->  Repository (.git)
        ^                                                                     |
        +------------------------- git restore / git checkout ----------------+
```

---

## ⚡ Git Cheat Sheet (with examples)

### 1. Setup (once per machine)

```bash
git config --global user.name  "Berker Parlaker"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.editor "code --wait"   # VS Code as editor
```

### 2. Start or copy a project

```bash
git init                                  # new repo in current folder
git clone https://github.com/bparlaker/cmpe-git-practice.git
```

### 3. The daily loop

```bash
git status                 # what changed?
git diff                   # line-by-line changes (unstaged)
git add README.md          # stage one file
git add -p                 # stage interactively, hunk by hunk
git commit -m "docs: add Git cheat sheet to README (#3)"
git push                   # send commits to GitHub
git pull --rebase          # get others' work, keep history linear
```

### 4. Branching & merging

```bash
git switch -c feature/wiki-branching     # create + switch to a branch
# ...edit, add, commit...
git push -u origin feature/wiki-branching
git switch main
git merge --no-ff feature/wiki-branching  # keep a merge commit
git branch -d feature/wiki-branching      # delete merged branch
```

### 5. Looking at history

```bash
git log --oneline --graph --decorate --all
git log -p -- README.md          # full history of one file
git blame README.md              # who last touched each line
git show HEAD~2                  # inspect a specific commit
```

Example output of `git log --oneline --graph`:

```
*   7c1e2a9 (HEAD -> main) Merge branch 'feature/labels'
|\
| * 3b9f0d1 docs: explain label colour scheme
| * a41c7e2 docs: add Issue-Labels wiki page
|/
* 1e0d5c3 docs: initial README
```

### 6. Undoing things (safely)

| Situation | Command |
|---|---|
| Discard unstaged edits to a file | `git restore file.txt` |
| Unstage a file (keep edits) | `git restore --staged file.txt` |
| Fix the last commit message / add a forgotten file | `git commit --amend` |
| Undo a pushed commit **without rewriting history** | `git revert <sha>` |
| Move branch back, keep changes staged | `git reset --soft HEAD~1` |
| Find a "lost" commit | `git reflog` |

> ⚠️ Never `reset --hard` or force-push a branch other people are using. Prefer `git revert` on shared branches.

### 7. Stash - park work in progress

```bash
git stash push -m "half-done README table"
git switch main          # do something else
git switch -
git stash pop
```

### 8. Tags & releases

```bash
git tag -a v1.0 -m "Assignment 1 submission"
git push origin v1.0
```

### 9. Linking commits to issues

Writing `Closes #4` (or `Fixes #4`, `Resolves #4`) in a commit message or pull request description closes issue #4 automatically when merged into `main`.

```bash
git commit -m "docs: add undoing-changes wiki page

Closes #4"
```

---

## ✍️ Commit Message Convention

This repo follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(optional scope): <short summary in imperative mood>

<optional body: what and why, wrapped at 72 chars>

<optional footer: Closes #12>
```

Types used: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.

---

## 🏷 Labels at a Glance

Labels are grouped by prefix and colour family - see the [Issue Labels](https://github.com/bparlaker/cmpe-git-practice/wiki/Issue-Labels) wiki page for the full reasoning.

| Group | Question it answers | Examples |
|---|---|---|
| `Type:` | What kind of work is it? | Bug, Feature, Documentation, Research |
| `Priority:` | How urgent? | Critical, High, Medium, Low |
| `Status:` | Where is it in the workflow? | Needs Triage, In Progress, Blocked |
| `Effort:` | How big? | Small, Medium, Large |
| `Area:` | Which part of the project? | README, Wiki, Repo Setup |

---

## 📎 References

- *Pro Git* book (free): https://git-scm.com/book
- Git reference docs: https://git-scm.com/docs
- GitHub Docs - Managing labels: https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels
- Conventional Commits: https://www.conventionalcommits.org/
