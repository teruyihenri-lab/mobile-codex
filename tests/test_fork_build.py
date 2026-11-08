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
        self.assertNotIn('gh release', workflow)
        self.assertRegex(workflow, r'permissions:\n  contents: read')

if __name__ == '__main__':
    unittest.main()
