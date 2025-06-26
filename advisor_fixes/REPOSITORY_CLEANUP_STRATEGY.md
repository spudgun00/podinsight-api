# 🧹 PodInsight Repository Cleanup Strategy

**Purpose**: Clean up the repository while preserving all files in organized archives
**Date**: June 26, 2025
**Status**: Ready for implementation

---

## 📋 CLEANUP OVERVIEW

### Current State
- **50+ test scripts** scattered in `/scripts`
- **Multiple documentation files** with overlapping content
- **Debug reports and logs** from development sprints
- **Temporary test files** left from debugging sessions

### Target State
- **Clean root directory** with only essential files
- **Organized archives** by category and date
- **Clear file structure** for new team members
- **Easy access** to archived files when needed

---

## 🗂️ ARCHIVE STRUCTURE

```
/archive/
├── 2025-06-development/           # By date/sprint
│   ├── scripts/                   # Test and debug scripts
│   ├── docs/                      # Development docs
│   ├── logs/                      # Debug reports
│   └── temp-files/                # Temporary test files
├── 2025-05-sprint2/
├── legacy-documentation/          # Old architecture docs
├── testing-archive/               # All test scripts
└── development-notes/             # Sprint logs and notes
```

---

## 📁 FILES TO ARCHIVE

### Scripts to Archive (Keep Core Production Scripts)

#### ✅ KEEP (Production Essential)
```
/scripts/
├── modal_web_endpoint_simple.py     # Production Modal endpoint
├── test_e2e_production.py          # E2E test suite
└── quick_vc_test.py                # Quick VC validation
```

#### 📦 ARCHIVE (Development/Debug Scripts)
```bash
# Testing scripts (50+ files)
test_*.py
*_test.py
*_debug.py
*_fix.py
*_diagnostics.py

# Examples to archive:
- test_current_status.py
- test_local_fix.py
- test_mongodb_connection.py
- test_production_diagnostics.py
- test_production_fix.py
- test_venture_capital_fixed.py
- create_mongodb_index.py
- test_modal_production.py
```

### Documentation to Archive

#### ✅ KEEP (Essential Docs)
```
/
├── README.md                                   # Main project README
├── MODAL_ARCHITECTURE_DIAGRAM.md             # Architecture overview
└── advisor_fixes/
    ├── PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md  # Single source of truth
    └── REPOSITORY_CLEANUP_STRATEGY.md         # This file
```

#### 📦 ARCHIVE (Development Docs)
```bash
# Sprint logs and debug reports
SPRINT_LOG_*.md
COMPLETE_*_DOCUMENTATION.md
FULL_SESSION_*.md
*_DEBUG_REPORT.md
*_ANALYSIS.md
*_PLAYBOOK.md

# Examples to archive:
- advisor_fixes/COMPLETE_CONTEXT_DOCUMENTATION.md
- advisor_fixes/FULL_SESSION_CONTEXT_E2E_COMPLETE.md
- SPRINT_LOG_VECTOR_SEARCH_DEBUG.md
- Various debug and analysis files
```

### Test Files to Archive

#### ✅ KEEP (Production Testing)
```
/
└── test-podinsight-advanced.html  # Primary test interface
```

#### 📦 ARCHIVE (Development Testing)
```bash
# Old/duplicate test interfaces
test-search-browser.html
test-podinsight-combined.html
test-*.html (if any others)
```

---

## 🚀 CLEANUP EXECUTION SCRIPT

### Automated Cleanup Script

```bash
#!/bin/bash
# cleanup_repository.sh
# Execute from repository root

echo "🧹 Starting PodInsight Repository Cleanup..."
echo "Creating archive structure..."

# Create archive directory structure
mkdir -p archive/2025-06-development/{scripts,docs,logs,temp-files}
mkdir -p archive/legacy-documentation
mkdir -p archive/testing-archive
mkdir -p archive/development-notes

echo "📦 Archiving scripts..."

# Archive test and debug scripts (keep production essentials)
PRODUCTION_SCRIPTS=(
    "modal_web_endpoint_simple.py"
    "test_e2e_production.py"
    "quick_vc_test.py"
)

cd scripts
for script in *.py; do
    if [[ ! " ${PRODUCTION_SCRIPTS[@]} " =~ " ${script} " ]]; then
        echo "  Archiving: scripts/$script"
        mv "$script" "../archive/2025-06-development/scripts/"
    else
        echo "  Keeping: scripts/$script (production essential)"
    fi
done
cd ..

echo "📦 Archiving documentation..."

# Archive development documentation
DOCS_TO_ARCHIVE=(
    "SPRINT_LOG_VECTOR_SEARCH_DEBUG.md"
    "advisor_fixes/COMPLETE_CONTEXT_DOCUMENTATION.md"
    "advisor_fixes/FULL_SESSION_CONTEXT_E2E_COMPLETE.md"
)

for doc in "${DOCS_TO_ARCHIVE[@]}"; do
    if [ -f "$doc" ]; then
        echo "  Archiving: $doc"
        mv "$doc" "archive/development-notes/"
    fi
done

# Archive any other debug/analysis files
find . -maxdepth 1 -name "*DEBUG*" -o -name "*ANALYSIS*" -o -name "*COMPLETE_*" | while read file; do
    if [ -f "$file" ]; then
        echo "  Archiving: $file"
        mv "$file" "archive/development-notes/"
    fi
done

echo "📦 Archiving test files..."

# Archive old test interfaces (keep the main one)
TEST_FILES_TO_ARCHIVE=(
    "test-search-browser.html"
    "test-podinsight-combined.html"
)

for test_file in "${TEST_FILES_TO_ARCHIVE[@]}"; do
    if [ -f "$test_file" ]; then
        echo "  Archiving: $test_file"
        mv "$test_file" "archive/testing-archive/"
    fi
done

echo "📝 Creating archive index..."

# Create index of what's archived
cat > archive/ARCHIVE_INDEX.md << 'EOF'
# 📦 PodInsight Archive Index

**Created**: $(date)
**Purpose**: Index of all archived files for easy reference

## Archive Structure

### 2025-06-development/
Development files from June 2025 cleanup sprint

#### scripts/
- All test and debug scripts
- Database connection tests
- Modal.com experiments
- Vector search debugging tools

#### docs/
- Sprint documentation
- Debug reports
- Development notes

### testing-archive/
- Old test interfaces
- Prototype testing tools

### development-notes/
- Sprint logs
- Complete documentation drafts
- Analysis reports

## Accessing Archived Files

```bash
# View archive contents
ls -la archive/

# Find specific file
find archive/ -name "*search*" -type f

# Restore file if needed
cp archive/path/to/file ./
```

## Production Files Kept

### Scripts
- scripts/modal_web_endpoint_simple.py
- scripts/test_e2e_production.py
- scripts/quick_vc_test.py

### Documentation
- README.md
- MODAL_ARCHITECTURE_DIAGRAM.md
- advisor_fixes/PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md

### Test Interface
- test-podinsight-advanced.html
EOF

echo "✅ Repository cleanup complete!"
echo ""
echo "📊 Summary:"
echo "  • Archived $(find archive/2025-06-development/scripts -name "*.py" | wc -l) scripts"
echo "  • Archived $(find archive/development-notes -name "*.md" | wc -l) documentation files"
echo "  • Archived $(find archive/testing-archive -name "*.html" | wc -l) test files"
echo "  • Kept 3 production scripts"
echo "  • Kept 3 essential documentation files"
echo "  • Kept 1 test interface"
echo ""
echo "📁 Archive location: ./archive/"
echo "📋 Archive index: ./archive/ARCHIVE_INDEX.md"
echo ""
echo "🎯 Repository is now clean and organized!"
```

---

## 📝 MANUAL CLEANUP STEPS

If you prefer manual control, follow these steps:

### Step 1: Create Archive Structure
```bash
mkdir -p archive/2025-06-development/{scripts,docs,logs,temp-files}
mkdir -p archive/legacy-documentation
mkdir -p archive/testing-archive
mkdir -p archive/development-notes
```

### Step 2: Archive Scripts
```bash
cd scripts

# Keep these production files:
# - modal_web_endpoint_simple.py
# - test_e2e_production.py
# - quick_vc_test.py

# Archive everything else:
mv test_*.py ../archive/2025-06-development/scripts/
mv *_test.py ../archive/2025-06-development/scripts/
mv *_debug.py ../archive/2025-06-development/scripts/
mv *_fix.py ../archive/2025-06-development/scripts/
```

### Step 3: Archive Documentation
```bash
# Archive development docs
mv SPRINT_LOG_*.md archive/development-notes/
mv advisor_fixes/COMPLETE_CONTEXT_DOCUMENTATION.md archive/development-notes/
mv advisor_fixes/FULL_SESSION_CONTEXT_E2E_COMPLETE.md archive/development-notes/

# Archive any debug reports
find . -name "*DEBUG*" -o -name "*ANALYSIS*" | xargs -I {} mv {} archive/development-notes/
```

### Step 4: Archive Test Files
```bash
# Keep test-podinsight-advanced.html
# Archive others:
mv test-search-browser.html archive/testing-archive/
mv test-podinsight-combined.html archive/testing-archive/
```

---

## 🎯 FINAL REPOSITORY STRUCTURE

After cleanup, the repository will look like:

```
podinsight-api/
├── README.md                           # Project overview
├── MODAL_ARCHITECTURE_DIAGRAM.md       # Architecture diagram
├── requirements.txt                    # Dependencies
├── vercel.json                        # Vercel config
├── .env                               # Local environment (gitignored)
├── .gitignore                         # Git exclusions
├── .pre-commit-config.yaml            # Pre-commit hooks
├── .secrets.baseline                  # Secret scanning
├── test-podinsight-advanced.html      # Test interface
│
├── api/                               # API endpoints
│   ├── topic_velocity.py              # Main FastAPI app
│   ├── search_lightweight_768d.py     # Search implementation
│   ├── mongodb_vector_search.py       # Vector search
│   ├── mongodb_search.py              # Text search fallback
│   └── diag.py                        # Diagnostics
│
├── scripts/                           # Production scripts only
│   ├── modal_web_endpoint_simple.py   # Modal endpoint
│   ├── test_e2e_production.py         # E2E tests
│   └── quick_vc_test.py               # Quick VC tests
│
├── advisor_fixes/                     # Essential documentation
│   ├── PODINSIGHT_COMPLETE_ARCHITECTURE_ENCYCLOPEDIA.md
│   └── REPOSITORY_CLEANUP_STRATEGY.md
│
└── archive/                           # All archived files
    ├── ARCHIVE_INDEX.md               # What's archived
    ├── 2025-06-development/           # June 2025 sprint files
    ├── legacy-documentation/          # Old docs
    ├── testing-archive/               # Old test files
    └── development-notes/             # Sprint logs
```

---

## 🔍 FINDING ARCHIVED FILES

### Search Commands
```bash
# Find all archived scripts containing "mongo"
find archive/ -name "*mongo*" -type f

# Find all documentation about vector search
grep -r "vector search" archive/

# List all archived test scripts
ls archive/2025-06-development/scripts/test_*.py

# Find specific file by partial name
find archive/ -name "*debug*" -type f
```

### Restore Files if Needed
```bash
# Copy file back to working directory
cp archive/2025-06-development/scripts/test_mongodb_connection.py scripts/

# Or move it back permanently
mv archive/testing-archive/test-search-browser.html ./
```

---

## ✅ BENEFITS OF THIS APPROACH

1. **Clean Repository**
   - Only essential files in main directories
   - Clear structure for new team members
   - Faster navigation and development

2. **Nothing Lost**
   - All files preserved in organized archives
   - Easy to find and restore files
   - Complete history maintained

3. **Better Organization**
   - Files grouped by purpose and date
   - Clear distinction between production and development
   - Archive index for quick reference

4. **Future-Proof**
   - Established pattern for future cleanups
   - Scalable archive structure
   - Documentation of what's where

---

## 🚀 READY TO EXECUTE

Choose your approach:

1. **Automated**: Run the cleanup script above
2. **Manual**: Follow the step-by-step process
3. **Gradual**: Do it in phases over time

Either way, you'll have a clean, organized repository with all files safely archived and easily accessible!
