import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ForkApkBuildTests(unittest.TestCase):
    def test_distinct_debug_package_is_only_enabled_for_fork_ci(self):
        gradle = (ROOT / 'app/build.gradle').read_text(encoding='utf-8')
        self.assertIn("applicationId 'dev.mobilecodex.app'", gradle)
        self.assertIn("System.getenv('MOBILE_CODEX_FORK_TEST') == 'true'", gradle)
        self.assertIn("applicationIdSuffix '.fork'", gradle)

    def test_upstream_production_job_is_disabled_on_public_forks(self):
        workflow = (ROOT / '.github/workflows/android.yml').read_text(encoding='utf-8')
        self.assertIn("if: github.repository == 'nokryong/mobile-codex' || github.repository == 'SeeUSoon93/mobile-codex'", workflow)
        self.assertIn("run: python3 tools/sign_ci_apk.py --check-config", workflow)

    def test_fork_resolves_a_fresh_content_addressed_termux_lock_for_debug_only(self):
        workflow = (ROOT / '.github/workflows/fork-test-apk.yml').read_text(encoding='utf-8')
        upstream = (ROOT / '.github/workflows/android.yml').read_text(encoding='utf-8')
        self.assertIn("python3 tools/prepare_devtools.py --write-lock", workflow)
        self.assertLess(workflow.index("python3 tools/prepare_devtools.py --write-lock"),
                        workflow.index("python3 tools/prepare_devtools.py --verify"))
        self.assertIn("tools/devtools-lock.json", workflow)
        self.assertIn('rm -f .runtime-cache/termux-Packages', workflow)
        self.assertNotIn("python3 tools/prepare_devtools.py --write-lock", upstream)

    def test_fork_workflow_tests_before_upload_and_does_not_publish_or_request_secrets(self):
        workflow = (ROOT / '.github/workflows/fork-test-apk.yml').read_text(encoding='utf-8')
        self.assertIn("github.repository == 'teruyihenri-lab/mobile-codex'", workflow)
        self.assertIn("MOBILE_CODEX_FORK_TEST: 'true'", workflow)
        for command in ('npm test', "unittest discover -s tests -p 'test_*.py'",
                        'npm run test:layout', 'assembleDebug testDebugUnitTest lintDebug assembleDebugAndroidTest',
                        'apksigner', 'dev.mobilecodex.app.fork', 'sha256sum'):
            self.assertIn(command, workflow)
        self.assertLess(workflow.index('npm test'), workflow.index('Upload verified installable test APK'))
        self.assertLess(workflow.index('assembleDebug testDebugUnitTest'), workflow.index('Upload verified installable test APK'))
        self.assertNotIn('${{ secrets.', workflow)
        self.assertLess(workflow.index('Prepare pinned ARM64 runtime and developer tools'), workflow.index('Check responsive browser layouts'))
        self.assertLess(workflow.index('Build debug APK, compile Android tests, run unit tests and lint'), workflow.index('Check responsive browser layouts'))
        self.assertNotIn('gh release', workflow)
        self.assertRegex(workflow, r'permissions:\n  contents: read')

if __name__ == '__main__':
    unittest.main()
