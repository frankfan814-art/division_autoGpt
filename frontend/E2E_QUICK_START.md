#!/bin/bash

# E2E Test Quick Start Script for Creative AutoGPT
# This script helps you run E2E tests easily

set -e

echo "=========================================="
echo "Creative AutoGPT E2E Tests"
echo "=========================================="
echo ""

# Check if we're in the frontend directory
if [ ! -f "package.json" ] || [ ! -d "e2e" ]; then
    echo "❌ Error: Please run this script from the frontend directory"
    echo "   Usage: cd frontend && ./e2e-quick-start.sh"
    exit 1
fi

# Check if Playwright is installed
if ! command -v npx &> /dev/null; then
    echo "❌ Error: npx is not installed"
    echo "   Please install Node.js and npm"
    exit 1
fi

echo "✅ Environment check passed"
echo ""

# Menu
echo "Select an option:"
echo "  1) Run smoke tests (fast health check)"
echo "  2) Run critical tests (core flows)"
echo "  3) Run important tests (key features)"
echo "  4) Run all E2E tests"
echo "  5) Run tests in UI mode (interactive)"
echo "  6) Run tests in headed mode (see browser)"
echo "  7) Run tests in debug mode"
echo "  8) View test report"
echo "  9) Clean up test sessions"
echo "  0) Exit"
echo ""

read -p "Enter your choice (0-9): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Running smoke tests..."
        npx playwright test e2e/smoke --reporter=list
        ;;
    2)
        echo ""
        echo "🚀 Running critical tests..."
        npx playwright test e2e/critical --reporter=list
        ;;
    3)
        echo ""
        echo "🚀 Running important tests..."
        npx playwright test e2e/important --reporter=list
        ;;
    4)
        echo ""
        echo "🚀 Running all E2E tests..."
        npx playwright test --reporter=list
        ;;
    5)
        echo ""
        echo "🚀 Running tests in UI mode..."
        npx playwright test --ui
        ;;
    6)
        echo ""
        echo "🚀 Running tests in headed mode..."
        npx playwright test --headed
        ;;
    7)
        echo ""
        echo "🚀 Running tests in debug mode..."
        npx playwright test --debug
        ;;
    8)
        echo ""
        echo "📊 Opening test report..."
        npx playwright show-report
        ;;
    9)
        echo ""
        echo "🧹 Cleaning up test sessions..."
        node -e "
        const http = require('http');

        function cleanup() {
            const options = {
                hostname: 'localhost',
                port: 8000,
                path: '/sessions?page_size=100',
                method: 'GET'
            };

            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => { data += chunk; });
                res.on('end', () => {
                    try {
                        const sessions = JSON.parse(data).sessions || [];
                        const testSessions = sessions.filter(s =>
                            s.title?.toLowerCase().includes('e2e') ||
                            s.title?.toLowerCase().includes('test') ||
                            s.title?.includes('测试')
                        );

                        console.log(\`Found \${testSessions.length} test sessions\`);

                        let deleted = 0;
                        testSessions.forEach((session, index) => {
                            setTimeout(() => {
                                const delOptions = {
                                    hostname: 'localhost',
                                    port: 8000,
                                    path: \`/sessions/\${session.id}\`,
                                    method: 'DELETE'
                                };

                                const delReq = http.request(delOptions, (delRes) => {
                                    console.log(\`  Deleted: \${session.id}\`);
                                    deleted++;
                                    if (deleted === testSessions.length) {
                                        console.log(\`\\n✅ Cleaned up \${deleted} test sessions\`);
                                        process.exit(0);
                                    }
                                });

                                delReq.on('error', (err) => {
                                    console.error(\`  Failed to delete \${session.id}:\`, err.message);
                                    deleted++;
                                    if (deleted === testSessions.length) {
                                        console.log(\`\\n✅ Cleaned up \${deleted} test sessions\`);
                                        process.exit(0);
                                    }
                                });

                                delReq.end();
                            }, index * 100);
                        });

                        if (testSessions.length === 0) {
                            console.log('✅ No test sessions to clean up');
                            process.exit(0);
                        }
                    } catch (error) {
                        console.error('Error parsing sessions:', error.message);
                        process.exit(1);
                    }
                });
            });

            req.on('error', (err) => {
                console.error('❌ Error fetching sessions:', err.message);
                console.log('   Make sure the backend is running on port 8000');
                process.exit(1);
            });

            req.end();
        }
        cleanup();
        "
        ;;
    0)
        echo ""
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Invalid choice. Please run again."
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Test run complete!"
echo "=========================================="
echo ""
echo "View results:"
echo "  HTML Report: npx playwright show-report"
echo "  Screenshots: ls -la artifacts/"
echo "  Videos:      ls -la test-results/"
echo ""
