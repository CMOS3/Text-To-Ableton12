# **The Professional Git Loop**

As part of our Version Control and DevOps strategy, adhering to a strict, industry-standard Git workflow is essential. This protocol ensures a stable architecture, logical feature isolation, and a clean version history.

### **1\. Sync (Pull)**

Before branching, you must ensure your local environment reflects the latest remote state.

git checkout main

*What it means:* This switches your active working environment (the files you currently see on your machine) to the main branch, ensuring you are on the core baseline before making new changes.

git pull

*What it means:* This command connects to the remote repository, downloads any new updates, and automatically merges them into your local main branch so your codebase is fully up to date.

### **2\. Branch**

Never work directly on the main branch. Isolate the new logic.

git checkout \-b feat/your-new-feature

*What it means:* The \-b flag creates a brand new branch named feat/your-new-feature. The checkout portion immediately moves your working environment onto this new branch so you can build safely in isolation without affecting main.

### **3\. Code & Test**

This is our Vibe Coding phase. We build, test, and verify the changes locally.

### **4\. Stage (Add)**

You must explicitly tell Git which modified files to include in the next snapshot. This allows for atomic commits.

git add .

*What it means:* The . represents the current directory. This stages *all* modified, new, and deleted files, preparing them to be included in the next commit snapshot.

(or adding specific files like:)

git add src/main.py

*What it means:* This is a targeted approach. It tells Git to stage *only* the changes within src/main.py. Any other modified files are left unstaged. This is crucial for keeping your commits atomic and focused.

### **5\. Commit**

Lock the staged changes into the repository history using a Conventional Commit prefix.

git commit \-m "feat: implement user authentication block"

*What it means:* This takes the files you staged with git add and permanently records them as a snapshot in your local repository's history. The \-m flag allows you to attach an inline, human-readable message explaining the specific change.

### **6\. Push**

Upload your local branch to the remote repository.

git push \-u origin feat/your-new-feature

*What it means:* This uploads your newly created local branch and its commits to the remote server (origin). The \-u (upstream) flag establishes a tracking connection, meaning for future updates on this branch, you can simply type git push instead of writing out the full command.

### **7\. Review / Pull Request**

Even as a solo developer, treating the merge as a Pull Request provides a final verification phase to review the diffs before they integrate into the core system.

git diff main

*What it means:* This command displays the line-by-line differences between your current feature branch and the main branch, allowing you to safely review your exact code changes locally before initiating a merge.

### **8\. Merge**

Integrate the verified branch back into main.

git checkout main

*What it means:* Switches your working environment back to the core main branch to prepare for integration.

git merge feat/your-new-feature

*What it means:* This takes all the commits from your isolated feature branch and integrates them directly into the main branch.

git push

*What it means:* Uploads the newly merged main branch back to the remote repository, establishing the new shared baseline for the project.

### **Best Practices for Branch Naming Conventions**

Consistent branch naming makes your repository history readable and helps identify the purpose of a branch at a glance. We follow a prefix-based convention heavily inspired by Conventional Commits.

**General Rules:**

* **Format:** \<type\>/\<short-description\>  
* **Kebab-case:** Use lowercase letters and hyphens to separate words. Avoid spaces, underscores, or uppercase letters (e.g., use user-login instead of user\_login or UserLogin).  
* **Keep it concise:** The description should be short but descriptive enough to understand the branch's context.

**Standard Prefixes:**

* feat/: Used when adding a new feature or significant functionality. (e.g., feat/shopping-cart, feat/oauth-login)  
* fix/: Used when patching a bug or resolving an issue. (e.g., fix/header-alignment, fix/memory-leak)  
* chore/: Used for routine tasks, maintenance, dependency updates, or configuration changes that do not affect production code directly. (e.g., chore/update-dependencies, chore/setup-linter)  
* refactor/: Used for code changes that neither fix a bug nor add a feature, but improve code structure or performance. (e.g., refactor/auth-middleware)  
* docs/: Used for additions or changes exclusively related to documentation. (e.g., docs/api-endpoints, docs/readme-setup)

### **Other Commonly Used Commands**

While the loop above covers the daily feature workflow, you will frequently need these additional commands to inspect and manage your repository effectively.

git status

*What it means:* Displays the state of the working directory and the staging area. It lets you quickly see which changes have been staged, which haven't, and which files aren't being tracked by Git at all. Always run this if you aren't sure what state your files are in.

git log

*What it means:* Shows the chronological commit history for the current branch. It allows you to see who made changes, what the commit messages were, when they were made, and the unique commit hashes.

git stash

*What it means:* Temporarily shelves (or "stashes") uncommitted changes you've made to your working copy. This is incredibly useful if you need to switch branches quickly to look at something else, but aren't ready to commit your current work. You can restore the stashed work later using git stash pop.

git revert \<commit-hash\>

*What it means:* Safely undoes changes by creating a *new* commit that is the exact opposite of the target commit. This is the safest and recommended way to undo changes that have already been pushed to a shared remote repository, as it doesn't rewrite history.

git reset \--hard HEAD

*What it means:* **Use with caution\!** This completely throws away all uncommitted changes in your working directory and staging area, forcefully returning your files to exactly how they were at the last commit.