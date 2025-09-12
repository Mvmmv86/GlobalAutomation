#!/bin/bash

# TradingView Gateway - Test Suite Runner
# Executa toda a suite de testes de forma organizada

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'  
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VERBOSE=${VERBOSE:-false}
COVERAGE=${COVERAGE:-false}
QUICK=${QUICK:-false}
CI=${CI:-false}

# Helper functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [[ ! -d "integration" || ! -d "stress" || ! -d "chaos" ]]; then
    error "Please run this script from packages/shared/src/test directory"
    exit 1
fi

# Print banner
echo "🧪 ===== TradingView Gateway Test Suite ====="
echo "📊 Comprehensive testing for trading platform"
echo "⏰ Started at: $(date)"
echo "🔧 Quick mode: $QUICK"
echo "📋 CI mode: $CI"
echo "================================================="
echo

# Test results tracking
declare -A test_results
total_tests=0
passed_tests=0
failed_tests=0

# Function to run test suite
run_test_suite() {
    local suite_name="$1"
    local suite_dir="$2" 
    local test_command="$3"
    
    log "Running $suite_name tests..."
    
    if [[ ! -d "$suite_dir" ]]; then
        warning "Directory $suite_dir not found, skipping..."
        return 0
    fi
    
    cd "$suite_dir"
    
    # Check if package.json exists and install deps if needed
    if [[ -f "package.json" && ! -d "node_modules" ]]; then
        log "Installing dependencies for $suite_name..."
        npm install --silent
    fi
    
    # Run the tests
    local start_time=$(date +%s)
    if eval "$test_command" > "/tmp/${suite_name,,}_test_output.log" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        success "$suite_name tests passed (${duration}s)"
        test_results["$suite_name"]="PASSED"
        ((passed_tests++))
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        error "$suite_name tests failed (${duration}s)"
        test_results["$suite_name"]="FAILED"
        ((failed_tests++))
        
        # Show last 20 lines of output on failure
        echo "📋 Last 20 lines of output:"
        tail -20 "/tmp/${suite_name,,}_test_output.log"
        echo
    fi
    
    ((total_tests++))
    cd - > /dev/null
}

# Function to run quick tests (for CI)
run_quick_tests() {
    log "Running quick test suite for CI/CD..."
    
    run_test_suite "Integration" "integration" "npm test -- --maxWorkers=2"
    run_test_suite "Light Load" "stress" "npm run load:light"
    run_test_suite "Small Spike" "stress" "npm run spike:small"
    run_test_suite "Basic Chaos" "chaos" "npm test -- --testNamePattern='handle primary exchange failure'"
}

# Function to run full test suite
run_full_tests() {
    log "Running comprehensive test suite..."
    
    # Integration Tests
    run_test_suite "Integration" "integration" "npm test${COVERAGE:+ --coverage}"
    
    # Stress Tests
    if [[ "$CI" == "true" ]]; then
        run_test_suite "Load Testing" "stress" "npm run test:ci"
    else
        run_test_suite "Load Testing" "stress" "npm run all:medium"
    fi
    
    # Chaos Engineering Tests  
    run_test_suite "Chaos Engineering" "chaos" "npm test${COVERAGE:+ --coverage}"
    
    # E2E Tests
    run_test_suite "End-to-End" "e2e" "npm test${COVERAGE:+ --coverage}"
}

# Pre-flight checks
log "Running pre-flight checks..."

# Check Node.js version
if ! command -v node &> /dev/null; then
    error "Node.js is not installed"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [[ $NODE_VERSION -lt 16 ]]; then
    error "Node.js version 16+ required, found: $(node --version)"
    exit 1
fi

success "Node.js version: $(node --version)"

# Check available memory
if command -v free &> /dev/null; then
    AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [[ $AVAILABLE_MEM -lt 1000 ]]; then
        warning "Low available memory: ${AVAILABLE_MEM}MB"
        warning "Stress tests may be unreliable"
    fi
fi

# Main test execution
start_time=$(date +%s)

if [[ "$QUICK" == "true" ]]; then
    run_quick_tests
else
    run_full_tests
fi

end_time=$(date +%s)
total_duration=$((end_time - start_time))

# Results summary
echo
echo "📊 ===== TEST RESULTS SUMMARY ====="
echo "⏰ Total Duration: ${total_duration}s"
echo "📈 Total Suites: $total_tests"
echo "✅ Passed: $passed_tests"  
echo "❌ Failed: $failed_tests"
echo

# Print detailed results
for suite in "${!test_results[@]}"; do
    status="${test_results[$suite]}"
    if [[ "$status" == "PASSED" ]]; then
        success "$suite: $status"
    else
        error "$suite: $status"
    fi
done

echo
echo "📋 ===== DETAILED LOGS ====="
echo "Individual test outputs available in /tmp/*_test_output.log"

# Coverage summary (if enabled)
if [[ "$COVERAGE" == "true" ]]; then
    echo
    log "Coverage reports generated in respective coverage/ directories"
fi

# Exit with appropriate code
if [[ $failed_tests -eq 0 ]]; then
    echo
    success "🎉 All test suites passed! System ready for deployment."
    echo "🔥 Performance targets met, no critical issues detected."
    exit 0
else
    echo  
    error "💥 $failed_tests test suite(s) failed!"
    echo "🚫 System NOT ready for deployment."
    echo "📋 Review the logs above and fix the issues."
    exit 1
fi