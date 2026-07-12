from __future__ import annotations

from sweagent.patch_utils import paths_from_patch, sanitize_model_patch


def test_paths_from_patch_reads_unified_diff_paths():
    patch = """diff --git a/packages/foo/Foo.js b/packages/foo/Foo.js
index 1111111..2222222 100644
--- a/packages/foo/Foo.js
+++ b/packages/foo/Foo.js
@@ -1 +1 @@
-old
+new
"""

    assert paths_from_patch(patch) == {"packages/foo/Foo.js"}


def test_sanitize_model_patch_removes_test_patch_files_and_root_gitignore():
    patch = """diff --git a/.gitignore b/.gitignore
index 1111111..2222222 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1 +1,2 @@
 node_modules
+dist
diff --git a/packages/foo/Foo.test.js b/packages/foo/Foo.test.js
index 3333333..4444444 100644
--- a/packages/foo/Foo.test.js
+++ b/packages/foo/Foo.test.js
@@ -1 +1 @@
-expect(false).to.equal(true)
+expect(true).to.equal(true)
diff --git a/packages/foo/Foo.js b/packages/foo/Foo.js
index 5555555..6666666 100644
--- a/packages/foo/Foo.js
+++ b/packages/foo/Foo.js
@@ -1 +1 @@
-old
+new
"""

    sanitized = sanitize_model_patch(patch, exclude_paths={"packages/foo/Foo.test.js"})

    assert sanitized is not None
    assert "diff --git a/packages/foo/Foo.js b/packages/foo/Foo.js" in sanitized
    assert "diff --git a/.gitignore b/.gitignore" not in sanitized
    assert "diff --git a/packages/foo/Foo.test.js b/packages/foo/Foo.test.js" not in sanitized


def test_sanitize_model_patch_returns_none_when_every_file_is_removed():
    patch = """diff --git a/.gitignore b/.gitignore
index 1111111..2222222 100644
--- a/.gitignore
+++ b/.gitignore
@@ -1 +1,2 @@
 node_modules
+dist
"""

    assert sanitize_model_patch(patch) is None
