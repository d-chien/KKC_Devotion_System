import os
import unittest
import re

class TestFrontendIntegrity(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.frontend_dir = os.path.join(self.base_dir, 'frontend')

    def test_files_exist(self):
        """Check if critical frontend files exist."""
        required_files = [
            'index.html',
            'js/app.js',
            'admin/index.html',
            'admin/dashboard.html',
            'media/logo.svg',
            'media/logo_bgrm.svg',
            'media/favicon.svg'
        ]
        for f in required_files:
            path = os.path.join(self.frontend_dir, f)
            self.assertTrue(os.path.exists(path), f"File {f} not found")

    def test_index_html_structure(self):
        """Check availability of key elements in index.html."""
        with open(os.path.join(self.frontend_dir, 'index.html'), 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('id="login-view"', content)
        self.assertIn('id="dashboard-view"', content)
        self.assertIn('id="bind-modal"', content)
        self.assertIn('src="/js/app.js"', content)
        self.assertIn('media/favicon.svg', content)

    def test_app_js_functions(self):
        """Check if app.js contains expected functions."""
        with open(os.path.join(self.frontend_dir, 'js/app.js'), 'r', encoding='utf-8') as f:
            content = f.read()
            
        functions = [
            'checkAuth',
            'showLogin',
            'showDashboard',
            'showBindModal',
            'submitBind',
            'loadDashboard',
            'renderDashboard',
            'toggleAmount',
            'renderCharts',
            'logout'
        ]
        for func in functions:
            # Simple regex to find "function name(" or "name ="
            pattern = re.compile(rf'function\s+{func}|{func}\s*=\s*')
            self.assertTrue(pattern.search(content), f"Function {func} not found in app.js")

    def test_admin_dashboard_structure(self):
         with open(os.path.join(self.frontend_dir, 'admin/dashboard.html'), 'r', encoding='utf-8') as f:
            content = f.read()
            
         self.assertIn('id="tab-dashboard"', content)
         self.assertIn('id="tab-upload"', content)
         self.assertIn('uploadFile()', content)

if __name__ == "__main__":
    unittest.main()
