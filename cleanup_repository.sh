#!/bin/bash
# PodInsight Repository Cleanup Script
# Execute from repository root: ./cleanup_repository.sh

set -e  # Exit on any error

echo "🧹 Starting PodInsight Repository Cleanup..."
echo "Current directory: $(pwd)"
echo ""

# Confirm we're in the right directory
if [ ! -f "vercel.json" ] || [ ! -d "api" ]; then
    echo "❌ Error: Please run this script from the repository root (where vercel.json exists)"
    exit 1
fi

echo "✅ Confirmed: Running from repository root"
echo ""

# Create archive directory structure
echo "📁 Creating archive structure..."
mkdir -p archive/2025-06-development/{scripts,docs,logs,temp-files}
mkdir -p archive/legacy-documentation
mkdir -p archive/testing-archive
mkdir -p archive/development-notes

echo "📦 Archiving scripts (keeping production essentials)..."

# Production scripts to keep
PRODUCTION_SCRIPTS=(
    "modal_web_endpoint_simple.py"
    "test_e2e_production.py"
    "quick_vc_test.py"
)

# Count scripts before archiving
TOTAL_SCRIPTS=$(find scripts -name "*.py" 2>/dev/null | wc -l)
echo "  Found $TOTAL_SCRIPTS Python scripts in /scripts"

# Archive non-production scripts
ARCHIVED_SCRIPTS=0
cd scripts 2>/dev/null || { echo "  No scripts directory found, skipping..."; cd .; }

if [ "$(pwd | grep scripts)" ]; then
    for script in *.py 2>/dev/null; do
        if [ -f "$script" ]; then
            if [[ ! " ${PRODUCTION_SCRIPTS[@]} " =~ " ${script} " ]]; then
                echo "    Archiving: scripts/$script"
                mv "$script" "../archive/2025-06-development/scripts/"
                ((ARCHIVED_SCRIPTS++))
            else
                echo "    ✅ Keeping: scripts/$script (production essential)"
            fi
        fi
    done
    cd ..
fi

echo "  📊 Archived $ARCHIVED_SCRIPTS scripts, kept ${#PRODUCTION_SCRIPTS[@]} production scripts"
echo ""

echo "📦 Archiving documentation..."

# Documentation files to archive
DOCS_TO_ARCHIVE=(
    "SPRINT_LOG_VECTOR_SEARCH_DEBUG.md"
    "advisor_fixes/COMPLETE_CONTEXT_DOCUMENTATION.md"
    "advisor_fixes/FULL_SESSION_CONTEXT_E2E_COMPLETE.md"
)

ARCHIVED_DOCS=0
for doc in "${DOCS_TO_ARCHIVE[@]}"; do
    if [ -f "$doc" ]; then
        echo "    Archiving: $doc"
        mv "$doc" "archive/development-notes/"
        ((ARCHIVED_DOCS++))
    fi
done

# Archive any other debug/analysis files in root
find . -maxdepth 1 -name "*DEBUG*" -o -name "*ANALYSIS*" -o -name "*COMPLETE_*" -o -name "*PLAYBOOK*" | while read file; do
    if [ -f "$file" ] && [[ "$file" != "./advisor_fixes/"* ]]; then
        echo "    Archiving: $file"
        mv "$file" "archive/development-notes/"
        ((ARCHIVED_DOCS++))
    fi
done

echo "  📊 Archived documentation files"
echo ""

echo "📦 Archiving test files..."

# Test files to archive (keep main test interface)
TEST_FILES_TO_ARCHIVE=(
    "test-search-browser.html"
    "test-podinsight-combined.html"
)

ARCHIVED_TESTS=0
for test_file in "${TEST_FILES_TO_ARCHIVE[@]}"; do
    if [ -f "$test_file" ]; then
        echo "    Archiving: $test_file"
        mv "$test_file" "archive/testing-archive/"
        ((ARCHIVED_TESTS++))
    fi
done

echo "  📊 Archived $ARCHIVED_TESTS test files"
echo "  ✅ Keeping: test-podinsight-advanced.html (primary test interface)"
echo ""

echo "📝 Creating archive index..."

# Create comprehensive archive index
cat > archive/ARCHIVE_INDEX.md << EOF
# 📦 PodInsight Archive Index

**Created**: $(date)
**Purpose**: Index of all archived files from repository cleanup

---

## 📊 Archive Summary

| Category | Count | Location |
|----------|-------|----------|
| Scripts | $ARCHIVED_SCRIPTS | archive/2025-06-development/scripts/ |
| Documentation | Multiple | archive/development-notes/ |
| Test Files | $ARCHIVED_TESTS | archive/testing-archive/ |

---

## 📁 Archive Structure

### archive/2025-06-development/scripts/
Development and test scripts from June 2025 cleanup:
$(find archive/2025-06-development/scripts -name "*.py" 2>/dev/null | sed 's|archive/2025-06-development/scripts/|- |' || echo "- (No files)")

### archive/development-notes/
Sprint logs, debug reports, and development documentation:
$(find archive/development-notes -name "*.md" 2>/dev/null | sed 's|archive/development-notes/|- |' || echo "- (No files)")

### archive/testing-archive/
Old test interfaces and prototype testing tools:
$(find archive/testing-archive -name "*.html" 2>/dev/null | sed 's|archive/testing-archive/|- |' || echo "- (No files)")

---

## 🎯 Production Files Kept

### Essential Scripts (scripts/)
- modal_web_endpoint_simple.py    # Production Modal.com endpoint
- test_e2e_production.py         # End-to-end test suite
- quick_vc_test.py              # Quick VC validation tests

### Essential Documentation
- README.md                     # Project overview
- MODAL_ARCHITECTURE_DIAGRAM.md # System architecture
- advisor_fixes/PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md # Single source of truth

### Test Interface
- test-podinsight-advanced.html # Primary testing interface

---

## 🔍 Finding Archived Files

### Search Commands
\`\`\`bash
# Find all archived scripts containing "mongo"
find archive/ -name "*mongo*" -type f

# Find all documentation about vector search
grep -r "vector search" archive/

# List all archived test scripts
ls archive/2025-06-development/scripts/test_*.py

# Find specific file by partial name
find archive/ -name "*debug*" -type f
\`\`\`

### Restore Files if Needed
\`\`\`bash
# Copy file back to working directory
cp archive/2025-06-development/scripts/test_mongodb_connection.py scripts/

# Or move it back permanently
mv archive/testing-archive/test-search-browser.html ./
\`\`\`

---

## 📋 Archive Maintenance

- **Files are safe**: Nothing was deleted, only moved
- **Organized by date**: 2025-06-development for this cleanup sprint
- **Easy access**: Use find commands or browse directories
- **Restore anytime**: Copy or move files back as needed

**Next cleanup**: Create archive/2025-07-development/ for future cleanups
EOF

echo "✅ Repository cleanup complete!"
echo ""
echo "📊 Cleanup Summary:"
echo "  🗂️  Created organized archive structure"
echo "  📦 Archived $ARCHIVED_SCRIPTS development/test scripts"
echo "  📄 Archived development documentation"
echo "  🌐 Archived $ARCHIVED_TESTS old test files"
echo "  ✅ Kept 3 production scripts"
echo "  ✅ Kept 3 essential documentation files"
echo "  ✅ Kept 1 primary test interface"
echo ""
echo "📁 Archive location: ./archive/"
echo "📋 Archive index: ./archive/ARCHIVE_INDEX.md"
echo ""
echo "🎯 Repository is now clean and organized!"
echo "💡 Run 'cat archive/ARCHIVE_INDEX.md' to see what was archived"
echo "🔍 Use 'find archive/ -name \"*filename*\"' to locate specific files"
