# Mobile Codex fork: Android test build

This fork keeps the original release app ID `dev.mobilecodex.app` unchanged.

## Build on GitHub

1. Open the fork's **Actions** tab. GitHub may require you to enable workflows for a newly created fork.
2. Run **Fork Android test APK** via **Run workflow**, or open a pull request into `main`.
3. Wait for both JavaScript/Python and Android unit tests and lint to pass.
4. Download the **mobile-codex-fork-test-apk** artifact from the workflow run.
5. Unzip it and install `app-debug.apk` on an ARM64 device (Android 10+).

The workflow verifies the APK signature and package name and uploads a SHA-256 manifest.

**Important:** This is a developer **debug/test** build, not a production release.
The test APK has application ID `dev.mobilecodex.app.fork` and a CI-generated debug signature.
It installs **beside** the original `dev.mobilecodex.app` without removing the original app.
It does not inherit the original app's chats, account data, or credentials. It cannot update
the original app in place, because the original production signing key is not available.
Never share or copy your original app's credentials into CI to bypass this restriction.

Only a production APK signed with the original certificate can update an existing
`dev.mobilecodex.app` installation without uninstalling it.

## Known limitations

The sign-in startup/initialize timeout reported in upstream issue #15 is unresolved
without a sanitized diagnostic report from a device on which it reproduces.
The fork includes login error/retry handling and prevents a late device-code response
from reviving a dismissed dialog, but those are not a confirmed fix for the root cause.

This workflow does not run Android **instrumentation tests on a physical device**.
It compiles the instrumentation test APK and runs unit tests/lint. Actual sign-in
and installation should still be tested on a real ARM64 phone.
