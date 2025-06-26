#!/bin/bash

# Final comprehensive cleanup script
# This archives ALL remaining development files except core project files

set -e

echo "🧹 Final Comprehensive Cleanup Script"
echo "====================================="

# Create timestamp for this cleanup
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
CLEANUP_LOG="final_cleanup_${TIMESTAMP}.log"

# Archive directories (use existing structure)
ARCHIVE_DIR="archive"
DEV_NOTES_DIR="$ARCHIVE_DIR/development-notes"
LOGS_DIR="$ARCHIVE_DIR/2025-06-development/logs"
TESTS_DIR="$ARCHIVE_DIR/2025-06-development/test-reports"
CONFIG_DIR="$ARCHIVE_DIR/2025-06-development/configs"
TEMP_DIR="$ARCHIVE_DIR/2025-06-development/temp-files"

# Ensure all archive directories exist
mkdir -p "$DEV_NOTES_DIR"
mkdir -p "$LOGS_DIR"
mkdir -p "$TESTS_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$TEMP_DIR"

echo "📁 Archive directories ready:"
echo "  - $DEV_NOTES_DIR"
echo "  - $LOGS_DIR"
echo "  - $TESTS_DIR"
echo "  - $CONFIG_DIR"
echo "  - $TEMP_DIR"
echo ""

# Function to move file with logging
move_file() {
    local file="$1"
    local dest_dir="$2"
    local category="$3"

    if [[ -f "$file" ]]; then
        mv "$file" "$dest_dir/"
        echo "✅ [$category] $(basename "$file")" | tee -a "$CLEANUP_LOG"
        return 0
    else
        echo "⚠️  [$category] $(basename "$file") - not found" | tee -a "$CLEANUP_LOG"
        return 1
    fi
}

# Archive remaining markdown files
echo "🗂️  Archiving Remaining Markdown Documentation..."
remaining_md_files=(
    "SESSION_SUMMARY_JUNE_25_2025.md"
    "MONGODB_DATA_MODEL.md"
    "FIXES_IMPLEMENTED_JUNE_25_2025.md"
    "API_SEARCH_ISSUE_DETAILED_REPORT.md"
    "PRODUCTION_READY_STATUS.md"
    "E2E_TEST_RESULTS_JUNE_25.md"
    "E2E_TEST_RESULTS_LATEST.md"
    "CONTEXT_FOR_NEXT_SESSION.md"
    "CHATGPT_ADVISOR_PROMPT.md"
    "ADVISOR_CODE_APPENDIX.md"
    "CLEANUP_READY.md"
)

for file in "${remaining_md_files[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "SESSION_DOCS"
done

echo ""
echo "🗂️  Archiving Test Reports and HTML Files..."
# Test reports and HTML files
test_files=(
    "podinsight-test-report-2025-06-24T20-52-55-155Z.txt"
    "load_test_results.txt"
    "segment_mismatch_report.txt"
    "frontend_test.html"
    "test-podinsight-advanced.html"
)

for file in "${test_files[@]}"; do
    move_file "$file" "$TESTS_DIR" "TEST_REPORTS"
done

echo ""
echo "🗂️  Archiving Log Files..."
# Log files
log_files=(
    "api.log"
    "migration.log"
    "monitoring.log"
    "mongodb_verification_20250619_221857.log"
    "cleanup_docs_2025-06-26_133629.log"
)

for file in "${log_files[@]}"; do
    move_file "$file" "$LOGS_DIR" "LOGS"
done

echo ""
echo "🗂️  Archiving JSON Reports and Data Files..."
# JSON reports and data files
json_files=(
    "health_check_results.json"
    "logs_result.json"
    "meta_0e983347-7815-4b62-87a6-84d988a772b7_details.json"
    "meta_1f70dc6c-ed89-11ef-99d7-1f4bf7b18593_details.json"
    "missing_episodes_detailed_20250619_222717.json"
    "missing_episodes_report_20250619_222206.json"
    "missing_episodes_report_20250619_222233.json"
    "missing_episodes_report_20250619_222319.json"
    "modal_diagnostic_report.json"
    "modal_response.json"
    "mongodb_vector_debug_report.json"
    "monitoring_report_20250622_220024.json"
    "real_test_episodes.json"
    "supabase_test_results.json"
    "fix_vector_index.json"
)

for file in "${json_files[@]}"; do
    move_file "$file" "$LOGS_DIR" "JSON_REPORTS"
done

echo ""
echo "🗂️  Archiving Configuration Files..."
# Configuration files (keep requirements.txt and vercel.json)
config_files=(
    "requirements_768d.txt"
    "requirements_full.txt"
    "requirements_vercel.txt"
    "runtime.txt"
    "pytest.ini"
)

for file in "${config_files[@]}"; do
    move_file "$file" "$CONFIG_DIR" "CONFIGS"
done

echo ""
echo "🗂️  Archiving Shell Scripts..."
# Shell scripts (keep the cleanup scripts we just created)
script_files=(
    "DEPLOY_COMMANDS.sh"
    "add_vercel_env.sh"
    "check_env.sh"
    "deploy_manual.sh"
    "deploy_with_hf.sh"
    "post_deployment_tests.sh"
    "start_test_server.sh"
    "test_deployment.sh"
    "test_search_api.sh"
    "test_search_simple.sh"
    "update_hf_key.sh"
    "verify_768d_system.sh"
)

for file in "${script_files[@]}"; do
    move_file "$file" "$CONFIG_DIR" "SCRIPTS"
done

echo ""
echo "🗂️  Archiving Temporary and Miscellaneous Files..."
# Temporary and miscellaneous files
temp_files=(
    "chatgpt_episodeidmismatch"
    "chatgpt_propsal"
    "chatgpt_vectorsearchadvice"
    "emergency_mongo_cleanup.js"
    "sentiment_analysis.bak"
)

for file in "${temp_files[@]}"; do
    move_file "$file" "$TEMP_DIR" "TEMP_FILES"
done

echo ""
echo "🗂️  Archiving advisor_fixes Directory..."
# Move entire advisor_fixes directory
if [[ -d "advisor_fixes" ]]; then
    mv "advisor_fixes" "$DEV_NOTES_DIR/"
    echo "✅ [ADVISOR] advisor_fixes/ directory" | tee -a "$CLEANUP_LOG"
else
    echo "⚠️  [ADVISOR] advisor_fixes/ directory - not found" | tee -a "$CLEANUP_LOG"
fi

echo ""
echo "🗂️  Archiving env and test_env Directories..."
# Archive env and test_env directories
if [[ -d "env" ]]; then
    mv "env" "$CONFIG_DIR/"
    echo "✅ [ENV] env/ directory" | tee -a "$CLEANUP_LOG"
else
    echo "⚠️  [ENV] env/ directory - not found" | tee -a "$CLEANUP_LOG"
fi

if [[ -d "test_env" ]]; then
    mv "test_env" "$CONFIG_DIR/"
    echo "✅ [ENV] test_env/ directory" | tee -a "$CLEANUP_LOG"
else
    echo "⚠️  [ENV] test_env/ directory - not found" | tee -a "$CLEANUP_LOG"
fi

# Count results
echo ""
echo "📊 Final Cleanup Summary"
echo "======================="
echo "Log file: $CLEANUP_LOG"
echo ""

# Count files in each category
echo "Files archived by category:"
grep "✅" "$CLEANUP_LOG" | cut -d']' -f1 | cut -d'[' -f2 | sort | uniq -c | sort -rn

echo ""
echo "Total files processed:"
total_moved=$(grep -c "✅" "$CLEANUP_LOG" 2>/dev/null || echo "0")
total_missing=$(grep -c "⚠️" "$CLEANUP_LOG" 2>/dev/null || echo "0")
echo "  ✅ Successfully archived: $total_moved"
echo "  ⚠️  Files not found: $total_missing"

echo ""
echo "🎯 Remaining files in root directory:"
echo ""
echo "📋 Core Project Files (KEEP):"
echo "  - README.md"
echo "  - PROJECT.md"
echo "  - requirements.txt"
echo "  - vercel.json"
echo ""

echo "📋 Cleanup Scripts (KEEP):"
echo "  - cleanup_repository.sh"
echo "  - cleanup_remaining_docs.sh"
echo "  - final_cleanup.sh"
echo "  - $CLEANUP_LOG"
echo ""

echo "📋 Core Directories (KEEP):"
echo "  - api/"
echo "  - scripts/"
echo "  - tests/"
echo "  - archive/"
echo "  - .git/"
echo ""

# Check what's actually left
echo "📋 Actual remaining files:"
find . -maxdepth 1 -type f \
    -not -name "README.md" \
    -not -name "PROJECT.md" \
    -not -name "requirements.txt" \
    -not -name "vercel.json" \
    -not -name "cleanup_repository.sh" \
    -not -name "cleanup_remaining_docs.sh" \
    -not -name "final_cleanup.sh" \
    -not -name "$CLEANUP_LOG" \
    | sort

remaining_count=$(find . -maxdepth 1 -type f \
    -not -name "README.md" \
    -not -name "PROJECT.md" \
    -not -name "requirements.txt" \
    -not -name "vercel.json" \
    -not -name "cleanup_repository.sh" \
    -not -name "cleanup_remaining_docs.sh" \
    -not -name "final_cleanup.sh" \
    -not -name "$CLEANUP_LOG" \
    | wc -l)

echo ""
if [[ $remaining_count -eq 0 ]]; then
    echo "🎉 ROOT DIRECTORY IS NOW CLEAN!"
    echo "    Only essential project files and directories remain."
else
    echo "📊 $remaining_count unexpected files still in root directory"
fi

echo ""
echo "✅ Final comprehensive cleanup complete!"
echo ""
echo "📁 Final archive structure:"
echo "$ARCHIVE_DIR/"
echo "├── development-notes/ (documentation + advisor_fixes/)"
echo "├── 2025-06-development/"
echo "│   ├── logs/ (log files + JSON reports)"
echo "│   ├── test-reports/ (test results + HTML files)"
echo "│   ├── configs/ (config files + scripts + env dirs)"
echo "│   ├── temp-files/ (temporary files)"
echo "│   ├── scripts/ (archived scripts from previous cleanup)"
echo "│   └── sprints/ (sprint documentation)"
echo "└── ..."
