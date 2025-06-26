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
mkdir -p archive/2025-06-development/scripts
mkdir -p archive/2025-06-development/docs
mkdir -p archive/development-notes
mkdir -p archive/testing-archive

echo "📦 Archiving scripts (keeping production essentials)..."

# Production scripts to keep
echo "  ✅ Keeping production scripts:"
echo "    - modal_web_endpoint_simple.py"
echo "    - test_e2e_production.py"
echo "    - quick_vc_test.py"

# Count and archive scripts
ARCHIVED_SCRIPTS=0
cd scripts

# Archive all scripts except production ones
for script in *.py; do
    if [ -f "$script" ]; then
        if [ "$script" != "modal_web_endpoint_simple.py" ] && \
           [ "$script" != "test_e2e_production.py" ] && \
           [ "$script" != "quick_vc_test.py" ]; then
            echo "    📦 Archiving: scripts/$script"
            mv "$script" "../archive/2025-06-development/scripts/"
            ARCHIVED_SCRIPTS=$((ARCHIVED_SCRIPTS + 1))
        fi
    fi
done

cd ..

echo "  📊 Archived $ARCHIVED_SCRIPTS scripts"
echo ""

echo "📦 Archiving documentation..."

# Archive specific documentation files
if [ -f "SPRINT_LOG_VECTOR_SEARCH_DEBUG.md" ]; then
    echo "    📦 Archiving: SPRINT_LOG_VECTOR_SEARCH_DEBUG.md"
    mv "SPRINT_LOG_VECTOR_SEARCH_DEBUG.md" "archive/development-notes/"
fi

if [ -f "advisor_fixes/COMPLETE_CONTEXT_DOCUMENTATION.md" ]; then
    echo "    📦 Archiving: advisor_fixes/COMPLETE_CONTEXT_DOCUMENTATION.md"
    mv "advisor_fixes/COMPLETE_CONTEXT_DOCUMENTATION.md" "archive/development-notes/"
fi

if [ -f "advisor_fixes/FULL_SESSION_CONTEXT_E2E_COMPLETE.md" ]; then
    echo "    📦 Archiving: advisor_fixes/FULL_SESSION_CONTEXT_E2E_COMPLETE.md"
    mv "advisor_fixes/FULL_SESSION_CONTEXT_E2E_COMPLETE.md" "archive/development-notes/"
fi

# Archive debug and analysis files
for pattern in "*DEBUG*" "*ANALYSIS*" "*COMPLETE_*" "*PLAYBOOK*" "SPRINT_LOG*"; do
    for file in $pattern; do
        if [ -f "$file" ]; then
            echo "    📦 Archiving: $file"
            mv "$file" "archive/development-notes/"
        fi
    done
done

echo "  📊 Archived development documentation"
echo ""

echo "📦 Archiving test files..."

ARCHIVED_TESTS=0

# Archive old test interfaces (keep the main one)
if [ -f "test-search-browser.html" ]; then
    echo "    📦 Archiving: test-search-browser.html"
    mv "test-search-browser.html" "archive/testing-archive/"
    ARCHIVED_TESTS=$((ARCHIVED_TESTS + 1))
fi

if [ -f "test-podinsight-combined.html" ]; then
    echo "    📦 Archiving: test-podinsight-combined.html"
    mv "test-podinsight-combined.html" "archive/testing-archive/"
    ARCHIVED_TESTS=$((ARCHIVED_TESTS + 1))
fi

if [ -f "test-search-browser-enhanced.html" ]; then
    echo "    📦 Archiving: test-search-browser-enhanced.html"
    mv "test-search-browser-enhanced.html" "archive/testing-archive/"
    ARCHIVED_TESTS=$((ARCHIVED_TESTS + 1))
fi

if [ -f "test-entities-browser.html" ]; then
    echo "    📦 Archiving: test-entities-browser.html"
    mv "test-entities-browser.html" "archive/testing-archive/"
    ARCHIVED_TESTS=$((ARCHIVED_TESTS + 1))
fi

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

## 📁 Archive Contents

### archive/2025-06-development/scripts/
Development and test scripts:
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
echo "  ✅ Kept essential documentation files"
echo "  ✅ Kept 1 primary test interface"
echo ""
echo "📁 Archive location: ./archive/"
echo "📋 Archive index: ./archive/ARCHIVE_INDEX.md"
echo ""
echo "🎯 Repository is now clean and organized!"
echo "💡 Run 'cat archive/ARCHIVE_INDEX.md' to see what was archived"
echo "🔍 Use 'find archive/ -name \"*filename*\"' to locate specific files"
