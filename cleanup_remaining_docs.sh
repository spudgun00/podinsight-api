#!/bin/bash

# Enhanced cleanup script for remaining markdown files
# This handles all the development documentation that wasn't caught by the first cleanup

set -e

echo "🧹 Enhanced Documentation Cleanup Script"
echo "========================================="

# Create timestamp for this cleanup
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
CLEANUP_LOG="cleanup_docs_${TIMESTAMP}.log"

# Archive directory (use existing structure)
ARCHIVE_DIR="archive"
DEV_NOTES_DIR="$ARCHIVE_DIR/development-notes"
SPRINTS_DIR="$ARCHIVE_DIR/2025-06-development/sprints"

# Ensure archive directories exist
mkdir -p "$DEV_NOTES_DIR"
mkdir -p "$SPRINTS_DIR"

echo "📁 Archive directories ready:"
echo "  - $DEV_NOTES_DIR"
echo "  - $SPRINTS_DIR"
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

# Categories of files to archive

echo "🗂️  Archiving Sprint 1 Documentation..."
# Sprint 1 specific files
sprint1_files=(
    "sprint1-key-prompts.md"
    "sprint1-migration-summary.md"
    "sprint1-playbook-updated.md"
    "sprint1-progress-update.md"
    "sprint1-progress-log.md"
    "sprint1-test-log_ARCHIVE.md"
    "sprint1-mongodb-integration.md"
    "playbook_sprint1.md"
    "SPRINT1_MONGODB_INTEGRATION_STATUS.md"
    "SPRINT1_NEXT_SESSION_PROMPTS.md"
    "SPRINT1_ENHANCEMENTS_DISCOVERED.md"
)

for file in "${sprint1_files[@]}"; do
    move_file "$file" "$SPRINTS_DIR" "SPRINT1"
done

echo ""
echo "🗂️  Archiving Sprint 2/3 Documentation..."
# Sprint 2/3 files
sprint23_files=(
    "SPRINT_2_768D_UPDATE.md"
    "SPRINT_3_VECTOR_SEARCH_IMPLEMENTATION.md"
    "SPRINT_SESSION_JUNE23_SUMMARY.md"
    "SPRINT_SESSION_JUNE24_UPDATE.md"
)

for file in "${sprint23_files[@]}"; do
    move_file "$file" "$SPRINTS_DIR" "SPRINT2/3"
done

echo ""
echo "🗂️  Archiving API/Deployment Documentation..."
# API and deployment documentation
api_docs=(
    "api_deployment_instructions.md"
    "api_deployment_checklist.md"
    "SEARCH_API_DOCUMENTATION.md"
    "SEARCH_DEPLOYMENT_CHECKLIST.md"
    "VERCEL_DEPLOYMENT_GUIDE.md"
    "SEARCH_API_FIX_INSTRUCTIONS.md"
    "DEPLOYMENT_WORKAROUND.md"
    "DEPLOYMENT_FIX_GUIDE.md"
    "SERVER_SETUP_GUIDE.md"
    "api-endpoints.md"
)

for file in "${api_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "API_DOCS"
done

echo ""
echo "🗂️  Archiving Architecture Documentation..."
# Architecture and system docs
arch_docs=(
    "architecture-overview.md"
    "system-overview.md"
    "database-schema.md"
    "database-schema copy.md"
    "s3_bucket_structure.md"
    "s3_bucket_structure copy.md"
    "S3_BUCKET_STRUCTURE_CORRECTED.md"
    "mongodb-transcript-structure.md"
    "DATABASE_ARCHITECTURE.md"
    "MODAL_ARCHITECTURE_DIAGRAM.md"
)

for file in "${arch_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "ARCHITECTURE"
done

echo ""
echo "🗂️  Archiving Testing Documentation..."
# Testing documentation
test_docs=(
    "test_results.md"
    "comprehensive_test_results.md"
    "test_results_phase3.md"
    "TEST_RESULTS_PHASE3.2.md"
    "COMPREHENSIVE_TEST_REPORT.md"
    "MONGODB_SEARCH_TEST_GUIDE.md"
    "TESTING_ROADMAP.md"
    "check_search_status.md"
    "TROUBLESHOOTING_SEARCH.md"
)

for file in "${test_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "TESTING"
done

echo ""
echo "🗂️  Archiving Modal.com Documentation..."
# Modal documentation
modal_docs=(
    "README_MODAL.md"
    "README_MODAL_COMPREHENSIVE.md"
    "MODAL_INFRASTRUCTURE_COMPARISON.md"
    "MODAL_FIX_EXPLANATION.md"
    "MODAL_OPTIMIZATION_COMPREHENSIVE_GUIDE.md"
    "MODAL_OPTIMIZATION_TEST_PLAN.md"
    "MODAL_SNAPSHOT_FIX_GUIDE.md"
    "MODAL_PHYSICS_EXPLANATION.md"
    "MODAL_OPERATIONS_GUIDE.md"
)

for file in "${modal_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "MODAL"
done

echo ""
echo "🗂️  Archiving Vector Search Documentation..."
# Vector search documentation
vector_docs=(
    "VECTOR_SEARCH_DECISION.md"
    "VECTOR_SEARCH_FINDINGS.md"
    "VECTOR_SEARCH_COMPARISON.md"
    "INSTRUCTOR_XL_EVALUATION.md"
    "embedding-strategy.md"
    "EMBEDDINGS_STATUS.md"
    "How to Index Fields for Vector Search.md"
    "SEARCH_ARCHITECTURE_PROBLEM_STATEMENT.md"
)

for file in "${vector_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "VECTOR_SEARCH"
done

echo ""
echo "🗂️  Archiving Business/Planning Documentation..."
# Business and planning docs
business_docs=(
    "Business_Overview.md"
    "podinsight-90day-roadmap.md"
    "podinsight-credits-strategy.md"
    "EPISODE_LEVEL_SEARCH_BUSINESS_CASE.md"
    "PRODUCTION_READINESS_CHECKLIST.md"
)

for file in "${business_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "BUSINESS"
done

echo ""
echo "🗂️  Archiving Integration/Setup Documentation..."
# Integration and setup guides
integration_docs=(
    "FRONTEND_INTEGRATION_GUIDE.md"
    "FRONTEND_INTEGRATION_GUIDE 2.md"
    "dashboard-integration-guide.md"
    "transcript-integration-plan.md"
    "VIRTUAL_ENV_SETUP.md"
    "CONNECTION_POOL_DOCS.md"
    "AUTO_LOGGING_GUIDE.md"
)

for file in "${integration_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "INTEGRATION"
done

echo ""
echo "🗂️  Archiving Session Handoff Documentation..."
# Session handoff docs
handoff_docs=(
    "NEXT_SESSION_PROMPT.md"
    "NEXT_SESSION_PROMPT_PHASE3.md"
    "NEXT_SESSION_HANDOFF.md"
    "@NEXT_SESSION_HANDOFF_CRITICAL_FIXES.md"
    "@NEXT_SESSION_HANDOFF_FINAL.md"
    "CLAUDE_MAX_PROMPT_PHASE3.md"
    "CLAUDE_CODE_MONGODB_PROMPT.md"
)

for file in "${handoff_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "SESSION_HANDOFFS"
done

echo ""
echo "🗂️  Archiving Miscellaneous Documentation..."
# Miscellaneous files
misc_docs=(
    "playbook.md"
    "mongodb-migration-plan_ARCHIVE.md"
    "mongodb-action-plan.md"
    "mongodb-scoring-explanation.md"
    "phase3-search-api-summary.md"
    "CACHE_BUSTING_GUIDE.md"
    "ENTITIES_DOCUMENTATION.md"
    "EPISODE_TITLES_SOLUTION.md"
    "ETL_REPROCESSING_REQUIREMENTS.md"
    "RECOVERY_VALIDATION_REPORT.md"
    "MONGODB_COVERAGE_VERIFICATION_REPORT.md"
    "FINAL_COVERAGE_VERIFICATION.md"
    "EMERGENCY_STORAGE_ISSUE_DOCUMENTATION.md"
    "SINGLE_SOURCE_USER_TESTING_CLI_AND_WEB.md"
    "SUPABASE_EPISODE_METADATA_ISSUE_REPORT.md"
    "MONGODB_METADATA_API_UPDATE.md"
    "chatgpt_segmentissue.md"
    "FIX_NOW.md"
)

for file in "${misc_docs[@]}"; do
    move_file "$file" "$DEV_NOTES_DIR" "MISC"
done

# Count results
echo ""
echo "📊 Cleanup Summary"
echo "=================="
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
echo "🎯 Remaining root-level .md files:"
remaining_md=$(find . -maxdepth 1 -name "*.md" -not -name "README.md" -not -name "PROJECT.md" | wc -l)
if [[ $remaining_md -eq 0 ]]; then
    echo "  🎉 All development documentation archived! Only README.md and PROJECT.md remain."
else
    echo "  📋 $remaining_md files still in root directory:"
    find . -maxdepth 1 -name "*.md" -not -name "README.md" -not -name "PROJECT.md" | sort
fi

echo ""
echo "✅ Enhanced documentation cleanup complete!"
echo ""
echo "Archive structure:"
echo "📁 $ARCHIVE_DIR/"
echo "  ├── development-notes/ (categorized documentation)"
echo "  └── 2025-06-development/sprints/ (sprint-specific files)"
