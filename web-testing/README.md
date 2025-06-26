# Web Testing Tools

This directory contains browser-based testing tools for the PodInsight API.

## Available Test Files

### 1. **test-podinsight-advanced.html**
- Advanced testing interface with multiple features
- Includes session management and detailed logging
- Best for comprehensive testing scenarios

### 2. **test-search-browser-enhanced.html**
- Enhanced search testing with improved UI
- Includes performance metrics and caching stats
- Good for search-specific testing

### 3. **test-podinsight-combined.html**
- Combined testing interface
- Integrates multiple test scenarios
- Useful for full system testing

### 4. **test-entities-browser.html**
- Entity search and display testing
- Tests entity extraction and relationships
- Specialized for entity-related features

### 5. **test-search-browser.html**
- Basic search testing interface
- Simple and straightforward
- Good for quick search tests

### 6. **frontend_test.html**
- Frontend integration testing
- Tests API integration from browser perspective
- Useful for frontend development

## How to Use

1. Open any HTML file in a web browser
2. The interface will connect to the production API at `https://podinsight-api.vercel.app`
3. Enter search queries and test various features
4. Check browser console for detailed debugging information

## API Endpoints Tested

- **Health Check**: `/api/health`
- **Search**: `/api/search`
- **Entity Search**: `/api/entities` (if available)

## Production Status

All test files are configured to work with the production deployment.
