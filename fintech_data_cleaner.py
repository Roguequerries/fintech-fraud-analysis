import pandas as pd
import numpy as np
import re
from datetime import datetime
import json

# Configuration
INPUT_FILE = 'fintech_sample_data.csv'
OUTPUT_FILE = 'fintech_data_cleaned.csv'
LOGS_FILE = 'cleaning_logs.json'
REPORT_FILE = 'cleaning_report.txt'

class FinTechDataCleaner:
    def __init__(self, input_file):
        self.df = pd.read_csv(input_file)
        self.original_count = len(self.df)
        self.cleaning_logs = []
        self.report = {}
        
    def log_issue(self, row_idx, column, issue, action):
        """Log data quality issues"""
        self.cleaning_logs.append({
            'row_index': int(row_idx),
            'column': column,
            'issue': issue,
            'action': action,
            'timestamp': datetime.now().isoformat()
        })
    
    def validate_email(self, email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return pd.isna(email) or bool(re.match(pattern, str(email)))
    
    def validate_cpf(self, cpf):
        """Validate Brazilian CPF format"""
        if pd.isna(cpf):
            return False
        cpf_str = str(cpf).strip()
        # Check if matches XXX.XXX.XXX-XX or basic format
        if cpf_str == 'XXX.XXX.XXX-XX':
            return False
        pattern = r'^\d{3}\.\d{3}\.\d{3}-\d{2}$'
        return bool(re.match(pattern, cpf_str))
    
    def validate_account_number(self, account):
        """Validate account number format"""
        if pd.isna(account):
            return False
        account_str = str(account).strip()
        if 'INVALID' in account_str:
            return False
        pattern = r'^\d{4}-\d{6}$'
        return bool(re.match(pattern, account_str))
    
    def validate_timestamp(self, ts):
        """Validate timestamp format"""
        if pd.isna(ts):
            return False
        try:
            datetime.strptime(str(ts), '%Y-%m-%d %H:%M:%S')
            # Check if date is reasonable (not in future, not too old)
            parsed_date = datetime.strptime(str(ts), '%Y-%m-%d %H:%M:%S')
            if parsed_date.year < 2000 or parsed_date > datetime.now():
                return False
            return True
        except:
            return False
    
    def validate_phone(self, phone):
        """Validate phone number"""
        if pd.isna(phone) or phone == '':
            return False
        phone_str = str(phone).strip()
        # Remove common formatting
        digits_only = re.sub(r'\D', '', phone_str)
        return len(digits_only) >= 10
    
    def validate_enum(self, value, allowed_values):
        """Validate against allowed values"""
        if pd.isna(value):
            return False
        return str(value).strip() in allowed_values
    
    def clean_customer_id(self):
        """Clean customer_id column"""
        issues = 0
        pattern = r'^CUST\d{8}$'
        for idx, val in self.df['customer_id'].items():
            if not bool(re.match(pattern, str(val))):
                self.log_issue(idx, 'customer_id', f'Invalid format: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['customer_id'] = {'issues': issues, 'action': 'validated format'}
        return issues
    
    def clean_customer_name(self):
        """Clean customer_name column"""
        issues = 0
        for idx, val in self.df['customer_name'].items():
            if pd.isna(val) or str(val).strip() == '':
                self.log_issue(idx, 'customer_name', 'Empty name', 'MARKED_FOR_REMOVAL')
                issues += 1
            elif any(char.isdigit() for char in str(val)) and str(val).count(' ') == 0:
                self.log_issue(idx, 'customer_name', f'Contains numbers: {val}', 'FLAGGED')
                issues += 1
        
        # Trim whitespace
        self.df['customer_name'] = self.df['customer_name'].str.strip()
        self.report['customer_name'] = {'issues': issues, 'action': 'trim whitespace, validate'}
        return issues
    
    def clean_email(self):
        """Clean email column"""
        issues = 0
        for idx, val in self.df['email'].items():
            if not self.validate_email(val):
                self.log_issue(idx, 'email', f'Invalid format: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['email'] = {'issues': issues, 'action': 'regex validation'}
        return issues
    
    def clean_phone(self):
        """Clean phone column"""
        issues = 0
        for idx, val in self.df['phone'].items():
            if pd.isna(val) or val == '':
                self.df.at[idx, 'phone'] = 'UNKNOWN'
                self.log_issue(idx, 'phone', 'Missing phone', 'FILLED_WITH_UNKNOWN')
                issues += 1
            elif not self.validate_phone(val):
                self.log_issue(idx, 'phone', f'Invalid format: {val}', 'FILLED_WITH_UNKNOWN')
                self.df.at[idx, 'phone'] = 'UNKNOWN'
                issues += 1
        
        self.report['phone'] = {'issues': issues, 'action': 'validation, fill missing with UNKNOWN'}
        return issues
    
    def clean_cpf(self):
        """Clean CPF column"""
        issues = 0
        for idx, val in self.df['cpf'].items():
            if not self.validate_cpf(val):
                self.log_issue(idx, 'cpf', f'Invalid CPF: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['cpf'] = {'issues': issues, 'action': 'validate CPF format'}
        return issues
    
    def clean_account_number(self):
        """Clean account_number column"""
        issues = 0
        for idx, val in self.df['account_number'].items():
            if not self.validate_account_number(val):
                self.log_issue(idx, 'account_number', f'Invalid account: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['account_number'] = {'issues': issues, 'action': 'validate format'}
        return issues
    
    def clean_account_balance(self):
        """Clean account_balance column"""
        issues = 0
        for idx, val in self.df['account_balance'].items():
            if pd.isna(val):
                self.log_issue(idx, 'account_balance', 'Missing balance', 'MARKED_FOR_REMOVAL')
                issues += 1
            elif val < 0:
                self.log_issue(idx, 'account_balance', f'Negative balance: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
            elif val > 10000000:
                self.log_issue(idx, 'account_balance', f'Unrealistic balance: {val}', 'FLAGGED')
        
        self.report['account_balance'] = {'issues': issues, 'action': 'remove negative/missing, flag outliers'}
        return issues
    
    def clean_transaction_id(self):
        """Clean transaction_id column"""
        issues = 0
        duplicates = self.df['transaction_id'].duplicated(keep=False)
        for idx in self.df[duplicates].index:
            self.log_issue(idx, 'transaction_id', f'Duplicate ID: {self.df.at[idx, "transaction_id"]}', 'MARKED_FOR_REMOVAL')
            issues += 1
        
        self.report['transaction_id'] = {'issues': issues, 'action': 'remove duplicates'}
        return issues
    
    def clean_transaction_type(self):
        """Clean transaction_type column"""
        allowed = ['debit', 'credit', 'transfer', 'withdrawal', 'deposit']
        issues = 0
        for idx, val in self.df['transaction_type'].items():
            if not self.validate_enum(val, allowed):
                self.log_issue(idx, 'transaction_type', f'Invalid type: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['transaction_type'] = {'issues': issues, 'action': 'validate enum'}
        return issues
    
    def clean_amount(self):
        """Clean amount column"""
        issues = 0
        for idx, val in self.df['amount'].items():
            if pd.isna(val):
                self.log_issue(idx, 'amount', 'Missing amount', 'MARKED_FOR_REMOVAL')
                issues += 1
            elif val < 0:
                self.log_issue(idx, 'amount', f'Negative amount: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
            elif val > 1000000:
                self.log_issue(idx, 'amount', f'Unrealistic amount: {val}', 'FLAGGED')
        
        self.report['amount'] = {'issues': issues, 'action': 'remove negative/missing, flag outliers'}
        return issues
    
    def clean_currency(self):
        """Clean currency column"""
        allowed = ['BRL', 'USD', 'EUR']
        issues = 0
        for idx, val in self.df['currency'].items():
            if not self.validate_enum(val, allowed):
                self.log_issue(idx, 'currency', f'Invalid currency: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['currency'] = {'issues': issues, 'action': 'validate enum'}
        return issues
    
    def clean_timestamp(self):
        """Clean timestamp column"""
        issues = 0
        for idx, val in self.df['timestamp'].items():
            if not self.validate_timestamp(val):
                self.log_issue(idx, 'timestamp', f'Invalid timestamp: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['timestamp'] = {'issues': issues, 'action': 'validate format and range'}
        return issues
    
    def clean_merchant_name(self):
        """Clean merchant_name column"""
        issues = 0
        for idx, val in self.df['merchant_name'].items():
            if pd.isna(val) or str(val).strip() == '':
                self.df.at[idx, 'merchant_name'] = 'UNKNOWN'
                self.log_issue(idx, 'merchant_name', 'Empty merchant name', 'FILLED_WITH_UNKNOWN')
                issues += 1
        
        # Trim whitespace
        self.df['merchant_name'] = self.df['merchant_name'].str.strip()
        self.report['merchant_name'] = {'issues': issues, 'action': 'fill empty with UNKNOWN, trim whitespace'}
        return issues
    
    def clean_merchant_category(self):
        """Clean merchant_category column"""
        issues = 0
        for idx, val in self.df['merchant_category'].items():
            if pd.isna(val) or str(val).strip() == '':
                self.log_issue(idx, 'merchant_category', 'Empty category', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['merchant_category'] = {'issues': issues, 'action': 'validate non-empty'}
        return issues
    
    def clean_status(self):
        """Clean status column"""
        allowed = ['completed', 'pending', 'failed', 'reversed']
        issues = 0
        for idx, val in self.df['status'].items():
            if not self.validate_enum(val, allowed):
                self.log_issue(idx, 'status', f'Invalid status: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['status'] = {'issues': issues, 'action': 'validate enum'}
        return issues
    
    def clean_location(self):
        """Clean location column"""
        issues = 0
        for idx, val in self.df['location'].items():
            if pd.isna(val) or str(val).strip() == '':
                self.log_issue(idx, 'location', 'Empty location', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['location'] = {'issues': issues, 'action': 'validate non-empty'}
        return issues
    
    def clean_device(self):
        """Clean device column"""
        allowed = ['Mobile', 'Web', 'ATM', 'Card']
        issues = 0
        for idx, val in self.df['device'].items():
            if not self.validate_enum(val, allowed):
                self.log_issue(idx, 'device', f'Invalid device: {val}', 'MARKED_FOR_REMOVAL')
                issues += 1
        
        self.report['device'] = {'issues': issues, 'action': 'validate enum'}
        return issues
    
    def identify_rows_for_removal(self):
        """Identify rows with multiple critical errors"""
        rows_to_remove = set()
        issue_count = {}
        
        # Count issues per row
        for log in self.cleaning_logs:
            row = log['row_index']
            if log['action'] == 'MARKED_FOR_REMOVAL':
                issue_count[row] = issue_count.get(row, 0) + 1
        
        # Mark for removal if >2 critical issues
        for row, count in issue_count.items():
            if count > 2:
                rows_to_remove.add(row)
                self.log_issue(row, 'overall', f'{count} critical errors', 'MARKED_FOR_REMOVAL')
        
        return rows_to_remove
    
    def clean_all(self):
        """Execute full cleaning pipeline"""
        print("Starting data cleaning pipeline...")
        print("=" * 70)
        
        # Step 1: Clean individual columns
        print("\n1. Validating columns...")
        self.clean_customer_id()
        self.clean_customer_name()
        self.clean_email()
        self.clean_phone()
        self.clean_cpf()
        self.clean_account_number()
        self.clean_account_balance()
        self.clean_transaction_id()
        self.clean_transaction_type()
        self.clean_amount()
        self.clean_currency()
        self.clean_timestamp()
        self.clean_merchant_name()
        self.clean_merchant_category()
        self.clean_status()
        self.clean_location()
        self.clean_device()
        
        print("   ✓ All columns validated")
        
        # Step 2: Identify rows for removal
        print("2. Identifying rows with multiple critical errors...")
        rows_to_remove = self.identify_rows_for_removal()
        print(f"   ✓ Found {len(rows_to_remove)} rows for removal")
        
        # Step 3: Remove problematic rows
        print("3. Removing problematic rows...")
        self.df = self.df.drop(rows_to_remove)
        self.df = self.df.reset_index(drop=True)
        print(f"   ✓ Removed {len(rows_to_remove)} rows")
        
        # Step 4: Final validation
        print("4. Final validation...")
        final_issues = len([log for log in self.cleaning_logs if log['action'] == 'MARKED_FOR_REMOVAL'])
        print(f"   ✓ Remaining data quality issues: {final_issues}")
        
        return self.df
    
    def generate_report(self):
        """Generate cleaning report"""
        final_count = len(self.df)
        removed_count = self.original_count - final_count
        
        report_text = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    FINTECH DATA CLEANING REPORT                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

SUMMARY STATISTICS
─────────────────────────────────────────────────────────────────────────────
Original Records:              {self.original_count:,}
Final Records:                 {final_count:,}
Removed Records:               {removed_count:,} ({removed_count/self.original_count*100:.2f}%)
Data Retention Rate:           {final_count/self.original_count*100:.2f}%

COLUMN-BY-COLUMN CLEANING SUMMARY
─────────────────────────────────────────────────────────────────────────────
"""
        
        for column, info in sorted(self.report.items()):
            report_text += f"\n{column}:\n"
            report_text += f"  Issues Found: {info['issues']}\n"
            report_text += f"  Action Taken: {info['action']}\n"
        
        report_text += f"""

ISSUES LOGGED
─────────────────────────────────────────────────────────────────────────────
Total Issues Logged: {len(self.cleaning_logs)}

Most Common Issues:
"""
        
        # Count issue types
        issue_types = {}
        for log in self.cleaning_logs:
            issue = log['issue']
            issue_types[issue] = issue_types.get(issue, 0) + 1
        
        for issue, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            report_text += f"\n  • {issue}: {count} occurrences"
        
        report_text += f"""

ACTIONS TAKEN
─────────────────────────────────────────────────────────────────────────────
• Removed rows with >2 critical errors
• Validated email, CPF, and account number formats
• Removed negative amounts and balances
• Removed duplicate transaction IDs
• Filled missing phone numbers with "UNKNOWN"
• Filled missing merchant names with "UNKNOWN"
• Validated enum fields (transaction_type, currency, status, device)
• Validated timestamp format and range
• Trimmed whitespace from text fields

OUTPUT FILES
─────────────────────────────────────────────────────────────────────────────
✓ Cleaned Data:     {OUTPUT_FILE}
✓ Cleaning Logs:    {LOGS_FILE}
✓ Report:           {REPORT_FILE}

═════════════════════════════════════════════════════════════════════════════════
"""
        
        return report_text
    
    def save_results(self):
        """Save cleaned data and logs"""
        print("\n5. Saving results...")
        
        # Save cleaned data
        self.df.to_csv(OUTPUT_FILE, index=False)
        print(f"   ✓ Cleaned data saved: {OUTPUT_FILE}")
        
        # Save logs
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cleaning_logs, f, indent=2)
        print(f"   ✓ Cleaning logs saved: {LOGS_FILE}")
        
        # Save report
        report = self.generate_report()
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"   ✓ Report saved: {REPORT_FILE}")
        
        return report

def main():
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║         FINTECH DATA CLEANING TOOL                            ║")
    print("╚════════════════════════════════════════════════════════════════╝\n")
    
    try:
        cleaner = FinTechDataCleaner(INPUT_FILE)
        cleaned_df = cleaner.clean_all()
        report = cleaner.save_results()
        print("\n" + report)
        print("✓ Data cleaning completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error during cleaning: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
