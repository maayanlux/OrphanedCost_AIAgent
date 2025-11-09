# Secret Scanning Setup

This repository includes comprehensive secret scanning to prevent accidental exposure of sensitive information.

## 🔒 Automated Secret Scanning

### GitHub Actions Workflow
The `.github/workflows/secret-scan.yml` workflow automatically runs on:
- Every push to main/master/develop branches
- Every pull request
- Daily at 2 AM UTC (scheduled scan)

### Tools Used
1. **TruffleHog OSS** - Detects secrets in git history
2. **GitLeaks** - Fast git secret scanner
3. **Semgrep** - Static analysis for security issues
4. **detect-secrets** - Baseline-driven secret detection
5. **secretlint** - Pluggable secret linting
6. **Custom Pattern Matching** - Repository-specific patterns
7. **Entropy Analysis** - Detects high-entropy strings

## 🛠️ Local Development Setup

### Install Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Manual Secret Scanning
```bash
# Run TruffleHog
trufflehog git file://. --only-verified

# Run GitLeaks
gitleaks detect --source . -v

# Run detect-secrets
detect-secrets scan --all-files --baseline .secrets.baseline

# Run secretlint
npx @secretlint/cli "**/*"
```

## ⚙️ Configuration Files

- `.gitleaks.toml` - GitLeaks configuration with custom rules
- `.pre-commit-config.yaml` - Pre-commit hooks setup
- `.secrets.baseline` - detect-secrets baseline
- `.secretlintrc.json` - secretlint configuration

## 🚨 What Gets Detected

### Common Secrets
- AWS Access Keys (`AKIA...`)
- Azure Storage Keys
- Azure Connection Strings
- GitHub Personal Access Tokens (`ghp_...`)
- OpenAI API Keys (`sk-...`)
- JWT Tokens
- Generic passwords and API keys
- Private keys (RSA, SSH, etc.)
- Database connection strings

### High-Entropy Strings
- Base64 encoded secrets
- Hex-encoded keys
- Random alphanumeric strings (potential tokens)

## 🔧 Handling False Positives

### GitLeaks Allowlist
Edit `.gitleaks.toml` to add patterns to ignore:
```toml
[allowlist]
regexes = [
    '''example\.com''',
    '''placeholder''',
    '''your-pattern-here'''
]
```

### detect-secrets Baseline
Update the baseline when legitimate secrets are detected:
```bash
detect-secrets scan --update .secrets.baseline
```

### secretlint Ignore
Add to `.secretlintrc.json`:
```json
{
  "allowMessageIds": ["pattern-to-ignore"]
}
```

## 🛡️ Best Practices

### ✅ Do
- Use environment variables for secrets
- Store secrets in Azure Key Vault, AWS Secrets Manager, etc.
- Use GitHub repository secrets for CI/CD
- Rotate secrets regularly
- Use least-privilege access

### ❌ Don't
- Commit secrets to version control
- Share secrets in plain text
- Use secrets in URLs or logs
- Store secrets in configuration files
- Use weak or default passwords

## 🚑 If Secrets Are Detected

1. **Stop immediately** - Don't push the commit
2. **Remove the secret** from your code
3. **Rewrite git history** if already committed:
   ```bash
   # For the last commit
   git reset --soft HEAD~1
   
   # For older commits, use interactive rebase
   git rebase -i HEAD~n
   ```
4. **Rotate the secret** immediately
5. **Update the baseline** if it's a false positive

## 📊 Security Report

Each scan generates a security report available in the GitHub Actions artifacts. The report includes:
- Scan summary and timestamp
- Tools used and their results
- Recommendations for remediation
- Links to detailed findings

## 🔄 Integration with Branch Protection

The workflow includes a required status check that:
- Blocks PR merges if secrets are detected
- Provides clear feedback on failures
- Links to detailed scan results

## 📝 Customization

### Adding Custom Patterns
Edit the "Custom Secret Patterns Check" step in the workflow:
```bash
SECRET_PATTERNS+=(
  "your-custom-pattern-here"
)
```

### Adjusting Entropy Threshold
Modify the entropy calculation threshold in the workflow (default: 4.5):
```python
if calculate_entropy(string) > 5.0:  # Stricter threshold
```

### Adding New File Types
Update the extensions list for entropy scanning:
```python
extensions = ['.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.config', '.your-ext']
```

## 🆘 Support

If you encounter issues with the secret scanning:
1. Check the GitHub Actions logs for detailed error messages
2. Verify your configuration files are valid
3. Test locally with the pre-commit hooks
4. Review the allowlists for false positives

## 🔗 Resources

- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)
- [GitLeaks Documentation](https://github.com/zricethezav/gitleaks)
- [detect-secrets Documentation](https://github.com/Yelp/detect-secrets)
- [secretlint Documentation](https://github.com/secretlint/secretlint)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)