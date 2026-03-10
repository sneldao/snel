#!/bin/bash
# Pre-commit hook to detect potential secrets before committing

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Running secrets detection..."

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${GREEN}✓ No staged files to check${NC}"
    exit 0
fi

# Secret patterns to detect
# Each pattern: name|regex
PATTERNS=(
    "AWS Access Key|AKIA[0-9A-Z]{16}"
    "AWS Secret Key|(?<![0-9a-fA-Fx])['\"]?[A-Za-z0-9/+=]{40}['\"]?(?![0-9a-fA-F])"
    "Private Key|-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----"
    "GitHub Token|gh[pousr]_[A-Za-z0-9_]{36,}"
    "Generic API Key|(api[_-]?key|apikey)\s*[=:]\s*['\"][a-zA-Z0-9_-]{20,}['\"]"
    "Password Assignment|password\s*[=:]\s*['\"][^'\"]{8,}['\"]"
    "Secret Assignment|(secret|private)_?(key|token)\s*[=:]\s*['\"][^'\"]{20,}['\"]"
    "Bearer Token|Bearer\s+[A-Za-z0-9\-\._~+/]{20,}=*"
    "Base64 Secret|['\"][A-Za-z0-9+/]{50,}={0,2}['\"]"
)

FOUND_SECRETS=0
FOUND_FILES=()

for file in $STAGED_FILES; do
    # Skip documentation files
    if [[ "$file" =~ \.(md|rst)$ ]]; then
        continue
    fi
    
    # Skip blockchain config/contract files (contain hex addresses by nature)
    if [[ "$file" =~ chains\.py$ ]] || \
       [[ "$file" =~ tokens\.py$ ]] || \
       [[ "$file" =~ starknet_service\.py$ ]] || \
       [[ "$file" =~ privacy_processor\.py$ ]] || \
       [[ "$file" =~ token_query_service\.py$ ]] || \
       [[ "$file" =~ \.cairo$ ]] || \
       [[ "$file" =~ ^contracts/ ]]; then
        continue
    fi
    
    # Skip example/env files in specific paths (not all files with "test" in name)
    if [[ "$file" =~ ^[^/]+/examples/ ]] || \
       [[ "$file" =~ ^[^/]+/example- ]] || \
       [[ "$file" =~ \.env\.example$ ]] || \
       [[ "$file" =~ ^docs/ ]]; then
        continue
    fi
    
    # Skip if file doesn't exist (might be deleted)
    if [ ! -f "$file" ]; then
        continue
    fi
    
    # Get the staged content
    CONTENT=$(git show ":$file" 2>/dev/null || echo "")
    
    if [ -z "$CONTENT" ]; then
        continue
    fi
    
    for pattern_entry in "${PATTERNS[@]}"; do
        pattern_name="${pattern_entry%%|*}"
        pattern_regex="${pattern_entry#*|}"
        
        # Check for matches (case-insensitive)
        if echo "$CONTENT" | grep -iE "$pattern_regex" > /dev/null 2>&1; then
            if [ $FOUND_SECRETS -eq 0 ]; then
                echo -e "${RED}⚠️  Potential secrets detected!${NC}"
                echo ""
            fi
            FOUND_SECRETS=1
            
            # Add to found files if not already there
            if [[ ! " ${FOUND_FILES[@]} " =~ " ${file} " ]]; then
                FOUND_FILES+=("$file")
            fi
            
            echo -e "${YELLOW}  File:${NC} $file"
            echo -e "${YELLOW}  Pattern:${NC} $pattern_name"
            
            # Show matching lines (with line numbers)
            echo "$CONTENT" | grep -inE "$pattern_regex" | head -3 | while read -r line; do
                echo -e "    ${RED}→${NC} $line"
            done
            echo ""
        fi
    done
done

if [ $FOUND_SECRETS -eq 1 ]; then
    echo -e "${RED}❌ Commit blocked: Potential secrets found${NC}"
    echo ""
    echo -e "${YELLOW}Recommendations:${NC}"
    echo "  • Use environment variables instead of hardcoding secrets"
    echo "  • Add sensitive files to .gitignore"
    echo "  • Use a secrets manager for production credentials"
    echo ""
    echo -e "${YELLOW}To bypass (NOT RECOMMENDED):${NC} git commit --no-verify"
    exit 1
fi

echo -e "${GREEN}✓ No secrets detected${NC}"
exit 0
